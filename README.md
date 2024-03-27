# TSNConf

Try the online [DEMO](https://tsnconf-0202fa94a705.herokuapp.com/).

Feel free to contact me with issues & feedback.

## Acknowledgement
This application was developed at the Technical University of Denmark as part of my [PhD project](https://orbit.dtu.dk/en/publications/safety-and-security-aware-configuration-synthesis-for-time-sensit).
Many thanks to my supervisor Paul Pop and Silviu S. Craciunas for their feedback and support.

## Requirements
- Python 3.9
- [GraphViz](https://graphviz.org/download/)
    - Add to PATH
- On Windows: 
    - Build Tools for Visual Studio: https://visualstudio.microsoft.com/downloads/ (required for some libraries) 
        - Only default C++ build tools necessary

## Optional requirements
- [GGen](https://github.com/perarnau/ggen) (If you want to generate your own testcases)

## Setup
- It is recommended to setup a [python virtual environment](https://docs.python.org/3/library/venv.html) before installing the requirements.
- Setup:
```
git clone https://github.com/nreusch/TSNConf.git
cd TSNConf
pip install -r requirements.txt
```

## Running
Run a simple example:
```
python main.py .\testcases\TC0_example.flex_network_description --mode 1 --visualize
```

Then open [http://127.0.0.1:8050](http://127.0.0.1:8050) in your browser.

The output of each run is stored in testcases\output\XXX\, where XXX is the name of the testcase with a suffix for the chosen parameters.
The output includes:
- Graphs of all applications and the topology as .gv (GraphViz), .svg & .pdf
- A .flex_network_description including the testcase + whatever was generated/optimized(security apps, streams, routing, schedule)
- A .pickle of the solution. This can be used to show the dashboard of the results again without rerunning the optimization
- If a schedule exists: A schedule.html, the interactive schedule

To show the dashboard for a given .pickle, run this in the root folder:
```
python -m dashboard.dash_outputter [PICKLE_PATH]
```

For example:
```
python -m dashboard.dash_outputter testcases\output\TC0_example_mode1_600_1800_1800_0.2\solution.pickle
```

Then open [http://127.0.0.1:8050](http://127.0.0.1:8050) in your browser.

## Running extensibility & task mapping optimization
To run a testcase where you want to optimize the extensibility, i.e. have regular free intervals between tasks, and where you have tasks without mapping, use:
```
-- mode CP_ROUTING_CP_SCHEDULING_EXT
```

A task without mapping does not have a node assigned in the .flex_network_description. It may have a list of allowed_assignments, which constrains on which this task may be mapped. Make sure that tasks that send & receive streams are only allowed to be mapped to connected ES.

Example task without mapping:
```
<task name="AppNoMap_t1" wcet="500" period="1000" type="NORMAL" allowed_assignments="ES1,ES2,ES3,ES4"/>
```

## Available commands:
```
usage: main.py [-h] [--mode MODE] [--aggregate AGGREGATE] [--extra_apps_path EXTRA_APPS_PATH] [--visualize] [--port PORT] [--no_redundancy] [--no_security] [--allow_overlap] [--allow_infeasible] [--original_tesla] [--timeout_routing TIMEOUT_ROUTING]
               [--timeout_scheduling TIMEOUT_SCHEDULING] [--timeout_pint TIMEOUT_PINT] [--k K] [--a A] [--b B] [--Tstart TSTART] [--alpha ALPHA] [--Prmv PRMV] [--w W]
               testcase_path

test

positional arguments:
  testcase_path         The path to the testcase. E.g "testcases/TC0_example.flex_network_description"

optional arguments:
  -h, --help            show this help message and exit
  --mode MODE           Mode to run
  --aggregate AGGREGATE
                        Aggregate results to [path]
  --extra_apps_path EXTRA_APPS_PATH
                        Extra applications to apply onto initial schedule
  --visualize           Visualize testcase (show dashboard)  (Default: False)
  --port PORT           Visualization Dashboard Port
  --no_redundancy       Disable redundancy, by ignoring RL specified in testcase  (Default: False)
  --no_security         Disable security  (Default: False)
  --allow_overlap       Allow redundant stream overlap for CP solutions  (Default: False)
  --allow_infeasible    Allow the CP solver to produce infeasible solutions, including stream overlap or missed deadlines
  --original_tesla      Use TESLA without modification (key only sent in secure stream). Will incure higher bandwidth and cost
  --timeout_routing TIMEOUT_ROUTING
                        Timeout: Routing Solver (s) (Default: 300)
  --timeout_scheduling TIMEOUT_SCHEDULING
                        Timeout: Scheduling Solver (s) (Default: 300)
  --timeout_pint TIMEOUT_PINT
                        Timeout: Pint Solver (s) (Default: 60)
  --k K                 K: Parameter for k-shortest-paths heuristic (Default: 3)
  --a A                 a: Weight for routing overlap component of cost function (Default: 5000)
  --b B                 b: Weight for infeasible stream component of cost function (Default: 1000)
  --Tstart TSTART       Tstart: Start temperature for SA metaheuristic (Default: 10)
  --alpha ALPHA         alpha: Cooling factor for SA  metaheuristic (Default: 0.999)
  --Prmv PRMV           Prmv: Probability of a routing move for SA metaheuristic (Default: 0.8)
  --w W                 w: Weight for punishing overlap in k-shortest-paths for SA heuristic (Default: 10)

Available Modes:
- Mode 0: View/Check the testcase. Doesn't generate/optimize anything
- Mode 1: CP Routing, CP Scheduling, Security, Redundancy, Optimization (Optimize laxity)
- Mode 2: CP Routing, CP Scheduling, Security, Redundancy, Optimization (Optimize laxity + extensibility)
- Mode 11: SA Routing, ASAP Scheduling, Security, Redundancy, Optimization
- Mode 12: SA Routing, SA Scheduling, Security, Redundancy, Optimization
- Mode 13: SA Routing+Scheduling, Security, Redundancy, Optimization
- Mode 99: Check Edge applicaitons against existing solution (Provide solution.pickle as path and extra_apps using --extra_apps_path
```
