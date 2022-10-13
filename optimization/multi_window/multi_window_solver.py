import copy
import math
import random
import subprocess
import time
from enum import Enum
from pathlib import Path
import socket
from typing import Tuple, List, Dict, Optional

from input.model.route import route

from input.model.link import link

from input.model.stream import stream

from input import testcase
from input.input_parameters import InputParameters
from input.testcase import Testcase
from optimization.multi_window.multi_window_schedule import MultiWindowInitialSchedule
from solution.solution_optimization_status import EOptimizationStatus
from solution.solution_timing_data import TimingData
from utils import serializer
from utils.utilities import Timer, debug_print, get_results_from_luxis_tool, sorted_complement, \
    get_available_intervals_for_length

from intervaltree import IntervalTree, Interval

class MultiWindowOptimizationMode(Enum):
    NORMAL = 0


class Window:
    def __init__(self, offset, length, period, link_speed, priority, guard_band, minimum_size):
        self.offset = offset
        self.length = length
        self.period = period
        self.end = offset+length

        self.link_speed = link_speed
        self.priority = priority
        self.guard_band = guard_band
        self.minimum_size = minimum_size

    def __repr__(self):
        return f"({self.offset},{self.end},{self.period},{self.priority})"

    def set_length(self, length, guardband):
        # length is excluding guardband
        self.guard_band = math.ceil(guardband)
        self.length = math.ceil(length + self.guard_band)
        self.end = self.offset + self.length

    def extend(self, by_percentage: float):
        self.set_length(int((self.length-self.guard_band)*by_percentage), self.guard_band)

    def move(self, new_offset: int):
        self.offset = new_offset
        self.set_length(self.length, self.guard_band)

