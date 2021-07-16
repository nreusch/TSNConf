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
from optimization.sa.sa_routing_solver import SARoutingSolver, SARoutingSolution, solution_to_datastructures
from optimization.sa.task_graph import PrecedenceGraph, TopologicalTaskGraphApp
from solution.solution_optimization_status import EOptimizationStatus
from solution.solution_timing_data import TimingData
from utils.cost import cost_SA_scheduling_solution, cost_SA_routing_solution
from utils.utilities import Timer, report_exception, debug_print

class SAOptimizationMode(Enum):
    SEPERATED_NO_SA = 0 # routing&scheduling seperated. No SA scheduling
    SEPERATED_SA = 1 # routing&scheduling seperated. SA scheduling
    COMBINED_SA = 2 # routing&scheduling combined. SA

class SASchedulingSolution:
    def __init__(self, order: Tuple[List[TopologicalTaskGraphApp], List[TopologicalTaskGraphApp]]):
        self.order: Tuple[List[TopologicalTaskGraphApp], List[TopologicalTaskGraphApp]] = order

    def switch_random_normal_apps(self):
        if len(self.order[1]) > 1:
            l = range(len(self.order[1]))
            i1, i2 = random.sample(l, 2)
            self.order[1][i1], self.order[1][i2] = self.order[1][i2], self.order[1][i1]


