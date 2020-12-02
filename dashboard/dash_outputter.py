import sys
from pathlib import Path

import dash
from dash.dependencies import Input, Output

from solution import solution_parser
from utils import serializer
from dashboard.layout_elements.layout_elements import *
from solution.solution import Solution
from utils.utilities import flatten

def run_from_pickle(sol_obj_path: Path):
    solution = serializer.deserialize_solution(sol_obj_path)
    run(solution)

def run(solution: Solution):
    # Init Dash
    app = dash.Dash(
        __name__,
        meta_tags=[
            {"name": "viewport", "content": "width=device-width, initial-scale=1"}
        ],
    )  # using js and css files in assets folder

    solution: Solution = solution

    # Generate all the visualizations

    # Generate the layout components
    # --- Input
    # ------- App DAG Tabs
    normal_app_id_digraph_map = solution_parser.get_testcase_application_graphs(
        solution
    )

    option_list = []
    first_app_id = ""
    for app_id in normal_app_id_digraph_map.keys():
        if first_app_id == "":
            first_app_id = app_id
        option_list.append({
            "label":app_id,
            "value":app_id
        })

    input_normal_app_dag_dropdown = dcc.Dropdown(
        id='input_normal_app_dag_dropdown',
        options=option_list,
        value=first_app_id
    )

    input_normal_app_dag_viewer = html.Div(id='input_normal_app_dag_viewer')

    # ------- Toplogy
    input_topology = html.Img(
        src=solution_parser.get_testcase_topology_graph(solution),
        style={"width": "100%", "height" : "100%", "max-height" : "400px"}
    )
    # ------- Task Table
    df = solution_parser.get_testcase_task_dataframe(solution)
    input_task_table = table("table_input_tasks", df)
    # ------- Signal Table
    df = solution_parser.get_testcase_signal_dataframe(solution)
    input_signal_table = table("table_input_signals", df)

    # --- Derived

    # ------- Security Toplogy
    derived_security_topology = html.Img(
        src=solution_parser.get_derived_security_topology_graph(solution),
        style={"width": "100%", "height" : "100%", "max-height" : "400px"}
    )

    # ------- Security App DAG Tabs
    security_app_id_digraph_map = solution_parser.get_derived_security_application_graphs(
        solution
    )

    option_list = []
    first_app_id = ""
    for app_id in security_app_id_digraph_map.keys():
        if first_app_id == "":
            first_app_id = app_id
        option_list.append({
            "label": app_id,
            "value": app_id
        })

    input_security_app_dag_dropdown = dcc.Dropdown(
        id='input_security_app_dag_dropdown',
        options=option_list,
        value=first_app_id
    )

    input_security_app_dag_viewer = html.Div(id='input_security_app_dag_viewer')

    # ------- Security Task Table
    df = solution_parser.get_derived_security_task_dataframe(solution)
    derived_security_task_table = table("table_derived_security_tasks", df)

    # ------- Security Signal Table
    df = solution_parser.get_derived_security_signal_dataframe(solution)
    derived_security_signal_table = table("table_derived_security_signals", df)

    # ------- Frame Table
    df = solution_parser.get_derived_streams_dataframe(solution)
    derived_stream_table = table("table_derived_frames", df)

    # --- Output
    # ------- Information
    df = solution_parser.get_solution_general_info_dataframe(solution)
    solution_general_info_table = table("table_solution_general_info", df)

    df = solution_parser.get_solution_results_optimization_status_dataframe(
        solution
    )
    solution_opt_status_table = optstatus_table("table_solution_opt_status", df)

    df = solution_parser.get_solution_inputparam_info_dataframe(solution)
    solution_inputparam_info_table = table("table_solution_inputparam_info", df)

    df = solution_parser.get_solution_timing_info_dataframe(solution)

    solution_timing_info_pint = table("table_solution_timing_info_pint", df[["Creating Variables - Pint (ms)", "Creating Constraints - Pint (ms)", "Optimizing - Pint (ms)"]])
    solution_timing_info_routing = table("table_solution_timing_info_routing", df[["Creating Variables - Routing (ms)", "Creating Constraints - Routing (ms)", "Optimizing - Routing (ms)"]])
    solution_timing_info_scheduling = table("table_solution_timing_info_scheduling", df[["Creating Variables - Scheduling (ms)", "Creating Constraints - Scheduling (ms)", "Optimizing - Scheduling (ms)"]])
    solution_timing_info_other = table("table_solution_timing_info_other", df[["Testcase Parsing (ms)"]])

    descr = solution_parser.get_solution_mode_description(solution)
    solution_mode_description = html.P(descr)

    # -------- Results
    df = solution_parser.get_solution_results_info_dataframe(solution)
    solution_results_info_table = table("table_solution_results_info", df)

    """
    df = solution_parser.get_solution_application_e2edelay_table(
        solution_object
    )
    solution_application_e2edelay_table = table(
        "table_solution_application_e2edelay", df
    )
    """
    solution_application_e2edelay_table = None

    df = solution_parser.get_solution_functionpath_dataframe(solution)
    solution_results_functionpaths_table = table("table_solution_functionpaths", df)

    # ------- Routing
    if solution.is_feasible_routing():
        solution_routing = solution_parser.get_solution_routing_cytoscape(
            solution
        )
    else:
        solution_routing = html.P("No feasible route found")

    # ------- Schedule
    if solution.is_feasible_all():
        fig = solution_parser.get_solution_schedule_plotly(solution)
        solution_schedule = dcc.Graph(id="solution_schedule", figure=fig)
    else:
        solution_schedule = html.P("No solution found")

    app.layout = html.Div(
        [
            html.Div(
                [
                    section(
                        [
                            header("Input"),
                            row(
                                [
                                    columns(
                                        [
                                            column(
                                                [
                                                    inner_container(
                                                        "Topology",
                                                        inner_element_topology(input_topology),
                                                    ),
                                                    inner_container(
                                                        "Tasks", input_task_table
                                                    ),
                                                ]
                                            ),
                                            column(
                                                [
                                                    inner_container(
                                                        "Normal Applications",
                                                        row(
                                                            [
                                                                inner_element_dag(input_normal_app_dag_dropdown),
                                                                inner_element_dag(input_normal_app_dag_viewer)
                                                            ]
                                                        )
                                                    ),
                                                    inner_container(
                                                        "Input Signals",
                                                        input_signal_table,
                                                    ),
                                                ]
                                            ),
                                        ]
                                    )
                                ]
                            ),
                        ]
                    ),
                    section(
                        [
                            header("Derived Security Applications"),
                            row(
                                [
                                    columns(
                                        [
                                            column(
                                                [
                                                    inner_container(
                                                        "Security Topology",
                                                        inner_element_topology(derived_security_topology),
                                                    ),
                                                    inner_container(
                                                        "Security Tasks",
                                                        derived_security_task_table,
                                                    ),
                                                ]
                                            ),
                                            column(
                                                [
                                                    inner_container(
                                                        "Security Applications",
                                                        row(
                                                            [
                                                                inner_element_dag(input_security_app_dag_dropdown),
                                                                inner_element_dag(input_security_app_dag_viewer)
                                                            ]
                                                        )
                                                    ),
                                                    inner_container(
                                                        "Security Signals",
                                                        derived_security_signal_table,
                                                    ),
                                                ]
                                            ),
                                        ]
                                    )
                                ]
                            ),
                        ]
                    ),
                    section(
                        [
                            header("Derived Streams"),
                            row([inner_container("Streams", derived_stream_table)]),
                        ]
                    ),
                    section(
                        [
                            header("Optimized Routing"),
                            row(
                                [
                                    columns(
                                        [
                                            column(
                                                [
                                                    html.H5("Layout:"),
                                                    cytoscape_layout_dropdown(),
                                                    html.H5("Streams:"),
                                                    stream_checklist(solution.tc.F),
                                                ],
                                                size="one-third"
                                            ),
                                            column(
                                                [
                                                    row(
                                                        [
                                                            solution_routing
                                                        ]
                                                    )
                                                ],
                                                size="two-thirds"
                                            ),
                                        ]
                                    ),
                                ]
                            )

                        ]
                    ),
                    section(
                        [
                            header("Output"),
                            row(
                                [
                                    row(
                                        [
                                            html.H3(
                                                "Testcase Information",
                                                className="subsection__header",
                                            ),
                                            columns(
                                                [
                                                    column(
                                                        [
                                                            inner_container(
                                                                "General",
                                                                solution_general_info_table,
                                                            ),
                                                            inner_container(
                                                                "Network Parameters",
                                                                solution_inputparam_info_table,
                                                            ),
                                                        ]
                                                    ),
                                                    column(
                                                        [
                                                            inner_container(
                                                                "Optimization Parameters",
                                                                solution_mode_description,
                                                            ),
                                                            inner_container(
                                                                "Timings",
                                                                row(
                                                                    [
                                                                        inner_element(solution_timing_info_pint),
                                                                        inner_element(solution_timing_info_routing),
                                                                        inner_element(solution_timing_info_scheduling),
                                                                        inner_element(solution_timing_info_other)
                                                                    ]
                                                                )
                                                            ),
                                                        ]
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                    row(
                                        [
                                            html.H3(
                                                "Results",
                                                className="subsection__header",
                                            ),
                                            columns(
                                                [
                                                    column(
                                                        [
                                                            inner_container(
                                                                "Results",
                                                                solution_results_info_table,
                                                            ),
                                                            inner_container(
                                                                "Optimization Status",
                                                                solution_opt_status_table,
                                                            ),
                                                        ]
                                                    ),
                                                    column(
                                                        [
                                                            inner_container(
                                                                "Functionpath Laxities",
                                                                solution_results_functionpaths_table,
                                                            ),
                                                        ]
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                    inner_container("Schedule", solution_schedule),
                                ]
                            ),
                        ]
                    ),
                ]
            )
        ]
    )

    @app.callback(
        Output("cytoscape-routing-graph", "layout"),
        [Input("dropdown-update-layout", "value")],
    )
    def update_layout(layout):
        print("Callback")
        return {"name": layout, "animate": True}

    @app.callback(
        Output('input_normal_app_dag_viewer', 'children'),
        [Input('input_normal_app_dag_dropdown', 'value')])
    def update_normal_app_dag_viewer(value):
        i = html.Img(src=normal_app_id_digraph_map[value], style={"width":"100%", "height" : "100%", "max-height" : "200px"})
        return i

    @app.callback(
        Output('input_security_app_dag_viewer', 'children'),
        [Input('input_security_app_dag_dropdown', 'value')])
    def update_security_app_dag_viewer(value):
        i = html.Img(src=security_app_id_digraph_map[value], style={"width": "100%", "height" : "100%", "max-height" : "200px"})
        return i

    @app.callback(
        Output("cytoscape-routing-graph", "stylesheet"),
        [Input("checklist-display-routes", "value")],
    )
    def display_routes(checklist_values):
        color_set = solution_parser._cytoscape_route_colorset()

        selectors = []
        i = 0
        for f_id in solution.tc.F.keys():

            if f_id in checklist_values:
                selectors.append(
                    {
                        "selector": ".{}".format(f_id),
                        "style": {
                            "curve-style": "bezier",
                            "target-arrow-shape": "triangle",
                            "target-arrow-color": color_set[i % len(color_set)],
                            "line-color": color_set[i % len(color_set)],
                        },
                    }
                )
            else:
                selectors.append(
                    {"selector": ".{}".format(f_id), "style": {"display": "none"}}
                )
            i += 1

        stylesheet = solution_parser._cytoscape_base_stylesheet()

        stylesheet = flatten([stylesheet, selectors])

        return stylesheet

    app.run_server()


if __name__ == "__main__":
    run_from_pickle(sys.argv[1])
