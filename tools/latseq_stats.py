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
# Software description: LatSeq stats script
#################################################################################

"""Calculate statistics on a latseq_logs output

Example:
    ./latseq_logs.py -l /home/flavien/latseq.simple.lseq -j | ./latseq_stats.py -j

TODO
    * Issue with float representation in python https://docs.python.org/3.6/tutorial/floatingpoint.html
    * Handle -s and -n
"""

import sys
import argparse
import subprocess
import json
import datetime
import statistics
import numpy
import operator  # itemgetter
import decimal
# import math

#
# GLOBALS
#
S_TO_MS = 1000
B_TO_MB = 1048576
BASIC_STATS = ["size", "min", "max", "mean", "stdev", ["quantiles", "0.05", "0.25", "0.50", "0.75", "0.95"]]
QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]
PRECISION = 6
OUT_FORMATS = ["json", "csv"]

#
# FUNCTIONS
#

def output_function(outP: dict, flagP=False, fmtP="json", data_nameP="") -> str:
    """output wrapper

    Arguments:
        outP (:obj:`dict`): object to out
        flagP (bool): Print string if True, Json otherwise
    """
    if flagP:
        return latseq_stats.str_statistics(data_nameP, outP)
    else:
        if fmtP == "json":
            return json.dumps(outP)
        elif fmtP == "csv":
            return out_csv(outP)
        else:
            sys.stderr.write("No supported format provided for output\n")

def out_csv(outP: dict) -> str:
    resS = ";;"
    for s in BASIC_STATS:
        if isinstance(s, list):
            iterlist = iter(s)
            next(iterlist)
            for k in iterlist:
                resS += f"{s[0]}:{k};"
        else:    
            resS += f"{s};"
    resS += "\n"
    for k in outP:
        resS += f"{k};"
        for s in outP[k]:
            if isinstance(outP[k][s], list):
                for l in outP[k][s]:
                    resS += f"{l};"
            else:
                resS += f"{outP[k][s]};"
        resS += "\n"
    return resS
