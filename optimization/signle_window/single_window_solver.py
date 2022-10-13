import copy
import itertools
import math
import os
import random
import subprocess
import time
from enum import Enum
from pathlib import Path
import socket
from typing import Tuple, List, Dict

from intervaltree import IntervalTree, Interval

from input.model.stream import stream

from input import testcase
from input.input_parameters import InputParameters
from input.testcase import Testcase
from solution.solution_optimization_status import EOptimizationStatus
from solution.solution_timing_data import TimingData
from utils import serializer
from utils.cost import cost_SA_scheduling_solution
from utils.utilities import Timer, debug_print, get_results_from_luxis_tool, lcm, divisorGenerator, list_gcd, \
    get_available_intervals_for_length, get_available_intervals, get_available_intervals_including_window, \
    get_random_offset_in_intervals


class SAOptimizationMode(Enum):
    NORMAL = 0

class Window:
    def __init__(self, offset, length, period, link_speed, priority, guard_band, min_sending_time):
        self.offset = offset
        self.length = length
        self.period = period
        self.end = offset+length

        self.link_speed = link_speed
        self.priority = priority
        self.guard_band = guard_band
        self.min_sending_time = min_sending_time


    def __repr__(self):
        return f"({self.offset},{self.end},{self.period})"


    def set_length(self, length, guardband):
        # length is excluding guardband
        self.guard_band = math.ceil(guardband)
        self.length = math.ceil(length + self.guard_band)
        self.end = self.offset + self.length

    def length_from_streamsize(self, stream_size, stream_period):
        # stream_size: Byte
        # link_speed: Byte/us
        return math.ceil(((stream_size/stream_period) / self.link_speed) * self.period)


    def extend(self, by_percentage: float):
        new_length = int((self.length)*by_percentage-self.guard_band)
        new_length = max(self.min_sending_time-self.guard_band, new_length)
        self.set_length(new_length, self.guard_band)
        assert self.end <= self.period
        assert self.length >= self.min_sending_time

    def move(self, new_offset: int):
        self.offset = new_offset
        self.set_length(self.length - self.guard_band, self.guard_band)
        assert self.end <= self.period
        assert self.length >= self.min_sending_time

