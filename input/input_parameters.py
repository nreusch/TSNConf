from dataclasses import dataclass
from enum import Enum
from pathlib import Path


@dataclass
class Timeouts:
    def __init__(
        self, timeout_scheduling: int
    ):
        """

        :param timeout_pint: Timeout of Pint optimization in seconds
        :param timeout_routing: Timeout of routing optimization in seconds
        :param timeout_scheduling: Timeout of scheduling optimization in seconds
        :return:
        """
        self.timeout_scheduling = timeout_scheduling

    def __str__(self):
        return "Timeout Scheduling: {}s\n".format(
             self.timeout_scheduling
        )


class EMode(Enum):
    SA_SingleWindow = 0
    SA_MultiWindow = 1

    def describe(self) -> str:
        if self.value == 0:
            return "Mode 0: Unscheduled ES, SA solution, single window per queue"
        elif self.value == 1:
            return "Mode 1: Unscheduled ES, SA solution, multi window per queue"
        return ""

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


@dataclass
class InputParameters:
    def __init__(self, mode: EMode, timeouts: Timeouts, tc_path: str, visualize: bool, aggregate_path: str, port: int, luxi_port: int, b: int, Tstart: int, alpha: float, Prmv: float, simple: bool):
        self.mode = mode

        self.timeouts = timeouts

        self.tc_path = tc_path
        self.tc_name = Path(tc_path).stem

        if aggregate_path != "":
            self.aggregate_path = Path(aggregate_path)
        else:
            self.aggregate_path = ""
        self.visualize = visualize
        self.port = port
        self.luxi_port = luxi_port

        self.b = b
        self.Tstart = Tstart
        self.alpha = alpha
        self.Prmv = Prmv

        self.simple = simple

    def get_summary_string(self) -> str:
        """
        Returns a short string summarizing the input parameters
        """
        s = "mode{}_{}".format(
            self.mode.value,
            self.timeouts.timeout_scheduling,
        )
        return s

    def get_full_string(self) -> str:
        """
        Returns a long string summarizing the input parameters
        """
        return "{}\nTestcase: {}\n{}\n{}\n{}\n{}\n{}\n".format(
            "-" * 80, self.tc_name, self.mode.describe(), self.timeouts,
            f"b: {self.b}",
            f"Tstart: {self.Tstart}",
            f"alpha: {self.alpha}",
            "-" * 80
        )
