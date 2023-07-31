#!/usr/bin/python3

#################################################################################
# Software Name : LatSeq
# Version: 1.0
# SPDX-FileCopyrightText: Copyright (c) 2020-2021 Orange Labs
# SPDX-License-Identifier: BSD-3-Clause
#
# This software is distributed under the BSD 3-clause,
# the text of which is available at https://opensource.org/licenses/BSD-3-Clause
# or see the "license.txt" file for more details.
#
# Author: Flavien Ronteix--Jacquet
# Software description: LatSeq rebuild journeys script
#################################################################################

"""Process latseq logs module

This modules is used to process latseq logs and provides
some useful statistics and stats

Example:
    python3 tools/latseq_logs.py -l data/latseq.simple.lseq

Attributes:
    none

TODO
    * Retransmissions
    * find ALL in and out points (dynamically). Should I do ?
    * APIify with flask to be called easily by the others modules
        https://programminghistorian.org/en/lessons/creating-apis-with-python-and-flask#creating-a-basic-flask-application
    * Rebuild_packet with multithreading...
    * Uniformize output to julia processing
    * Alex Algorithm container

"""

import sys
import os
import argparse
import re
import datetime
import operator
import statistics
import numpy
from copy import deepcopy
import pickle
import simplejson as json
import decimal
from tqdm import tqdm
import concurrent.futures
import multiprocessing
from itertools import cycle
import copy
import logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    stream=sys.stderr
)
# import math
import rdtsctots

#
# GLOBALS
#

# Reducing search space
# 4ms treshold to seek the next trace
DURATION_TO_SEARCH_PKT = decimal.Decimal(0.1) # TODO NOT USED AT THE MOMENT
# 4ms treshold to find segmentation
DURATION_TO_SEARCH_FORKS = decimal.Decimal(0.1) # TODO NOT USED AT THE MOMENT
# TODO: limit time to search concatenation: or use the properties like size ?
# DURATION_TO_SEARCH_CONCA = 0.005  # 5ms to find concatenation
DURATION_TO_SEARCH_RETX = decimal.Decimal(0.01) # TODO NOT USED AT THE MOMENT   10ms : Set according to drx-RetransmissionTimerDL RRC config (3GPP-TS38.321) for MAC and max_seq_num for RLC (3GPP-TS38.322)

# decimal.getcontext().prec = 6  # fix precision to 6 (precision of timestamp, then do not be more precise). BE CAREFUL : precision is different to fix place after point

S_TO_MS = 1000
KWS_BUFFER = []  # buffer keywords, TODO NOT USED AT THE MOMENT
KWS_NO_CONCATENATION = ['pdcp.in']  # TODO NOT USED AT THE MOMENT
KWS_NO_SEGMENTATION = [] # full name of all points where segmentation can't happen; the user has to know if segmentation can happen; this improves perfomance as unnecessary search is avoided
KWS_IN_D = ['ip.in']  # TODO : put in conf file and verify why when add 'ip' it breaks rebuild
KWS_OUT_D = ['phy.out.proc']
KWS_IN_U = ['phy.start']
KWS_OUT_U = ['gtp.out', 'pdcp.discarded.rcvdsmallerdeliv', 'pdcp.discarded.badpdusize', 'pdcp.discarded.integrityfailed', 'macdrop']
VERBOSITY = False  # Verbosity for rebuild phase False by default; only shows progress bar when MULTIPROCESSING is False
MULTIPROCESSING = True
#
# UTILS
#


def epoch_to_datetime(epoch: decimal.Decimal) -> str:
    """Convert an epoch to datetime"""
    return datetime.datetime.fromtimestamp(
        float(epoch)).strftime('%Y%m%d_%H%M%S.%f')


def dstamp_to_epoch(dstamptime: str) -> decimal.Decimal:
    """Convert a dstamptime to float epoch"""
    return decimal.Decimal(datetime.datetime.strptime(
        dstamptime, "%Y%m%d_%H%M%S.%f"
    ).timestamp())


def path_to_str(pathP: list) -> str:
    """Use to get a string representing a path from a list"""
    if len(pathP) < 1:
        return ""
    if len(pathP) < 2:
        return pathP[0]
    res = f"{pathP[0]} -> "
    for i in range(1, len(pathP) - 1):
        res += f"{pathP[i]} -> "
    return res + f"{pathP[-1]}"

def dict_ids_to_str(idsP: dict) -> str:
    return '.'.join([f"{k}{v}" for k,v in idsP.items()])

def make_immutable_list(listP: list) -> tuple:
    return tuple(listP)

def write_string_to_stdout(sstream: str):
    try:
        sys.stdout.write(sstream + '\n')
    except IOError as e:
        if e.errno == errno.EPIPE:  # Ignore broken pipe Error
            logging.warning("write_string_to_stdout() : Broken pipe error")
            return
        else:
            logging.error(f"write_string_to_stdout() : {e}")
            exit()

