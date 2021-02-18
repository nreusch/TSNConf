
from input.testcase import Testcase
from input.input_parameters import InputParameters
from solution.solution_optimization_status import StatusObject
from solution.solution_timing_data import TimingData
from utils.utilities import VERSION


class Solution:
    def __init__(
        self,
        tc: Testcase,
        input_params: InputParameters,
        status_obj: StatusObject,
        timing_object: TimingData,
    ):
        self.tc = tc
        self.input_params = input_params
        self.status_obj = status_obj
        self.timing_object = timing_object

        self.laxity_total: int = -1
        self.total_deadlines: int = 0
        self.missed_deadlines: int = 0
        self.e2e_delays_total: int = -1
        self.bandwidth_used_percentage_total: int = -1
        self.cpu_used_percentage_total: int = -1

        self.total_cost_routing: float = -1
        # Populate variables
        if self.is_feasible_routing():
            self.total_cost_routing = 0
            for r_info in self.tc.R_info.values():
                self.total_cost_routing += r_info.cost
        if self.is_feasible_scheduling():
            for v in self.tc.schedule.laxities_val.values():
                self.total_deadlines += 1
                if v < 0:
                    self.missed_deadlines += 1
                self.laxity_total += v

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
            """
            for v in self.tc.schedule.e2e_delays.values():
                self.e2e_delays_total += v

            # bandwidth_used_percentage_total = (sum of all total sending times on links / (hyperperiod*amount of links))*100
            if len(self.tc.schedule.bandwidth_used) == 0:
                self.bandwidth_used_percentage_total = 0
            else:
                for v in self.tc.schedule.bandwidth_used.values():
                    self.bandwidth_used_percentage_total += v
                self.bandwidth_used_percentage_total = (self.bandwidth_used_percentage_total / (
                            self.tc.hyperperiod * len(self.tc.schedule.bandwidth_used))) * 100

            # cpu_used_percentage_total = (sum of all total wcet on pes / (hyperperiod*amount of pes)) * 100
            for v in self.tc.schedule.cpu_used.values():
                self.cpu_used_percentage_total += v
            self.cpu_used_percentage_total = (self.cpu_used_percentage_total / (
                        self.tc.hyperperiod * len(self.tc.schedule.cpu_used))) * 100
            """

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
        return "{}: {} ES, {} SW, {} Tasks, {} Streams, {} Laxity, {:.2f}% Bandwidth , {:.2f}% CPU , {:.2f}ms Optimization Time, Missed Deadlines {}/{}, Routing {}, Scheduling {}".format(
            self.input_params.tc_name,
            len(self.tc.ES),
            len(self.tc.SW),
            len(self.tc.T),
            len(self.tc.F),
            self.laxity_total,
            self.bandwidth_used_percentage_total * 100,
            self.cpu_used_percentage_total * 100,
            self.timing_object.get_optimization_time(),
            self.missed_deadlines,
            self.total_deadlines,
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
