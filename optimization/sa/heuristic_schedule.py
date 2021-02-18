import itertools
import math
from typing import Dict, Union, Tuple, List, Optional

from intervaltree import IntervalTree, Interval

from input import testcase
from input.model.link import link
from input.model.nodes import end_system
from input.model.route import route
from input.model.stream import stream
from input.model.task import task, key_verification_task
from optimization.sa.task_graph import TaskGraphNode, TaskGraphNode_Task, TaskGraphNode_Stream, TaskGraph
from utils.utilities import sorted_complement, debug_print


class frame:
    def __init__(self, s_or_t, l_or_es, lb: int, ub: int, length: int, offset: int, period: int, prev_frame, next_frames: List):
        self.s_or_t = s_or_t
        self.l_or_es = l_or_es
        self.lb = lb
        self.ub = ub
        self.length = length
        self.offset = offset
        self.period = period

        self.prev_frame: frame = prev_frame
        self.next_frames: List[frame] = next_frames

    def __repr__(self):
        return f"({self.s_or_t.id}, {self.l_or_es}, {self.offset}, {self.offset+self.length})"

class heuristic_schedule:
    def __init__(self, tc: testcase, task_graph: TaskGraph):
        self.tc: testcase = tc
        self.task_graph = task_graph
        self.StartTimes: Dict[str, List[Tuple[int, int]]] = {} # Dict[tgn.id -> List[offset]]
        self.Blocks: Dict[str, Dict[int, IntervalTree]] = {}  # l_or_es.id -> (T -> IntervalTree)
        self.frames : Dict[str, Dict[str, frame]] = {} # Dict[tgn.id -> Dict[link_or_es.id, frame]]
        self.all_frames_on_link : Dict[str, List[frame]] = {} # Dict[l_or_es.id -> List[frame]]

        for l_or_es_id in itertools.chain(tc.L.keys(), tc.ES.keys()):
            self.Blocks[l_or_es_id] = {}
            for T in tc.Periods:
                self.Blocks[l_or_es_id][T] = IntervalTree()

    def get_latency(self, tgn: TaskGraphNode):
        s_or_t, l_or_es_list = self._extract_from_tgn(tgn)
        first_frame = self.frames[tgn.id][l_or_es_list[0].id]
        last_frame = self.frames[tgn.id][l_or_es_list[-1].id]

        if first_frame.offset == -1 or last_frame.offset == -1:
            return -1
        else:
            return (last_frame.offset+last_frame.length)-first_frame.offset

    def _extract_from_tgn(self, tgn: TaskGraphNode) -> Tuple[Union[stream, task], List[Union[link, end_system]]]:
        if isinstance(tgn, TaskGraphNode_Task):
            return tgn.t, [self.tc.ES[tgn.t.src_es_id]]
        elif isinstance(tgn, TaskGraphNode_Stream):
            s: stream = tgn.s
            if s.is_secure:
                return s, self.tc.R[s.id].get_all_es_and_links_dfs(self.tc)
            else:
                return s, self.tc.R[s.id].get_all_links_dfs(self.tc)
        else:
            raise ValueError

    def _get_length_on_link_or_es(self, tgn : TaskGraphNode, l_or_es: Union[link, end_system]):
        s_or_t, _ = self._extract_from_tgn(tgn)
        if isinstance(s_or_t, stream):
            s : stream = s_or_t
            if isinstance(l_or_es, link):
                l : link = l_or_es
                return l.transmission_length(s.size)
            elif isinstance(l_or_es, end_system):
                es: end_system = l_or_es
                return es.mac_exec_time
            else:
                raise ValueError
        elif isinstance(s_or_t, task):
            t : task = s_or_t
            if isinstance(l_or_es, end_system):
                return t.exec_time
            else:
                raise ValueError

    def _calc_lower_bound(self, tgn: TaskGraphNode, frm : frame, l_or_es: Union[link, end_system]):

        lb = 0

        if self._is_first_instance(frm):
            # For tasks & the first stream instance, set the lower bound to the max end-time of all predecessor tgn's
            for tgn_pred_id in self.task_graph.get_predecessors_ids(tgn.id):
                _, l_or_es_list = self._extract_from_tgn(self.task_graph.get_tgn_by_id(tgn_pred_id))
                f = self.frames[tgn_pred_id][l_or_es_list[-1].id]
                lb = max(lb, f.offset + f.length)
        elif isinstance(frm.s_or_t, stream) and isinstance(l_or_es, link):
            # For consecutive stream instances, set the lower bound to the max end-time of the stream on the previous links
            r: route = self.tc.R[frm.s_or_t.id]

            if frm.s_or_t.is_secure:
                previous_links_or_es = r.get_predeccessor_links_and_es(l_or_es.id, self.tc)
            else:
                previous_links_or_es = r.get_predeccessor_links(l_or_es.id, self.tc)

            for l_or_es in previous_links_or_es:
                prev_frame = self.frames[tgn.id][l_or_es.id]
                lb = max(lb, prev_frame.offset + prev_frame.length)
        elif isinstance(frm.s_or_t, stream) and isinstance(l_or_es, end_system) and l_or_es.id in frm.s_or_t.receiver_es_ids:
            # For the stream instances on receiver ES, set the lower bound after the end-time of appropriate key verification task
            es_recv: end_system = l_or_es


            t_key_verify: key_verification_task = self.tc.T_verify[frm.s_or_t.sender_es_id][es_recv.id]
            t_key_verify_frame = self.frames[self.task_graph.get_task_tgn(t_key_verify.id).id][es_recv.id]

            # TODO: Make sure i is after inteval of previous frame
            # TODO: What happens if t_key_verify_frame.offset > max_previous_end_time
            # TODO: What happens if there is no space for task in first interval after last stream arrival
            i = self._calculate_pint_interval_from_key_verification_task(t_key_verify_frame, l_or_es.id, tgn)

            lb = t_key_verify_frame.offset + i * t_key_verify_frame.period + t_key_verify_frame.length
        else:
            raise ValueError

        # frm.lb might have been set from outside. Thus return the max
        return max(lb, frm.lb)

    def _calculate_pint_interval_from_key_verification_task(self, t_key_verify_frame: frame, es_id:str, tgn: TaskGraphNode):
        assert isinstance(tgn, TaskGraphNode_Stream)
        r: route = self.tc.R[tgn.s.id]
        previous_links = r.get_predeccessor_links(es_id, self.tc)
        assert len(previous_links) != 0
        max_previous_end_time = max(
            [self.frames[tgn.id][l.id].offset + self.frames[tgn.id][l.id].length for l in previous_links])

        # TODO: Align to phi from constraint model
        # TODO: Fix TC4_test_6 for constraint model, detect infeasible TC in heuristic
        return math.ceil((max_previous_end_time - t_key_verify_frame.offset) / t_key_verify_frame.period)

    def _earliest_offset(self, tgn : TaskGraphNode, l_or_es: Union[link, end_system], frm: frame):
        """
        Returns the earliest offset in the free intervals for given task/stream on given link/node, which is >= frm.lb and where the frame fits inside the interval
        """
        intervals = self._get_feasible_region(frm, l_or_es)

        for iv in intervals:
            offset = max(frm.lb, iv.begin)
            # also included end of interval
            if iv.contains_point(offset) or iv.end == offset:
                return offset

        return -1

    def _create_frames(self, tgn : TaskGraphNode):
        s_or_t, l_or_es_list = self._extract_from_tgn(tgn)
        link_to_frame_dict = {}
        ordered_l_or_es_list = []

        for l_or_es in l_or_es_list:
            f = frame(s_or_t, l_or_es, -1, -1, self._get_length_on_link_or_es(tgn, l_or_es),
                      -1, s_or_t.period, None, [])

            if l_or_es.id not in self.all_frames_on_link:
                self.all_frames_on_link[l_or_es.id] = [f]
            else:
                self.all_frames_on_link[l_or_es.id].append(f)

            link_to_frame_dict[l_or_es.id] = f
            ordered_l_or_es_list.append(l_or_es)

            if isinstance(s_or_t, stream):
                s: stream = s_or_t
                r: route = self.tc.R[s.id]

                if s.is_secure:
                    previous_links_or_es = r.get_predeccessor_links_and_es(l_or_es.id, self.tc)
                else:
                    previous_links_or_es = r.get_predeccessor_links(l_or_es.id, self.tc)

                # Connect frame with previous frame
                for l_or_es in previous_links_or_es:
                    prev_frame = link_to_frame_dict[l_or_es.id]
                    prev_frame.next_frames.append(f)
                    f.prev_frame = prev_frame


        return link_to_frame_dict, ordered_l_or_es_list

    def schedule(self, tgn : TaskGraphNode):
        debug_print(f"Scheduling TGN {tgn.id}:")
        link_to_frame_dict, ordered_l_or_es_list = self._create_frames(tgn)
        # tgn.id -> (l_or_es.id -> frame)
        self.frames[tgn.id]: Dict[str, Dict[str, frame]] = link_to_frame_dict

        finished = False
        i = 0
        l = ordered_l_or_es_list[0]
        while True:
            f = self.frames[tgn.id][l.id]
            f.lb = self._calc_lower_bound(tgn, f, l)
            offset = self._earliest_offset(tgn, l, f)
            debug_print(f"\tCurrent frame on {f.l_or_es.id}: LB {f.lb}, UB {f.ub}, Calc. Offset {offset}")

            if offset == -1:
                return False
            elif offset <= f.ub or f.ub == -1:
                f.offset = offset
                debug_print(f"\t\tScheduled frame on {f.l_or_es.id} for [{f.offset},{f.offset+f.length}]")

                # Set upper bound of following frames, except those on end_systems
                for f_next in f.next_frames:
                    if isinstance(f_next.l_or_es, link):
                        lqat = self._latest_queue_available_time(f_next, offset)

                        if lqat != -1:
                            f_next.ub = lqat
                            debug_print(f"\t\tSetting upper bound for frame on {f_next.l_or_es.id} to {lqat}")
                        else:
                            return False

                i += 1
                if i < len(ordered_l_or_es_list):
                    l = ordered_l_or_es_list[i]
                else:
                    finished = True
            else:
                eqat = self._earliest_queue_available_time(f, offset)

                # Set lower bound of previous frame
                if f.prev_frame != None:
                    if eqat != -1:
                        f.prev_frame.lb = eqat
                        debug_print(f"\t\tSetting lower bound for frame on {f.l_or_es.id} to {eqat}")
                    else:
                        return False
                else:
                    return False

                l = f.prev_frame.l_or_es
                i = ordered_l_or_es_list.index(f.prev_frame.l_or_es)

            if finished:
                break

        if isinstance(tgn, TaskGraphNode_Stream):
            #self._optimize_latency(tgn, tgn.s)
            pass
        self._block_queues(tgn)
        debug_print("")
        return True

    def _optimize_latency(self, tgn: TaskGraphNode, s: stream):
        # for each receiver es
        # for each incoming frame to that receiver es
        # interval_upper_bound = Pint * index of key_verification_task OR -1 if stream not secure
        # set frame.ub = max(frame.ub, interval_upper_bound-frame.length)
        # set frame.offset to frame.ub
        # set ub of previous frame to max(prev_frame.ub, frame.offset-prev_frame.length)
        # set prev_frame.offset to prev_frame.ub
        # repeat until not prev_frame available
        for recv_es_id in s.receiver_es_ids:
            if s.is_secure:
                f = self.frames[tgn.id][recv_es_id]
                incoming_f = f.prev_frame
                t_key_verify: key_verification_task = self.tc.T_verify[s.sender_es_id][recv_es_id]
                t_key_verify_frame = self.frames[self.task_graph.get_task_tgn(t_key_verify.id).id][recv_es_id]

                # TODO: What happens if t_key_verify_frame.offset > max_previous_end_time
                # TODO: What happens if there is no space for task in first interval after last stream arrival
                i = self._calculate_pint_interval_from_key_verification_task(t_key_verify_frame, recv_es_id, tgn)

                # t_key_verify.period = Pint
                upper_bound = t_key_verify.period * i - incoming_f.length
            else:
                # TODO: Handle tasks
                incoming_f = None
                upper_bound = 0

            while incoming_f != None:
                print(f"{incoming_f}.offset = min({upper_bound},{incoming_f.ub}) = {min(upper_bound, incoming_f.ub)}")
                if incoming_f.ub == -1:
                    incoming_f.offset = upper_bound
                else:
                    incoming_f.offset = min(upper_bound, incoming_f.ub)

                if incoming_f.prev_frame is None and isinstance(incoming_f.s_or_t, stream):
                    sender_task_tgn: TaskGraphNode_Task = self.task_graph.get_task_tgn(s.sender_task_id)
                    task_f = self.frames[sender_task_tgn.id][sender_task_tgn.es_id]
                    upper_bound = incoming_f.offset - task_f.length
                    incoming_f = task_f
                elif incoming_f.prev_frame is not None:
                    upper_bound = incoming_f.offset - incoming_f.prev_frame.length
                    incoming_f = incoming_f.prev_frame
                else:
                    incoming_f = incoming_f.prev_frame




        pass

    def _get_feasible_region(self, f: frame, l_or_es: Union[link, end_system]):
        if isinstance(l_or_es, end_system):
            return self._get_feasible_region_es(f, l_or_es)
        elif isinstance(l_or_es, link):
            return self._get_feasible_region_link(f, l_or_es)
        else:
            raise ValueError

    def _get_feasible_region_link(self, f: frame, l: link) -> IntervalTree:
        feasible_region = IntervalTree()
        free_blocks = sorted_complement(self.Blocks[l.id][f.period], start=0, end=f.period)

        # Condition (i): Link va_vb is available in [t, t+frame.length]
        for iv in free_blocks:
            if iv.end - f.length >= iv.begin:
                feasible_region.add(Interval(iv.begin, iv.end - f.length))

        # Condition (iii): Chop out queue occupations of other streams on next link
        # TODO: Improve performance: Create datastructure that holds feasible region and update it
        for f_next in f.next_frames:
            if isinstance(f_next.l_or_es, link):
                for other_frame in self.all_frames_on_link[f_next.l_or_es.id]:
                    if other_frame != f_next:
                        feasible_region.chop(other_frame.prev_frame.offset, other_frame.offset)

        # TODO: Condition (ii)
        return sorted(feasible_region)

    def _get_feasible_region_es(self, f: frame, es: end_system) -> IntervalTree:
        feasible_region = IntervalTree()
        free_blocks = sorted_complement(self.Blocks[es.id][f.period], start=0, end=f.period)

        for iv in free_blocks:
            if iv.end - f.length >= iv.begin:
                feasible_region.add(Interval(iv.begin, iv.end - f.length))

        return sorted(feasible_region)

    def _block_queues(self, tgn: TaskGraphNode):
        s_or_t, l_or_es_list = self._extract_from_tgn(tgn)

        if isinstance(s_or_t, stream):
            s : stream = s_or_t

            for l_or_es in l_or_es_list:
                start_time = self.frames[tgn.id][l_or_es.id].offset
                if isinstance(l_or_es, link):
                    l : link = l_or_es
                    offsets = [start_time + i*s.period for i in range(0, int(self.tc.hyperperiod/s.period))]
                    endtimes = [start_time + l.transmission_length(s.size) + i*s.period for i in range(0, int(self.tc.hyperperiod/s.period))]

                    self._block(offsets, endtimes, l_or_es)
                elif isinstance(l_or_es, end_system):
                    es: end_system = l_or_es
                    offsets = [start_time + i * s.period for i in range(0, int(self.tc.hyperperiod / s.period))]
                    endtimes = [start_time + es.mac_exec_time + i * s.period for i in
                                range(0, int(self.tc.hyperperiod / s.period))]
                    self._block(offsets, endtimes, l_or_es)
                else:
                    raise ValueError
        elif isinstance(s_or_t, task):
            t : task = s_or_t
            for l_or_es in l_or_es_list:
                start_time = self.frames[tgn.id][l_or_es.id].offset
                if isinstance(l_or_es, end_system):
                    es: end_system = l_or_es
                    offsets = [start_time + i * t.period for i in range(0, int(self.tc.hyperperiod / t.period))]
                    endtimes = [start_time + t.exec_time + i * t.period for i in
                                range(0, int(self.tc.hyperperiod / t.period))]
                    self._block(offsets, endtimes, l_or_es)
                else:
                    raise ValueError
        else:
            raise ValueError

    def _block(self, offsets: List[int], endtimes: List[int], l_or_es: Union[link, end_system]):
        assert len(offsets) == len(endtimes)

        for T in self.tc.Periods:
            for i in range(len(offsets)):
                o = offsets[i]
                e = endtimes[i]

                # block on va_vb [offset, offset+length]

                if e%T < o%T:
                    # if block wraps around
                    self.Blocks[l_or_es.id][T].add(Interval(o % T, T))
                    if e%T > 0:
                        self.Blocks[l_or_es.id][T].add(Interval(0, e%T))
                else:
                    self.Blocks[l_or_es.id][T].add(Interval(o % T, e % T))

    def _latest_queue_available_time(self, f: frame, offset: int):
        """
        Returns the latest point in time where the queue in egress port "link" is available and has been continuously since time "offset"
        """
        feasible_region = self._get_feasible_region(f, f.l_or_es)
        latest_available_time = -1

        # Return the end of the right-open interval that contains offset OR the first interval that begins after offset
        for iv in feasible_region:
            if iv.contains_point(offset):
                latest_available_time = iv.end
                break
            elif iv.begin > offset:
                latest_available_time = iv.end
                break

        return latest_available_time

    def _earliest_queue_available_time(self, f: frame, offset: int):
        """
        Returns the earliest point of time from which queue in egress port "l" is available until "offset"
        """
        feasible_region = self._get_feasible_region(f, f.l_or_es)
        earliest_available_time = -1

        # Return the begin of the closed interval that contains offset
        for iv in feasible_region:
            if iv.contains_point(offset) or iv.end == offset:
                earliest_available_time = iv.begin
                break

        return earliest_available_time

    def _is_first_instance(self, frm : frame):
        # TODO: Replace by frm.prev == None
        if isinstance(frm.s_or_t, task):
            return True
        elif isinstance(frm.s_or_t, stream):
            if frm.l_or_es.id == frm.s_or_t.sender_es_id:
                return True
            if isinstance(frm.l_or_es, link) and frm.l_or_es.src.id == frm.s_or_t.sender_es_id and not frm.s_or_t.is_secure:
                return True
        return False


