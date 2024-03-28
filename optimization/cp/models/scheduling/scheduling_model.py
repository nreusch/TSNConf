import itertools
from enum import Enum
from typing import Dict, Tuple

from ortools.sat.python import cp_model
from ortools.sat.python.cp_model import (FEASIBLE, INFEASIBLE, MODEL_INVALID,
                                         OPTIMAL, UNKNOWN, CpModel, CpSolver,
                                         IntVar)

from input import testcase
from input.model.route import route
from optimization.cp.models.scheduling import (scheduling_model_constraints, scheduling_model_variables)
from optimization.cp.models.scheduling import scheduling_model_goals

from input.model.schedule import schedule
from input.testcase import Testcase
from input.input_parameters import InputParameters
from solution.solution_optimization_status import EOptimizationStatus
from solution.solution_timing_data import TimingData
from utils.utilities import Timer, print_model_stats, report_exception, list_gcd, debug_print


class EOptimizationGoal(Enum):
    MAXIMIZE_LAXITY = 1
    MAXIMIZE_LAXITY_AND_EXTENSIBLITY = 2
    MAXIMIZE_EXTENSIBILITY = 3


class CPSchedulingSolver:
    def __init__(
        self,
        tc: Testcase,
        timing_object: TimingData,
        optimization_goal: EOptimizationGoal,
        existing_schedule: schedule = None,
        do_security: bool = True,
        do_allow_infeasible_solutions: bool = False,
        dont_optimize: bool = False
    ):
        self.tc: testcase = tc

        period_set = set()
        for app in self.tc.A_app.values():
            period_set.add(app.period)
        period_list = list(period_set)
        self.gcd = list_gcd(period_list)

        self.Pint = tc.Pint
        self.mtrees: Dict[str, route] = tc.R  # stream.id -> Route

        # Create the CP model
        self.model = CpModel()

        # Create variables
        t = Timer()
        with t:
            self._create_variables()
            scheduling_model_variables.init_variables(self, existing_schedule, do_security)
        timing_object.time_creating_vars_scheduling = t.elapsed_time

        # Add constraints to CP model
        t = Timer()
        with t:
            scheduling_model_constraints.add_constraints(self, do_security, do_allow_infeasible_solutions)

            # Add optimization goal
            if optimization_goal == EOptimizationGoal.MAXIMIZE_LAXITY_AND_EXTENSIBLITY:
                scheduling_model_goals.maximize_laxity_and_extensibility(self)
            elif optimization_goal == EOptimizationGoal.MAXIMIZE_EXTENSIBILITY:
                scheduling_model_goals.maximize_extensibility(self, dont_optimize)
            elif optimization_goal == EOptimizationGoal.MAXIMIZE_LAXITY:
                scheduling_model_goals.maximize_laxity(self)
            else:
                raise ValueError

        timing_object.time_creating_constraints_scheduling = t.elapsed_time

    def _create_variables(self):
        # --- Streams
        # l.id -> Dict(stream.id -> IntVar)
        self.o_f: Dict[
            str, Dict[str, IntVar]
        ] = {}  # start time of stream on link from node n on route
        # l.id -> Dict(stream.id -> IntVar)
        self.c_f: Dict[
            str, Dict[str, IntVar]
        ] = {}  # execution time of stream on link from node n on route
        # l.id -> Dict(stream.id -> IntVar)
        self.a_f: Dict[
            str, Dict[str, IntVar]
        ] = {}  # finish time of stream on link from node n on route

        # stream.id -> IntVar
        self.phi_f: Dict[str, IntVar] = {}  # release interval of stream MAC key

        # --- Tasks
        # Dict(task.id -> IntVar)
        self.o_t: Dict[str, IntVar] = {}  # start time of t

        # Dict(task.id -> IntVar)
        self.a_t: Dict[str, IntVar] = {}  # end time of t

        # Dict(app.id -> IntVar)
        self.app_cost: Dict[str, IntVar] = {} # cost of app
        self.min_start_time: Dict[str, IntVar] = {} # min start time of app
        self.max_end_time: Dict[str, IntVar] = {} # max end time of app

        self.cost: IntVar = None

        self.actual_distances: Dict[str, IntVar] = {} # distance of task to closest next task
        self.inverse_distances: Dict[str, IntVar] = {} # hyperperiod - actual distance (so we can minimize)




    def optimize(
        self, input_params, timing_object: TimingData
    ) -> Tuple[Testcase, EOptimizationStatus, schedule, int]:
        solver = CpSolver()
        solver.parameters.max_time_in_seconds = input_params.timeouts.timeout_scheduling
        solver.parameters.random_seed = 10
        print_model_stats(self.model.ModelStats())

        t = Timer()
        try:
            with t:

                for l_or_n_id in itertools.chain(self.tc.L.keys(), self.tc.N.keys()):
                    self.model.AddDecisionStrategy(
                        list(self.o_f[l_or_n_id].values()),
                        cp_model.CHOOSE_LOWEST_MIN,
                        cp_model.SELECT_MIN_VALUE,
                    )

                ''' Probably better to avoid manual search strategy here for extensibility
                self.model.AddDecisionStrategy(
                    list(self.o_t.values()),
                    cp_model.CHOOSE_LOWEST_MIN,
                    cp_model.SELECT_MIN_VALUE,
                )
                '''

                self.model.AddDecisionStrategy(
                    list(self.phi_f.values()),
                    cp_model.CHOOSE_LOWEST_MIN,
                    cp_model.SELECT_MIN_VALUE,
                )

                solution_printer = cp_model.ObjectiveSolutionPrinter()
                solver_status = solver.SolveWithSolutionCallback(self.model, solution_printer)
                # print("Solved!\n{}".format(solver.ResponseStats()))
        except Exception as e:
            report_exception(e)
            solver_status = -1
        timing_object.time_optimizing_scheduling = t.elapsed_time

        print(solver.StatusName(solver_status))
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

        if (
            status == EOptimizationStatus.FEASIBLE
            or status == EOptimizationStatus.OPTIMAL
        ):
            debug_print(f"Total Cost: {solver.Value(self.cost)}")
            for app in self.tc.A.values():
                debug_print(f"Cost {app.id} = {solver.Value(self.app_cost[app.id])}")
                debug_print(f"MinStartTime {app.id} = {solver.Value(self.min_start_time[app.id])}")
                debug_print(f"MaxEndTime {app.id} = {solver.Value(self.max_end_time[app.id])}")
                debug_print("\n")
            for t in self.tc.T.values():
                if len(self.actual_distances) > 0:
                    if t.id in self.actual_distances and t.id in self.inverse_distances:
                        debug_print(f"Distance {t.id} = {solver.Value(self.actual_distances[t.id])}")
                        debug_print(f"Inverse Distance {t.id} = {solver.Value(self.inverse_distances[t.id])}")
                debug_print(f"o_t {t.id} = {solver.Value(self.o_t[t.id])}")
                debug_print(f"a_t {t.id} = {solver.Value(self.a_t[t.id])}")
                debug_print("\n")
            schdl = schedule.from_cp_solver(solver, self, self.tc)
            return self.tc, status,schdl,solver.Value(self.cost)
        else:
            report_exception(
                "CPSolver returned invalid status for scheduling model: " + str(status)
            )
            return self.tc, status,None,-1
