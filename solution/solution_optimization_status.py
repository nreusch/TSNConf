from enum import Enum


class EOptimizationStatus(Enum):
    NOT_OPTIMIZED = 0
    INFEASIBLE = 1
    FEASIBLE = 2
    OPTIMAL = 3
    MODEL_INVALID = 5
    UNKNOW = 6


class StatusObject:
    def __init__(self):
        self.Scheduling_status: EOptimizationStatus = EOptimizationStatus.NOT_OPTIMIZED
