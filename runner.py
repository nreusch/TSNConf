from pathlib import Path

from input import parser
from input.input_parameters import EMode, InputParameters
from optimization.multi_window.multi_window_solver import MultiWindowSASchedulingSolver, MultiWindowOptimizationMode
from optimization.signle_window.single_window_solver import SingleWindowSASchedulingSolver, SAOptimizationMode
from solution.solution import Solution
from solution.solution_optimization_status import StatusObject
from solution.solution_timing_data import TimingData
from utils import serializer
from utils.utilities import Timer


def _mode_sa_single(timing_object: TimingData, input_params: InputParameters) -> Solution:
    """
    Mode 1: SA
    """
    status_obj = StatusObject()

    # 1. Parse the given testcase
    t = Timer()
    with t:
        tc = parser.parse_to_model(input_params.tc_name, input_params.tc_path)
    timing_object.time_parsing = t.elapsed_time
    print(
        "-" * 20
        + " Parsed testcase: {}, in {:.2f} ms".format(
            input_params.tc_name, timing_object.time_parsing
        )
    )

    # 2. Find scheduling (SA)
    scheduling_model = SingleWindowSASchedulingSolver(tc, timing_object, input_params)
    tc, schedule_solution, status = scheduling_model.optimize(input_params, timing_object, SAOptimizationMode.NORMAL)
    print(
        "-" * 20
        + " Found Schedule in {:.2f} ms".format(
            timing_object.time_optimizing_simulated_annealing
        )
    )
    status_obj.Scheduling_status = status


    # 3. Serialize solution
    solution = Solution(tc, schedule_solution, schedule_solution.cost, schedule_solution.infeasible_streams, schedule_solution.stream_costs, input_params, status_obj, timing_object)
    if input_params.simple:
        serializer.minimal_serialize_solution(Path("testcases/output"), solution, True)
    else:
        serializer.serialize_solution(Path("testcases/output"), solution, True)

    return solution, tc

def _mode_sa_multi(timing_object: TimingData, input_params: InputParameters) -> Solution:
    """
    Mode 1: SA
    """
    status_obj = StatusObject()

    # 1. Parse the given testcase
    t = Timer()
    with t:
        tc = parser.parse_to_model(input_params.tc_name, input_params.tc_path)
    timing_object.time_parsing = t.elapsed_time
    print(
        "-" * 20
        + " Parsed testcase: {}, in {:.2f} ms".format(
            input_params.tc_name, timing_object.time_parsing
        )
    )

    # 2. Find scheduling (SA, Multi window)
    scheduling_model = MultiWindowSASchedulingSolver(tc, timing_object, input_params)
    tc, schedule_solution, status = scheduling_model.optimize(input_params, timing_object, MultiWindowOptimizationMode.NORMAL)
    print(
        "-" * 20
        + " Found Schedule in {:.2f} ms".format(
            timing_object.time_optimizing_simulated_annealing
        )
    )
    status_obj.Scheduling_status = status


    # 3. Serialize solution
    solution = Solution(tc, schedule_solution, schedule_solution.cost, schedule_solution.infeasible_streams, schedule_solution.stream_costs, input_params, status_obj, timing_object)
    if input_params.simple:
        serializer.minimal_serialize_solution(Path("testcases/output"), solution, True)
    else:
        serializer.serialize_solution(Path("testcases/output"), solution, True)

    return solution, tc

def run_mode(
    mode: EMode, timing_object: TimingData, input_params: InputParameters
) -> Solution:
    if mode is EMode.SA_SingleWindow:
        return _mode_sa_single(timing_object, input_params)
    elif mode is EMode.SA_MultiWindow:
        return _mode_sa_multi(timing_object, input_params)
    else:
        raise ValueError(f"Mode {mode} is not supported")
