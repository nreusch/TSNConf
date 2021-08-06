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
    security = not input_params.no_security
    redundancy = not input_params.no_redundancy

    # 1. Parse the given testcase
    t = Timer()
    with t:
        tc = parser.parse_to_model(input_params, redundancy, security)
    timing_object.time_parsing = t.elapsed_time
    print(
        "-" * 20
        + " Parsed testcase: {}, in {:.2f} ms".format(
            input_params.tc_name, timing_object.time_parsing
        )
    )

    # 2. Generate Security applications
    if security:
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

    # 3. Create solution object
    solution_object = Solution(tc, input_params, status_obj, timing_object, security, redundancy)

    return solution_object

def _mode_1(timing_object: TimingData, input_params: InputParameters) -> Solution:
    """
    Mode 1: CP Routing, CP Scheduling, Security, Redundancy, Optimization
    """
    status_obj = StatusObject()
    security = not input_params.no_security
    redundancy = not input_params.no_redundancy
    allow_overlap = input_params.allow_overlap
    allow_infeasible_solutions = input_params.allow_infeasible_solutions

    # 1. Parse the given testcase
    t = Timer()
    with t:
        tc = parser.parse_to_model(input_params, redundancy, security)
    timing_object.time_parsing = t.elapsed_time
    print(
        "-" * 20
        + " Parsed testcase: {}, in {:.2f} ms".format(
            input_params.tc_name, timing_object.time_parsing
        )
    )

    # 2. Calculate Pint
    if security:
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
        tc.Pint = tc.hyperperiod
        print(
            "-" * 20
            + "Skipping Pint optimization, because no security wanted"
        )

    # 3. Generate Security applications
    if security:
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
    routing_model = CPRoutingSolver(tc, timing_object, redundancy, allow_overlap)
    tc, status = routing_model.optimize(input_params, timing_object)
    print(
        "-" * 20
        + " Found Routing, in {:.2f} ms".format(timing_object.time_optimizing_routing)
    )
    status_obj.Routing_status = status

    # 6. Find scheduling
    scheduling_model = CPSchedulingSolver(tc, timing_object, do_security=security, do_allow_infeasible_solutions=allow_infeasible_solutions)
    tc, status = scheduling_model.optimize(input_params, timing_object)
    print(
        "-" * 20
        + " Found Schedule in {:.2f} ms".format(
            timing_object.time_optimizing_scheduling
        )
    )
    status_obj.Scheduling_status = status

    # 7. Create solution object
    solution_object = Solution(tc, input_params, status_obj, timing_object, security, redundancy)

    return solution_object

def _mode_11(timing_object: TimingData, input_params: InputParameters) -> Solution:
    """
    Mode 21: SA Routing, ASAP Scheduling, Security, Redundancy, Optimization
    """
    status_obj = StatusObject()
    security = not input_params.no_security
    redundancy = not input_params.no_redundancy

    # 1. Parse the given testcase
    t = Timer()
    with t:
        tc = parser.parse_to_model(input_params, redundancy, security)
    timing_object.time_parsing = t.elapsed_time
    print(
        "-" * 20
        + " Parsed testcase: {}, in {:.2f} ms".format(
            input_params.tc_name, timing_object.time_parsing
        )
    )

    # 2. Calculate Pint
    if security:
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
    if security:
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
    routing_solver = SARoutingSolver(tc, timing_object, input_params.k, input_params.a, input_params.w)
    tc, status = routing_solver.optimize(input_params, timing_object)
    print(
        "-" * 20
        + " Found Routing, in {:.2f} ms".format(timing_object.time_optimizing_routing)
    )
    status_obj.Routing_status = status

    # 5. Find scheduling (SA)
    scheduling_model = SASchedulingSolver(tc, timing_object, input_params)
    tc, status = scheduling_model.optimize(input_params, timing_object, SAOptimizationMode.SEPERATED_NO_SA)
    print(
        "-" * 20
        + " Found Schedule in {:.2f} ms".format(
            timing_object.time_optimizing_scheduling
        )
    )
    status_obj.Scheduling_status = status

    # 6. Create solution object
    solution_object = Solution(tc, input_params, status_obj, timing_object, security, redundancy)

    return solution_object

