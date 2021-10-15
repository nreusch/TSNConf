import copy
import math
from typing import Dict, Tuple, List

from input.model.application import EApplicationType, application
from input.model.stream import stream, EStreamType
from input.model.task import ETaskType, key_verification_task, task
from input.testcase import Testcase
from solution.solution_timing_data import TimingData
from utils.utilities import Timer


def run(tc: Testcase, timing_object: TimingData) -> Testcase:
    tmr = Timer()
    with tmr:
        es_to_secapp_map: Dict[str, Tuple[application, stream, List[task]]] = {}  # Since a security application is specific to the ES of its release task

        # Security Applications:
        # Go through all the streams
        #   Go through all receiver ES
        #       Check if sender ES is already key in map
        #       -> if no, create new secapp with key release task, create correspong key stream
        #       Check if receiver ES already has a verification task
        #       -> if no, add a new key verificaiton task to existing secapp
        for f in tc.F.values():
            # Only consider routed signals
            if not f.is_self_stream() and f.is_secure:
                src_es_id = f.sender_es_id
                for dest_es_id in f.receiver_es_ids:
                    if dest_es_id != src_es_id:
                        # If sender ES doesnt have a security app yet
                        if src_es_id not in es_to_secapp_map:
                            secapp = application.from_params(
                                "SecApp_{}".format(src_es_id),
                                tc.Pint,
                                EApplicationType.KEY,
                                src_es_id,
                            )

                            wcet = math.ceil(0.5 * tc.ES[src_es_id].mac_exec_time)
                            key_rel_task_id = "t_rel_{}".format(src_es_id)
                            key_rel_task = task(
                                key_rel_task_id,
                                secapp.id,
                                src_es_id,
                                wcet,
                                tc.Pint,
                                0,
                                ETaskType.KEY_RELEASE,
                            )

                            key_stream = stream(
                                "s_key_{}".format(src_es_id),
                                secapp.id,
                                src_es_id,
                                {},
                                key_rel_task.id,
                                {},
                                tc.key_length + tc.OH,
                                tc.Pint,
                                f.rl,
                                False,
                                tc.key_length,
                                0,
                                tc.OH,
                                EStreamType.KEY
                            )
                            es_to_secapp_map[src_es_id] = (secapp, key_stream, [key_rel_task])

                        secapp = es_to_secapp_map[src_es_id][0]
                        key_verify_task_id = "t_ver_{}_{}".format(src_es_id, dest_es_id)
                        if key_verify_task_id not in es_to_secapp_map[src_es_id][1].receiver_task_ids:
                            key_verify_task = key_verification_task(
                                key_verify_task_id,
                                secapp.id,
                                dest_es_id,
                                tc.ES[dest_es_id].mac_exec_time,
                                tc.Pint,
                                ETaskType.KEY_VERIFICATION,
                                src_es_id,
                            )

                            key_stream = es_to_secapp_map[src_es_id][1]
                            key_stream.receiver_es_ids[dest_es_id] = None
                            key_stream.receiver_task_ids[key_verify_task.id] = None
                            key_stream.rl = max(key_stream.rl, f.rl)

                            es_to_secapp_map[src_es_id][2].append(key_verify_task)

    # Add newly created apps, streams & tasks to testcase
    for tpl in es_to_secapp_map.values():
        tc.add_to_datastructures(tpl[0])
        for t in tpl[2]:
            tc.add_to_datastructures(t)
        # Add RL redundant copies of key stream
        base_stream = tpl[1]
        for i in range(base_stream.rl):
            red_copy = copy.deepcopy(base_stream)
            red_copy.id += f"_{i}"
            tc.add_to_datastructures(red_copy)

    timing_object.time_creating_secapps = tmr.elapsed_time
    return tc