import math
import random
import time
from typing import Dict, Tuple, List

from intervaltree import IntervalTree, Interval
from ortools.sat.python import cp_model
from ortools.sat.python.cp_model import (FEASIBLE, INFEASIBLE, MODEL_INVALID,
                                         OPTIMAL, UNKNOWN, CpModel, CpSolver,
                                         IntVar)

from input import testcase
from input.model.route import route
from input.model.task import task
from optimization.cp.models.scheduling import (scheduling_model_constraints, scheduling_model_variables)
from optimization.cp.models.scheduling import scheduling_model_goals

from input.model.schedule import schedule
from input.testcase import Testcase
from optimization.cp.models.scheduling.scheduling_model import EOptimizationGoal, CPSchedulingSolver
from solution.solution_optimization_status import EOptimizationStatus
from solution.solution_timing_data import TimingData
from utils.utilities import Timer, print_model_stats, report_exception, list_gcd, debug_print, sorted_complement, \
    longest_interval_in_list


class SACPSolver:
    def __init__(
            self,
            tc: Testcase,
            timing_object: TimingData,
            optimization_goal: EOptimizationGoal,
            do_security: bool = True,
            do_allow_infeasible_solutions: bool = False,
            dont_optimize: bool = False
    ):
        self.dont_optimize = dont_optimize
        self.timing_object = timing_object
        self.do_allow_infeasible_solutions = do_allow_infeasible_solutions
        self.do_security = do_security
        self.optimization_goal = optimization_goal
        self.tc: testcase = tc
        self.Pint = tc.Pint

    def optimize(
            self, input_params, timing_object: TimingData
    ) -> Tuple[Testcase, EOptimizationStatus, schedule, int]:
        self.input_params = input_params
        temp_reset = False
        Tstart = input_params.Tstart
        alpha = input_params.alpha
        start = time.time()
        first_feasible_time = -1
        status = EOptimizationStatus.INFEASIBLE

        s_i = self._initial_solution()
        s_best = s_i
        status, best_cost,schdl = self._cost(s_best)
        print(
            f"Running SA-CP-Metaheuristic: Tstart {Tstart}, alpha {alpha}")
        print(f"INITIAL COST: {best_cost}\n")
        print(f"Initial Solution: {s_best}\n")

        if status == EOptimizationStatus.FEASIBLE or status == EOptimizationStatus.OPTIMAL:
            first_feasible_time = time.time() - start
            print(f"FIRST FEASIBLE SOLUTION after {first_feasible_time}")
            print(f"Solution: {s_best}\n")
            timing_object.time_first_feasible_solution = first_feasible_time


        temp = Tstart
        step = 0

        while time.time() - start < input_params.timeouts.timeout_scheduling:
            s = self._random_neighbour(s_i)
            status, old_cost, schdl = self._cost(s_i)
            status, new_cost, schdl = self._cost(s)
            print(".", end="")

            if first_feasible_time == -1 and (status == EOptimizationStatus.FEASIBLE or status == EOptimizationStatus.OPTIMAL):
                first_feasible_time = time.time() - start
                print(f"\nFIRST FEASIBLE SOLUTION after {first_feasible_time}")
                print(f"Solution: {s}\n")
                timing_object.time_first_feasible_solution = first_feasible_time

            delta = new_cost - old_cost  # new_cost - old_cost, because we want to minimize cost

            if delta < 0 or self._probability_check(delta, temp):
                s_i = s

                if new_cost < best_cost:
                    s_best = s
                    best_cost = new_cost
                    print(
                        f"\nNEW BEST COST: {best_cost};")
                    print(f"Solution: {s_best}\n")

            if not temp_reset:
                oldtemp = temp
                temp = temp * alpha
                if temp == 0:
                    temp = oldtemp
                    print(f"\nWARNING: Temperature reached zero due to float limitations. Resetting to prev temp")
                    temp_reset = True
            step += 1


        return self.tc, status, schdl, best_cost

    def _cost(self, s: Dict[str, Dict[int, List[task]]]):
        schdl = self._heuristic_schedule(s)
        self.cp_scheduling_model = CPSchedulingSolver(self.tc, self.timing_object, EOptimizationGoal.MAXIMIZE_EXTENSIBILITY,
                                                      existing_schedule=schdl,
                                                      do_security=self.do_security,
                                                      do_allow_infeasible_solutions=self.do_allow_infeasible_solutions,
                                                      dont_optimize=True)  # dont_optimize -> don't add minimization goal
        tc, status, schdl, total_cost_scheduling = self.cp_scheduling_model.optimize(self.input_params, self.timing_object, verbose=False)
        return status, total_cost_scheduling, schdl

    def _random_neighbour(self, s : Dict[str, Dict[int, List[task]]]):
        # mutate order
        while True:
            random_es = random.choice(list(s.keys()))
            if len(s[random_es]) > 0:
                break

        random_period = random.choice(list(s[random_es].keys()))
        lst = s[random_es][random_period]
        #print(f"Switching random tasks in {random_es} list: {lst}")
        if len(lst) > 1:
            random_task_1, random_task_2 = random.sample(lst, 2)
            a, b = lst.index(random_task_1), lst.index(random_task_2)
            lst[b], lst[a] = lst[a], lst[b]
        #print(f"New list: {lst}")
        return  s

    def _initial_solution(self) -> Dict[str, Dict[int, List[task]]]:
        print("SACPSolver creating initial schedule:")
        print(f"Hyperperiod: {self.tc.hyperperiod}")

        # Gather all free & sender tasks
        all_free_tasks = []
        sender_task_id_to_stream_id = {}
        for app in self.tc.A.values():
            all_task_ids = [t.id for t in list(app.verticies.values())]
            all_free_tasks.extend(all_task_ids)
            all_streams = app.edges.items()
            for s_id, task_tuple in all_streams:
                sender_task_id_to_stream_id[task_tuple[0][0]] = s_id
                all_free_tasks.remove(task_tuple[0][0])
                all_free_tasks.remove(task_tuple[0][1])

        # Create ordered datastructure for heuristic schedule
        scheduling_order = {}
        for es in self.tc.ES.values():
            scheduling_order[es.id] = {}
            tsks = []
            free_tsks = {}
            sender_tsks = {}
            if es.is_edge_device() or es.is_prover():
                for t in self.tc.T_g[es.id]:
                    if t.id in all_free_tasks:
                        # for each task on edge devices and provers, distribute
                        tsks.append(t)
                        if t.period not in free_tsks:
                            free_tsks[t.period] = [t]
                        else:
                            free_tsks[t.period].append(t)
                    if t.id in sender_task_id_to_stream_id:
                        tsks.append(t)
                        if t.period not in sender_tsks:
                            sender_tsks[t.period] = [t]
                        else:
                            sender_tsks[t.period].append(t)

                    if t.period not in scheduling_order[es.id]:
                        scheduling_order[es.id][t.period] = []

            # create order for es
            # first sender tasks, then free tasks
            for period, t_list in sender_tsks.items():
                for t in t_list:
                    scheduling_order[es.id][period].append(t)
            for period, t_list in free_tsks.items():
                for t in t_list:
                    scheduling_order[es.id][period].append(t)

        return scheduling_order

    def _heuristic_schedule(self, scheduling_order : Dict[str, Dict[int, List[task]]]):
        # scheduling_order: Dict(ES.id -> Dict(Period -> List[task.id])), where we can permutate the list to change scheduling order
        s = schedule()
        for es_id, period_dict in scheduling_order.items():
            es = self.tc.ES[es_id]

            # iterate through periods, smallest first
            # we assume that periods are multiples of each other
            iv_tree = IntervalTree()
            first_task = True
            for period in sorted(period_dict):
                for t in period_dict[period]:
                    if first_task:
                        # place first task at offset 0
                        for alpha in range(self.tc.hyperperiod // period):
                            iv_tree.add(Interval(alpha * period + 0, alpha * period + t.exec_time))
                        s.o_t_val[t.id] = 0
                        s.a_t_val[t.id] = t.exec_time

                        first_task = False
                    else:
                        slacks = sorted_complement(iv_tree, start=0, end=period)
                        idx, iv_length = longest_interval_in_list(slacks)
                        longest_interval = slacks[idx]
                        iv_start = longest_interval.begin
                        iv_end = longest_interval.end
                        assert iv_length > t.exec_time
                        middle = iv_start + (iv_length // 2) - (t.exec_time // 2)

                        # place other task in the middle of the largest free interval within their period
                        # there should be no overlap in subsequent periods, if all periods are multiples of each other
                        for alpha in range(self.tc.hyperperiod // period):
                            iv_tree.add(Interval(alpha * period + middle, alpha * period + middle + t.exec_time))
                        s.o_t_val[t.id] = middle
                        s.a_t_val[t.id] = middle + t.exec_time

            debug_print(f"{es.id} {es.type}")
            debug_print(iv_tree)
            debug_print("")


        debug_print(s.o_t_val)
        debug_print(s.a_t_val)
        return s

    def _probability_check(self, delta, t):
        return random.uniform(0, 1) < self.p(delta, t)

    def p(self, delta, t):
        return math.e ** (-1 * (delta / t))