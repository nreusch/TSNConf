from optimization.cp.models.routing.routing_model import CPRoutingSolver
from optimization.sa.sa_routing_solver import SARoutingSolver
from optimization.sa.sa_scheduling_solver import SASchedulingSolver, SAOptimizationMode
from optimization.cp.models.scheduling.scheduling_model import CPSchedulingSolver
from optimization.cp.models.pint.pint_model import CPPintSolver

from generators import security_app_generator
from input import parser
from input.input_parameters import EMode, InputParameters
from solution.solution_optimization_status import EOptimizationStatus, StatusObject
from solution.solution import Solution
from solution.solution_timing_data import TimingData
from utils.utilities import Timer

def _mode_0(timing_object: TimingData, input_params: InputParameters) -> Solution:
    """
    Mode 0: View/Check the testcase. Doesn't generate/optimize anything
    """
    status_obj = StatusObject()

    # 1. Parse the given testcase
    t = Timer()
    with t:
        tc = parser.parse_to_model(input_params)
    timing_object.time_parsing = t.elapsed_time
    print(
        "-" * 20
        + " Parsed testcase: {}, in {:.2f} ms".format(
            input_params.tc_name, timing_object.time_parsing
        )
    )

    # 2. Create solution object
    solution_object = Solution(tc, input_params, status_obj, timing_object)

    return solution_object

def _mode_1(timing_object: TimingData, input_params: InputParameters) -> Solution:
    """
    Mode 1: Generate Security Applications, CP Routing, CP Scheduling
    """
    status_obj = StatusObject()

    # 1. Parse the given testcase
    t = Timer()
    with t:
        tc = parser.parse_to_model(input_params)
    timing_object.time_parsing = t.elapsed_time
    print(
        "-" * 20
        + " Parsed testcase: {}, in {:.2f} ms".format(
            input_params.tc_name, timing_object.time_parsing
        )
    )

    # 2. Calculate Pint
    if not input_params.no_security:
        pint_model = CPPintSolver(tc, timing_object)
        tc, status = pint_model.optimize(input_params, timing_object)
        print(
            "-" * 20
            + " Found Pint: {},  in {:.2f} ms".format(
                tc.Pint, timing_object.time_optimizing_pint
            )
        )
        status_obj.Pint_status = status
    else:
        print(
            "-" * 20
            + "Skipping Pint optimization, because no security wanted"
        )

    # 3. Generate Security applications
    if not input_params.no_security:
        tc = security_app_generator.run(tc, timing_object)
        print(
            "-" * 20
            + " Created {} Security Applications,  in {:.2f} ms".format(
                len(tc.A_sec), timing_object.time_creating_secapps
            )
        )
    else:
        print(
            "-" * 20
            + "Skipping generating security applications, because no security wanted"
        )

    # 5. Find routing
    routing_model = CPRoutingSolver(tc, timing_object)
    tc, status = routing_model.optimize(input_params, timing_object)
    print(
        "-" * 20
        + " Found Routing, in {:.2f} ms".format(timing_object.time_optimizing_routing)
    )
    status_obj.Routing_status = status

    # 6. Find scheduling
    scheduling_model = CPSchedulingSolver(tc, timing_object, input_params)
    tc, status = scheduling_model.optimize(input_params, timing_object)
    print(
        "-" * 20
        + " Found Schedule in {:.2f} ms".format(
            timing_object.time_optimizing_scheduling
        )
    )
    status_obj.Scheduling_status = status

    # 7. Create solution object
    solution_object = Solution(tc, input_params, status_obj, timing_object)

    return solution_object


