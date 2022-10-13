import argparse
import sys
from pathlib import Path
from typing import List, Tuple

import runner
from dashboard import dash_outputter
from input.input_parameters import EMode, InputParameters, Timeouts
from solution import solution_parser
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
        #f = open("out.txt", "w")
        #self.print_help(f)
        #f.close()
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
        help='The path to the testcase. E.g "testcases/example.flex_network_description"',
    )

    parser.add_argument("--mode", type=str, help="Mode to run")

    parser.add_argument('--aggregate', type=str, default=False,
                       help='Aggregate results to [path]')

    parser.add_argument(
        "--simple",
        action="store_true",
        default=False,
        help="Only serialize essentials  (Default: False)",
    )

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
        "--luxi_port",
        default=27015,
        type=int,
        help="Luxi WCDA Tool Port",
    )

    parser.add_argument(
        "--timeout_scheduling",
        default=300,
        type=float,
        help="Timeout: Scheduling Solver (s) (Default: 300)",
    )


    parser.add_argument(
        "--b",
        default=100000,
        type=int,
        help="b: Weight for infeasible stream component of cost function (Default: 1000)",
    )

    parser.add_argument(
        "--Tstart",
        default=10,
        type=int,
        help="Tstart: Start temperature for SA metaheuristic (Default: 10)",
    )

    parser.add_argument(
        "--alpha",
        default=0.999,
        type=float,
        help="alpha: Cooling factor for SA  metaheuristic (Default: 0.999)",
    )

    parser.add_argument(
        "--Prmv",
        default=0.0,
        type=float,
        help="Prmv: Probability of a routing move for SA metaheuristic (Default: 0.8)",
    )


    results = parser.parse_args()

    input_param_list = []

    if results.mode != None:
        if results.mode.isdigit():
            mode = EMode(int(results.mode))
        else:
            mode = EMode[results.mode]
    else:
        mode = EMode.SA_MultiWindow

    if results.timeout_scheduling:
        timeouts = Timeouts(
            results.timeout_scheduling
        )
    else:
        timeouts = Timeouts(300)
    tc_path = results.testcase_path

    if results.aggregate == False:
        aggregate = ""
    else:
        aggregate = results.aggregate
    visualize = results.visualize
    port = results.port
    luxi_port = results.luxi_port
    simple = results.simple

    b = results.b
    Tstart = results.Tstart
    alpha = results.alpha
    Prmv = results.Prmv
    input_param_list.append(InputParameters(mode, timeouts, tc_path, visualize, aggregate, port,luxi_port, b, Tstart, alpha, Prmv, simple))

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
        solution, tc = runner.run_mode(input_params.mode, timing_object, input_params)
    except Exception as e:
        print("Error in Step 1: Running the chosen mode")
        print(e)
        raise e

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
