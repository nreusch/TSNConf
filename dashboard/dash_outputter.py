import sys
from pathlib import Path

import dash
from dash.dependencies import Input, Output

from dashboard.layout_elements.layout_elements import *
from solution import solution_parser
from solution.solution import Solution
from utils import serializer
from utils.utilities import flatten


def run_from_pickle(sol_obj_path: Path, PORT=None):
    solution = serializer.deserialize_solution(sol_obj_path)
    run(solution, PORT=PORT)

def run(solution: Solution, PORT=None):
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

    # ------- Toplogy
    input_topology = html.Img(
        src=solution_parser.get_testcase_topology_graph(solution),
        style={"width": "100%", "height" : "100%", "max-height" : "400px"}
    )
    # ------- Stream Table
    df = solution_parser.get_testcase_stream_dataframe(solution)
    input_stream_table = table("table_input_streams", df)


    # --- Output
    # ------- Information
    df = solution_parser.get_solution_general_info_dataframe(solution)
    solution_general_info_table = table("table_solution_general_info", df)

    df = solution_parser.get_solution_results_optimization_status_dataframe(
        solution
    )
    solution_opt_status_table = optstatus_table("table_solution_opt_status", df)

    df = solution_parser.get_solution_parameter_info_dataframe(solution)
    solution_inputparam_info_table = table("table_solution_inputparam_info", df)

    df = solution_parser.get_solution_timing_info_dataframe(solution)

    solution_timing_info_pint = table("table_solution_timing_info_pint", df[["Creating Variables - Pint (ms)", "Creating Constraints - Pint (ms)", "Optimizing - Pint (ms)"]])
    solution_timing_info_routing = table("table_solution_timing_info_routing", df[["Creating Variables - Routing (ms)", "Creating Constraints - Routing (ms)", "Optimizing - Routing (ms)"]])
    solution_timing_info_scheduling = table("table_solution_timing_info_scheduling", df[["Creating Variables - Scheduling (ms)", "Creating Constraints - Scheduling (ms)", "Optimizing - Scheduling (ms)"]])
    solution_timing_info_sa = table("table_solution_timing_info_sa", df[["Creating Variables - Simulated Annealing (ms)", "Optimizing - Simulated Annealing (ms)"]])
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

    df = solution_parser.get_solution_application_dataframe(solution)
    solution_results_applications_table = table("table_solution_applications", df)

    # ------- Routing
    if len(solution.tc.R) > 0:
        solution_routing = solution_parser.get_solution_routing_cytoscape(
            solution
        )
        solution_routing_info_table = html.P("Routing was given -> No information available")
        solution_routing_total_cost = None
    else:
        solution_routing = html.P("No feasible route found")
        solution_routing_info_table = html.P("No information available")
        solution_routing_total_cost = None

    # ------- Schedule
    if solution.tc.schedule:
        fig = solution_parser.get_solution_schedule_plotly(solution)
        solution_schedule = dcc.Graph(id="solution_schedule", figure=fig)
    else:
        solution_schedule = html.P("No solution found")

    input_section = section(
                        [
                            header("Input"),
                            row(
                                [
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
                                                        ]
                                                    ),
                                                    column(
                                                        [
                                                            inner_container(
                                                                "Normal Applications",
                                                                row(
                                                                    [

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
                                        ]
                                    ),

                                    row(
                                        [
                                            inner_container(
                                                "Input Streams",
                                                input_stream_table,
                                            )
                                        ]
                                    ),
                                ]
                            ),




                        ]
                    )


    routing_section = section(
                        [
                            header("Routing"),
                            row(
                                [
                                    columns(
                                        [
                                            column(
                                                [
                                                    row(
                                                        [
                                                            html.H5("Layout:"),
                                                            cytoscape_layout_dropdown(),
                                                            html.H5("Streams:"),
                                                            stream_checklist(solution.tc.F),
                                                        ]
                                                    )

                                                ],
                                                size="one-third"
                                            ),
                                            column(
                                                [
                                                    row(
                                                        [
                                                            html.H5("Cytoscape:"),
                                                            solution_routing,
                                                            html.H5("Routing Information:"),
                                                            solution_routing_total_cost,
                                                            solution_routing_info_table
                                                        ]
                                                    )
                                                ],
                                                size="two-thirds"
                                            )
                                        ]
                                    ),
                                ]
                            )

                        ]
                    )

    results_section = section(
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
                                                                        inner_element(solution_timing_info_sa),
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
                                                                "Applications",
                                                                solution_results_applications_table,
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
                    )

    app.layout = html.Div(
        [
            html.Div(
                [
                    input_section,
                    routing_section,
                    results_section
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

    if PORT is None:
        PORT = 8050
    app.run_server(port=PORT)


if __name__ == "__main__":
    run_from_pickle(sys.argv[1])

# .\TSNNetCal.exe ..\..\usecases\USES\example\ C:\Users\phd\Nextcloud\PhD\Projects\NetCal\RTCtoolbox\rtc.jar