def _mode_2(timing_object: TimingData, input_params: InputParameters) -> Solution:
    """
    Mode 2: CP Scheduling
    """
    status_obj = StatusObject()

    # 1. Parse the given testcase
    t = Timer()
    with t:
        tc = parser.parse_to_model(input_params)
    timing_object.time_parsing = t.elapsed_time
    print(
        "-" * 20
        + " Parsed testcase: {}, in {:.2f} ms".format(
            input_params.tc_name, timing_object.time_parsing
        )
    )

    # 2. Calculate Pint
    if not input_params.no_security:
        pint_model = CPPintSolver(tc, timing_object)
        tc, status = pint_model.optimize(input_params, timing_object)
        print(
            "-" * 20
            + " Found Pint: {},  in {:.2f} ms".format(
                tc.Pint, timing_object.time_optimizing_pint
            )
        )
        status_obj.Pint_status = status
    else:
        print(
            "-" * 20
            + "Skipping Pint optimization, because no security wanted"
        )

    # Don't optimize routing
    status_obj.Routing_status = EOptimizationStatus.NOT_OPTIMIZED

    # 6. Find scheduling
    scheduling_model = CPSchedulingSolver(tc, timing_object, input_params)
    schedule, status = scheduling_model.optimize(input_params, timing_object)
    print(
        "-" * 20
        + " Found Schedule in {:.2f} ms".format(
            timing_object.time_optimizing_scheduling
        )
    )
    status_obj.Scheduling_status = status

    # 7. Create solution object
    solution_object = Solution(tc, input_params, status_obj, timing_object)

    return solution_object

def _mode_3(timing_object: TimingData, input_params: InputParameters) -> Solution:
    """
    Mode 1: Generate Security Applications, Generate Stream, SA Routing, SA Scheduling
    """
    status_obj = StatusObject()

    # 1. Parse the given testcase
    t = Timer()
    with t:
        tc = parser.parse_to_model(input_params)
    timing_object.time_parsing = t.elapsed_time
    print(
        "-" * 20
        + " Parsed testcase: {}, in {:.2f} ms".format(
            input_params.tc_name, timing_object.time_parsing
        )
    )

    # 2. Calculate Pint
    if not input_params.no_security:
        pint_model = CPPintSolver(tc, timing_object)
        tc, status = pint_model.optimize(input_params, timing_object)
        print(
            "-" * 20
            + " Found Pint: {},  in {:.2f} ms".format(
                tc.Pint, timing_object.time_optimizing_pint
            )
        )
        status_obj.Pint_status = status
    else:
        print(
            "-" * 20
            + "Skipping Pint optimization, because no security wanted"
        )

    # 3. Generate Security applications
    if not input_params.no_security:
        tc = security_app_generator.run(tc, timing_object)
        print(
            "-" * 20
            + " Created {} Security Applications,  in {:.2f} ms".format(
                len(tc.A_sec), timing_object.time_creating_secapps
            )
        )
    else:
        print(
            "-" * 20
            + "Skipping generating security applications, because no security wanted"
        )

    # 4. Find routing (SA)
    routing_solver = SARoutingSolver(tc, timing_object)
    tc, status = routing_solver.optimize(input_params, timing_object)
    print(
        "-" * 20
        + " Found Routing, in {:.2f} ms".format(timing_object.time_optimizing_routing)
    )
    status_obj.Routing_status = status

    # 5. Find scheduling (SA)
    scheduling_model = SASchedulingSolver(tc, timing_object)
    tc, status = scheduling_model.optimize(input_params, timing_object, SAOptimizationMode.SEPERATED_NO_SA)
    print(
        "-" * 20
        + " Found Schedule in {:.2f} ms".format(
            timing_object.time_optimizing_scheduling
        )
    )
    status_obj.Scheduling_status = status

    # 6. Create solution object
    solution_object = Solution(tc, input_params, status_obj, timing_object)

    return solution_object

