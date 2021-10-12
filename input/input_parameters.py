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
        return "Timeout Pint: {}s\nTimeout Routing: {}s\nTimeout Scheduling: {}s\n(If combined routing+scheduling, Timeout Scheduling is used)".format(
            self.timeout_pint, self.timeout_routing, self.timeout_scheduling
        )


class EMode(Enum):
    VIEW = 0
    CP_ROUTING_CP_SCHEDULING = 1
    CP_ROUTING_CP_SCHEDULING_EXT = 2
    SA_ROUTING_ASAP_SCHEDULING = 11
    SA_ROUTING_SA_SCHEDULING = 12
    SA_ROUTING_SA_SCHEDULING_COMB = 13

    def describe(self) -> str:
        if self.value == 0:
            return "Mode 0: View/Check the testcase. Doesn't generate/optimize anything"
        elif self.value == 1:
            return "Mode 1: CP Routing, CP Scheduling, Security, Redundancy, Optimization (Optimize laxity)"
        elif self.value == 2:
            return "Mode 2: CP Routing, CP Scheduling, Security, Redundancy, Optimization (Optimize laxity + extensibility)"
        elif self.value == 11:
            return "Mode 11: SA Routing, ASAP Scheduling, Security, Redundancy, Optimization"
        elif self.value == 12:
            return "Mode 12: SA Routing, SA Scheduling, Security, Redundancy, Optimization"
        elif self.value == 13:
            return "Mode 13: SA Routing+Scheduling, Security, Redundancy, Optimization"
        return ""

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


@dataclass
class InputParameters:
    def __init__(self, mode: EMode, timeouts: Timeouts, tc_path: str, extra_apps_path: str, visualize: bool, aggregate_path: str, port: int, no_redundancy: bool, no_security: bool, allow_overlap: bool, allow_infeasible_solutions: bool, k: int, a: int, b: int, Tstart: int, alpha: float, Prmv: float, w: int):
        self.mode = mode

        self.timeouts = timeouts

        self.tc_path = tc_path
        self.extra_apps_path = extra_apps_path
        self.tc_name = Path(tc_path).stem

        if aggregate_path != "":
            self.aggregate_path = Path(aggregate_path)
        else:
            self.aggregate_path = ""
        self.visualize = visualize
        self.port = port

        self.no_redundancy = no_redundancy
        self.no_security = no_security
        self.allow_overlap = allow_overlap
        self.allow_infeasible_solutions = allow_infeasible_solutions

        self.k = k
        self.a = a
        self.b = b
        self.Tstart = Tstart
        self.alpha = alpha
        self.Prmv = Prmv
        self.w = w

    def get_summary_string(self) -> str:
        """
        Returns a short string summarizing the input parameters
        """
        s = "mode{}_{}_{}_{}_{}{}{}".format(
            self.mode.value,
            self.timeouts.timeout_pint,
            self.timeouts.timeout_routing,
            self.timeouts.timeout_scheduling,
            'T' if self.no_redundancy else 'F',
            'T' if self.no_security else 'F',
            'T' if self.allow_overlap else 'F',
            'T' if self.allow_infeasible_solutions else 'F'
        )
        return s

    def get_full_string(self) -> str:
        """
        Returns a long string summarizing the input parameters
        """
        return "{}\nTestcase: {}\n{}\n{}\n{}\n{}\n{}\n{}\n{}".format(
            "-" * 80, self.tc_name, self.mode.describe(), self.timeouts,
            f"No redundancy: {self.no_redundancy}",
            f"No security: {self.no_security}",
            f"Overlap allowed for CP: {self.allow_overlap}",
            f"Infeasible solutions allowed for CP: {self.allow_infeasible_solutions}",
            "-" * 80
        )
