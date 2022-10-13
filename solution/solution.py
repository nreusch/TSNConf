from typing import Dict

from input.input_parameters import InputParameters, EMode
from input.testcase import Testcase
from solution.solution_optimization_status import StatusObject
from solution.solution_timing_data import TimingData
from utils.cost import cost_schedule
from utils.utilities import VERSION


class Solution:
    def __init__(
        self,
        tc: Testcase,
        scheduling_solution,
        cost: int,
        infeasible_streams: int,
        stream_costs: Dict,
        input_params: InputParameters,
        status_obj: StatusObject,
        timing_object: TimingData,
    ):
        self.tc = tc
        self.input_params = input_params
        self.status_obj = status_obj
        self.timing_object = timing_object

        self.stream_costs = stream_costs
        self.infeasible_streams = infeasible_streams
        self.cost = cost
        self.scheduling_solution = scheduling_solution

    def get_folder_name(self) -> str:
        """
        Returns the name of the folder used to store the solution data
        """
        return "{}_{}_{}".format(
            self.tc.name, self.input_params.get_summary_string(), VERSION
        )

    def get_result_string(self) -> str:
        """
        Returns a string containing all important results
        """
        return "{}: {} ES, {} SW, {} Streams, {} Cost, {:.2f}ms Optimization Time, Infeasible Streams {}/{}, Scheduling {}".format(
            self.input_params.tc_name,
            len(self.tc.ES),
            len(self.tc.SW),
            len(self.tc.F),
            self.cost,
            self.timing_object.get_optimization_time(),
            self.infeasible_streams,
            len(self.tc.F),
            self.getStatusScheduling(),
        )

    def getStatusScheduling(self) -> str:
        return self.status_obj.Scheduling_status.name

    def is_feasible_scheduling(self) -> bool:
        return (
            self.getStatusScheduling() == "FEASIBLE"
            or self.getStatusScheduling() == "OPTIMAL"
        )