#
# CLASSES
#
class latseq_log:
    """class for log processing associated to a log file

    Args:

        logpathP (str): path to the log file

    Attributes:

        logpath (str): path to the log file
        initialized (bool): become true when __init__ is successfully done
        raw_inputs (:obj:`list` of :obj:`str`): list of lines from logpath file
        raw_infos (:obj:`list` of :obj:`str`): list of lines from logpath
        inputs (:obj:`list` of :obj:`list`): list of lines after a first pass
            of processing from raw_inputs
                inputs[i][0] : Timestamp
                inputs[i][1] : Direction
                inputs[i][2] : Src point
                inputs[i][3] : Dst point
                inputs[i][4] : Properties
                inputs[i][5] : Global identifiers
                inputs[i][6] : Local identifiers
        infos (:obj:`list` of :obj:`list`): list of information lines
                infos[i][0] : Timestamp
                infos[i][1] : Point
                infos[i][2] : Properties
                infos[i][3] : Context identifiers
        dataids (:obj:`list` of :obj:`str`): list of dataids found in the logs
        points (:obj:`dict` of :obj:`list`): list of points
            points[i] (:obj:`dict`): a point
                points[i]['dir'] (:obj:`list` of int): list of direction where this point can be found
                points[i]['count'] (int): number of occurences of this point on `inputs`
                points[i]['next'] (:obj:`list` of str): list of possible next points
                points[i]['duration'] (:obj:`list` of float): list of duration for this point in the `journey`. WARNING: Computed at a rebuild journey function... not in build_points
        pointsInD (:obj:`list` of str): list of input points for Downlink
        pointsInU (:obj:`list` of str): list of input points for Uplink
        pointsOutD (:obj:`list` of str): list of output points for Downlink
        pointsOutU (:obj:`list` of str): list of output points for Uplink
        paths (:obj:`list` of :obj:`list`):
            list[0] is a list of all DownLink paths possibles
                list[0][i] : ordered list of points' name
            list[1] is a list of all UpLink paths possibles
        timestamps (:obj:`list` of float): list of timestamps in the logs
        journeys (:obj:`dict`): the dictionnary containing journeys
            journeys[i] (:obj:`dict`): a journey
                journeys[i]['dir'] (int): 0 if a Downlink journey, 1 otherwise
                journeys[i]['glob'] (:obj:`dict`): the globals context ids to match necessary
                journeys[i]['completed'] (bool): True if the journey is compete, e.g. journey from an in to an out point
                journeys[i]['ts_in'] (float): timestamp at which the journey begins
                journeys[i]['ts_out'] (float): timestamp at which the journey ends if `completed`
                journeys[i]['next_points'] (:obj:`list`): the next points' identifier expected
                journeys[i]['set']inputs: list (:obj:`list` of :obj:`tuple`): list of measures 
                    journeys[i]['set'][s][0] (int): corresponding id in `input`
                    journeys[i]['set'][s][1] (float): timestamp
                    journeys[i]['set'][s][2] (string): segment
                journeys[i]['set_ids'] (:obj:`list`): the last measurement point identifier added
                journeys[i]['path'] (int): the path id according to self.paths
        out_journeys (:obj:`list`): the list of measurements like `raw_inputs` but ordered, filtered and with unique identifier (uid) by journey
            out_journeys[o] : a log line of out_journeys = a log line from input (if input is present in a journey)
                out_journeys[o][0] (Decimal): timestamp
                out_journeys[o][1] (char): direction, U/D
                out_journeys[o][2] (str): segment
                out_journeys[o][3] (str): properties
                out_journeys[o][4] (str): data identifier with journey id(s) associated to this measurement
    """
    def __init__(self, logpathP: str):
        self.logpath = logpathP
        self.initialized = False
        # Open and Read the logpath file
        if not self.logpath:
            raise AssertionError("Error, no logpath provided")
        try:
            self.raw_inputs = list()
            self.raw_infos = list()
            self._read_log()
        except FileNotFoundError:
            raise FileNotFoundError(f"Error, {logpathP} not found")
        except IOError:
            raise IOError(f"Error at Reading {logpathP}")
        else:
            # Filter raw_inputs to fill inputs
            try:
                self.inputs = list()
                self.infos = list()
                self.dataids = list()
                self._clean_log()
            except Exception:
                raise ValueError(f"Error in Cleaning or Filtering {logpathP}")
        # Build points
        try:
            self.points = dict()  # the couple (key, "next") is basically a graph
            self.pointsInD = KWS_IN_D
            self.pointsOutD = KWS_OUT_D
            self.pointsInU = KWS_IN_U
            self.pointsOutU = KWS_OUT_U
            self._build_points()
        except Exception:
            raise Exception("Error at getting points")
        else:
            # Build paths
            try:
                self.paths = [[], []]
                self._build_paths()
            except Exception as e:
                raise e
        # Build timestamps
        self.timestamps = list()
        self._build_timestamp()
        # Returns
        self.initialized = True
        return

    def _read_file(self):
        """Read the content of the file pointed by `logpath`

        Returns:
            str: the content of the log file

        Raises:
            IOError: error at opening the log file
        """
        try:
            with open(self.logpath, 'r') as f:
                logging.info(f"latseq_log._read_file() : Reading {self.logpath} ...")
                return f.read()
        except IOError:
            raise IOError(f"error at opening ({self.logpath})")

    def _read_log(self):
        """Read log file `logpath` to fill up `raw_inputs` with cleaned string entries

        Filters : comments, empty lines and malformed lines
        """
        for l in self._read_file().splitlines():
            if not l:  # line is not empty
                continue
            # Match pattern
            # https://www.tutorialspoint.com/python/python_reg_expressions.htm
            if re.match(r'#.*$', l, re.M):
                continue
            tmp = l.split(' ')
            if len(tmp) < 4:
                logging.warning(f"latseq_log._read_log() : {l} is a malformed line")
                continue
            if tmp[1] == 'S':  # synchronisation-type line
                continue
            if tmp[1] == 'I':  # information-type line
                self.raw_infos.append(tuple([
                    decimal.Decimal(tmp[0]),
                    tmp[2],
                    tmp[3]
                ]))
                continue
            # TODO : rendre dynamique cette valeur avec
            # le format donne par le header
            self.raw_inputs.append(tuple([
                decimal.Decimal(tmp[0]),
                0 if tmp[1] == 'D' else 1,
                tmp[2],
                tmp[3]]))

    def _clean_log(self):
        """Clean logs from `raw_inputs` to `inputs`

        Extract ids and values from pattern id123, 'id': 123
        Transform the string entry in tuple entry
        At the end, `input` is made immutable for the rest of the program

        Filters :
            rnti65535

        Attributes:
            inputs (:obj:`list` of :obj:`tuple`) : list of log elements
                inputs[i][0] : Timestamp
                inputs[i][1] : Direction
                inputs[i][2] : Src point
                inputs[i][3] : Dst point
                inputs[i][4] : Properties
                inputs[i][5] : Global identifiers
                inputs[i][6] : Local identifiers
            infos (:obj:`list` of :obj:`list`): list of information lines
                infos[i][0] : Timestamp
                infos[i][1] : Point
                infos[i][2] : Properties
                infos[i][3] : Context identifiers
        Raises:
            ValueError : Error at parsing a line
        """
        # patterns dataidO to detect
        match_ids = re.compile("([a-zA-Z]+)([0-9]+)")

        # First process informations
        self.raw_infos.sort(key=operator.itemgetter(1, 0))  # sort by point followed timestamp
        for i in self.raw_infos:
            # process infomation line
            try:
                i_points = tuple(i[1].split('.'))
                tmp_infos_d = dict()
                meas_ctxt = i[2].split(':')  # Left part represents properties, right parts optional local identifier
                for d in meas_ctxt[0].split('.'):
                    try:
                        did = match_ids.match(d).groups()
                    except Exception:
                        continue
                    else:
                        tmp_infos_d[did[0]] = did[1]
                if len(meas_ctxt) == 2:  # measurement context identifier
                    tmp_ctxt_d = dict()
                    for c in meas_ctxt[1].split('.'):
                        try:
                            dic = match_ids.match(d).groups()
                        except Exception:
                            continue
                        else:
                            tmp_ctxt_d[dic[0]] = dic[1]
                    # TODO : A problem here, tmp_infos_d == tmp_ctxt_d at yielding
                    self.infos.append((
                        i[0],
                        i_points,
                        deepcopy(tmp_infos_d),
                        deepcopy(tmp_ctxt_d),
                    ))
                else:
                    self.infos.append((
                        i[0],
                        i_points,
                        deepcopy(tmp_infos_d),
                    ))
                # not other processing needed for infos
            except Exception:
                logging.error(f"latseq_log._clean_log() : at parsing information line {i}")

        # sort by timestamp. important assumption for the next methods
        self.raw_inputs.sort(key=operator.itemgetter(0))

        # match_emptyrnti = re.compile("rnti65535")
        for e in self.raw_inputs:
            # an entry is a timestamp, a direction,
            # an in point an out point, a size,
            # a list of glibal context data id and local data id

            # skip lines which matches the following re
            if re.search("rnti65535", e[3]):
                continue

            # process line
            try:
                e_points = e[2].split('--')
                dataids = e[3].split(':')
                if len(dataids) < 3:
                    continue
                ptmp = {}
                # properties values
                if dataids[0] != '':
                    for p in dataids[0].split('.'):
                        try:
                            dip = match_ids.match(p).groups()
                        except Exception:
                            continue
                        else:
                            ptmp[dip[0]] = dip[1]
                # global context ids
                ctmp = {}
                if dataids[1] != '':
                    for c in dataids[1].split('.'):
                        try:
                            # dic[0] is the global context identifier
                            # dic[1] the value associated
                            dic = match_ids.match(c).groups()
                        except Exception:
                            continue
                        else:
                            ctmp[dic[0]] = dic[1]
                            if dic[0] not in self.dataids:
                                self.dataids.append(dic[0])
                dtmp = {}
                # local context ids
                if dataids[2] != '':
                    for d in dataids[2].split('.'):
                        try:
                            # did[0] is the local context identifier
                            # did[1] the value associated
                            did = match_ids.match(d).groups()
                        except Exception:
                            continue
                        else:
                            if did[0] not in dtmp:
                                dtmp[did[0]] = did[1]
                            else:  # case we have multiple value for the same id
                                if isinstance(dtmp[did[0]], list):
                                    dtmp[did[0]].append(did[1])
                                else:
                                    tmpl = [dtmp[did[0]], did[1]]
                                    del dtmp[did[0]]
                                    dtmp[did[0]] = tmpl
                            if did[0] not in self.dataids:
                                self.dataids.append(did[0])

                self.inputs.append((
                        e[0],
                        e[1],
                        e_points[0],
                        e_points[1],
                        deepcopy(ptmp),
                        deepcopy(ctmp),
                        deepcopy(dtmp)
                    ))
            except Exception:
                raise ValueError(f"Error at parsing line {e}")
        self.inputs = make_immutable_list(self.inputs)

    def _build_points(self):
        """Build graph of measurement `points` and find in and out points

        Attributes:
            points (:obj:`dict`):
                points['point']['next'] (:obj:`list` of str): list of next point possible
                points['point']['count'] (int): number of occurence of this point
                points['point']['dir'] (list): could be 0, 1 or 0 and 1
        """
        # Build graph
        for e in self.raw_inputs:
            e_points = e[2].split('--')  # [0] is src point and [1] is dest point
            if e_points[0] not in self.points:
                # list of pointers and direction 0 for D and 1 for U
                self.points[e_points[0]] = {}
                self.points[e_points[0]]['next'] = []
                self.points[e_points[0]]['count'] = 0
                self.points[e_points[0]]['dir'] = [e[1]]
            if e_points[1] not in self.points[e_points[0]]['next']:
                # Get combinations of dest point
                # ex. rlc.seg.um : rlc, rlc.seg, rlc.seg.um
                destpt = e_points[1].split('.')
                for i in range(len(destpt)):
                    tmps = ""
                    j = 0
                    while j <= i:
                        tmps += f"{destpt[j]}."
                        j += 1
                    self.points[e_points[0]]['next'].append(tmps[:-1])
            if e_points[1] not in self.points:
                self.points[e_points[1]] = {}
                self.points[e_points[1]]['next'] = []
                self.points[e_points[1]]['count'] = 1
                self.points[e_points[1]]['dir'] = [e[1]]
            self.points[e_points[0]]['count'] += 1
            if e[1] not in self.points[e_points[0]]['dir']:
                self.points[e_points[0]]['dir'].append(e[1])
        
        # The IN and OUT are not fixed in the __init__ before calling this method
        if not hasattr(self, 'pointsInD') or not hasattr(self, 'pointsInU') or not hasattr(self, 'pointsOutD') or not hasattr(self, 'pointsOutU'):
            # Find IN et OUT points dynamically
            tmpD = [x[0] for x,y in self.points if y[1]==0]
            tmpDin = tmpD
            tmpDout = []
            tmpU = [x[0] for x in self.points if x[1]==1]
            tmpUin = tmpU
            tmpUout = []
            for p in self.points:
                # case D
                if p[1] == 0:
                    # if not pointed by anyone, then, it is the input
                    for e in p[0]:
                        tmpDin.remove(e)
                    # if pointed but not in keys, it is the output
                        if e not in tmpD:
                            tmpDout.append(e)
                elif p[1] == 1:
                    # if not pointed by anyone, then, it is the input
                    for e in p[0]:
                        tmpUin.remove(e)
                    # if pointed but not in keys, it is the output
                        if e not in tmpU:
                            tmpUout.append(e)
                else:
                    logging.error(f"latseq_log._build_points() : Unknown direction for {p[0]} : {p[1]}")
            self.pointsInD  = tmpDin
            self.pointsOutD = tmpDout
            self.pointsInU  = tmpUin
            self.pointsOutU = tmpUout

    def _build_paths(self):
        """Build all possible `paths` in the graph `points`

        BFS is used as algorithm to build all paths possible between an IN and OUT point
        """
        def _find_all_paths(graphP: dict, startP: str, endP: str, pathP=[]):
            tmppath = pathP + [startP]
            if startP == endP:
                return [tmppath]
            if startP not in graphP:
                return []
            paths = []
            for p in graphP[startP]['next']:
                if p not in tmppath:
                    newpaths = _find_all_paths(graphP, p, endP, tmppath)
                    for newpath in newpaths:
                        paths.append(newpath)
            return paths
        # build downlink paths
        for i in self.pointsInD:
            for o in self.pointsOutD:
                self.paths[0].extend(_find_all_paths(self.points, i, o))
        for i in self.pointsInU:
            for o in self.pointsOutU:
                self.paths[1].extend(_find_all_paths(self.points, i, o))
        if len(self.paths[0]) == 0 and len(self.paths[1]) == 0:
            raise Exception("Error no paths found in Downlink nor in Uplink")
        elif len(self.paths[0]) == 0:
            logging.info("latseq_log._build_paths() : no path found in Downlink")
        elif len(self.paths[1]) == 0:
            logging.info("latseq_log._build_paths() : no path found in Uplink")
        else:  # make immutable paths
            for dp in range(len(self.paths)):
                for p in range(len(self.paths[dp])):
                    self.paths[dp][p] = make_immutable_list(self.paths[dp][p])

    def _build_timestamp(self):
        """Build `timestamps` a :obj:`list` of Decimal of timestamp
        """
        self.timestamps = list(map(lambda x: x[0], self.raw_inputs))

    class RebuildJourneys:
        def __init__(self, use_multiprocessing, inputs, logpath):
            self.logpath = logpath
            self.use_multiprocessing = use_multiprocessing
            self.inputs = inputs
            self.input_DL_dict, self.input_UL_dict, self.startpoint_list = self._init_DL_UL_dicts_and_startpoint_lst()
            self.indexes_lst = list(range(len(self.startpoint_list)))

        def rebuild_journeys(self):
            if self.use_multiprocessing:
                results = self._rebuild_multiprocess()
                return self._flatten_list_of_lists(results)
            else:
                results = self._rebuild_singleprocess()
                return self._flatten_list_of_lists(results)
        
        def _rebuild_singleprocess(self):
            results = []
            if VERBOSITY:
                with tqdm(total=len(self.startpoint_list),file=sys.stderr) as pbar:
                    for startpoint in self.startpoint_list:
                        results.append(self._rebuild_from_startingpoint(startpoint))
                        pbar.update(1)
            else:
                for startpoint in self.startpoint_list:
                    results.append(self._rebuild_from_startingpoint(startpoint))
            return results
            
        def _rebuild_multiprocess(self):
            pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
            results = pool.map(self._rebuild_from_startingpoint, self.startpoint_list)
            pool.close()
            pool.join()
            return results
        
        def _init_DL_UL_dicts_and_startpoint_lst(self):
            #  create a List of dictionaries for all start points
            input_startpoint_list = []
        
            # create two dictionaries (one for Uplink, one for Downlink) for all non-starting points, distinguished between Uplink and Downlink
            input_DL_dict = dict()
            input_UL_dict = dict()
            
            # iterate over all inputs and fill the starting point list and the non-starting point dictionaries
            for input in self.inputs:
                if input[2] in KWS_IN_U or input[2] in KWS_IN_D:
                    input_startpoint_list.append(input)
                    continue # jump to next input

                is_UL = input[1] # input[1] == 0 -> Downlink; input[1] == 1 -> Uplink
                if is_UL:
                    if input[2] in input_UL_dict:
                        input_UL_dict[input[2]].append(input)
                    else:
                        input_UL_dict[input[2]] = []
                        input_UL_dict[input[2]].append(input)
                else:
                    if input[2] in input_DL_dict:
                        input_DL_dict[input[2]].append(input)
                    else:
                        input_DL_dict[input[2]] = []
                        input_DL_dict[input[2]].append(input)
            return input_DL_dict, input_UL_dict, input_startpoint_list

        def _match_ids(self, point: dict, journey: dict):
            match_ids = dict()
            logging_ids = dict()
            current_local_ids = journey['set_ids']
            next_local_ids = point[6]
            for key in next_local_ids.keys():
                if key in current_local_ids:
                    if current_local_ids[key] == next_local_ids[key]:
                        match_ids[key] = current_local_ids[key]
                    else:
                        return False, {}, {} # matching failed, return False and empty dicts
                else:
                    logging_ids[key] = next_local_ids[key]
            return True, match_ids, logging_ids # matching successfull, return True and dictionary of neighbouring identifiers (match_ids) and identifiers only in local point (logging_ids)

        def _new_journey(self, startpoint: dict):
            journey = dict()
            journey['completed'] = False
            journey['no_next_point'] = False
            journey['next_point'] = startpoint[3]
            journey['dir'] = startpoint[1]
            journey['glob'] = startpoint[5]
            journey['file'] = self.logpath
            journey['set'] = list()
            journey['set'].append((self.inputs.index(startpoint), startpoint[0], f"{startpoint[2]}--{startpoint[3]}"))
            journey['set_ids'] = dict()
            journey['set_ids'].update(startpoint[6])
            journey['ts_in'] = startpoint[0]
            journey['path'] = 0
            return journey

        def _add_point_to_journey(self, point: dict, journey:dict):
            _, match_ids, logging_ids = self._match_ids(point, journey)
            journey['set'].append((self.inputs.index(point), point[0], f"{point[2]}--{point[3]}"))
            journey['set_ids'].update(match_ids)
            journey['set_ids'].update(logging_ids)
            journey['next_point'] = point[3]
            is_UL = point[1]
            if is_UL and point[3] in KWS_OUT_U:
                journey['completed'] = True
                journey['ts_out'] = point[0]
            elif not is_UL and point[3] in KWS_OUT_D:
                journey['completed'] = True
                journey['ts_out'] = point[0]
            return journey

        def _get_all_next_points(self, journey: dict, input_point_list: list):
            result_point_list = []
            for point in input_point_list:
                match, _, _ = self._match_ids(point, journey)
                if match:
                    result_point_list.append(point)
                    if point in KWS_NO_SEGMENTATION:
                        break
            return result_point_list

        def _are_all_journeys_finished(self, journeys: list):
            all_completed_or_no_next_point = True
            for journey in journeys:
                if not journey['completed'] and not journey['no_next_point']:
                    all_completed_or_no_next_point = False
                    break
            return all_completed_or_no_next_point


        def _rebuild_from_startingpoint(self, startpoint: dict):
            is_UL = startpoint[1]
            if is_UL:
                input_dict = self.input_UL_dict
            else:
                input_dict = self.input_DL_dict
            journeys = []
            journeys.append(self._new_journey(startpoint))
            all_finished = False
            while not all_finished:
                len_journeys = len(journeys)
                for index in range(0, len_journeys):
                    journey = journeys[index]
                    if journey['completed'] or journey['no_next_point']:
                        continue # jump over all journeys, which are already completed or have no next point

                    input_point_list = input_dict[journey['next_point']]
                    all_next_points = self._get_all_next_points(journey, input_point_list)
                    if not all_next_points:
                        journey['no_next_point'] = True
                        continue

                    journey_copied = copy.deepcopy(journey)
                    for i, point in enumerate(all_next_points):
                        if i == 0:
                            journey = self._add_point_to_journey(point, journey)
                        else:
                            journeys.append(self._add_point_to_journey(point, journey_copied))

                all_finished = self._are_all_journeys_finished(journeys)
            return journeys
        
        def _flatten_list_of_lists(self, lst_of_lsts: list):
                journeys_dict = dict()
                uid = 0
                for list_from_startpoint in lst_of_lsts:
                    for journey in list_from_startpoint:
                        journey['uid'] = uid
                        journeys_dict[uid] = journey
                        uid += 1
                return journeys_dict

    def rebuild_packets_journey_iteratively(self):
        """Rebuild the packets journey from a list of measure recursively
        Algorithm:
            for each input packet, try to rebuild the journey with the next measurements (depth limited)

        Args:
            inputs: ordered and cleaned inputs

        Attributs:
            journeys (:obj:`dict`): the dictionnary of journey
            out_journeys (:obj:`list`): the list of journeys prepare for output
        """
        
        #############################################################
        ### START "rebuild_packets_journey_iteratively" algorithm ###
        #############################################################

        # Case: the instance has not been initialized correctly
        if not self.initialized:
            try:
                self(self.logpath)
            except Exception:
                raise Exception("Impossible to rebuild packet because this instance of latseq_log has not been initialized correctly")

        if MULTIPROCESSING:
            Rebuild_Class = self.RebuildJourneys(use_multiprocessing=True, inputs=self.inputs, logpath=self.logpath)
        else:
            Rebuild_Class = self.RebuildJourneys(use_multiprocessing=False, inputs=self.inputs, logpath=self.logpath)
        self.journeys = Rebuild_Class.rebuild_journeys()
        self.store_object()
        self._build_out_journeys()

    def _build_out_journeys(self):
        """Build out_journeys. Compute 'duration' for each points present in each journeys.

        Attributes:
            out_journeys (:obj:`list`): the list of measurements like `raw_inputs` but ordered, filtered and with unique identifier (uid) by journey
                out_journeys[o] : a log line of out_journeys = a log line from input (if input is present in a journey)
                    out_journeys[o][0] (Decimal): timestamp
                    out_journeys[o][1] (char): direction, U/D
                    out_journeys[o][2] (str): segment
                    out_journeys[o][3] (str): properties
                    out_journeys[o][4] (str): data identifier with journey id(s) associated to this measurement
        
        Returns:
            int: size of out_journeys list

        Raises:
            AttributeError: journeys not present in `latseq_logs` object
        """
        if not hasattr(self, 'journeys'):
            logging.error("latseq_log._build_out_journeys() First rebuild journeys")
            raise AttributeError('journeys not present in object, first try rebuild journeys')
        self.out_journeys = list()
        nb_meas = len(self.inputs)
        added_out_j = {}
        points_added = {}

        # retrieves all journey to build out_journeys
        for j in self.journeys:
            # Case : The journey is incomplete
            if not self.journeys[j]['completed']:
                continue
            for e in self.journeys[j]['set']: # for all elements in set of ids
                # List all points used for the out journeys
                if e[0] not in points_added:
                    points_added[e[0]] = [j]
                else:
                    points_added[e[0]].append(j)
                e_tmp = self.inputs[e[0]]  # Get the point in the inputs list
                if e[0] not in added_out_j:  # create a new entry for this point in out journeys
                    added_out_j[e[0]] = len(self.out_journeys)
                    tmp_uid = self.journeys[j]['uid']
                    tmp_str = f"uid{tmp_uid}:{dict_ids_to_str(self.journeys[j]['glob'])}.{dict_ids_to_str(e_tmp[6])}"
                    # have segment corresponding to journey's path
                    src_point_s = e_tmp[2]
                    while src_point_s not in self.paths[self.journeys[j]['dir']][self.journeys[j]['path']]:
                        src_point_s = '.'.join(src_point_s.split('.')[:-1])
                        if not src_point_s:  # TODO: error to categorize correctly the path
                            src_point_s = e_tmp[2]
                            break
                    
                    dst_point_s = e_tmp[3]
                    while dst_point_s not in self.paths[self.journeys[j]['dir']][self.journeys[j]['path']]:
                        dst_point_s = '.'.join(dst_point_s.split('.')[:-1])
                        if not dst_point_s:  # not in this path. TODO: error to categorize correctly the path
                            dst_point_s = e_tmp[3]
                            break
                    
                    tmp_seg = f"{src_point_s}--{dst_point_s}"
                    # build out_journeys for lseqj
                    self.out_journeys.append([
                        e_tmp[0],  # [0] : timestamp
                        'D' if e_tmp[1] == 0 else 'U',  # [1] : dir
                        tmp_seg, # [2] : segment
                        e_tmp[4],  # [3] : properties
                        tmp_str])  # [4] : data id
                else:  # update the current entry
                    self.out_journeys[added_out_j[e[0]]][4] = f"uid{self.journeys[j]['uid']}." + self.out_journeys[added_out_j[e[0]]][4]

                # points latency
                tmp_point = self.points[e_tmp[2]]
                if 'duration' not in tmp_point:
                    tmp_point['duration'] = {}
                if e_tmp[2] in self.pointsInD or e_tmp[2] in self.pointsInU:  # Is an in points
                    tmp_point['duration'][tmp_uid] = 0
                else:  # Is a mid point because out could not be in e_tmp[2]
                    current_index = self.journeys[j]['set'].index(e)
                    prev_ts = self.inputs[self.journeys[j]['set'][current_index - 1][0]][0]
                    tmp_point['duration'][tmp_uid] = e_tmp[0] - prev_ts
        self.out_journeys.sort(key=operator.itemgetter(0))
        orphans = 0
        # Check which points (clean inputs) are not in the completed journeys
        for e in range(nb_meas):
            if e not in points_added:
                if VERBOSITY:
                    tmp_str = f"{float(self.inputs[e][0])} "
                    tmp_str += "D " if self.inputs[e][1] == 0 else "U "
                    tmp_str += f"{self.inputs[e][2]}--{self.inputs[e][3]}"
                    logging.info(f"latseq_log._build_out_journeys() : inputs({e}) [{tmp_str}] is missing in completed journeys")
                orphans += 1
        # TODO : export all orphans as clean output to be compared with original cleaned output in a file
        logging.info(f"latseq_log._build_out_journeys() : {orphans} orphans / {nb_meas} measurements")
        self.store_object()
        return len(self.out_journeys)


    # GETTERS
    def get_filename(self) -> str:
        """Get filename used for this instance of latseq_logs
        Returns:
            filename (str)
        """
        return self.logpath.split('/')[-1]

    def get_list_of_points(self) -> list:
        """Get the list of points in the file
        Returns:
            points (:obj:`list` of str)
        """
        return list(self.points.keys())

    def get_list_timestamp(self) -> list:
        """Get the timestamps in `input` file
        Returns:
            list of timestamps
        """
        if not self.timestamps:
            self._build_timestamp()
        return self.timestamps

    def get_log_file_stats(self):
        """Get stats of the logfile
        Returns:
            file_stats (:obj:`dict`): name, nb_raw_meas, nb_meas, points
        """
        return {
            "name": self.logpath,
            "nb_raw_meas": len(self.raw_inputs),
            "nb_meas": len(self.inputs),
            "points": self.get_list_of_points()
            }

    def get_paths(self):
        """Get paths found in the file
        Returns:
            paths (:obj:`dict` of :obj:`list`): 0 for Downlink paths and 1 for Uplink paths
        """
        if len(self.paths[0]) == 0 and len(self.paths[1]) == 0:
            self._build_paths()
        return {'D': self.paths[0], 'U': self.paths[1]}

    # YIELDERS
    def yield_clean_inputs(self):
        """Yielder of cleaned inputs
        Yields:
            measurement line of log (str)
        Raises:
            ValueError: line malformed
        """
        try:
            for i in self.inputs:
                tmp_str = f"{i[0]} "
                tmp_str += "U " if i[1] else "D "
                tmp_str += f"(len{i[4]['len']}) "
                tmp_str += f"{i[2]}--{i[3]} "
                for g in i[5]:
                    tmp_str += f"{g}{i[5][g]}."
                tmp_str = tmp_str[:-1] + ':'
                for l in i[6]:
                    tmp_str += f"{l}{i[6][l]}."
                yield tmp_str[:-1]
        except Exception:
            raise ValueError(f"{i} is malformed")

    def yield_journeys(self):
        """Yielder of journeys
        Yields:
            journey element (:obj:`dict`)
        Raises:
            ValueError: Impossible to yield a journey from self.journeys
            Exception: Impossible to rebuild journeys
        """
        try:
            if not hasattr(self, 'journeys'):
                try:
                    self.rebuild_packets_journey_iteratively()
                except Exception:
                    raise Exception("[ERROR] to rebuild journeys")
            for j in self.journeys:
                if self.journeys[j]["completed"]:
                    yield self.journeys[j]
        except Exception:
            raise ValueError(f"[ERROR] to yield journeys for {self.logpath}")
    
    def yield_out_journeys(self):
        """Yielder for cleaned inputs
        Yields:
            str: A line of input
        Raises:
            ValueError : if the entry in out_journeys is malformed
        """
        # if not hasattr(self, 'out_journeys'):
        if not self._build_out_journeys():
            logging.error("latseq_log.yield_out_journeys() : to build out_journeys")
            exit(-1)
        def _build_header():
            res_str = "#funcId "
            paths = [path for dir in self.get_paths() for path in self.get_paths()[dir]]  # flatten the dict
            added_points = []
            for p in paths:
                for j in p:
                    if j not in added_points:
                        res_str += f"{j} "
                        added_points.append(j)
            return res_str
        try:
            yield _build_header()
            for e in self.out_journeys:
                try:
                    yield f"{epoch_to_datetime(e[0])} {e[1]} ({e[3]['len']})\t{e[2]}\t{e[4]}"
                except KeyError:
                    yield f"{epoch_to_datetime(e[0])} {e[1]} \t{e[2]}\t{e[4]}"
        except Exception:
            raise ValueError(f"{e} is malformed")

    def yield_out_metadata(self):
        """Yielder for cleaned meta data sort by points and by timestamp
        """
        try:
            for i in self.infos:  # for all informations
                tmp_ctxt_s = ""
                # TODO : set to 4 when infos construct fixed
                if len(i) == 0: # ctxt identifier
                    tmp_ctxt_l = []
                    for c in i[3]:
                        tmp_ctxt_l.append(f"{c}{i[3][c]}")
                    tmp_ctxt_s = ".".join(tmp_ctxt_l)
                for im in i[2]:  # for all individual information in i (one line in trace can generate multiple line in output)
                        yield f"{i[0]}\t{'.'.join(i[1])}{tmp_ctxt_s}.{im}\t{i[2][im]}"
        except Exception:
            raise ValueError(f"{i} is malformed")

    def yield_points(self):
        """Yielder for points
        Yields:
            :obj:`dict`: point's name with corresponding self.points dict element
        """
        # Warning for stats if journeys has not been rebuilt
        if "duration" not in self.points[next(iter(self.points.keys()))]:
            logging.warning("latseq_log.yield_points() : points without duration, first rebuild journeys for stat")
        for p in self.points:
            self.points[p]['point'] = p
            yield self.points[p]

    def yield_global_csv(self):
        """Yielder for a csv file from journeys
        Yields:
            str: csv line of timestamp by measurement point (column) and journeys (line) 
        """
        points = self.get_list_of_points()
        # Yields header
        NB_PREAMBLE = 3
        yield "journeys uid, dir, path_id, " + ", ".join(points) + "\n"
        # Yields one line per journey
        for j in self.journeys:
            if not self.journeys[j]['completed']:
                continue
            tmp_tab = (len(points) + NB_PREAMBLE)*['']
            tmp_tab[0] = str(self.journeys[j]['uid'])
            tmp_tab[1] = str(self.journeys[j]['dir'])
            tmp_tab[2] = str(self.journeys[j]['path'])
            for i in self.journeys[j]['set']:
                tmp_tab[points.index(self.inputs[i[0]][3])+NB_PREAMBLE] = str(self.inputs[i[0]][0])
            yield ", ".join(tmp_tab) + "\n"

    def yield_matrix(self):
        """Yield a line for matrix file for journeys
        Yields:
            str: csv string per matrix
        """
        tmp_d = {}  # key=path direction + path type
        points = self.get_list_of_points()
        for j in self.journeys:
            if not self.journeys[j]['completed']:
                continue
            tmp_path_id = f"{self.journeys[j]['dir']}.{self.journeys[j]['path']}"
            # New matrix for this journey
            if tmp_path_id not in tmp_d:
                tmp_header = "uid;"
                tmp_l = f"{self.journeys[j]['uid']};"
                tmp_tm1 = self.journeys[j]['ts_in']
                for i in self.journeys[j]['set']:
                    tmp_i = self.inputs[i[0]]
                    tmp_header += f"{tmp_i[2]}--{tmp_i[3]};"
                    tmp_l += "{:.6f};".format(tmp_i[0] - tmp_tm1)
                    tmp_tm1 = tmp_i[0]
                tmp_d[tmp_path_id] = [tmp_header]
                tmp_d[tmp_path_id].append(tmp_l)
            # Add a line to an existing matrix
            else:
                tmp_l = f"{self.journeys[j]['uid']};"
                tmp_tm1 = self.journeys[j]['ts_in']
                for i in self.journeys[j]['set']:
                    tmp_i = self.inputs[i[0]]
                    tmp_l += "{:.6f};".format(tmp_i[0] - tmp_tm1)
                    tmp_tm1 = tmp_i[0]
                tmp_d[tmp_path_id].append(tmp_l)
        # end for self.journeys
        res = []
        for k in tmp_d:
            res.append(f"{'D' if k.split('.')[0] == '0' else 'U'}{k.split('.')[1]}")
            for l in tmp_d[k]:
                res.append(l)
            res.append("")
        for e in res:
            yield e

    # WRITERS TO FILE
    def out_journeys_to_file(self):
        """ Saves out_journey to a lseqj file
        Attributes:
            out_journeys
        Raises:
            IOError: Error at writing lseqj files
        """
        # Save out_journeys to file type lseqj
        out_journeyspath = self.logpath.replace('lseq', 'lseqj')
        def _build_header() -> str:
            res_str = "#funcId "
            paths = [path for dir in self.get_paths() for path in self.get_paths()[dir]]  # flatten the dict
            added_points = []
            for p in paths:
                if p not in added_points:
                    res_str += f"{p} "
                    added_points.append(p)
            return res_str + "\n"
        try:
            with open(out_journeyspath, 'w+') as f:
                logging.info(f"latseq_log.out_journeys_to_file() : Writing latseq.lseqj ...")
                f.write(_build_header())  # write header
                for e in self.yield_out_journeys():
                    f.write(f"{e}\n")
        except IOError as e:
            logging.error(f"latseq_log.out_journeys_to_file() : on writing({self.logpath})")
            raise e

    def store_object(self):
        """Store latseq_log object into a pickle file
        Raises:
            IOError: Error at saving file to pkl
        TODO:
            handle pickle error
        """
        pickle_file = self.logpath.replace("lseq", "pkl")
        try:
            with open(pickle_file, 'wb') as fout:
                pickle.dump(self, fout, pickle.HIGHEST_PROTOCOL)
        except IOError:
            logging.error(f"[ERROR] latseq_log.store_object() : at saving {pickle_file}")
        logging.info(f"[INFO] latseq_log.store_object() : Saving lseq instance to {pickle_file}")

    def paths_to_str(self) -> str:
        """Stringify paths
        Returns:
            str: paths
        """
        res = f"Paths found in {self.logpath} \n"
        i, j = 0, 0
        for d in self.get_paths():
            if i == 0:
                res += "Downlink paths\n"
            if i == 1:
                res += "Uplink paths\n"
            for p in d:
                if p:
                    res += f"\tpath {j} : "
                    res += path_to_str(p)
                    res += "\n"
                j += 1
            i += 1
        return res



