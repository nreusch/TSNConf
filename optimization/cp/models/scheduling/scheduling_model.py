import itertools
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
from utils.utilities import Timer, print_model_stats, report_exception


class CPSchedulingSolver:
    def __init__(
        self,
        tc: Testcase,
        timing_object: TimingData,
        input_params: InputParameters,
        do_simple_scheduling: bool = False,
    ):
        self.tc: testcase = tc
        self.Pint = tc.Pint
        self.mtrees: Dict[str, route] = tc.R  # stream.id -> Route

        # Create the CP model
        self.model = CpModel()

        # Create variables
        t = Timer()
        with t:
            self._create_variables()
            scheduling_model_variables.init_variables(self, input_params)
        timing_object.time_creating_vars_scheduling = t.elapsed_time

        # Add constraints to CP model
        t = Timer()
        with t:
            if do_simple_scheduling:
                scheduling_model_constraints.add_simple_constraints(self)
            else:
                scheduling_model_constraints.add_constraints(self)

            # Add optimization goal
            scheduling_model_goals.maximize_laxity(self, do_simple_scheduling)

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

    def optimize(
        self, input_params, timing_object: TimingData
    ) -> Tuple[Testcase, EOptimizationStatus]:
        solver = CpSolver()
        solver.parameters.max_time_in_seconds = input_params.timeouts.timeout_scheduling
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

                self.model.AddDecisionStrategy(
                    list(self.o_t.values()),
                    cp_model.CHOOSE_LOWEST_MIN,
                    cp_model.SELECT_MIN_VALUE,
                )
                self.model.AddDecisionStrategy(
                    list(self.phi_f.values()),
                    cp_model.CHOOSE_LOWEST_MIN,
                    cp_model.SELECT_MIN_VALUE,
                )
                solver_status = solver.Solve(self.model)
                # print("Solved!\n{}".format(solver.ResponseStats()))
        except Exception as e:
            report_exception(e)
            solver_status = -1
        timing_object.time_optimizing_scheduling = t.elapsed_time

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
            schdl = schedule.from_cp_solver(solver, self)
            self.tc.add_to_datastructures(schdl)
            return self.tc, status
        else:
            report_exception(
                "CPSolver returned invalid status for scheduling model_old: " + str(status)
            )
            return self.tc, status
