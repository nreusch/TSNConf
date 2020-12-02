from typing import Tuple

from ortools.sat.python.cp_model import (FEASIBLE, INFEASIBLE, MODEL_INVALID,
                                         OPTIMAL, UNKNOWN, CpModel, CpSolver)

from input.testcase import Testcase
from input.input_parameters import InputParameters
from solution.solution_optimization_status import EOptimizationStatus
from solution.solution_timing_data import TimingData
from utils.utilities import Timer, list_gcd, print_model_stats


class CPPintSolver:
    def __init__(self, tc: Testcase, timing_object: TimingData):
        self.tc = tc

        # Create the model
        self.model = CpModel()

        # Create variables
        t = Timer()
        with t:
            self._create_variables()
        timing_object.time_creating_vars_pint = t.elapsed_time

        # Add constraints to model
        t = Timer()
        with t:
            self._add_constraints()

            self._add_optimization_goal_maximize()

            timing_object.time_creating_constraints_pint = t.elapsed_time

    def _create_variables(self):
        self.Pint_var = self.model.NewIntVar(0, self.tc.hyperperiod, "Pint")

    def _add_constraints(self):
        app_period_list = []

        for app in self.tc.A_app.values():
            # Constraint 1: Pint * fp.C <= fp.D
            for fp in app.function_paths.values():
                self.model.Add(self.Pint_var * fp.signal_level <= fp.deadline)

            # Constraint 2: Pint <= app.T
            self.model.Add(self.Pint_var <= app.period)

            app_period_list.append(app.period)

        # Constraint 3: Pint mod gcd(all app periods) = 0 OR Pint * n = gcd(all app periods)
        gcd = list_gcd(app_period_list)
        PintIsMultiple = self.model.NewBoolVar("PintIsMultiple")
        PintIsFactor = self.model.NewBoolVar("PintIsFactor")

        pint_mod_gcd = self.model.NewIntVar(0, self.tc.hyperperiod, "")
        self.model.AddModuloEquality(pint_mod_gcd, self.Pint_var, gcd)
        self.model.Add(pint_mod_gcd == 0).OnlyEnforceIf(PintIsMultiple)

        n = self.model.NewIntVar(1, gcd, "n")
        pint_times_n = self.model.NewIntVar(0, self.tc.hyperperiod, "")
        self.model.AddMultiplicationEquality(pint_times_n, [self.Pint_var, n])
        self.model.Add(pint_times_n == gcd).OnlyEnforceIf(PintIsFactor)

        self.model.AddBoolOr([PintIsFactor, PintIsMultiple])

    def _add_optimization_goal_maximize(self):
        self.model.Maximize(self.Pint_var)

    def optimize(
        self, input_params: InputParameters, timing_object: TimingData
    ) -> Tuple[Testcase, EOptimizationStatus]:
        solver = CpSolver()
        solver.parameters.max_time_in_seconds = input_params.timeouts.timeout_pint
        print_model_stats(self.model.ModelStats())

        t = Timer()
        with t:
            solver_status = solver.Solve(self.model)
        timing_object.time_optimizing_pint = t.elapsed_time

        Pint = -1
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
            r = solver.Value(self.Pint_var)
            Pint = r

        else:
            raise ValueError(
                "CPSolver returned invalid status for Pint model: " + str(status)
            )
        self.tc.Pint = Pint
        return self.tc, status