class MultiWindowSchedulingSolution:
    def __init__(self, tc: Testcase, base_schedule: MultiWindowInitialSchedule):
        self.tc = tc
        self.inital_schedule = base_schedule

        self.schedule : Dict[str, Dict[int, List[Window]]] = {} # l_id -> {priority -> List[Window]}
        self.port_combined_windows : Dict[str, IntervalTree] = {}

        self.create_solution_from_base_schedule()

    def delete_random_window(self):
        l_id = random.choice(list(self.schedule.keys()))
        priority = random.choice(list(self.schedule[l_id].keys()))

        index = random.randint(0, len(self.schedule[l_id][priority])-1)
        wnd = self.schedule[l_id][priority][index]
        self.port_combined_windows[l_id].remove(Interval(wnd.offset, wnd.end))
        self.schedule[l_id][priority].pop(index)

    def add_random_window(self):
        l_id = random.choice(list(self.schedule.keys()))
        priority = random.choice(list(self.schedule[l_id].keys()))

        # take minimum length
        length = self.tc.min_windows_sizes[l_id][priority]
        random_offset = random.randint(0, self.tc.hyperperiod)

        feasible_region = get_available_intervals_for_length(self.port_combined_windows[l_id], length, 0, self.tc.hyperperiod)
        feasible_offset = -1
        for i in range(len(feasible_region)):
            if feasible_region[i].end >= random_offset:
                if feasible_region[i].begin <= random_offset:
                    feasible_offset = random_offset
                else:
                    dist_previous = random_offset - feasible_region[i-1].end if i > 0 else -1
                    dist_next = feasible_region[i].begin - random_offset
                    if dist_previous == -1:
                        feasible_offset = feasible_region[i].begin
                    else:
                        feasible_offset = feasible_region[i-1].end if dist_previous < dist_next else feasible_region[i].begin

                break

        w = Window(feasible_offset, length, self.tc.hyperperiod, self.tc.L[l_id].speed, priority, 0, self.tc.min_windows_sizes[l_id][priority])
        self.schedule[l_id][priority].append(w)
        self.port_combined_windows[l_id].add(Interval(w.offset, w.end))

        print(f"Created window {w} on {l_id}")

    def extend_random_window(self, max_percentage: float):
        l_id = random.choice(list(self.schedule.keys()))
        priority = random.choice(list(self.schedule[l_id].keys()))
        w = random.choice(self.schedule[l_id][priority])

        old_offset = w.offset
        old_Length = w.length


        percentage = random.uniform(w.minimum_size / w.length, min(max_percentage, (w.period - w.offset) / w.length))
        w.extend(percentage)
        self.port_combined_windows[l_id].remove(Interval(old_offset, old_offset+old_Length))
        self.port_combined_windows[l_id].add(Interval(w.offset, w.end))
        #print(f"Extended window {w} on {l_id} from {old_Length} to {w.length}")

    def create_solution_from_base_schedule(self):
        for s_id, dct in self.inital_schedule.windows.items():
            s = self.tc.F[s_id]
            priority = s.priority
            for l_id, wnd_list in dct.items():
                l = self.tc.L[l_id]
                if l_id not in self.schedule:
                    self.schedule[l_id] = {}
                    self.port_combined_windows[l_id] = IntervalTree()
                if priority not in self.schedule[l_id]:
                    self.schedule[l_id][priority] = []
                for wnd in wnd_list:
                    # Assume hyperperiod and wnd.period are harmonic (hyperperiod % wnd.period == 0)
                    for i in range(self.tc.hyperperiod//wnd.period):
                        offset_i = i*wnd.period + wnd.offset
                        end_i = offset_i + wnd.length
                        self.schedule[l_id][priority].append(Window(offset_i, wnd.length, self.tc.hyperperiod, l.speed, priority, 0, self.tc.min_windows_sizes[l_id][priority]))
                        self.port_combined_windows[l_id].add(Interval(offset_i, end_i))

    def get_bandwidth_cost(self) -> float:
        # occpuating percentage sum divided by amount of ports
        bwsum = 0
        for l_id, iv_tree in self.port_combined_windows.items():
            # create temporary intervaltree and merge overlapping windows
            temp_tree = IntervalTree(iv_tree.items())
            temp_tree.merge_overlaps()
            for iv in temp_tree:
                bwsum += (iv.end-iv.begin)/self.tc.hyperperiod

        # divide the sum by amount of ports
        bwsum = bwsum / len(self.port_combined_windows.keys())
        return bwsum


class MultiWindowSASchedulingSolver:
    def __init__(self, tc: Testcase, timing_object: TimingData, input_params: InputParameters):
        self.tc = tc

        self.cost = -1
        self.infeasible_streams = -1
        self.stream_costs = None

        self.input_params = input_params
        self.b = input_params.b

    def _start_luxis_tool(self, sol: MultiWindowSchedulingSolution) -> socket:
        luxi_path = Path(".") / "luxi"
        luxi_path.mkdir(exist_ok=True)
        serializer.create_luxi_files_multi_window(luxi_path, self.tc, sol)
        print("Created TSNNetCal input files")

        wcdtool_path = "luxi/"
        try:
            # .\TSNNetCal.exe ..\luxi\ C:\Users\phd\Nextcloud\PhD\Projects\NetCal\RTCtoolbox\rtc.jar
            log_f = open("log.txt", "wb")
            proc = subprocess.Popen(
                [wcdtool_path + 'TSNNetCal.exe', "luxi\\",
                      r"C:\Users\phd\Nextcloud\PhD\Projects\NetCal\RTCtoolbox\rtc.jar"], stdout=log_f)
            time.sleep(1)

            input("Please start TSNNetCal")
            print("TSNNetCal started")
        except subprocess.TimeoutExpired:
            print('TSNNetCal Timeout')
            return None

        HOST = '127.0.0.1'  # The server's hostname or IP address
        PORT = 27015  # The port used by the server
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        try:
            s.connect((HOST, PORT))
            s.settimeout(30)
            print("Connected to socket")
        except (TimeoutError, ConnectionRefusedError) as e:
            print("Socket Error")
            print(e)
            proc.kill()

        return s

    def _cost(self, sol: MultiWindowSchedulingSolution, sock):
        start = time.time()

        #print("Calculating cost for this solution:")
        #print(sol)
        #print()
        # Run luxis tool
        #
        wcportdelay_list, wce2edelay_list = get_results_from_luxis_tool(sock, serializer.luxi_sched_from_multiwindow_solution(self.tc, sol))

        #print(wcportdelay_list)
        #print(wce2edelay_list)
        #print()

        # Parse results
        stream_costs = {}
        e2e_sum = 0
        exceeding_sum = 0
        infeasible_streams = 0
        for l in wce2edelay_list:
            s_id = l.strip().split(",")[0]
            cost = l.strip().split(":")[1]

            if cost == "1.#INF":
                stream_costs[s_id] = -1
                infeasible_streams += 1
            else:
                stream_costs[s_id] = float(cost)
                if stream_costs[s_id] > self.tc.F[s_id].deadline:
                    exceeding_sum += stream_costs[s_id] - self.tc.F[s_id].deadline
                    infeasible_streams += 1
                e2e_sum += stream_costs[s_id]

        port_costs = {}
        for l in wcportdelay_list:
            link = l.strip().split(":")[0]
            linK_a = link.split(" -> ")[0]
            linK_b = link.split(" -> ")[1].split(" ")[0]
            lnk = self.tc.L_from_nodes[linK_a][linK_b]

            cost = float(l.strip().split(":")[1].split(",")[0].strip())

            if cost == "inf":
                port_costs[lnk.id] = -1
            else:
                port_costs[lnk.id] = float(cost)



        # bandwidth_cost is between 0 and 1
        bw = sol.get_bandwidth_cost()
        cost = 1000*bw + 100000 * exceeding_sum
        return cost, infeasible_streams, stream_costs, bw, exceeding_sum


    def _probability_check(self, delta, t):
        return random.uniform(0, 1) < self.p(delta, t)

    def p(self, delta, t):
        return math.e ** (-1 * (delta / t))

    def _solve(self, timing_object: TimingData, input_params: InputParameters):
        Tstart = input_params.Tstart
        alpha = input_params.alpha
        SCHEDULING_MOVE_PROBABILITY = 1 - input_params.Prmv
        temp_reset = False

        first_feasible_time = -1

        total_timer = Timer()
        with total_timer:
            inital_schedule = MultiWindowInitialSchedule(self.tc)
        timing_object.time_creating_vars_simulated_annealing = total_timer.elapsed_time
        inital_schedule.schedule()
        s_i = MultiWindowSchedulingSolution(self.tc, inital_schedule)

        s_best = s_i
        sock = self._start_luxis_tool(s_best)
        start = time.time()
        best_cost, infeasible_streams, stream_costs, bw, exceeding_sum = self._cost(s_best, sock)
        print(f"Running MultiWindow-Metaheuristic: Tstart {Tstart}, alpha {alpha}")
        print(f"INITIAL COST: {best_cost}; INFEASIBLE Streams: {infeasible_streams}; Bandwidth cost: {bw}; Exceeding sum: {exceeding_sum}\n")
        print(stream_costs)
        print(f"Mean worst-case e2e delay: {sum(stream_costs.values())/len(stream_costs.values())}")

        if infeasible_streams == 0 and first_feasible_time == -1:
            first_feasible_time = time.time() - start
            print(f"FIRST FEASIBLE SOLUTION after {first_feasible_time}")
            timing_object.time_first_feasible_solution = first_feasible_time

        print(f"SCHEDULING SOLUTION:\n{s_best}")
        # print_simple_solution(s_i, index_to_core_map)
        debug_print("")

        temp = Tstart
        step = 0


        neighbour_time = 0
        cost_time = 0
        total_time = 0


        while time.time() - start < input_params.timeouts.timeout_scheduling:
            total_timer = Timer()
            with total_timer:
                nigh_timer = Timer()
                with nigh_timer:
                    s_neigh = self._random_neighbour(s_i)
                neighbour_time = nigh_timer.elapsed_time
                cost_timer = Timer()
                with cost_timer:
                    old_cost, _, _, _, _ = self._cost(s_i, sock)
                    new_cost, infeasible_streams, stream_costs, bw, exceeding_sum = self._cost(s_neigh, sock)
                cost_time = cost_timer.elapsed_time
                if infeasible_streams == 0 and first_feasible_time == -1:
                    first_feasible_time = time.time() - start
                    print(f"FIRST FEASIBLE SOLUTION after {first_feasible_time}")
                    timing_object.time_first_feasible_solution = first_feasible_time


                delta = new_cost - old_cost  # new_cost - old_cost, because we want to minimize cost

                if delta < 0 or self._probability_check(delta, temp):
                    s_i = s_neigh

                    if new_cost < best_cost:
                        s_best = s_neigh
                        best_cost = new_cost
                        print(
                            f"NEW BEST COST: {best_cost}; INFEASIBLE Streams: {infeasible_streams}; Bandwidth cost: {bw}; Exceeding sum: {exceeding_sum}; TEMP: {temp}")
                        print(stream_costs)
                        print(f"Mean worst-case e2e delay: {sum(stream_costs.values()) / len(stream_costs.values())}\n")

                if not temp_reset:
                    oldtemp = temp
                    temp = temp * alpha
                    if temp == 0:
                        temp = oldtemp
                        print(f"WARNING: Temperature reached zero due to float limitations. Resetting to prev temp")
                        temp_reset = True
                step += 1
            total_time = total_timer.elapsed_time
            #print(f"{neighbour_time}({neighbour_time/total_time}) {cost_time}({cost_time/total_time}) {total_time}")

        return s_best

    def optimize(
        self, input_params: InputParameters, timing_object: TimingData, mode: MultiWindowOptimizationMode
    ) -> Tuple[Testcase, MultiWindowInitialSchedule, EOptimizationStatus]:

        status = EOptimizationStatus.INFEASIBLE
        t = Timer()
        with t:
            if mode == MultiWindowOptimizationMode.NORMAL:
                schedule_solution = self._solve(timing_object, input_params)
            else:
                raise ValueError

        print(schedule_solution)
        timing_object.time_optimizing_scheduling = t.elapsed_time

        print("Optimization done")
        return self.tc, schedule_solution, status

    def _random_neighbour(self, s_i: MultiWindowSchedulingSolution) -> MultiWindowSchedulingSolution:
        s_new = copy.deepcopy(s_i)

        p = random.uniform(0, 1)

        if p < 1:
            s_new.extend_random_window(2.0)
        elif p < 0.9:
            pass
            #s_new.add_random_window()
        else:
            pass
            #s_new.delete_random_window()

        return s_new
        # TODO: moves