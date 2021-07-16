
from input.testcase import Testcase
from input.input_parameters import InputParameters, EMode
from solution.solution_optimization_status import StatusObject
from solution.solution_timing_data import TimingData
from utils.cost import cost_routing, cost_schedule
from utils.utilities import VERSION


class Solution:
    def __init__(
        self,
        tc: Testcase,
        input_params: InputParameters,
        status_obj: StatusObject,
        timing_object: TimingData,
        security: bool,
        redundancy: bool,
    ):
        self.tc = tc
        self.input_params = input_params
        self.security = security
        self.redundancy = redundancy
        self.status_obj = status_obj
        self.timing_object = timing_object

        self.cost_total: int = -1
        self.bandwidth_used_percentage_total: float = -1
        self.cpu_used_percentage_total: float = -1

        self.cost_scheduling: int = -1
        self.infeasible_apps: int = -1
        self.cost_routing: int = -1
        self.total_overlaps_routing: int = -1
        self.total_number_of_stream_that_have_overlap: int = -1

        if not input_params.mode == EMode.VIEW:
            self.calculate_cost()
            self.calculate_bandwidth()
            self.calculate_cpu()


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
        return "{}: {} ES, {} SW, {} Tasks, {} Streams, {} Apps, {} Cost, {:.2f}% Bandwidth , {:.2f}% CPU , {:.2f}ms Optimization Time, Infeasible Apps {}/{}, Routing {}, Scheduling {}".format(
            self.input_params.tc_name,
            len(self.tc.ES),
            len(self.tc.SW),
            len(self.tc.T),
            len(self.tc.F),
            len(self.tc.A),
            self.cost_total,
            self.bandwidth_used_percentage_total * 100,
            self.cpu_used_percentage_total * 100,
            self.timing_object.get_optimization_time(),
            self.infeasible_apps,
            len(self.tc.A),
            self.getStatusRouting(),
            self.getStatusScheduling(),
        )

    def getStatusRouting(self) -> str:
        return self.status_obj.Routing_status.name

    def getStatusPint(self) -> str:
        return self.status_obj.Pint_status.name

    def getStatusScheduling(self) -> str:
        return self.status_obj.Scheduling_status.name

    def is_feasible_routing(self) -> bool:
        return (
            self.getStatusRouting() == "FEASIBLE"
            or self.getStatusRouting() == "OPTIMAL"
        )

    def is_feasible_scheduling(self) -> bool:
        return (
            self.getStatusScheduling() == "FEASIBLE"
            or self.getStatusScheduling() == "OPTIMAL"
        )

    def is_feasible_pint(self) -> bool:
        return (
            self.getStatusPint() == "FEASIBLE"
            or self.getStatusPint() == "OPTIMAL"
            or self.getStatusPint() == "NOT OPTIMIZED"
        )

    def is_feasible_all(self) -> bool:
        return (
            self.is_feasible_routing()
            and self.is_feasible_pint()
            and self.is_feasible_scheduling()
        )

    def calculate_cost(self):
        self.cost_routing, self.total_overlaps_routing, self.total_number_of_stream_that_have_overlap = cost_routing(self.tc, self.input_params.a)
        self.cost_scheduling, self.infeasible_apps = cost_schedule(self.tc, self.input_params.b)
        self.cost_total = self.cost_routing + self.cost_scheduling


    def calculate_bandwidth(self):
        perc_sum = 0
        for l in self.tc.L.values():
            bw_used = 0
            for f in self.tc.F_routed.values():
                if self.tc.R[f.id].is_in_tree(l.id, self.tc):
                    bw_used += f.size / f.period  # B/us
            perc = bw_used / l.speed
            assert perc <= 1
            perc_sum += perc

        self.bandwidth_used_percentage_total = perc_sum / len(self.tc.L.values())

    def calculate_cpu(self):
        perc_sum = 0
        for es in self.tc.ES.values():
            cpu_used = 0
            for t in self.tc.T_g[es.id]:
                cpu_used += t.exec_time / t.period

            for f in self.tc.F_g_out[es.id]:
                if f.is_secure:
                    cpu_used += es.mac_exec_time / f.period

            for f in self.tc.F_g_in[es.id]:
                if f.is_secure:
                    cpu_used += es.mac_exec_time / f.period

            perc = cpu_used
            assert perc <= 1
            perc_sum += perc

        self.cpu_used_percentage_total = perc_sum / len(self.tc.ES.values())

