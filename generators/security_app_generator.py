import math

from input.model.application import EApplicationType, application
from input.model.signal import ESignalType, signal
from input.model.task import ETaskType, key_verification_task, task
from input.testcase import Testcase
from solution.solution_timing_data import TimingData
from utils.utilities import Timer


def run(tc: Testcase, timing_object: TimingData) -> Testcase:
    tmr = Timer()
    with tmr:
        es_to_secapp_map = (
            {}
        )  # Since a security application is specific to the ES of its release task

        # Security Applications:
        # Go through all the signals of an application
        # Check if sender and receiver are different
        # Check if sender.id is already key in map -> if yes add new node+edge to sec app
        # otherwise add new sec
        for app in tc.A_app.values():
            for sig_id in app.edges.keys():
                sig = tc.S_all[sig_id]
                # Only consider routed signals
                if not sig.is_self_signal() and sig.is_secure:
                    src_es_id = sig.sender_es_id
                    dest_es_id = sig.receiver_es_id
                    rl = max([s.rl for s in tc.S_g[src_es_id]])

                    # If sender ES doesnt have a security app yet
                    if src_es_id not in es_to_secapp_map:
                        secapp = application.from_params(
                            "SecApp_{}_to_{}".format(src_es_id, dest_es_id),
                            tc.Pint,
                            EApplicationType.KEY,
                            src_es_id,
                        )

                        tc.add_to_datastructures(secapp)

                        wcet = math.ceil(0.5 * tc.ES[src_es_id].mac_exec_time)
                        key_rel_task_id = "t_rel_{}".format(src_es_id)
                        key_rel_task = task(
                            key_rel_task_id,
                            secapp.id,
                            src_es_id,
                            wcet,
                            tc.Pint,
                            rl,
                            set(),
                            ETaskType.KEY_RELEASE,
                            False,
                        )
                        tc.add_to_datastructures(key_rel_task)

                        es_to_secapp_map[src_es_id] = secapp
                    else:
                        secapp = es_to_secapp_map[src_es_id]
                        key_rel_task_id = list(secapp.edges.values())[0][0]

                    key_verify_task_id = "t_ver_{}_{}".format(src_es_id, dest_es_id)
                    if key_verify_task_id not in secapp.verticies:
                        key_verify_task = key_verification_task(
                            key_verify_task_id,
                            secapp.id,
                            sig.receiver_es_id,
                            tc.ES[sig.receiver_es_id].mac_exec_time,
                            tc.Pint,
                            1,
                            set(),
                            ETaskType.KEY_VERIFICATION,
                            False,
                            sig.sender_es_id,
                        )
                        tc.add_to_datastructures(key_verify_task)

                        # group id of key_signal is "key_ES.id"
                        group = "key_{}".format(sig.sender_es_id)
                        key_signal = signal(
                            "s_key_{}_{}".format(src_es_id, dest_es_id),
                            secapp.id,
                            key_rel_task_id,
                            key_verify_task_id,
                            src_es_id,
                            dest_es_id,
                            tc.key_length,
                            tc.Pint,
                            group,
                            rl,
                            ESignalType.KEY,
                            False,
                        )
                        tc.add_to_datastructures(key_signal)

    for s_list in tc.S_sec.values():
        for s in s_list:
            # Add group to tasks
            tc.T[s.src_task_id].groups.add(s.group)

    timing_object.time_creating_secapps = tmr.elapsed_time
    return tc
