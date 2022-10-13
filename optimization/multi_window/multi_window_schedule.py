from typing import Dict, List, Tuple

from input.model.nodes import end_system

from input.model.route import route

from utils.utilities import sorted_complement, debug_print

from input.model.link import link

from input.model.stream import stream
from intervaltree import IntervalTree, Interval

from input.testcase import Testcase

class Window:
    def __init__(self, s, l, lb: int, ub: int, length: int, offset: int, period: int, prev_window,
                 next_window, is_first_instance):
        self.s = s
        self.l = l
        self.lb = lb
        self.ub = ub
        self.length = length
        self.offset = offset
        self.period = period

        self.prev_window: Window = prev_window
        self.next_window: Window = next_window

        self.is_first_instance = is_first_instance

    def __repr__(self):
        return f"({self.l}, {self.offset}, {self.offset + self.length})"

class MultiWindowInitialSchedule:
    def __init__(self, tc: Testcase):
        self.tc = tc

        self.StartTimes: Dict[str, List[Tuple[int, int]]] = {}
        self.Blocks: Dict[str, Dict[int, IntervalTree]] = {}
        self.windows: Dict[str, Dict[str, List[Window]]] = {} # s_id
        self.all_windows_on_link: Dict[str, List[Window]] = {} # l_id

        for l_id in self.tc.L.keys():
            if not isinstance(self.tc.L[l_id].src, end_system):
                self.Blocks[l_id] = {}
                for T in self.tc.Periods:
                    self.Blocks[l_id][T] = IntervalTree()

    def _create_initial_windows(self, s: stream, hops: List[link]):
        # Creates an initial window along each hop of stream s
        # window = frame in TESLA implementation
        link_to_window_dict = {}

        is_first_instance = True
        for l in hops:
            w = Window(s, l, -1, -1, l.transmission_length(s.size),
                      -1, s.period, None, None, is_first_instance)
            is_first_instance = False

            if l.id not in self.all_windows_on_link:
                self.all_windows_on_link[l.id] = [w]
            else:
                self.all_windows_on_link[l.id].append(w)

            link_to_window_dict[l.id] = [w]

            r: route = self.tc.R[s.id]
            previous_links = r.get_predeccessor_link(l.id, self.tc)

            # Connect window with previous window
            for prev_l in previous_links:
                if not isinstance(prev_l.src, end_system):
                    prev_window = link_to_window_dict[prev_l.id][0]
                    prev_window.next_window = w
                    w.prev_window = prev_window

        return link_to_window_dict

    def _calc_lower_bound(self, s: stream, w: Window):
        assert s == w.s
        lb = 0

        if w.is_first_instance:
            # For the first stream instance, set the lower bound to 0
            lb = 0
        else:
            # For consecutive stream instances, set the lower bound to the max end-time of the stream on the previous link
            lb = max(lb, w.prev_window.offset + w.prev_window.length)

        # frm.lb might have been set from outside. Thus return the max
        return max(lb, w.lb)

    def _get_feasible_region(self, w: Window, l: link) -> List[Interval]:
        # returns a sorted list of intervals
        feasible_region = IntervalTree()
        free_blocks = sorted_complement(self.Blocks[l.id][w.period], w, start=0, end=w.period)

        # Condition (i): Link va_vb is available in [t, t+window.length]
        # TODO: Null intervals allowed? iv.begin == iv.end - f.length
        for iv in free_blocks:
            if iv.end - w.length > iv.begin:
                feasible_region.add(Interval(iv.begin, iv.end - w.length))

        # Condition (iii): Chop out queue occupations of other streams on next link
        # TODO: Improve performance: Create datastructure that holds feasible region and update it
        f_next = w.next_window
        if f_next != None:
            for other_window in self.all_windows_on_link[f_next.l.id]:
                if other_window != f_next:
                    feasible_region.chop(other_window.prev_window.offset, other_window.offset)

        # TODO: Condition (ii)
        return sorted(feasible_region)

    def _earliest_offset(self, l: link, w: Window):
        """
        Returns the earliest offset in the free intervals for given stream on given link, which is >=
        w.lb and where the window fits inside the interval
        """
        intervals = self._get_feasible_region(w, l)

        for iv in intervals:
            offset = max(w.lb, iv.begin)
            # consider intervals right-open
            if iv.contains_point(offset):
                return offset

        return -1

    def _earliest_queue_available_time(self, w: Window, offset: int):
        """
        Returns the earliest point of time from which queue in egress port "l" is available until "offset"
        """
        feasible_region = self._get_feasible_region(w, w.l)
        earliest_available_time = -1

        # Return the begin of the closed interval that contains offset
        for iv in feasible_region:
            if iv.contains_point(offset) or iv.end == offset:
                earliest_available_time = iv.begin
                break

        return earliest_available_time

    def _latest_queue_available_time(self, w: Window, offset: int):
        """
        Returns the latest point in time where the queue in egress port "link" is available and has been continuously since time "offset"
        """
        feasible_region = self._get_feasible_region(w, w.l)
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

    def _block_queues(self, s: stream):
        hops = self.tc.R[s.id].get_all_links_dfs(self.tc)
        # remove first link
        hops = hops[1:]
        for l in hops:
            # TODO: multiple windows
            start_time = self.windows[s.id][l.id][0].offset

            offsets = [start_time + i*s.period for i in range(0, int(self.tc.hyperperiod/s.period))]
            endtimes = [start_time + l.transmission_length(s.size) + i*s.period for i in range(0, int(self.tc.hyperperiod/s.period))]

            self._block(offsets, endtimes, l)

    def _block(self, offsets: List[int], endtimes: List[int], l: link):
        assert len(offsets) == len(endtimes)

        for T in self.tc.Periods:
            for i in range(len(offsets)):
                o = offsets[i]
                e = endtimes[i]

                # block on va_vb [offset, offset+length]

                if e%T < o%T:
                    # if block wraps around
                    self.Blocks[l.id][T].add(Interval(o % T, T))
                    if e%T > 0:
                        self.Blocks[l.id][T].add(Interval(0, e%T))
                else:
                    self.Blocks[l.id][T].add(Interval(o % T, e % T))

    def get_bandwidth_cost(self):
        c = 0
        wnd_count = 0
        for l_id, wnd_list in self.all_windows_on_link.items():
            for wnd in wnd_list:
                c += wnd.length / wnd.s.period
                wnd_count += 1

        return (c / wnd_count) * 1000

    def schedule(self) -> bool:
        # for each stream
        # for each hop
        # create window ASAP
        infeasible_streams = []

        for s in self.tc.F.values():
            hops = self.tc.R[s.id].get_all_links_dfs(self.tc)

            # optimistic window chain period
            window_chain_period = s.deadline - sum([hops[i].transmission_length(s.size) for i in range(len(hops))])
            if not self.schedule_stream(s):
                infeasible_streams.append(s)
                print(f"{s} was impossible to schedule")
        return (len(infeasible_streams) == 0)


    def schedule_stream(self, s):
        hops = self.tc.R[s.id].get_all_links_dfs(self.tc)
        # remove first link from es
        hops = hops[1:]

        link_to_window_dict = self._create_initial_windows(s, hops)
        self.windows[s.id]: Dict[str, Dict[str, List[Window]]] = link_to_window_dict

        # Begin ASAP scheduling
        finished = False
        i = 0
        l = hops[0]
        while True:
            # TODO: Multiple windows
            w = self.windows[s.id][l.id][0]
            w.lb = self._calc_lower_bound(s, w)
            offset = self._earliest_offset(l, w)
            debug_print(f"\tCurrent window on {w.l.id}: LB {w.lb}, UB {w.ub}, Calc. Offset {offset}")

            if offset == -1:
                return False
            elif offset <= w.ub or w.ub == -1:
                w.offset = offset
                debug_print(f"\t\tScheduled window on {w.l.id} for [{w.offset},{w.offset + w.length}]")

                # Set upper bound of following window
                f_next = w.next_window
                if f_next != None:
                    lqat = self._latest_queue_available_time(f_next, offset)

                    if lqat != -1:
                        f_next.ub = lqat
                        debug_print(f"\t\tSetting upper bound for window on {f_next.l.id} to {lqat}")
                    else:
                        return False

                i += 1
                if i < len(hops):
                    l = hops[i]
                else:
                    finished = True
            else:
                eqat = self._earliest_queue_available_time(w, offset)

                # Set lower bound of previous window
                if w.prev_window != None:
                    if eqat != -1:
                        w.prev_window.lb = eqat
                        debug_print(f"BACKTRACKING")
                        debug_print(f"\t\tSetting lower bound for window on {w.l.id} to {eqat}")
                    else:
                        return False
                else:
                    return False

                l = w.prev_window.l
                i = hops.index(w.prev_window.l)

            if finished:
                break

        # Only block queues if all blocks were scheduled!
        self._block_queues(s)

        return True