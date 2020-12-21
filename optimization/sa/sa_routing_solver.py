import copy
import math
import random
import time
from typing import Tuple, List, Dict

from ortools.sat.python.cp_model import (FEASIBLE, INFEASIBLE, MODEL_INVALID,
                                         OPTIMAL, UNKNOWN, CpModel, CpSolver)

from input.model.route import route, route_info
from input.testcase import Testcase
from input.input_parameters import InputParameters
from solution.solution_optimization_status import EOptimizationStatus
from solution.solution_timing_data import TimingData
from utils.utilities import Timer, list_gcd, print_model_stats
import networkx as nx


class SARoutingSolver:
    def __init__(self, tc: Testcase, timing_object: TimingData):
        self.tc = tc

        self.possible_paths : Dict[str, Dict[str, List[List[str]]]] = {} # stream_id -> Dict(receiver_es_id -> List[path])

        # Create the model_old
        self.model = CpModel()

        # Create variables
        t = Timer()
        with t:
            self._create_variables()
        timing_object.time_creating_vars_pint = t.elapsed_time


    def _create_variables(self):
        g = nx.DiGraph()

        g.add_nodes_from(self.tc.N.keys())

        for l in self.tc.L.values():
            g.add_edge(l.src.id, l.dest.id)

        for s in self.tc.F_routed.values():
            self.possible_paths[s.id] = {}
            paths = [p for p in nx.all_simple_paths(g, s.sender_es_id, s.receiver_es_ids)]

            for p in paths:
                # CONSTRAINT: Path may only contain ES at start and end
                es_in_route = False
                for n in p[1:-1]:
                    if n in self.tc.ES:
                        es_in_route = True

                if es_in_route:
                    continue

                if p[-1] not in self.possible_paths[s.id]:
                    self.possible_paths[s.id][p[-1]] = [p]
                else:
                    self.possible_paths[s.id][p[-1]].append(p)

    def _initial_solution(self):
        selected_paths = {}
        for s in self.tc.F_routed.values():
            selected_paths[s.id] = {}
            for receiver_es_id, path_list in self.possible_paths[s.id].items():
                selected_paths[s.id][receiver_es_id] = path_list[0]
        return selected_paths

    def _random_neighbour(self, s_i: Dict[str, Dict[str, List[str]]]) -> Dict[str, Dict[str, List[str]]]:
        # Dict[stream.id, Dict(receiver_es_id -> path)]
        s = copy.deepcopy(s_i)
        new = False
        while not new:
            rand_stream_nr = random.randint(0, len(self.tc.F.values())-1)
            rand_stream = list(self.tc.F_routed.values())[rand_stream_nr]
            rand_receiver_nr = random.randint(0, len(rand_stream.receiver_es_ids)-1)
            rand_receiver = list(rand_stream.receiver_es_ids)[rand_receiver_nr]

            current_path = s[rand_stream.id][rand_receiver]
            possible_path_amount = len(self.possible_paths[rand_stream.id][rand_receiver])

            if possible_path_amount > 1:
                new_path = current_path
                while new_path == current_path:
                    rand_path_nr = random.randint(0, possible_path_amount-1)
                    new_path = self.possible_paths[rand_stream.id][rand_receiver][rand_path_nr]
                new = True
        s[rand_stream.id][rand_receiver] = new_path
        return s

    def _solve(self, timeout) -> Dict[str, Dict[str, List[str]]]:
        # returns Dict[stream.id, Dict(receiver_es_id -> path)]


        Tstart = 1
        alpha = 0.999
        stop_time = 10  # seconds

        s_i = self._initial_solution()
        s_best = s_i
        best_cost = self._cost(s_best)
        print(f"INITIAL COST: {best_cost}")
        #print_simple_solution(s_i, index_to_core_map)
        print()

        temp = Tstart
        step = 0

        start = time.time()
        while time.time() - start < timeout:
            s = self._random_neighbour(s_i)
            old_cost = self._cost(s_i)
            new_cost = self._cost(s)
            delta = new_cost - old_cost   # new_cost - old_cost, because we want to minimize cost

            if delta < 0 or self._probability_check(delta, temp):
                s_i = s

                if new_cost < best_cost:
                    s_best = s
                    best_cost = new_cost
                    print("NEW BEST COST: " + str(best_cost))

            temp = temp * alpha
            step += 1

        return s_best

    def _cost_stream(self, stream_id: str, selected_paths: Dict[str, Dict[str, List[str]]]):
        f = self.tc.F_routed[stream_id]

        node_mapping = self._create_node_mapping(selected_paths, stream_id)

        route_len = len(node_mapping)

        overlap_amount = 0
        overlap_links = set()
        for stream_red_copy in self.tc.F_red[f.get_id_prefix()]:
            if stream_red_copy != f:
                node_mapping_red = self._create_node_mapping(selected_paths, stream_red_copy.id)

                for link in node_mapping_red:
                    if link in node_mapping:
                        overlap_amount += 1
                        overlap_links.add(self.tc.L_from_nodes[link[0]][link[1]])

        cost = 10 * overlap_amount + route_len

        return cost, route_len, overlap_amount, overlap_links

    def _cost(self, selected_paths: Dict[str, Dict[str, List[str]]]):
        total_cost = 0
        for s_id in self.tc.F_routed.keys():
            cost, _, _, _ = self._cost_stream(s_id, selected_paths)
            total_cost += cost
        return total_cost

    def _create_node_mapping(self, selected_paths, stream_id):
        node_mapping = set()
        for path in selected_paths[stream_id].values():
            for i in range(len(path) - 1):
                node_mapping.add((path[i], path[i + 1]))
        return node_mapping

    def _probability_check(self, delta, t):
        return random.uniform(0, 1) < self.p(delta, t)

    def p(self, delta, t):
        return math.e ** (-1 * (delta / t))

    def optimize(
        self, input_params: InputParameters, timing_object: TimingData
    ) -> Tuple[Testcase, EOptimizationStatus]:
        # Observerations
        # The earlier multicast streams split, the more bandwidth they consume. But it might be beneficial to avoid a congested link


        t = Timer()
        with t:
            # OPTIMIZE
            selected_paths = self._solve(3)
        timing_object.time_optimizing_pint = t.elapsed_time
        status = EOptimizationStatus.FEASIBLE



        if (status == EOptimizationStatus.FEASIBLE):
            # UPDATE tc

            for s in self.tc.F_routed.values():
                node_mapping = self._create_node_mapping(selected_paths, s.id)
                mt = route(s)
                mt.init_from_node_mapping(node_mapping, self.tc.L_from_nodes)
                self.tc.add_to_datastructures(mt)

                cost, route_len, overlap_amount, overlap_links = self._cost_stream(s.id, selected_paths)
                r_info = route_info(mt, cost, route_len, overlap_amount, overlap_links)
                self.tc.add_to_datastructures(r_info)
        else:
            raise ValueError(
                "SASolver returned invalid status for SARouting model: " + str(status)
            )
        return self.tc, status