def _mode_12(timing_object: TimingData, input_params: InputParameters) -> Solution:
    """
    Mode 22: SA Routing, SA Scheduling, Security, Redundancy, Optimization
    """
    status_obj = StatusObject()
    security = not input_params.no_security
    redundancy = not input_params.no_redundancy

    # 1. Parse the given testcase
    t = Timer()
    with t:
        tc = parser.parse_to_model(input_params, redundancy, security)
    timing_object.time_parsing = t.elapsed_time
    print(
        "-" * 20
        + " Parsed testcase: {}, in {:.2f} ms".format(
            input_params.tc_name, timing_object.time_parsing
        )
    )

    # 2. Calculate Pint
    if security:
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
    if security:
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
    routing_solver = SARoutingSolver(tc, timing_object, input_params.k, input_params.a, input_params.w)
    tc, status = routing_solver.optimize(input_params, timing_object)
    print(
        "-" * 20
        + " Found Routing, in {:.2f} ms".format(timing_object.time_optimizing_routing)
    )
    status_obj.Routing_status = status

    # 5. Find scheduling (SA)
    scheduling_model = SASchedulingSolver(tc, timing_object, input_params)
    tc, status = scheduling_model.optimize(input_params, timing_object, SAOptimizationMode.SEPERATED_SA)
    print(
        "-" * 20
        + " Found Schedule in {:.2f} ms".format(
            timing_object.time_optimizing_scheduling
        )
    )
    status_obj.Scheduling_status = status

    # 6. Create solution object
    solution_object = Solution(tc, input_params, status_obj, timing_object, security, redundancy)

    return solution_object

def _mode_13(timing_object: TimingData, input_params: InputParameters) -> Solution:
    """
    Mode 13: SA Routing+Scheduling, Security, Redundancy, Optimization
    """
    status_obj = StatusObject()
    security = not input_params.no_security
    redundancy = not input_params.no_redundancy

    # 1. Parse the given testcase
    t = Timer()
    with t:
        tc = parser.parse_to_model(input_params, redundancy, security)
    timing_object.time_parsing = t.elapsed_time
    print(
        "-" * 20
        + " Parsed testcase: {}, in {:.2f} ms".format(
            input_params.tc_name, timing_object.time_parsing
        )
    )

    # 2. Calculate Pint
    if security:
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
    if security:
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
    scheduling_model = SASchedulingSolver(tc, timing_object, input_params)
    tc, status = scheduling_model.optimize(input_params, timing_object, SAOptimizationMode.COMBINED_SA)
    print(
        "-" * 20
        + " Found Schedule in {:.2f} ms".format(
            timing_object.time_optimizing_scheduling
        )
    )
    status_obj.Scheduling_status = status

    # 5. Create solution object
    solution_object = Solution(tc, input_params, status_obj, timing_object, security, redundancy)

    return solution_object

def run_mode(
    mode: EMode, timing_object: TimingData, input_params: InputParameters
) -> Solution:
    if mode is EMode.VIEW:
        return _mode_0(timing_object, input_params)
    elif mode is EMode.CP_ROUTING_CP_SCHEDULING:
        return _mode_1(timing_object, input_params)
    elif mode is EMode.SA_ROUTING_ASAP_SCHEDULING:
        return _mode_11(timing_object, input_params)
    elif mode is EMode.SA_ROUTING_SA_SCHEDULING:
        return _mode_12(timing_object, input_params)
    elif mode is EMode.SA_ROUTING_SA_SCHEDULING_COMB:
        return _mode_13(timing_object, input_params)
    else:
        raise ValueError(f"Mode {mode} is not supported")
