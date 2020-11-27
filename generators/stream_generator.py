from input.model.signal import ESignalType
from input.model.stream import EStreamType, stream
from input.testcase import Testcase
from solution.solution_timing_data import TimingData
from utils.utilities import Timer


def run(tc: Testcase, timing_object: TimingData) -> Testcase:
    # For each task, for each group!="self", generate RL streams
    tmr = Timer()
    with tmr:
        for t in tc.T.values():
            for group_id in t.groups:
                some_signal = tc.S_group[group_id][0]
                if not some_signal.is_self_signal():
                    is_secure = False
                    for s in tc.S_group[group_id]:
                        if s.is_secure is True:
                            is_secure = True

                    rl = max([s.rl for s in tc.S_group[group_id]])

                    # all signals in group have the same size & period
                    # TODO: Split stream if size>MTU
                    mac_size = 0
                    if is_secure is True:
                        mac_size = tc.W_mac
                    stream_size = some_signal.size + tc.OH + mac_size

                    stream_period = some_signal.app_period
                    stream_type = (
                        EStreamType.NORMAL
                        if some_signal.type == ESignalType.NORMAL
                        else EStreamType.KEY
                    )
                    stream_receiver_es_ids = {
                        s.receiver_es_id for s in tc.S_group[group_id]
                    }
                    stream_receiver_task_ids = {
                        s.dest_task_id for s in tc.S_group[group_id]
                    }

                    # stream.get_id_prefix relies on this format: "strm_{}_{}"
                    for i in range(rl):
                        strm = stream(
                            "strm_{}_{}".format(group_id, i),
                            t.src_es_id,
                            stream_receiver_es_ids,
                            t.id,
                            stream_receiver_task_ids,
                            group_id,
                            stream_size,
                            stream_period,
                            rl,
                            is_secure,
                            some_signal.size,
                            mac_size,
                            tc.OH,
                            [
                                (
                                    ",".join(s.id for s in tc.S_group[group_id]),
                                    some_signal.size,
                                )
                            ],
                            stream_type,
                        )

                        tc.add_to_datastructures(strm)

    timing_object.time_creating_streams = tmr.elapsed_time
    return tc
