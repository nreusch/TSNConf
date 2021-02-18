import argparse
import sys
from pathlib import Path
from typing import List, Tuple

import runner
from input.input_parameters import EMode, InputParameters, Timeouts
from dashboard import dash_outputter
from solution.solution import Solution
from solution.solution_timing_data import TimingData
from utils import utilities, serializer
from utils.utilities import Timer

# we also need orca

# https://stackoverflow.com/questions/4042452/display-help-message-with-python-argparse-when-script-is-called-without-any-argu
# Also show help when error is thrown
class MyArgParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("error: %s\n" % message)
        f = open("out.txt", "w")
        self.print_help(f)
        f.close()
        self.print_help()
        sys.exit(2)


def parse_arguments() -> Tuple[List[InputParameters], Path]:
    epilog = "Available Modes:\n"
    for i in EMode.list():
        epilog += "- {}\n".format(EMode(i).describe())

    parser = MyArgParser(
        description="test", formatter_class=argparse.RawTextHelpFormatter, epilog=epilog
    )

    parser.add_argument(
        "testcase_path",
        help='The path to the testcase. E.g "testcases/TC0_example.flex_network_description"',
    )

    parser.add_argument("--mode", type=int, help="Mode to run")

    # parser.add_argument('--serialize', action="store_true", default=False,
    #                    help='Serialize testcase (Default: False)')
    parser.add_argument(
        "--visualize",
        action="store_true",
        default=False,
        help="Visualize testcase (show dashboard)  (Default: False)",
    )

    parser.add_argument(
        "--port",
        default=8050,
        type=int,
        help="Visualization Dashboard Port",
    )

    parser.add_argument(
        "--no_redundancy",
        action="store_true",
        default=False,
        help="Disable redundancy, by ignoring RL specified in testcase  (Default: False)",
    )

    parser.add_argument(
        "--no_security",
        action="store_true",
        default=False,
        help="Disable security  (Default: False)",
    )

    parser.add_argument(
        "--timeout_routing",
        default=300,
        type=int,
        help="Timeout: Routing Solver (s) (Default: 300)",
    )
    parser.add_argument(
        "--timeout_scheduling",
        default=300,
        type=int,
        help="Timeout: Scheduling Solver (s) (Default: 300)",
    )
    parser.add_argument(
        "--timeout_pint",
        default=60,
        type=int,
        help="Timeout: Pint Solver (s) (Default: 60)",
    )

    results = parser.parse_args()

    input_param_list = []
    mode = EMode[EMode(results.mode).name]
    timeouts = Timeouts(
        results.timeout_pint,
        results.timeout_routing,
        results.timeout_scheduling,
    )
    tc_path = results.testcase_path
    visualize = results.visualize
    port = results.port
    no_redundancy = results.no_redundancy
    no_security = results.no_security
    input_param_list.append(InputParameters(mode, timeouts, tc_path, visualize, port, no_redundancy, no_security))

    return input_param_list, Path(results.testcase_path)


def run(input_params: InputParameters) -> Solution:
    """
    Runs the given set of InputParameters
    """

    # 1. Print description of input parameters
    print("\n" + input_params.get_full_string() + "\n")

    # 2. Run the chose mode
    timing_object = TimingData()
    try:
        print("-" * 10 + " 1. Running the chosen mode")
        solution = runner.run_mode(input_params.mode, timing_object, input_params)
    except Exception as e:
        print("Error in Step 1: Running the chosen mode")
        raise

    # 3. Serialize result as .flex_network_description
    try:
        print("-" * 10 + " 2. Serializing the solution")
        t = Timer()
        with t:
            output_folder_path = serializer.serialize_solution(utilities.OUTPUT_PATH, solution)
        timing_object.time_serializing_solution = t.elapsed_time
        print(
            "-" * 20
            + " Serialized solution to: {},  in {:.2f} ms".format(
                output_folder_path, timing_object.time_serializing_solution
            )
        )
    except Exception as e:
        print("Error in Step 2: Serializing the solution")

    # 4. Print results
    try:
        print("-" * 10 + " 3. Printing results")
        print(solution.get_result_string())
    except Exception as e:
        print("Error in Step 3: Printing results")

    print("--------------------------\n")

    return solution


if __name__ == "__main__":
    # Parsing arguments
    input_param_list, testcase_path = parse_arguments()

    # For each set of op_params:
    results = []
    for input_params in input_param_list:
        solution_object = run(input_params)
        results.append(solution_object)

    # If --visualize, visualize first testcase
    if input_param_list[0].visualize:
        # Outputting to Dash
        dash_outputter.run(results[0], PORT=input_param_list[0].port)