class SASchedulingSolver:
    def __init__(self, tc: Testcase, timing_object: TimingData, input_params: InputParameters):
        self.tc = tc

        # Create the model
        self.model = CpModel()

        # Create variables
        t = Timer()
        with t:
            self._create_variables()
        timing_object.time_creating_vars_scheduling = t.elapsed_time

        self.b = input_params.b


    def _create_variables(self):
        self.prec_graph = PrecedenceGraph.from_applications(self.tc)


    def _initial_solution_schedule(self) -> SASchedulingSolution:
        return SASchedulingSolution(self.prec_graph.order)

    def _solve_seperated_no_sa(self):
        return self._initial_solution_schedule()

    def _cost_scheduling(self, sol: SASchedulingSolution):
        # 3. Schedule scheduling solution
        my_schedule = heuristic_schedule(self.tc, self.prec_graph)

        infeasible_tga = {}
        latencies = {}
        # chain keyApps and then normalApps
        for tga in itertools.chain(sol.order[0], sol.order[1]):
            tga_is_infeasible = False
            for tgn_id in tga.internal_order:
                tgn = self.prec_graph.nodes[tgn_id]
                result = my_schedule.schedule(tgn)
                if result == False:
                    #print(f"FAILED to schedule {tgn_id}")
                    tga_is_infeasible = True
                    break
                else:
                    latency = my_schedule.get_latency(tgn)
                    if latency == -1:
                        tga_is_infeasible = True
                        break

            if tga_is_infeasible:
                infeasible_tga[tga.app_id] = True
            else:
                start_time, end_time = my_schedule.optimize_latency(tga, self.prec_graph)
                tga_latency = end_time - start_time
                if tga_latency > self.tc.A[tga.app_id].period:
                    infeasible_tga[tga.app_id] = True
                else:
                    latencies[tga.app_id] = tga_latency

        # 4. Calculate scheduling cost
        scheduling_cost = cost_SA_scheduling_solution(sol, self.tc, self.b, infeasible_tga, latencies)

        return scheduling_cost, infeasible_tga, my_schedule

    def _cost_combined(self, sol: Tuple[SARoutingSolution, SASchedulingSolution], a):
        # TODO: Fix cost calculation
        # 1. Calculate routing cost of routing solution
        route_cost, overlap_amount = cost_SA_routing_solution(sol[0], self.tc, a)

        # 2. Clear the old routing and add current routing solution
        self.tc.clear_routes()
        R, R_info = solution_to_datastructures(self.tc, sol[0])
        for r in R.values():
            self.tc.add_to_datastructures(r)
        for r_info in R_info.values():
            self.tc.add_to_datastructures(r_info)

        # 3. Calculate scheduling cost
        scheduling_cost, infeasible_tga, _ = self._cost_scheduling(sol[1])

        # 4. Calculate total cost
        cost = route_cost + scheduling_cost

        return cost, infeasible_tga, route_cost, overlap_amount

    def _probability_check(self, delta, t):
        return random.uniform(0, 1) < self.p(delta, t)

    def p(self, delta, t):
        return math.e ** (-1 * (delta / t))

    def _solve_seperated_sa(self, timeout: int):
        Tstart = 1
        alpha = 0.999

        s_i = self._initial_solution_schedule()
        s_best = s_i
        best_cost, infeasible_tgn, _ = self._cost_scheduling(s_best)
        print(f"INITIAL COST: {best_cost}; INFEASIBLE TGN: {infeasible_tgn}; ORDER: {s_best.order[1]}")
        # print_simple_solution(s_i, index_to_core_map)
        debug_print("")

        temp = Tstart
        step = 0

        start = time.time()
        while time.time() - start < timeout:
            s = self._random_neighbour(s_i)
            old_cost, infeasible_tgn, _ = self._cost_scheduling(s_i)
            new_cost, infeasible_tgn, _ = self._cost_scheduling(s)
            delta = new_cost - old_cost  # new_cost - old_cost, because we want to minimize cost

            if delta < 0 or self._probability_check(delta, temp):
                s_i = s

                if new_cost < best_cost:
                    s_best = s
                    best_cost = new_cost
                    print(f"NEW BEST COST: {str(best_cost)}; INFEASIBLE TGN: {infeasible_tgn}; ORDER: {s_best.order[1]}; TEMP: {temp}")

            temp = temp * alpha
            step += 1

        return s_best

    def _solve_combined_sa(self, routingSolver: SARoutingSolver, timing_object: TimingData, timeout: int, a: int):
        Tstart = 10
        alpha = 0.999
        SCHEDULING_MOVE_PROBABILITY = 0.2

        s_i = (routingSolver._initial_solution(), self._initial_solution_schedule())
        s_best = s_i
        best_cost, infeasible_tgn, routing_cost, overlap_amount = self._cost_combined(s_best, a)
        print(f"INITIAL COST: {best_cost}; INFEASIBLE TGA: {infeasible_tgn}; ROUTING COST: {routing_cost}\n")
        #print(f"ROUTING SOLUTION: {s_best[0]}\nSCHEDULING SOLUTION: {s_best[1].order[1]}")
        # print_simple_solution(s_i, index_to_core_map)
        debug_print("")

        temp = Tstart
        step = 0

        first_feasible_time = -1
        start = time.time()
        while time.time() - start < timeout:
            s = self._random_neighbour_combined(s_i, routingSolver, SCHEDULING_MOVE_PROBABILITY)
            old_cost, infeasible_tgn, routing_cost, overlap_amount = self._cost_combined(s_i, a)
            new_cost, infeasible_tgn, routing_cost, overlap_amount = self._cost_combined(s, a)

            if infeasible_tgn == 0 and overlap_amount == 0 and first_feasible_time == -1:
                first_feasible_time = time.time() - start
                print(f"FIRST FEASIBLE SOLUTION after {first_feasible_time}")
                timing_object.time_first_feasible_solution = first_feasible_time


            delta = new_cost - old_cost  # new_cost - old_cost, because we want to minimize cost

            if delta < 0 or self._probability_check(delta, temp):
                s_i = s

                if new_cost < best_cost:
                    s_best = s
                    best_cost = new_cost
                    print(
                        f"NEW BEST COST: {best_cost}; INFEASIBLE TGA: {infeasible_tgn}; ROUTING COST: {routing_cost}; TEMP: {temp}\n")
                    #print(f"ROUTING SOLUTION: {s_best[0]}\nSCHEDULING SOLUTION: {s_best[1].order[1]}")

            temp = temp * alpha
            step += 1

        return s_best[0], s_best[1]

    def optimize(
        self, input_params: InputParameters, timing_object: TimingData, mode: SAOptimizationMode
    ) -> Tuple[Testcase, EOptimizationStatus]:

        status = EOptimizationStatus.INFEASIBLE
        t = Timer()
        with t:
            # OPTIMIZE
            if mode == SAOptimizationMode.SEPERATED_NO_SA:
                schedule_solution = self._solve_seperated_no_sa()
            elif mode == SAOptimizationMode.SEPERATED_SA:
                schedule_solution = self._solve_seperated_sa(input_params.timeouts.timeout_scheduling)
            elif mode == SAOptimizationMode.COMBINED_SA:
                routingSolver = SARoutingSolver(self.tc, timing_object, input_params.k, input_params.a)
                routing_solution, schedule_solution = self._solve_combined_sa(routingSolver, timing_object, input_params.timeouts.timeout_scheduling, input_params.a)
            else:
                raise ValueError
        timing_object.time_optimizing_scheduling = t.elapsed_time

        if mode == SAOptimizationMode.COMBINED_SA:
            self.tc.clear_routes()
            R, R_info = solution_to_datastructures(self.tc, routing_solution)
            for r in R.values():
                self.tc.add_to_datastructures(r)
            for r_info in R_info.values():
                self.tc.add_to_datastructures(r_info)
        _, infeasible_tga, output_schedule = self._cost_scheduling(schedule_solution)

        self.tc.schedule = schedule.from_heuristic_schedule_and_task_graph(output_schedule, self.prec_graph, self.tc, infeasible_tga)
        return self.tc, status

    def _random_neighbour(self, s_i: SASchedulingSolution) -> SASchedulingSolution:
        # Swap applications and or tasks within the same applications
        # No application interweaving due to dependency and queuing issues
        s_new = copy.deepcopy(s_i)
        s_new.switch_random_normal_apps()

        return s_new

    def _random_neighbour_combined(self, sol: Tuple[SARoutingSolution, SASchedulingSolution], routingSolver: SARoutingSolver, SCHEDULING_MOVE_PROBABILITY) -> Tuple[SARoutingSolution, SASchedulingSolution]:
        # Swap applications and or tasks within the same applications
        # No application interweaving due to dependency and queuing issues

        p = random.uniform(0, 1)

        if p < SCHEDULING_MOVE_PROBABILITY:
            # Scheduling move
            s_new = (sol[0], copy.deepcopy(sol[1]))
            s_new[1].switch_random_normal_apps()
        else:
            # Routing move
            new_route = routingSolver._random_neighbour(sol[0])
            s_new = (new_route, sol[1])

        return s_new