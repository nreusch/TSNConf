from dataclasses import dataclass
from enum import Enum
from pathlib import Path


@dataclass
class Timeouts:
    def __init__(
        self, timeout_pint: int, timeout_routing: int, timeout_scheduling: int
    ):
        """

        :param timeout_pint: Timeout of Pint optimization in seconds
        :param timeout_routing: Timeout of routing optimization in seconds
        :param timeout_scheduling: Timeout of scheduling optimization in seconds
        :return:
        """
        self.timeout_pint = timeout_pint
        self.timeout_routing = timeout_routing
        self.timeout_scheduling = timeout_scheduling

    def __str__(self):
        return "Timeout Pint: {}s\nTimeout Routing: {}s\nTimeout Scheduling: {}s".format(
            self.timeout_pint, self.timeout_routing, self.timeout_scheduling
        )


class EMode(Enum):
    VIEW = 0
    ALL_CP_ROUTING_AND_SECURITY = 1
    ONLY_CP_SCHEDULING = 2
    HEURISTIC_ROUTING_1_AND_SECURITY = 3
    HEURISTIC_ROUTING_2_AND_SECURITY = 4
    HEURISTIC_ROUTING_3_AND_SECURITY = 5

    def describe(self) -> str:
        if self.value == 0:
            return "Mode 0: View/Check the testcase. Doesn't generate/optimize anything"
        elif self.value == 1:
            return "Mode 1: Generate Security Applications, CP Routing, CP Scheduling"
        elif self.value == 2:
            return "Mode 2: CP Scheduling"
        elif self.value == 3:
            return "Mode 3: Generate Security Applications,  SA Routing, ASAP Scheduling"
        elif self.value == 4:
            return "Mode 4: Generate Security Applications,  SA Routing, SA Scheduling (Seperated)"
        elif self.value == 5:
            return "Mode 5: Generate Security Applications,  SA Routing, ASAP Scheduling (Combined)"
        return ""

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


@dataclass
class InputParameters:
    def __init__(self, mode: EMode, timeouts: Timeouts, tc_path: str, visualize: bool, port: int, no_redundancy: bool, no_security: bool):
        self.mode = mode

        self.timeouts = timeouts

        self.tc_path = tc_path
        self.tc_name = Path(tc_path).stem
        self.visualize = visualize
        self.port = port
        self.no_redundancy = no_redundancy
        self.no_security = no_security
        # self.tc_name = results.testcase_path.split("/")[-1].split(".")[0]

    def get_summary_string(self) -> str:
        """
        Returns a short string summarizing the input parameters
        """
        s = "mode{}_{}_{}_{}".format(
            self.mode.value,
            self.timeouts.timeout_pint,
            self.timeouts.timeout_routing,
            self.timeouts.timeout_scheduling,
        )
        return s

    def get_full_string(self) -> str:
        """
        Returns a long string summarizing the input parameters
        """
        return "{}\nTestcase: {}\n{}\n{}\n{}".format(
            "-" * 80, self.tc_name, self.mode.describe(), self.timeouts, "-" * 80
        )
