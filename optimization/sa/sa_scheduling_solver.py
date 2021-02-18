import copy
import itertools
import math
import random
import time
from enum import Enum
from typing import Tuple, List

from ortools.sat.python.cp_model import (CpModel)

from input.model.schedule import schedule
from input.testcase import Testcase
from input.input_parameters import InputParameters
from optimization.sa.heuristic_schedule import heuristic_schedule
from optimization.sa.task_graph import TaskGraph, TopologicalTaskGraphApp
from solution.solution_optimization_status import EOptimizationStatus
from solution.solution_timing_data import TimingData
from utils.utilities import Timer, report_exception

VERY_HIGH_COST = 99999999
T_START = 1
ALPHA = 0.999

class SAOptimizationMode(Enum):
    SEPERATED_NO_SA = 0 # routing&scheduling seperated. No SA scheduling
    SEPERATED_SA = 1 # routing&scheduling seperated. SA scheduling
    COMBINED_SA = 2 # routing&scheduling combined. SA

class SASchedulingOrder:
    def __init__(self, order: Tuple[List[TopologicalTaskGraphApp], List[TopologicalTaskGraphApp]]):
        self.order: Tuple[List[TopologicalTaskGraphApp], List[TopologicalTaskGraphApp]] = order

    def switch_random_normal_apps(self):
        l = range(len(self.order[1]))
        i1, i2 = random.sample(l, 2)
        self.order[1][i1], self.order[1][i2] = self.order[1][i2], self.order[1][i1]


class SASchedulingSolver:
    def __init__(self, tc: Testcase, timing_object: TimingData):
        self.tc = tc

        # Create the model
        self.model = CpModel()

        # Create variables
        t = Timer()
        with t:
            self._create_variables()
        timing_object.time_creating_vars_scheduling = t.elapsed_time


    def _create_variables(self):
        self.task_graph = TaskGraph.from_applications(self.tc)
        self.start_order: SASchedulingOrder = SASchedulingOrder(self.task_graph.order)

    def _list_schedule(self, order: SASchedulingOrder):
        status = EOptimizationStatus.FEASIBLE
        my_schedule = heuristic_schedule(self.tc, self.task_graph)

        # chain keyApps and then normalApps
        for tga in itertools.chain(order.order[0], order.order[1]):
            for tgn_id in tga.internal_order:
                tgn = self.task_graph.nodes[tgn_id]
                if not my_schedule.schedule(tgn):
                    status = EOptimizationStatus.INFEASIBLE
                    break

        return my_schedule, status

    def _solve_seperated_no_sa(self, order: SASchedulingOrder):
        output_schedule, status = self._list_schedule(order)
        return output_schedule, status

    def _cost(self, order: SASchedulingOrder):
        cost = 0
        infeasible_tgn = 0
        my_schedule = heuristic_schedule(self.tc, self.task_graph)

        # chain keyApps and then normalApps
        for tga in itertools.chain(order.order[0], order.order[1]):
            for tgn_id in tga.internal_order:
                tgn = self.task_graph.nodes[tgn_id]
                if not my_schedule.schedule(tgn):
                    cost += VERY_HIGH_COST
                    infeasible_tgn += 1
                else:
                    latency = my_schedule.get_latency(tgn)
                    if latency == -1:
                        cost += VERY_HIGH_COST
                        infeasible_tgn += 1
                    else:
                        cost += latency

        return cost, infeasible_tgn

    def _probability_check(self, delta, t):
        return random.uniform(0, 1) < self.p(delta, t)

    def p(self, delta, t):
        return math.e ** (-1 * (delta / t))

    def _solve_seperated_sa(self, start_order: SASchedulingOrder, timeout: int):
        Tstart = T_START
        alpha = ALPHA

        s_i = start_order
        s_best = s_i
        best_cost, infeasible_tgn = self._cost(s_best)
        print(f"INITIAL COST: {best_cost}; INFEASIBLE TGN: {infeasible_tgn}; ORDER: {s_best.order[1]}")
        # print_simple_solution(s_i, index_to_core_map)
        print()

        temp = Tstart
        step = 0

        start = time.time()
        while time.time() - start < timeout:
            s = self._random_neighbour(s_i)
            old_cost, infeasible_tgn = self._cost(s_i)
            new_cost, infeasible_tgn = self._cost(s)
            delta = new_cost - old_cost  # new_cost - old_cost, because we want to minimize cost

            if delta < 0 or self._probability_check(delta, temp):
                s_i = s

                if new_cost < best_cost:
                    s_best = s
                    best_cost = new_cost
                    print(f"NEW BEST COST: {str(best_cost)}; INFEASIBLE TGN: {infeasible_tgn}; ORDER: {s_best.order[1]}")

            temp = temp * alpha
            step += 1

        output_schedule, status = self._list_schedule(s_best)
        return output_schedule, status

    def optimize(
        self, input_params: InputParameters, timing_object: TimingData, mode: SAOptimizationMode
    ) -> Tuple[Testcase, EOptimizationStatus]:

        status = EOptimizationStatus.INFEASIBLE
        t = Timer()
        with t:
            # OPTIMIZE
            if mode == SAOptimizationMode.SEPERATED_NO_SA:
                output_schedule, status = self._solve_seperated_no_sa(self.start_order)
            elif mode == SAOptimizationMode.SEPERATED_SA:
                output_schedule, status = self._solve_seperated_sa(self.start_order, input_params.timeouts.timeout_scheduling)
            elif mode == SAOptimizationMode.COMBINED_SA:
                pass
        timing_object.time_optimizing_scheduling = t.elapsed_time

        if (status == EOptimizationStatus.FEASIBLE):
            # UPDATE tc
            self.tc.schedule = schedule.from_heuristic_schedule_and_task_graph(output_schedule, self.task_graph, self.tc)
        else:
            report_exception(
                "SASolver returned invalid status for scheduling model: " + str(status)
            )
        return self.tc, status

    def _random_neighbour(self, s_i: SASchedulingOrder) -> SASchedulingOrder:
        # Swap applications and or tasks within the same applications
        # No application interweaving due to dependency and queuing issues
        s_new = copy.deepcopy(s_i)
        s_new.switch_random_normal_apps()

        return s_new
