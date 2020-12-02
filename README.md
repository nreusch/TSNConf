# TSNConf

Try the online [DEMO](https://tsnconf-demo.herokuapp.com/).

This tool is still under development. Feel free to contact me with issues & feedback.

## Acknowledgement
This application was developed at the Technical University of Denmark as part of my [PhD project](https://orbit.dtu.dk/en/persons/niklas-reusch/publications/).
Many thanks to my supervisor Paul Pop and Silviu S. Craciunas for their feedback and support.

## Requirements
- Python 3.9
- [GraphViz](https://graphviz.org/download/)
  - Add to PATH
- On Windows: 
    - Build Tools for Visual Studio: https://visualstudio.microsoft.com/downloads/ (required for some libraries) 
        - Only default C++ build tools necessary

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

#Available commands:
```
usage: main.py [-h] [--mode MODE] [--visualize] [--no_redundancy] [--no_security] [--timeout_routing TIMEOUT_ROUTING] [--timeout_scheduling TIMEOUT_SCHEDULING]
               [--timeout_pint TIMEOUT_PINT]
               testcase_path

test

positional arguments:
  testcase_path         The path to the testcase. E.g "testcases/TC0_example.flex_network_description"

optional arguments:
  -h, --help            show this help message and exit
  --mode MODE           Mode to run
  --visualize           Visualize testcase (show dashboard)  (Default: False)
  --no_redundancy       Disable redundancy, by ignoring RL specified in testcase  (Default: False)
  --no_security         Disable security  (Default: False)
  --timeout_routing TIMEOUT_ROUTING
                        Timeout: Routing Solver (s) (Default: 300)
  --timeout_scheduling TIMEOUT_SCHEDULING
                        Timeout: Scheduling Solver (s) (Default: 300)
  --timeout_pint TIMEOUT_PINT
                        Timeout: Pint Solver (s) (Default: 60)

Available Modes:
- Mode 0: View/Check the testcase. Doesn't generate/optimize anything
- Mode 1: Generate Security Applications, Generate Stream, CP Routing, CP Scheduling
- Mode 2: CP Scheduling
```