class SASchedulingSolution:
    def __init__(self, tc: testcase):
        self.tc = tc
        self.W : Dict[str, Dict[int, Window]] = {}
        self.W_active : List[Window] = []
        self.port_combined_windows : Dict[str, IntervalTree] = {}

        self.cost = -1
        self.infeasible_streams = -1
        self.stream_costs = None

        for l_id in tc.F_l_out.keys():
            if tc.L[l_id].src.id not in tc.ES:
                self.W[l_id] = {}

                self.port_combined_windows[l_id] = IntervalTree()

        self.W_amount = len(self.W.keys()) * 8

    def get_length_list_for_port(self, l_id: str) -> List[Tuple[Tuple[int, int], int]]:
        # [((offset,end), priority)]
        # assume that window periods divide hyperperiod
        tpls = []
        windows = self.W[l_id].values()
        for w in windows:
            if w.length > 0:
                for instance in range(self.tc.hyperperiod // w.period):
                    tpls.append(((w.offset+instance*w.period, w.end+instance*w.period), w.priority))

        tpls.sort(key=lambda tup: tup[0][0])
        return tpls

    def move_window(self, w, l_id, new_offset):
        assert new_offset >= 0
        assert new_offset + w.length <= w.period
        self.port_combined_windows[l_id].remove(Interval(w.offset, w.end))
        w.move(new_offset)
        self.port_combined_windows[l_id].add(Interval(w.offset, w.end))

    def move_random_window(self):
        l_id = random.choice(list(self.W.keys()))
        priority = random.choice(list(self.W[l_id].keys()))

        w = self.W[l_id][priority]
        old_w_str = str(w)

        feasible_region = get_available_intervals_including_window(self.port_combined_windows[l_id], w, w.length, 0,
                                                             w.period)

        random_offset = get_random_offset_in_intervals(feasible_region)

        if random_offset != None:
            self.move_window(w, l_id, random_offset)
            #print(f"Moved window {l_id} {priority} from {old_w_str} to {w}")

    def extend(self, w, l_id, percentage):
        self.port_combined_windows[l_id].remove(Interval(w.offset, w.end))
        w.extend(percentage)
        self.port_combined_windows[l_id].add(Interval(w.offset, w.end))

    def extend_random_window(self, max_percentage: float):
        # extend/shrink window up to beginning of another window
        l_id = random.choice(list(self.W.keys()))
        priority = random.choice(list(self.W[l_id].keys()))

        w = self.W[l_id][priority]
        feasible_region = get_available_intervals(self.port_combined_windows[l_id], 0,
                                                             w.period)


        max_end = w.end
        # assume feasible-region is sorted
        for iv in feasible_region:
            if iv.begin == w.end:
                max_end = iv.end

        old_w_str = str(w)
        max_length = w.length + (max_end-w.end)
        percentage = random.uniform(w.min_sending_time/w.length, min(max_percentage, max_length/w.length))
        self.extend(w, l_id, percentage)
        #print(f"Extended window {l_id} {priority} from {old_w_str} to {w}")

        t_copy = copy.deepcopy(self.port_combined_windows[l_id])
        t_copy.merge_overlaps()
        if(len(self.port_combined_windows[l_id]) > len(t_copy)):
            raise ValueError


    def __repr__(self):
        s = ""
        for l_id in self.W.keys():
            l = self.tc.L[l_id]
            s += f"{l.src.id},{l.dest.id}\n"
            for w in self.W[l_id].values():
                if w.length > 0:
                    s += f"{w.offset}\t{w.end}\t{w.period}\t{w.priority}\n"
            s += "\n"
        s += "#"
        return s

    def get_luxi_gcl(self):
        return self.__repr__()

    def get_bandwidth_cost(self):
        c = 0
        for w in self.W_active:
            c += w.length/w.period
        return (c / len(self.W_active))*1000

    def add_stream_to_window(self, l_id:str, s: stream):
        success = True

        if self.W[l_id][s.priority].extend(s.size, s.period):
            for i in range(s.priority+1,8):
                if not self.W[l_id][i].move(s.size, s.period):
                    # TODO: Reset other windows
                    return False
        else:
            return False

        return True


class SingleWindowSASchedulingSolver:
    def __init__(self, tc: Testcase, timing_object: TimingData, input_params: InputParameters):
        self.tc = tc

        # Create variables
        t = Timer()
        with t:
            self._create_variables()
        timing_object.time_creating_vars_scheduling = t.elapsed_time

        self.input_params = input_params
        self.b = input_params.b


    def _create_variables(self):
        pass

    def _initial_solution(self) -> SASchedulingSolution:
        sol = SASchedulingSolution(self.tc)




        for l_id in sol.W.keys():
            if l_id == "link_SW2_ES11":
                print("bla")
            tpls = {}
            periods = []
            port_max_period = 0

            stream_periods = [self.tc.F[s_id].period for s_id in self.tc.F_l_out[l_id]]
            potential_periods = sorted(set([self.tc.F[s_id].period for s_id in self.tc.F_l_out[l_id]]))
            stream_lengths = [self.tc.L[l_id].transmission_length(self.tc.F[s_id].size) for s_id in self.tc.F_l_out[l_id]]
            stream_priorities = set([self.tc.F[s_id].priority for s_id in self.tc.F_l_out[l_id]])
            length_sum = sum(stream_lengths) + len(stream_priorities)*max(stream_lengths)

            port_period = 0
            gcd = list_gcd(stream_periods)
            potential_periods.append(gcd)
            potential_periods.append(math.ceil(gcd/2))
            potential_periods = sorted(potential_periods)
            for i in range(len(potential_periods)):
                if potential_periods[i] >= length_sum:
                    port_period = potential_periods[i]
                    break
            if port_period == 0:
                raise ValueError


            for priority in range(8):
                streams = [self.tc.F[s_id] for s_id in self.tc.F_l_out[l_id] if self.tc.F[s_id].priority == priority]

                if len(streams) > 0:
                    sol.W[l_id][priority] = Window(0, 0, self.tc.hyperperiod, self.tc.link_speed, priority, 0, 0)
                    stream_lengths = [math.ceil(s.size/self.tc.link_speed) for s in streams]
                    stream_period_percentages = [math.ceil(s.size/self.tc.link_speed)/s.period for s in streams]
                    periods = [s.period for s in streams]

                    #total_sending_time = sum(stream_lengths)
                    period_percentage_sum = sum(stream_period_percentages)
                    total_sending_time = math.ceil(period_percentage_sum*port_period)
                    total_sending_time = max(total_sending_time, sum(stream_lengths))
                    guardband = math.ceil(max(stream_lengths))
                    length = total_sending_time+guardband
                    period = math.ceil((length-guardband)/period_percentage_sum)
                    if period > port_max_period:
                        port_max_period = period

                    tpls[priority] = (total_sending_time, guardband, length, period)




            current_offset = 0
            for priority in tpls.keys():
                total_sending_time, guardband, length, period = tpls[priority]
                w = sol.W[l_id][priority]
                w.offset = current_offset
                scale_factor = port_period/w.period
                #window_list[priority].set_length(total_sending_time*scale_factor,guardband)
                w.set_length(total_sending_time,guardband)
                w.period = port_period
                w.min_sending_time = total_sending_time


                sol.port_combined_windows[l_id].add(Interval(w.offset, w.end))
                sol.W_active.append(w)
                current_offset += w.length



        return sol

    def _start_luxis_tool(self, sol, port) -> socket:
        luxi_path = Path(".") / "luxi_singlewindow" / str(port)
        luxi_path.mkdir(exist_ok=True)
        serializer.create_luxi_files_single_window(luxi_path, self.tc, sol)
        print("Created TSNNetCal input files")

        wcdtool_path = "luxi_singlewindow\\" + str(port) + "\\"

        try:
            # .\TSNNetCal.exe ..\luxi\ C:\Users\phd\Nextcloud\PhD\Projects\NetCal\RTCtoolbox\rtc.jar
            log_f = open(f"log_singlewindow_{port}.txt", "wb")
            proc = subprocess.Popen(
                [wcdtool_path + 'TSNNetCal.exe', wcdtool_path,
                 r"C:\Users\phd\Nextcloud\PhD\Projects\NetCal\RTCtoolbox\rtc.jar", str(port)], stdout=log_f)
            time.sleep(5)

            #input("Please start TSNNetCal")
            print(f"TSNNetCal started at {wcdtool_path} {port}")
        except subprocess.TimeoutExpired:
            print('TSNNetCal Timeout')
            return None

        HOST = '127.0.0.1'  # The server's hostname or IP address
        PORT = port  # The port used by the server
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(30)
        try:
            s.connect((HOST, PORT))
            s.settimeout(60)
            print("Connected to socket")
        except (TimeoutError, ConnectionRefusedError) as e:
            print("Socket Error")
            print(e)
            proc.kill()

        return s, proc

    def _cost(self, sol: SASchedulingSolution, sock):
        start = time.time()

        #print("Calculating cost for this solution:")
        #print(sol)
        #print()
        # Run luxis tool
        #
        infeasible_streams, stream_costs, port_costs = get_results_from_luxis_tool(sock, sol.get_luxi_gcl(), self.tc)

        #print(wcportdelay_list)
        #print(wce2edelay_list)
        #print()

        # Parse results




        cost = sol.get_bandwidth_cost() + 1000*infeasible_streams
        #print(f"Cost took: {(time.time()-start)*1000}ms")
        sol.cost = cost
        sol.infeasible_streams = infeasible_streams
        sol.stream_costs = stream_costs
        return cost, infeasible_streams, stream_costs


    def _probability_check(self, delta, t):
        return random.uniform(0, 1) < self.p(delta, t)

    def p(self, delta, t):
        return math.e ** (-1 * (delta / t))

    def _solve_normal(self, timing_object: TimingData, input_params: InputParameters):
        Tstart = input_params.Tstart
        alpha = input_params.alpha
        SCHEDULING_MOVE_PROBABILITY = 1 - input_params.Prmv
        temp_reset = False

        first_feasible_time = -1


        s_i = (self._initial_solution())
        s_best = s_i
        sock, proc = self._start_luxis_tool(s_best, input_params.luxi_port)
        start = time.time()
        best_cost, infeasible_streams, stream_costs = self._cost(s_best, sock)
        print(f"Running SA-Combined-Metaheuristic: Tstart {Tstart}, alpha {alpha}")
        print(f"INITIAL COST: {best_cost}; INFEASIBLE Streams: {infeasible_streams}\n")
        print(stream_costs)
        if len(stream_costs.values()) != 0:
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


        while time.time() - start < input_params.timeouts.timeout_scheduling:
            s_neigh = self._random_neighbour(s_i)
            old_cost, _, _ = self._cost(s_i, sock)
            new_cost, infeasible_streams, stream_costs = self._cost(s_neigh, sock)
            #print(f"Cost: {new_cost}")

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
                        f"NEW BEST COST: {best_cost}; INFEASIBLE Streams: {infeasible_streams}; TEMP: {temp}")
                    print(stream_costs)
                    if len(stream_costs.values()) != 0:
                        print(f"Mean worst-case e2e delay: {sum(stream_costs.values()) / len(stream_costs.values())}\n")

            if not temp_reset:
                oldtemp = temp
                temp = temp * alpha
                if temp == 0:
                    temp = oldtemp
                    print(f"WARNING: Temperature reached zero due to float limitations. Resetting to prev temp")
                    temp_reset = True
            step += 1

        sock.close()
        proc.kill()
        return s_best

    def optimize(
        self, input_params: InputParameters, timing_object: TimingData, mode: SAOptimizationMode
    ) -> Tuple[Testcase, SASchedulingSolution, EOptimizationStatus]:

        status = EOptimizationStatus.INFEASIBLE
        t = Timer()
        with t:
            # OPTIMIZE
            if mode == SAOptimizationMode.NORMAL:
                schedule_solution = self._solve_normal(timing_object, input_params)
            else:
                raise ValueError

        timing_object.time_optimizing_scheduling = t.elapsed_time

        print("Optimization done")
        print(f"Best cost: {schedule_solution.cost}")
        print(schedule_solution)
        return self.tc, schedule_solution, status

    def _random_neighbour(self, s_i: SASchedulingSolution) -> SASchedulingSolution:
        s_new = copy.deepcopy(s_i)

        # TODO: smartly choose windows based on port delays
        p = random.uniform(0, 1)

        if p < 0.8:
            s_new.move_random_window()
        else:
            s_new.extend_random_window(2.0)

        return s_new