#
# MAIN
#

if __name__ == "__main__":
    # Arguments
    parser = argparse.ArgumentParser("./latseq_logs.py",
    description="LatSeq Analysis Module - Log processing component")
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        dest="configfile",
        help="[WIP] Config file for the parser"
    )
    parser.add_argument(
        "-f",
        "--flask",
        dest="flask",
        action='store_true',
        help="[DEPRECATED] Run parser as flask service"
    )
    parser.add_argument(
        "-C",
        "--clean",
        dest="clean",
        action='store_true',
        help="Clean previous saves and rerun"
    )
    parser.add_argument(
        "-i",
        "--req_inputs",
        dest="req_inputs",
        action='store_true',
        help="Request cleaned input measurements in the case of command line script"
    )
    parser.add_argument(
        "-o",
        "--out_journeys",
        dest="req_outj",
        action='store_true',
        help="Request out journeys points from log file to stdout"
    )
    parser.add_argument(
        "-j",
        "--journeys",
        dest="req_journeys",
        action='store_true',
        help="Request journeys from log file to stdout"
    )
    parser.add_argument(
        "-p",
        "--points",
        dest="req_points",
        action='store_true',
        help="Request points from log file to stdout"
    )
    parser.add_argument(
        "-r",
        "--paths",
        "--routes",
        dest="req_paths",
        action='store_true',
        help="Request paths from log file to stdout"
    )
    parser.add_argument(
        "--notrdtsc",
        dest="notrdtsc",
        action='store_true',
        help="lseq already converted to rdtsc"
    )
    parser.add_argument(
        "-m",
        "--metadata",
        dest="req_metadata",
        action="store_true",
        help="Request metadata from log file to stdout"
    )
    parser.add_argument(
        "-M",
        "--mat",
        dest="req_matrix",
        action='store_true',
        help="Request matrix of points and journeys from log file to stdout",
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        dest="verbosity",
        action="store_true",
        help="Verbosity for rebuilding phase especially"
    )
    parser.add_argument(
        "-x",
        "--csv",
        dest="req_csv",
        action='store_true',
        help="[DEPRECATED] Request csv with journeys and points"
    )
    parser.add_argument(
        "-l",
        "--log",
        type=str,
        dest="logname",
        help="Log file",
        required=True
    )

    args = parser.parse_args()

    # Phase 1 : We init latseq_logs class
    if not args.logname:  # No logfile
        logging.error("[ERROR] __main__ : No log file provided")
        exit(-1)
    if args.logname.split('.')[-1] != "lseq":
        logging.error("[ERROR] __main__ : No LatSeq log file provided (.lseq)")
        exit(-1)

    # Logger handler
    root_logger  = logging.getLogger()
    # Verbosity level
    if args.verbosity:
        VERBOSITY = True
        root_logger.setLevel(logging.DEBUG)
    
    candidate_pickle_file = args.logname.replace('lseq', 'pkl')
    if args.clean:  # clean pickles and others stuff
        if os.path.exists(candidate_pickle_file):
            os.remove(candidate_pickle_file)
    try:  # Try load a previous session
        with open(candidate_pickle_file, 'rb') as fin:
            try:
                lseq = pickle.load(fin)
                logging.info(f"__main__ : load lseq instance from {candidate_pickle_file}")
            except EOFError:
                raise FileNotFoundError
    except FileNotFoundError:
        try:
            logging.info(f"__main__ : create a new lseq instance")
            if not args.notrdtsc:
                ro = rdtsctots.rdtsctots(args.logname)
                ro.write_rdtsctots(args.logname)
            lseq = latseq_log(args.logname)  # Build latseq_log object
        except Exception as e:
            logging.error(f"__main__ : {args.logname}, {e}")
            exit(-1)
    lseq.store_object()
    
    # Phase 2A : case Flask
    if args.flask:
        logging.info("__main__ : Run a flask server")
        logging.error("__main__ : Flask server not implemented yet")
        exit(1)
    # Phase 2B : case run as command line script
    else:
        # -i, --inputs
        if args.req_inputs:
            for i in lseq.yield_clean_inputs():
                write_string_to_stdout(i)
        # -o, --out_journeys
        elif args.req_outj:
            for o in lseq.yield_out_journeys():
                write_string_to_stdout(o)
        # -j, --journeys
        elif args.req_journeys:
            for j in lseq.yield_journeys():
                write_string_to_stdout(json.dumps(j))
        # -p, --points
        elif args.req_points:
            for p in lseq.yield_points():
                write_string_to_stdout(json.dumps(p))
        # -r, --routes
        elif args.req_paths:
            write_string_to_stdout(json.dumps(lseq.get_paths()))
        # -m, --metadata
        elif args.req_metadata:
            for m in lseq.yield_out_metadata():
                write_string_to_stdout(m)
        # -M, --mat
        elif args.req_matrix:
            for r in lseq.yield_matrix():
                write_string_to_stdout(r)
        # -x, --csv
        elif args.req_csv:
            for l in lseq.yield_global_csv():
                write_string_to_stdout(l)

