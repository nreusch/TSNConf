from input.model.application import EApplicationType
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

        self.ra_avg_max_unattested_time: float = -1
        self.ra_avg_time_spent_attesting: float = -1
        self.ext_avg_worst_case_resp_time: float = -1
        self.ext_avg_avg_case_resp_time: float = -1

        self.avg_edge_application_latency: float = -1

        if not input_params.mode == EMode.VIEW:
            self.calculate_cost()
            self.calculate_bandwidth()
            self.calculate_cpu()
            #self.calculate_ra_and_extensibility_metrics()


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
        perc_sum = sum([v for v in self.tc.schedule.bw_use.values()])

        self.bandwidth_used_percentage_total = perc_sum / len(self.tc.L.values())

    def calculate_cpu(self):
        print(self.tc.schedule.cpu_use)
        perc_sum = sum([v for v in self.tc.schedule.cpu_use.values()])

        self.cpu_used_percentage_total = perc_sum / len(self.tc.ES.values())

    def calculate_ra_and_extensibility_metrics(self):
        ra_metrics = self.tc.schedule.get_RA_metrics(self.tc)
        extensibility_metrics = self.tc.schedule.get_Extensibility_metrics(self.tc)

        self.ra_avg_max_unattested_time = sum([ram[0] for ram in ra_metrics.values()]) / len(ra_metrics)
        self.ra_avg_time_spent_attesting = sum([ram[1] for ram in ra_metrics.values()]) / len(ra_metrics)
        self.ext_avg_worst_case_resp_time = sum([em[0] for em in extensibility_metrics.values()]) / len(extensibility_metrics)
        self.ext_avg_avg_case_resp_time = sum([em[1] for em in extensibility_metrics.values()]) / len(extensibility_metrics)

        if self.input_params.extra_apps_path != "":
            nr_edge_apps = 0
            for app in self.tc.A.values():
                if app.type == EApplicationType.EDGE:
                    self.avg_edge_application_latency += (max([self.tc.schedule.a_t_val[t.id] for t in app.verticies.values()]) - min([t.arrival_time for t in app.verticies.values()]))
                    nr_edge_apps += 1

            if nr_edge_apps != 0:
                self.avg_edge_application_latency = self.avg_edge_application_latency / nr_edge_apps