#
# STATISTICS
#
class latseq_stats:
    """Class of static methods for statistics stuff for latseq
    """
    # PRESENTATION
    @staticmethod
    def str_statistics(statsNameP: str, statsP: dict) -> str:
        """Stringify a statistics

        A statistics here embedded size, average, max, min, quantiles, stdev

        Args:
            statsNameP (str): the title for this stats
            statsP (str): a dictionnary with statistics

        Returns:
            str: the formatted statistics
        
        TODO:
            more dynamic stuff
        """
        res_str = f"Stats for {statsNameP}\n"
        for s in statsP:
            if 'dir' in statsP[s]:
                dir = statsP[s]['dir']
            else:
                dir = s
            if dir == 'D' or dir.split(".")[0] == 'D':
                res_str += "Values \t\t | \t Downlink\n"
                res_str += "------ \t\t | \t --------\n"
            elif dir == 'U' or dir.split(".")[0] == 'U':
                res_str += "Values \t\t | \t Uplink\n"
                res_str += "------ \t\t | \t ------\n"
            else:
                continue
            keysD = statsP[s].keys()
            if 'size' in keysD:
                res_str += f"Size \t\t | \t {statsP[s]['size']}\n"
            if 'mean' in keysD:
                res_str += f"Average \t | \t {float(statsP[s]['mean']):.3}\n"
            if 'stdev' in keysD:
                res_str += f"StDev \t\t | \t {float(statsP[s]['stdev']):.3}\n"
            if 'max' in keysD:
                res_str += f"Max \t\t | \t {float(statsP[s]['max']):.3}\n"
            if 'quantiles' in keysD:
                if len(statsP[s]['quantiles']) == 5:
                    res_str += f"[75..95%] \t | \t {float(statsP[s]['quantiles'][4]):.3}\n"
                    res_str += f"[50..75%] \t | \t {float(statsP[s]['quantiles'][3]):.3}\n"
                    res_str += f"[25..50%] \t | \t {float(statsP[s]['quantiles'][2]):.3}\n"
                    res_str += f"[10..25%] \t | \t {float(statsP[s]['quantiles'][1]):.3}\n"
                    res_str += f"[0..5%] \t | \t {float(statsP[s]['quantiles'][0]):.3}\n"
                else:
                    for i in range(len(statsP[s]['quantiles']),0,-1):
                        res_str += f"Quantiles {i-1}\t | \t {statsP[s]['quantiles'][i-1]:.3}\n"
            if 'min' in keysD:
                res_str += f"Min \t\t | \t {float(statsP[s]['min']):.3}\n"
        return res_str

    # GLOBAL-BASED
    @staticmethod
    def mean_separation_time(tsLP: list) -> float:
        """Function to return means time separation between logs

        Args:
            TsLP (:obj:`list` of float): the list of timestamp

        Returns:
            float : mean time separation between log entries

        Raises:
            ValueError: The len of list is < 2
        """
        if len(tsLP) < 2:
            raise ValueError("The length of tsLP is inferior to 2")
        tmp = list()
        for i in range(len(tsLP)-1):
            tmp.append(abs(tsLP[i+1]-tsLP[i]))
        return statistics.mean(tmp)
    
    @staticmethod
    def yield_matrix(journeysP: dict):
        """Yield a line for matrix file for journeys
        Copied from latseq_logs.py::yield_matrix()
        Yields:
            str: csv string per matrix
        """
        tmp_d = {}  # key=path direction + path type
        for j in journeysP:
            if not journeysP[j]['completed']:
                continue
            tmp_path_id = f"{journeysP[j]['dir']}.{journeysP[j]['path']}"
            # New matrix for this journey
            if tmp_path_id not in tmp_d:
                tmp_header = "uid;"
                tmp_l = f"{journeysP[j]['uid']};"
                tmp_tm1 = journeysP[j]['ts_in']
                for i in journeysP[j]['set']:
                    # journeysP[j]['set'][0] : id dans inputs
                    # journeysP[j]['set'][1] : ts for this input
                    # journeysP[j]['set'][2] : corresponding segment
                    #tmp_i = journeysP[j]['set'][i]
                    tmp_header += str(i[2])
                    tmp_l += f"{(i[1] - tmp_tm1):.6f};"
                    tmp_tm1 = i[1]
                tmp_d[tmp_path_id] = [tmp_header]
                tmp_d[tmp_path_id].append(tmp_l)
            # Add a line to an existing matrix
            else:
                tmp_l = f"{journeysP[j]['uid']};"
                tmp_tm1 = journeysP[j]['ts_in']
                for i in journeysP[j]['set']:
                    #tmp_i = journeysP[j]['set'][i]
                    tmp_l += f"{(i[1] - tmp_tm1):.6f};"
                    tmp_tm1 = i[1]
                tmp_d[tmp_path_id].append(tmp_l)
        # end for self.journeys
        res = []
        for k in tmp_d:
            res.append(f"{'dl' if k.split('.')[0] == '0' else 'ul'}{k.split('.')[1]}")
            for l in tmp_d[k]:
                res.append(l)
            res.append("")
        for e in res:
            yield e


    # JOURNEYS-BASED
    @staticmethod
    def journeys_latency_statistics(journeysP: dict, flagTimesP: bool) -> dict:
        """Function calculate statistics on journey's latency

        Args:
            journeysP (:obj:`dict` of journey): dictionnary of journey

        Returns:
            :obj:`dict`: statistics
        """
        times = [[],[]]
        for j in journeysP:
            if not journeysP[j]['completed']:
                continue
            times[journeysP[j]['dir']].append((
                journeysP[j]['dir'],
                j,
                journeysP[j]['ts_in'],
                round((journeysP[j]['ts_out'] - journeysP[j]['ts_in'])*S_TO_MS, 6)
                ))
        tmp_t = list()
        if not times[0]:
            times[0].append((0,0,0,0))
        if not times[1]:
            times[1].append((1,0,0,0))
        tmp_t.append([t[3] for t in times[0]])
        tmp_t.append([t[3] for t in times[1]])
        res = {'D' : {}, 'U': {}}
        if flagTimesP:
            for d in res:
                dint = 0 if d == "D" else 1
                res[d]['times'] = times[dint]
        else:
            for d in res:
                dint = 0 if d == "D" else 1
                res[d] = {
                    'size': len(times[dint]),
                    'min': round(min(tmp_t[dint]), ndigits=PRECISION),
                    'max': round(max(tmp_t[dint]), ndigits=PRECISION),
                    'mean': numpy.around(numpy.average(tmp_t[dint]), decimals=PRECISION),
                    'stdev': numpy.around(numpy.std(tmp_t[dint]), decimals=PRECISION),
                    'quantiles': numpy.around(numpy.quantile(tmp_t[dint], QUANTILES), decimals=PRECISION).tolist(),
                }
        return res

    @staticmethod
    def journeys_latency_per_point_statistics(journeysP: dict, pathsP: dict) -> dict:
        """Function calculate statistics on journey's latency by points

        Args:
            journeysP (:obj:`dict` of journey): dictionnary of journey
            pathsP (:obj:`dict` of paths): dictionnray of path

        Returns:
            :obj:`dict`: statistics
        """
        res = {'D' : {}, 'U': {}}
        # compute share and duration For all journeys
        for j in journeysP:
            if not journeysP[j]['completed']:
                continue
            # Compute share of time for each points
            else:
                duration = round(journeysP[j]['ts_out'] - journeysP[j]['ts_in'], 6)
                tmp_j = {'total': duration, 'durations': []}
                try:
                    for p in range(len(journeysP[j]['set'])-1):
                        # replace seg par point according to paths
                        tmp_seg = (journeysP[j]['set'][p][0], journeysP[j]['set'][p+1][0])
                        tmp_duration =  round((journeysP[j]['set'][p+1][1] - journeysP[j]['set'][p][1]), 6)
                        tmp_j['durations'].append(
                            (
                                tmp_seg,
                                tmp_duration,
                                round((tmp_duration/duration), 4)
                            )
                        )
                except KeyError:
                    sys.stderr.write(f"[ERROR] set not in journey {j}\n")
                    continue
                else:
                    dir = 'D' if journeysP[j]['dir'] == 0 else 'U'
                    if journeysP[j]['path'] not in res[dir]:
                        res[dir][journeysP[j]['path']] = {}
                    res[dir][journeysP[j]['path']][j] = tmp_j

        shares = []
        for d in res:
            for path in res[d]:
                del shares[:]
                # correpond to the number of point
                size_path = len(res[d][path][list(res[d][path].keys())[0]]['durations'])
                shares = []
                for v in range(size_path):
                    shares.append([])
                    for j in res[d][path]:
                        shares[v].append(res[d][path][j]['durations'][v][2])
                res[d][path]['stats'] = {}
                for v in range(size_path):  # TODO : replace v par segment in path
                    res[d][path]['stats'][v] = {
                        'size': len(shares[v]),
                        'min': round(min(shares[v]), ndigits=PRECISION),
                        'max': round(max(shares[v]), ndigits=PRECISION),
                        'mean': numpy.around(numpy.average(shares[v]), decimals=PRECISION),
                        'stdev': numpy.around(numpy.std(shares[v]), decimals=PRECISION),
                        'quantiles': numpy.around(numpy.quantile(shares[v], QUANTILES), decimals=PRECISION).tolist()
                    }
        return res


    # POINTS-BASED
    @staticmethod
    def points_latency_statistics(pointsP: dict) -> dict:
        """Function calculate statistics on points' latency

        Args:
            pointsP (:obj:`dict` of points): dictionnary of point

        Returns:
            :obj:`dict`: statistics
        """
        times = [dict(), dict()]
        for p in pointsP:
            if 'duration' not in pointsP[p]:
                continue
            tmp_p = [v * S_TO_MS for v in list(pointsP[p]['duration'].values())]
            if 0 in pointsP[p]['dir']:
                times[0][p] = tmp_p
            if 1 in pointsP[p]['dir']:
                times[1][p] = tmp_p
        res = {'D': {}, 'U': {}}
        for d in res:
            dint = 0 if d == "D" else 1
            for e0 in times[dint]:
                res[d][e0] = {
                    'dir': d,
                    'size': len(times[dint][e0]),
                    'min': round(min(times[dint][e0]), ndigits=PRECISION),
                    'max': round(max(times[dint][e0]), ndigits=PRECISION),
                    'mean': numpy.around(numpy.average(times[dint][e0]), decimals=PRECISION),
                    'stdev': numpy.around(numpy.std(times[dint][e0]), decimals=PRECISION),
                    'quantiles': numpy.around(numpy.quantile(times[dint][e0], QUANTILES), decimals=PRECISION).tolist()
                }
        return res

    # OTHER METRIC
    @staticmethod
    def instant_out_throughput(journeysP: dict) -> dict:
        # TODO: sort the list
        def _handle_len_prop(jP):
            if 'properties' in jP:
                if 'len' in jP['properties']:
                    return int(jP['properties']['len'])
            return 1
        def _compute_instant_throughtput(tsN, tsN1, lenP):
            delta = abs(float(tsN1)-float(tsN))
            if delta == 0.0:
                raise ZeroDivisionError  # is not ideal because it says that if 2 initial packet which share same output is not differentiated
            return f"{int(lenP)/delta/B_TO_MB:.3f}"

        res = {'0': {}, '1': {}}  # for each direction and for each path in direction
        for j in journeysP:
            if not journeysP[j]['completed']:
                continue
            # Compute share of time for each points
            else:
                # new path
                dire = str(journeysP[j]['dir'])
                path = journeysP[j]['path']
                if path not in res[dire]:
                    res[dire][path] = [(journeysP[j]['set'][-1][1], _handle_len_prop(journeysP[j]), journeysP[j]['uid'], 0)]  # [i] = (ts, len, uid, instant throughput)
                    continue
                tmp_len = _handle_len_prop(journeysP[j])
                try:
                    tmp_tp = _compute_instant_throughtput(res[dire][path][-1][0], journeysP[j]['set'][-1][1], tmp_len)
                except ZeroDivisionError:
                    continue
                else:
                    res[dire][path].append((
                        journeysP[j]['set'][-1][1],
                        tmp_len,
                        journeysP[j]['uid'],
                        tmp_tp
                    ))
        return res

    @staticmethod
    def in_interarrivals_rate(journeysP: dict) -> dict:
        # TODO: sort the list
        res = {'0': {}, '1': {}}  # for each direction and for each path in direction
        for j in journeysP:
            if not journeysP[j]['completed']:
                continue
            else:
                # new path
                dire = str(journeysP[j]['dir'])
                path = journeysP[j]['path']
                if path not in res[dire]:
                    res[dire][path] = [(journeysP[j]['set'][0][1], journeysP[j]['uid'], 0)]  # [i] = (ts, len, uid, instant throughput)
                    continue
                # set.0 = first segment in path
                tmp_ia = abs(journeysP[j]['set'][0][1] - res[dire][path][-1][0])
                if tmp_ia == 0:  # FIX temporary
                    tmp_ia = 0.000001
                tmp_ia = f"{tmp_ia:.6f}"
                res[dire][path].append((
                    journeysP[j]['set'][-1][1],  # timestamp
                    journeysP[j]['uid'],
                    tmp_ia
                ))
        return res

