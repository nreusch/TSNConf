from typing import Tuple

from ortools.sat.python.cp_model import (FEASIBLE, INFEASIBLE, MODEL_INVALID,
                                         OPTIMAL, UNKNOWN, CpModel, CpSolver)

from input.model.schedule import schedule
from input.testcase import Testcase
from input.input_parameters import InputParameters
from solution.solution_optimization_status import EOptimizationStatus
from solution.solution_timing_data import TimingData
from utils.utilities import Timer, list_gcd, print_model_stats


class SASchedulingSolver:
    def __init__(self, tc: Testcase, timing_object: TimingData):
        self.tc = tc

        # Create the model
        self.model = CpModel()

        # Create variables
        t = Timer()
        with t:
            self._create_variables()
        timing_object.time_creating_vars_pint = t.elapsed_time


    def _create_variables(self):
        self.Pint_var = self.model.NewIntVar(0, self.tc.hyperperiod, "Pint")

    def optimize(
        self, input_params: InputParameters, timing_object: TimingData
    ) -> Tuple[Testcase, EOptimizationStatus]:

        status = EOptimizationStatus.FEASIBLE
        t = Timer()
        with t:
            # OPTIMIZE
            pass
        timing_object.time_optimizing_pint = t.elapsed_time



        if (status == EOptimizationStatus.FEASIBLE):
            # UPDATE tc
            # TODO: remove
            status = EOptimizationStatus.INFEASIBLE
            self.tc.schedule = schedule()
        else:
            raise ValueError(
                "CPSolver returned invalid status for SAScheduling model: " + str(status)
            )
        return self.tc, status
