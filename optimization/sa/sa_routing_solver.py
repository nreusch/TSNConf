from typing import Tuple, List, Dict

from ortools.sat.python.cp_model import (FEASIBLE, INFEASIBLE, MODEL_INVALID,
                                         OPTIMAL, UNKNOWN, CpModel, CpSolver)

from input.model.route import route
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

        # Create the model
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

        for s in self.tc.F.values():
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

    def _solve(self) -> Dict[str, Dict[str, List[str]]]:
        # returns Dict[stream.id, Dict(receiver_es_id -> path)]
        selected_paths = {}
        for s in self.tc.F.values():
            selected_paths[s.id] = {}
            for receiver_es_id, path_list in self.possible_paths[s.id].items():
                selected_paths[s.id][receiver_es_id] = path_list[0]

        return selected_paths

    def optimize(
        self, input_params: InputParameters, timing_object: TimingData
    ) -> Tuple[Testcase, EOptimizationStatus]:
        # Observerations
        # The earlier multicast streams split, the more bandwidth they consume. But it might be beneficial to avoid a congested link


        status = EOptimizationStatus.FEASIBLE
        t = Timer()
        with t:
            # OPTIMIZE
            selected_paths = self._solve()
        timing_object.time_optimizing_pint = t.elapsed_time



        if (status == EOptimizationStatus.FEASIBLE):
            # UPDATE tc

            for s in self.tc.F.values():
                node_mapping = set()
                for path in selected_paths[s.id].values():
                    for i in range(len(path)-1):
                        node_mapping.add((path[i], path[i+1]))

                mt = route(s)
                mt.init_from_node_mapping(node_mapping, self.tc.L_from_nodes)
                self.tc.add_to_datastructures(mt)
        else:
            raise ValueError(
                "CPSolver returned invalid status for SARouting model: " + str(status)
            )
        return self.tc, status
