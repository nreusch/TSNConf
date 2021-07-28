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
from utils import cost
from utils.utilities import Timer, list_gcd, print_model_stats, shortest_simple_paths_patched
import networkx as nx
from itertools import islice

class SARoutingSolution:
    def __init__(self, paths: Dict[str, Dict[str, List[str]]]):
        #Dict[stream.id, Dict(receiver_es_id -> path)]
        self.paths: Dict[str, Dict[str, List[str]]] = paths

    def __repr__(self):
        return str(self.paths)

    def __str__(self):
        return self.__repr__()

class SARoutingSolver:
    def __init__(self, tc: Testcase, timing_object: TimingData, k: int, a: int, w: int):
        self.tc = tc

        self.possible_paths : Dict[str, Dict[str, List[List[str]]]] = {} # stream_id -> Dict(receiver_es_id -> List[path])

        # Create the model
        self.model = CpModel()

        # Create variables
        t = Timer()
        with t:
            self._create_variables(k, w)
        timing_object.time_creating_vars_pint = t.elapsed_time

        self.a = a


    def _create_variables(self, k, w):
        # Create networkx digraph with all edges & links
        g = nx.DiGraph()
        g.add_nodes_from(self.tc.N.keys())
        for l in self.tc.L.values():
            g.add_edge(l.src.id, l.dest.id, weight=1)

        # For each stream, for each sender ES, receiver ES pair, add k-shortest-paths as possibilities
        s_prefixes = {}
        for s in self.tc.F_routed.values():

            if s.get_id_prefix() not in s_prefixes:
                # First stream
                self.possible_paths[s.id] = {}

                for es_recv_id in s.receiver_es_ids:
                    excluded_es = set(self.tc.ES.keys())
                    excluded_es.difference_update({s.sender_es_id, es_recv_id})
                    k_shortest_paths = list(
                        islice(shortest_simple_paths_patched(g, s.sender_es_id, es_recv_id, ignore_nodes_init=excluded_es), k)
                    )

                    self.possible_paths[s.id][es_recv_id] = k_shortest_paths
                s_prefixes[s.get_id_prefix()] = [self.possible_paths[s.id]]
            else:
                # Redundant copy
                self.possible_paths[s.id] = {}

                g_weighted = g.copy()
                # For each other exising redundant copy
                for es_recv_id in s.receiver_es_ids:
                    for ppath in s_prefixes[s.get_id_prefix()]:
                        for i in range(len(ppath[es_recv_id][0]) - 1):
                            n1 = ppath[es_recv_id][0][i]
                            n2 = ppath[es_recv_id][0][i + 1]
                            g_weighted[n1][n2]["weight"] = w

                for es_recv_id in s.receiver_es_ids:
                    excluded_es = set(self.tc.ES.keys())
                    excluded_es.difference_update({s.sender_es_id, es_recv_id})

                    try:
                        k_shortest_paths = list(
                            islice(
                                shortest_simple_paths_patched(g_weighted, s.sender_es_id, es_recv_id, ignore_nodes_init=excluded_es, weight="weight"),
                                k)
                        )
                    except nx.exception.NetworkXNoPath:
                        # If there exists no other path, use the same paths
                        k_shortest_paths = s_prefixes[s.get_id_prefix()][0][es_recv_id]

                    self.possible_paths[s.id][es_recv_id] = k_shortest_paths
                s_prefixes[s.get_id_prefix()].append(self.possible_paths[s.id])


    def _initial_solution(self) -> SARoutingSolution:
        selected_paths = {}
        for s in self.tc.F_routed.values():
            selected_paths[s.id] = {}
            for receiver_es_id, path_list in self.possible_paths[s.id].items():
                selected_paths[s.id][receiver_es_id] = path_list[0]
        return SARoutingSolution(selected_paths)

    def _random_neighbour(self, s_i: SARoutingSolution) -> SARoutingSolution:
        # Dict[stream.id, Dict(receiver_es_id -> path)]
        s = copy.deepcopy(s_i)

        # select random stream
        rand_stream_nr = random.randint(0, len(self.tc.F_routed.values())-1)
        rand_stream = list(self.tc.F_routed.values())[rand_stream_nr]

        # select random receiver of that stream
        rand_receiver_nr = random.randint(0, len(rand_stream.receiver_es_ids)-1)
        rand_receiver = list(rand_stream.receiver_es_ids)[rand_receiver_nr]

        current_path = s.paths[rand_stream.id][rand_receiver]
        possible_path_amount = len(self.possible_paths[rand_stream.id][rand_receiver])

        if possible_path_amount > 1:
            new_path = current_path
            while new_path == current_path:
                rand_path_nr = random.randint(0, possible_path_amount-1)
                new_path = self.possible_paths[rand_stream.id][rand_receiver][rand_path_nr]
            s.paths[rand_stream.id][rand_receiver] = new_path

        return s

    def _cost(self, sol: SARoutingSolution):
        total_cost, overlap_amount, overlapping_streams = cost.cost_SA_routing_solution(sol, self.tc, self.a)
        return total_cost, overlap_amount, overlapping_streams

    def _solve(self, timeout) -> SARoutingSolution:
        # returns Dict[stream.id, Dict(receiver_es_id -> path)]
        Tstart = 1
        alpha = 0.999

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

            if delta < 0 or _probability_check(delta, temp):
                s_i = s

                if new_cost < best_cost:
                    s_best = s
                    best_cost = new_cost
                    print("NEW BEST COST: " + str(best_cost))

            temp = temp * alpha
            step += 1

        return s_best

    def optimize(
        self, input_params: InputParameters, timing_object: TimingData
    ) -> Tuple[Testcase, EOptimizationStatus]:
        # Observerations
        # The earlier multicast streams split, the more bandwidth they consume. But it might be beneficial to avoid a congested link


        t = Timer()
        with t:
            # OPTIMIZE
            solution = self._solve(3)
        timing_object.time_optimizing_routing = t.elapsed_time
        status = EOptimizationStatus.FEASIBLE



        if (status == EOptimizationStatus.FEASIBLE):
            # UPDATE tc
            R, R_info = solution_to_datastructures(self.tc, solution)
            for r in R.values():
                self.tc.add_to_datastructures(r)
            for r_info in R_info.values():
                self.tc.add_to_datastructures(r_info)
        else:
            raise ValueError(
                "SASolver returned invalid status for SARouting model: " + str(status)
            )
        return self.tc, status

def p(delta, t):
    return math.e ** (-1 * (delta / t))

def _probability_check(delta, t):
    return random.uniform(0, 1) < p(delta, t)

def create_node_mapping(s: SARoutingSolution, stream_id: str) -> Dict[str, List[Tuple[str, str]]]:
    node_mapping = {}
    for es_recv_id, path in s.paths[stream_id].items():
        node_mapping[es_recv_id]  = []
        for i in range(len(path)-1):
            node_mapping[es_recv_id].append((path[i], path[i+1]))

    return node_mapping

def solution_to_datastructures(tc, sol):
    R = {}
    R_info = {}
    for s in tc.F_routed.values():
        node_mapping = create_node_mapping(sol, s.id)
        r = route(s)
        r.init_from_node_mapping(node_mapping)
        R[s.id] = r

        route_len, overlap_amount, overlap_links = cost.cost_parameters_for_stream(s, sol, tc)
        r_info = route_info(r, route_len, overlap_amount, overlap_links)
        R_info[s.id] = r_info

    return R, R_info
