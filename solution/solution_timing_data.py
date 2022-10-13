from dataclasses import dataclass


@dataclass
class TimingData:
    def __init__(self):
        self.time_parsing: float = 0
        self.time_creating_streams: float = 0

        self.time_creating_vars_simulated_annealing: float = 0


        self.time_optimizing_simulated_annealing: float = 0

        self.time_first_feasible_solution: float = 0

        self.time_serializing_solution: float = 0

    def get_total_time(self) -> float:
        return (
            self.get_optimization_time()
            + self.time_parsing
            + self.time_serializing_solution
            + self.time_creating_streams
        )

    def get_optimization_time(self) -> float:
        return (
            self.time_creating_vars_simulated_annealing
            + self.time_optimizing_simulated_annealing
        )