def _mode_4(timing_object: TimingData, input_params: InputParameters) -> Solution:
    """
    Mode 4: Generate Security Applications,  SA Routing, SA Scheduling (Seperated)
    """
    status_obj = StatusObject()

    # 1. Parse the given testcase
    t = Timer()
    with t:
        tc = parser.parse_to_model(input_params)
    timing_object.time_parsing = t.elapsed_time
    print(
        "-" * 20
        + " Parsed testcase: {}, in {:.2f} ms".format(
            input_params.tc_name, timing_object.time_parsing
        )
    )

    # 2. Calculate Pint
    if not input_params.no_security:
        pint_model = CPPintSolver(tc, timing_object)
        tc, status = pint_model.optimize(input_params, timing_object)
        print(
            "-" * 20
            + " Found Pint: {},  in {:.2f} ms".format(
                tc.Pint, timing_object.time_optimizing_pint
            )
        )
        status_obj.Pint_status = status
    else:
        print(
            "-" * 20
            + "Skipping Pint optimization, because no security wanted"
        )

    # 3. Generate Security applications
    if not input_params.no_security:
        tc = security_app_generator.run(tc, timing_object)
        print(
            "-" * 20
            + " Created {} Security Applications,  in {:.2f} ms".format(
                len(tc.A_sec), timing_object.time_creating_secapps
            )
        )
    else:
        print(
            "-" * 20
            + "Skipping generating security applications, because no security wanted"
        )

    # 4. Find routing (SA)
    routing_solver = SARoutingSolver(tc, timing_object)
    tc, status = routing_solver.optimize(input_params, timing_object)
    print(
        "-" * 20
        + " Found Routing, in {:.2f} ms".format(timing_object.time_optimizing_routing)
    )
    status_obj.Routing_status = status

    # 5. Find scheduling (SA)
    scheduling_model = SASchedulingSolver(tc, timing_object)
    tc, status = scheduling_model.optimize(input_params, timing_object, SAOptimizationMode.SEPERATED_SA)
    print(
        "-" * 20
        + " Found Schedule in {:.2f} ms".format(
            timing_object.time_optimizing_scheduling
        )
    )
    status_obj.Scheduling_status = status

    # 6. Create solution object
    solution_object = Solution(tc, input_params, status_obj, timing_object)

    return solution_object

def _mode_5(timing_object: TimingData, input_params: InputParameters) -> Solution:
    """
    Mode 5: Generate Security Applications,  SA Routing, ASAP Scheduling (Combined)
    """
    status_obj = StatusObject()

    # 1. Parse the given testcase
    t = Timer()
    with t:
        tc = parser.parse_to_model(input_params)
    timing_object.time_parsing = t.elapsed_time
    print(
        "-" * 20
        + " Parsed testcase: {}, in {:.2f} ms".format(
            input_params.tc_name, timing_object.time_parsing
        )
    )

    # 2. Calculate Pint
    if not input_params.no_security:
        pint_model = CPPintSolver(tc, timing_object)
        tc, status = pint_model.optimize(input_params, timing_object)
        print(
            "-" * 20
            + " Found Pint: {},  in {:.2f} ms".format(
                tc.Pint, timing_object.time_optimizing_pint
            )
        )
        status_obj.Pint_status = status
    else:
        print(
            "-" * 20
            + "Skipping Pint optimization, because no security wanted"
        )

    # 3. Generate Security applications
    if not input_params.no_security:
        tc = security_app_generator.run(tc, timing_object)
        print(
            "-" * 20
            + " Created {} Security Applications,  in {:.2f} ms".format(
                len(tc.A_sec), timing_object.time_creating_secapps
            )
        )
    else:
        print(
            "-" * 20
            + "Skipping generating security applications, because no security wanted"
        )

    # 4. Find scheduling & routing (SA)
    scheduling_model = SASchedulingSolver(tc, timing_object)
    tc, status = scheduling_model.optimize(input_params, timing_object, SAOptimizationMode.COMBINED_SA)
    print(
        "-" * 20
        + " Found Schedule in {:.2f} ms".format(
            timing_object.time_optimizing_scheduling
        )
    )
    status_obj.Scheduling_status = status

    # 5. Create solution object
    solution_object = Solution(tc, input_params, status_obj, timing_object)

    return solution_object

def run_mode(
    mode: EMode, timing_object: TimingData, input_params: InputParameters
) -> Solution:
    if mode is EMode.VIEW:
        return _mode_0(timing_object, input_params)
    elif mode is EMode.ALL_CP_ROUTING_AND_SECURITY:
        return _mode_1(timing_object, input_params)
    elif mode is EMode.ONLY_CP_SCHEDULING:
        return _mode_2(timing_object, input_params)
    elif mode is EMode.HEURISTIC_ROUTING_1_AND_SECURITY:
        return _mode_3(timing_object, input_params)
    elif mode is EMode.HEURISTIC_ROUTING_2_AND_SECURITY:
        return _mode_4(timing_object, input_params)
    elif mode is EMode.HEURISTIC_ROUTING_3_AND_SECURITY:
        return _mode_5(timing_object, input_params)
    else:
        raise ValueError(f"Mode {mode} is not supported")
