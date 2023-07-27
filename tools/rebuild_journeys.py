import copy

KWS_NO_SEGMENTATION = [] # full name of all points where segmentation can't happen; the user has to know if segmentation can happen; this improves perfomance as unnecessary search is avoided
KWS_OUT_D = ['phy.out.proc']
KWS_OUT_U = ['gtp.out', 'pdcp.discarded.rcvdsmallerdeliv', 'pdcp.discarded.badpdusize', 'pdcp.discarded.integrityfailed', 'macdrop']

def _match_ids(point: dict, journey: dict):
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

def _new_journey(startpoint: dict, inputs: list):
    journey = dict()
    journey['completed'] = False
    journey['no_next_point'] = False
    journey['next_point'] = startpoint[3]
    journey['dir'] = startpoint[1]
    journey['glob'] = startpoint[5]
    journey['set'] = list()
    journey['set'].append((inputs.index(startpoint), startpoint[0], f"{startpoint[2]}--{startpoint[3]}"))
    journey['set_ids'] = dict()
    journey['set_ids'].update(startpoint[6])
    journey['ts_in'] = startpoint[0]
    journey['path'] = 0
    return journey

def _add_point_to_journey(point: dict, journey:dict, inputs: list):
    _, match_ids, logging_ids = _match_ids(point, journey)
    journey['set'].append((inputs.index(point), point[0], f"{point[2]}--{point[3]}"))
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

def _get_all_next_points(journey: dict, input_point_list: list):
    result_point_list = []
    for point in input_point_list:
        match, _, _ = _match_ids(point, journey)
        if match:
            result_point_list.append(point)
            if point in KWS_NO_SEGMENTATION:
                break
    return result_point_list

def _are_all_journeys_finished(journeys: list):
    all_completed_or_no_next_point = True
    for journey in journeys:
        if not journey['completed'] and not journey['no_next_point']:
            all_completed_or_no_next_point = False
            break
    return all_completed_or_no_next_point


def _rebuild_from_startingpoint_with_direction(startpoint: dict, input_dict: dict, inputs: list):
    journeys = []
    journeys.append(_new_journey(startpoint, inputs))
    all_finished = False
    while not all_finished:
        len_journeys = len(journeys)
        for index in range(0, len_journeys):
            journey = journeys[index]
            if journey['completed'] or journey['no_next_point']:
                continue # jump over all journeys, which are already completed or have no next point

            input_point_list = input_dict[journey['next_point']]
            all_next_points = _get_all_next_points(journey, input_point_list)
            if not all_next_points:
                journey['no_next_point'] = True
                continue

            journey_copied = copy.deepcopy(journey)
            for i, point in enumerate(all_next_points):
                if i == 0:
                    journey = _add_point_to_journey(point, journey, inputs)
                else:
                    journeys.append(_add_point_to_journey(point, journey_copied, inputs))

        all_finished = _are_all_journeys_finished(journeys)
    return journeys
            
def rebuild_from_startingpoint(index: int, startpoint: dict, input_UL_dict: dict, input_DL_dict: dict, inputs: list):
    is_UL = startpoint[1]
    if index == 43:
        a = 1
    if is_UL:
        journeys_from_startpoint = _rebuild_from_startingpoint_with_direction(startpoint, input_UL_dict, inputs)
    else:
        journeys_from_startpoint = _rebuild_from_startingpoint_with_direction(startpoint, input_DL_dict, inputs)
    return index, journeys_from_startpoint