from dataclasses import dataclass


@dataclass
class TimingData:
    def __init__(self):
        self.time_parsing: float = 0
        self.time_creating_secapps: float = 0
        self.time_creating_streams: float = 0

        self.time_creating_vars_routing: float = 0
        self.time_creating_vars_pint: float = 0
        self.time_creating_vars_scheduling: float = 0
        self.time_creating_vars_simulated_annealing: float = 0


        self.time_creating_constraints_routing: float = 0
        self.time_creating_constraints_pint: float = 0
        self.time_creating_constraints_scheduling: float = 0

        self.time_optimizing_routing: float = 0
        self.time_optimizing_pint: float = 0
        self.time_optimizing_scheduling: float = 0
        self.time_optimizing_simulated_annealing: float = 0

        self.time_serializing_solution: float = 0

    def get_total_time(self) -> float:
        return (
            self.get_optimization_time()
            + self.time_parsing
            + self.time_serializing_solution
            + self.time_creating_secapps
            + self.time_creating_streams
        )

    def get_optimization_time(self) -> float:
        return (
            self.time_creating_vars_routing
            + self.time_creating_vars_scheduling
            + self.time_creating_vars_pint
            + self.time_creating_vars_simulated_annealing
            + self.time_creating_constraints_pint
            + self.time_creating_constraints_scheduling
            + self.time_creating_constraints_routing
            + self.time_optimizing_routing
            + self.time_optimizing_pint
            + self.time_optimizing_scheduling
            + self.time_optimizing_simulated_annealing
        )