#
# MAIN
#
if __name__ == "__main__":

    # Arguments
    parser = argparse.ArgumentParser(
        "./latseq_stats.py",
        description="LatSeq Analysis Module - Statistics script",
        epilog="arguments that start with 's' return numpy stats when those that start with 'd' return raw values for visualizations.")
    parser.add_argument(
        "-l",
        "--log",
        type=str,
        dest="logname",
        help="Log file",
    )
    parser.add_argument(
        "-P",
        "--print",
        dest="print_stats",
        action='store_true',
        help="Print statistics instead of return a json report"
    )
    parser.add_argument(
        "-f",
        "--format",
        dest="format",
        type=str,
        default=OUT_FORMATS[0],
        choices=OUT_FORMATS,
        help="Output's format. csv and json supported. by default, json"
    )
    parser.add_argument(
        "-sj",
        "--sjourneys",
        dest="stat_journeys",
        action='store_true',
        help="Request stats journeys in the case of command line script"
    )
    parser.add_argument(
        "-sjpp",
        "--sjperpoints",
        dest="stat_journeys_points",
        action='store_true',
        help="Request stats on journeys per points in the case of command line script"
    )
    parser.add_argument(
        "-sp",
        "--spoints",
        dest="stat_points",
        action='store_true',
        help="Request stats points in the case of command line script"
    )
    parser.add_argument(
        "-djd",
        "--djduration",
        dest="journeys_durations",
        action='store_true',
        help="Request journeys duration"
    )
    parser.add_argument(
        "-st",
        "--stp",
        dest="stat_throughput",
        action='store_true',
        help="Request instant throughtputs for each path"
    )
    parser.add_argument(
        "-ia",
        "--interarrival",
        dest="stat_interarrival",
        action='store_true',
        help="Request interarrival rate"
    )
    parser.add_argument(
        "-m",
        "--matrix",
        dest="matrix",
        action='store_true',
        help="Request matrix of segment/journey"
    )
    args = parser.parse_args()
    # Check arguments
    if not args.stat_journeys and not args.stat_points and not args.stat_journeys_points and not args.journeys_durations and not args.stat_throughput and not args.stat_interarrival and not args.matrix:
        sys.stderr.write("[WARNING] No action requested\n")
        exit()

    list_meas_json = []
    if args.logname:
        if args.logname.split('.')[-1] == 'lseqj':  # We do statistics from a log journey files
            pass
        if args.logname.split('.')[-1] == 'json':  # We do statistics from a json file
            try:
                with open(args.logname, 'r') as j:
                    for l in j.read().splitlines():
                        if l.startswith('#') or l.startswith('['):
                            continue
                        list_meas_json.append(l)
            except IOError:
                raise IOError(f"[Error] at openeing ({args.logname})")
    else:
        # Else, we read stdin
        for meas in sys.stdin.readlines():  # For all lines in stdin
            # Clean all lines begins with # or [
            if meas.startswith('#') or meas.startswith('['):
                continue
            list_meas_json.append(meas)

    output = ""  # Common variable for output

    # -j, --journeys
    if args.stat_journeys:
        journeys = {}
        # handle errors
        for j in list_meas_json:
            tmp_j = json.loads(j)
            journeys[tmp_j['uid']] = tmp_j
        output = output_function(latseq_stats.journeys_latency_statistics(journeys, False), args.print_stats, args.format, "Journeys latency stats")

    # -jpp, --jperpoints
    elif args.stat_journeys_points:
        journeys = {}
        # to a dict
        tmp_j = {}
        for jpp in list_meas_json:
            tmp_j = json.loads(jpp)
            journeys[tmp_j['uid']] = tmp_j
        # call latseq_logs to get path
        # TODO : gerer les erreurs
        # CA NE MARCHE PAS, avec run() et Popen me fait un Broken pipe...
        # La gestion des subprocess sous python c'est tout de même un peu rodeo !!!

        # print(journeys['32']['file'])
        # cmd = ["./latseq_logs.py", "-r", f"-l /home/flavien/latseq.simple.lseq"]
        # print(" ".join(cmd))
        # latseq_route_process = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, universal_newlines=True)
        # print(latseq_route_process)
        # On va dire que ca marche
        paths = {}
        # with open("routes.json", 'r') as fp:
        #     paths = json.load(fp)
        res = latseq_stats.journeys_latency_per_point_statistics(journeys, {})
        for d in res:
            for path in res[d]:
                for v in res[d][path]['stats']:
                    #continue
                    output += output_function({f"{d}{path}.{v}": res[d][path]['stats'][v]}, args.print_stats, args.format, f"Share of time for {v} in path {path}")
        # Clear output
        if args.format == "csv" and not args.print_stats:
            tmp_out = ""
            for l in output.splitlines():
                if l.startswith(";;"):
                    if not tmp_out:
                        tmp_out += f"{l}\n"
                else:
                    tmp_out += f"{l}\n"
            output = tmp_out

    # -jd, jduration
    elif args.journeys_durations:
        journeys = {}
        for jd in list_meas_json:
            tmp_j = json.loads(jd)
            journeys[tmp_j['uid']] = tmp_j
        tmp_out = latseq_stats.journeys_latency_statistics(journeys, True)  # tmp_out[dir][times][0..len]=(dir, jid, ts, durations)
        out_list = []

        for d in tmp_out:
            out_list.extend(tmp_out[d]['times'])
        out_list.sort(key=operator.itemgetter(2))

        output = ""
        if args.format == "json":
            tmp = {}
            for e in out_list:
                tmp[f"{e[0]}{e[1]}"] = {
                    'ts': e[2],
                    'durations': e[3]
                }
            output = json.dumps(tmp)
        elif args.format == "csv":
            output="jid;timestamp;duration;\n"
            for e in out_list:
                output += f"{e[0]}{e[1]};{e[2]};{e[3]};\n"
        else:
            sys.stderr.write("No supported format provided for output\n")

    # -p, --points
    elif args.stat_points:
        points = {}
        for p in list_meas_json:
            tmp_p = json.loads(p)
            #point_name = list(tmp_p.keys())[0]
            try:
                point_name = tmp_p['point']
            except KeyError:
                sys.stderr.write("[ERROR] no 'point' name key in input")
                exit()
            points[point_name] = tmp_p
        tmp_stats_points = latseq_stats.points_latency_statistics(points)
        for dir in tmp_stats_points:
            for p in tmp_stats_points[dir]:
                output += output_function({p: tmp_stats_points[dir][p]}, args.print_stats, args.format, f"Point Latency for {p}")
                # Clear output
        if args.format == "csv" and not args.print_stats:
            tmp_out = ""
            for l in output.splitlines():
                if l.startswith(";;"):
                    if not tmp_out:
                        tmp_out += f"{l}\n"
                else:
                    tmp_out += f"{l}\n"
            output = tmp_out

    # -st, --stp
    elif args.stat_throughput:
        journeys = {}
        # to a dict
        tmp_j = {}
        for jpp in list_meas_json:
            tmp_j = json.loads(jpp)
            journeys[tmp_j['uid']] = tmp_j
        if args.format == "json":
            output = json.dumps(latseq_stats.instant_out_throughput(journeys)) + "\n"
        if args.format == "csv":
            tmp_res = latseq_stats.instant_out_throughput(journeys)
            for dire in tmp_res:
                for path in tmp_res[dire]:
                    output+=f"{'dl' if dire == '0' else 'ul'}{path}\n"
                    output+="timestamp;throughput;\n"
                    for l in tmp_res[dire][path]:
                        output+=f"{l[0]};{l[-1]};\n"
                output+="\n"

    # -ia, --interarrival
    elif args.stat_interarrival:
        journeys = {}
        # to a dict
        tmp_j = {}
        for jpp in list_meas_json:
            tmp_j = json.loads(jpp)
            journeys[tmp_j['uid']] = tmp_j
        if args.format == "json":
            output = json.dumps(latseq_stats.in_interarrivals_rate(journeys)) + "\n"
        if args.format == "csv":
            tmp_res = latseq_stats.in_interarrivals_rate(journeys)
            for dire in tmp_res:
                for path in tmp_res[dire]:
                    output+=f"{'dl' if dire == '0' else 'ul'}{path}\n"
                    output+="timestamp;interarrival;\n"
                    for l in tmp_res[dire][path]:
                        output+=f"{l[0]};{l[-1]};\n"
                output+="\n"

    # -m, --matrix
    elif args.matrix:
        journeys = {}
        # to a dict
        tmp_j = {}
        for jpp in list_meas_json:
            tmp_j = json.loads(jpp)
            journeys[tmp_j['uid']] = tmp_j
        
        for l in latseq_stats.yield_matrix(journeys):
            # TODO: to uniformize with the rest of the script
            sys.stdout.write(l + '\n')
    if not output:
        sys.stderr.write("[ERROR] no output")
    else:
        sys.stdout.write(output)
 
