from typing import Dict, List, Tuple

from ortools.sat.python import cp_model
from ortools.sat.python.cp_model import (FEASIBLE, INFEASIBLE, MODEL_INVALID,
                                         OPTIMAL, UNKNOWN, CpModel, CpSolver,
                                         IntVar)
from optimization.cp.models.routing import routing_model_variables, routing_model_constraints, routing_model_goals
from optimization.cp.models.routing import routing_model_results

from input.model.route import route, route_info
from input.testcase import Testcase
from input.input_parameters import InputParameters
from solution.solution_optimization_status import EOptimizationStatus
from solution.solution_timing_data import TimingData
from utils.utilities import Timer, print_model_stats


def weight(v_int, x_v_val):
    print("weight: v_int={}; x_v_val={}".format(v_int, x_v_val))
    if x_v_val == -1:
        return 0
    else:
        return 1


class CPRoutingSolver:
    def __init__(self, tc: Testcase, timing_object: TimingData, redundancy: bool, allow_overlap: bool, existing_routes: Dict[str, route] = None, do_task_mapping: bool=False):
        self.tc = tc
        # Create the model
        self.model = CpModel()

        # Create variables
        t = Timer()
        with t:
            self._create_helper_variables()
            self._create_optimization_variables()
            routing_model_variables.init_helper_variables(self, existing_routes)
            routing_model_variables.init_optimization_variables(self, existing_routes)

        timing_object.time_creating_vars_routing = t.elapsed_time

        # Add constraints to model
        t = Timer()
        with t:
            routing_model_constraints.add_constraints(self, redundancy, allow_overlap)

            # Add optimization goal
            if do_task_mapping:
                # If we do task mapping, add task load balancing to the cost functions
                routing_model_goals.add_optimization_goal_plus_load_balancing(self, existing_routes)
            else:
                routing_model_goals.add_optimization_goal(self, existing_routes)

            timing_object.time_creating_constraints_routing = t.elapsed_time

    def _create_optimization_variables(self):
        # task mapping
        self.m_t: Dict[str, IntVar] = {}
        self.t_mapped_ES_is_v: Dict[List[IntVar]] = {}
        self.f_sender_is_v: List[List[IntVar]] = []
        self.f_rcvr_is_v: List[List[IntVar]] = []


        # ---  ES_capacity[v_int] = X, means X capacity is used on ES v
        # ---  ES_capc_use_of_t[v_int][t_int] = X, means X capacity is used by t on ES v
        self.ES_capacity: List[IntVar] = []
        self.ES_capc_use_of_t: List[List[IntVar]] = []

        # NOTE: The optimization finds the path backwards, from receivers to sender
        # Thus the meaning of successor/predecessor is reversed compared to the normal understanding

        # x[f_int][v_int] = u_int, means f uses the link from u to v
        # x[f_int][v_int] = -1, means f doesnt use the link from u to v
        self.x: List[List[IntVar]] = []  # MT_f
        self.x_v_possible_domain: Dict[str, Dict[str, List[str]]] = {}
        self.x_v_possible_domain_ids: Dict[str, Dict[str, List[int]]] = {}

        # x_v_has_successor[f_int][v_int] = 1, means f uses a link from somewhere to v
        # x_v_has_predecessor[f_int][v_int] = 1, means f uses a link from v to somewhere
        self.x_v_has_successor: List[List[IntVar]] = []
        self.x_v_has_predecessor: List[List[IntVar]] = []

        # x_v_is_u[f_int][v_int][u_int] = 1, means f uses the link from u to v x_v_is_not_u[f_int][v_int][u_int] = 1,
        # means f doesnt use the link from u to v x_v_is_u_and_uses_bandwidth[f_int][v_int][u_int] = 1, means f uses
        # the link from u to v and f is the one redundant copy using bandwidth
        self.x_v_is_u: List[List[List[IntVar]]] = []  #
        self.x_v_is_not_u: List[List[List[IntVar]]] = []  #
        self.x_v_is_u_and_uses_bandwidth: List[List[List[IntVar]]] = []

        self.y: List[List[IntVar]] = []  # MT_w

        # link_capacity[v_int][u_int] = X, means X capacity is used on link from u to v
        # v_to_u_capc_use_of_f[f_int][v_int][u_int] = X, means X capacity is used by f on link from u to v
        self.link_capacity: List[List[IntVar]] = []
        self.v_to_u_capc_use_of_f: List[List[List[IntVar]]] = []

        # stream_route_lens[f.id] = X, means the route of stream f is X links long link_weights[f.id][v.id] = 1,
        # means f uses a link from somewhere to v link_occupations[f.id_prefix][v.id][u.id] = X, means f and its
        # redundant copies use the link from u to v X times
        self.stream_route_lens: Dict[str, IntVar] = {}
        self.link_weights: Dict[str, Dict[str, IntVar]] = {}
        self.link_occupations: Dict[str, Dict[str, Dict[str, IntVar]]] = {}

        self.stream_overlaps: Dict[str, List[IntVar]] = {}  # stream.id -> [IntVar]
        self.stream_cost: Dict[str, IntVar] = {}  # stream.id -> IntVar
        self.es_cost: IntVar = None
        self.total_cost: IntVar = None  # IntVar

    def _create_helper_variables(self):
        self._StreamIDToIntMap: Dict[str, int] = {}
        self._IntToStreamIDMap: Dict[int, str] = {}
        self._NodeIDToIntMap: Dict[str, int] = {}
        self._IntToNodeIDMap: Dict[int, str] = {}
        self.max_stream_int: int = 0
        self.max_node_int: int = 0

    def optimize(
        self, input_params: InputParameters, timing_object: TimingData
    ) -> Tuple[Testcase, EOptimizationStatus, Dict, int]:
        # Solve model_Pint.
        solver = CpSolver()
        solver.parameters.max_time_in_seconds = input_params.timeouts.timeout_routing
        solver.parameters.random_seed = 10
        print_model_stats(self.model.ModelStats())
        t = Timer()
        with t:
            for f_int in range(self.max_stream_int):
                self.model.AddDecisionStrategy(
                    list(self.x[f_int]),
                    cp_model.CHOOSE_LOWEST_MIN,
                    cp_model.SELECT_MIN_VALUE,
                )
                self.model.AddDecisionStrategy(
                    list(self.x_v_has_successor[f_int]),
                    cp_model.CHOOSE_LOWEST_MIN,
                    cp_model.SELECT_MIN_VALUE,
                )
                self.model.AddDecisionStrategy(
                    list(self.y[f_int]),
                    cp_model.CHOOSE_LOWEST_MIN,
                    cp_model.SELECT_MIN_VALUE,
                )

            solver_status = solver.Solve(self.model)
            # print(solver.ResponseStats())
        timing_object.time_optimizing_routing = t.elapsed_time

        status = EOptimizationStatus.INFEASIBLE

        if solver_status == OPTIMAL:
            status = EOptimizationStatus.OPTIMAL
        elif solver_status == FEASIBLE:
            status = EOptimizationStatus.FEASIBLE
        elif solver_status == INFEASIBLE:
            status = EOptimizationStatus.INFEASIBLE
        elif solver_status == UNKNOWN:
            status = EOptimizationStatus.UNKNOW
        elif solver_status == MODEL_INVALID:
            status = EOptimizationStatus.MODEL_INVALID

        # Output
        if (
            status == EOptimizationStatus.FEASIBLE
            or status == EOptimizationStatus.OPTIMAL
        ):
            x_res, costs, route_lens, overlap_amounts, overlap_links, y_res, m_res, es_capacity_res, total_cost = routing_model_results.generate_result_structures(self, solver)

            # Add task mapping to data structures
            for t_id, es_id in m_res.items():
                t = self.tc.T[t_id]

                if t.src_es_id != "":
                    if t.src_es_id != es_id:
                        raise ValueError("task should not be mapped to a new ES, if it was already mapped")
                else:
                    print(f"Mapped {t} to {es_id}")
                    t.src_es_id = es_id
                    self.tc.T_g[t.src_es_id].append(t)


            # Add stream routing to data structures
            for f_int in range(self.max_stream_int):
                f_id = self._IntToStreamIDMap[f_int]
                f = self.tc.F[f_id]

                # Assign sender/receiver ES ids, if they weren't already given before optimization
                if f.sender_es_id == "":
                    f.sender_es_id = self.tc.T[f.sender_task_id].src_es_id
                    self.tc.F_g_out[f.sender_es_id].append(f)

                if len(f.receiver_es_ids.keys()) == 1 and "" in f.receiver_es_ids.keys():
                    f.receiver_es_ids = {} # clear out the empty entry
                    for t_id in f.receiver_task_ids.keys():
                        f.receiver_es_ids[self.tc.T[t_id].src_es_id] = None
                    for es_id in f.receiver_es_ids.keys():
                        self.tc.F_g_in[es_id].append(f)

                assert len(f.receiver_es_ids.keys()) > 0
                assert "" not in f.receiver_es_ids.keys()
                assert f.sender_es_id != ""

                mt = route(f)
                mt.init_from_x_res_vector(x_res[f.id])
                self.tc.add_to_datastructures(mt)

                r_info = route_info(mt, route_lens[f.id], overlap_amounts[f.id], overlap_links[f.id])
                self.tc.add_to_datastructures(r_info)
        else:
            raise ValueError(
                "CPSolver in RoutingModel returned invalid status for routing model:"
                + str(status)
            )

        return self.tc, status, es_capacity_res, total_cost
