import base64
import itertools
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import dash_cytoscape as cyto
import pandas as pd
import plotly.graph_objs as go

from input.model.nodes import end_system
from input.model.stream import EStreamType
from input.model.task import key_verification_task
from input.testcase import ETaskType
from solution.solution import Solution
from utils.utilities import flatten, set_to_string


def get_testcase_application_graphs(solution: Solution) -> Dict[str, str]:
    """
    Returns a dictionary mapping app_id's to html.img src strings of the application graphs
    """

    app_id_graph_b64_map = {}

    for app in solution.tc.A_app.values():
        svg_file_path = Path(
            "testcases/output/{}/svg/{}.gv.svg".format(
                solution.get_folder_name(), app.id
            )
        )

        encoded = base64.b64encode(open(svg_file_path, "rb").read())
        svg = "data:image/svg+xml;base64,{}".format(encoded.decode())

        app_id_graph_b64_map[app.id] = svg

    return app_id_graph_b64_map

def get_testcase_application_taskgraphs(solution: Solution) -> Dict[str, str]:
    """
    Returns a dictionary mapping app_id's to html.img src strings of the application task graphs
    """

    app_id_graph_b64_map = {}

    for app in solution.tc.A_app.values():
        svg_file_path = Path(
            "testcases/output/{}/svg/taskgraph_{}.svg".format(
                solution.get_folder_name(), app.id
            )
        )

        encoded = base64.b64encode(open(svg_file_path, "rb").read())
        svg = "data:image/svg+xml;base64,{}".format(encoded.decode())

        app_id_graph_b64_map[app.id] = svg

    return app_id_graph_b64_map

def get_testcase_topology_graph(solution: Solution) -> str:
    """
    Returns a html.img src string of the topology graph
    """
    svg_file_path = Path(
        "testcases/output/{}/svg/base_topology.gv.svg".format(
            solution.get_folder_name()
        )
    )

    encoded = base64.b64encode(open(svg_file_path, "rb").read())
    svg = "data:image/svg+xml;base64,{}".format(encoded.decode())

    return svg


def get_testcase_task_dataframe(solution: Solution) -> pd.DataFrame:
    """
    Returns a dataframe with ETaskType.NORMAL task information: columns=["ID", "Period (us)", "WCET (us)", "ES"]
    """
    columns = []
    for task in solution.tc.T.values():
        if task.type == ETaskType.NORMAL:
            row = []

            row.append(task.id)
            row.append(task.period)
            row.append(task.exec_time)
            row.append(task.src_es_id)

            columns.append(row)

    return pd.DataFrame(columns, columns=["ID", "Period (us)", "WCET (us)", "ES"])


def get_testcase_stream_dataframe(solution: Solution) -> pd.DataFrame:
    """
    Returns a dataframe with information about all EStreamType.NORMAL streams: columns=["ID","Sender ES", "Receiver ESs", "Sender Task", "Receiver Tasks", "Size", "Period", "Type", "RL", "Secure?"]
    """
    columns = []
    for f_id in solution.tc.F.keys():
        stream = solution.tc.F[f_id]
        if stream.type == EStreamType.NORMAL:
            row = []
            # ID
            row.append(stream.id)
            row.append(stream.sender_es_id)

            # Receiver ESs
            id_string = ""
            for recv_id in stream.receiver_es_ids:
                id_string += recv_id + ", "
            id_string = id_string[:-2]
            row.append(id_string)

            row.append(stream.sender_task_id)

            #Receiver Tasks
            task_string = ""
            for recv_id in stream.receiver_task_ids:
                task_string += recv_id + ", "
            task_string = task_string[:-2]
            row.append(task_string)


            row.append(
                "{} = {} + {} (OH) + {} (MAC)".format(
                    stream.size,
                    stream.message_size,
                    stream.frame_overhead_size,
                    stream.mac_size,
                )
            )
            row.append(stream.period)
            row.append(stream.type.name)
            row.append(stream.rl)
            row.append(stream.is_secure)

            columns.append(row)

    return pd.DataFrame(
        columns,
        columns=[
            "ID",
            "Sender ES",
            "Receiver ESs",
            "Sender Task",
            "Receiver Tasks",
            "Size",
            "Period",
            "Type",
            "RL",
            "Secure?",
        ],
    )


def get_derived_security_topology_graph(solution: Solution) -> str:
    """
    Returns a html.img src string of the topology graph
    """
    svg_file_path = Path(
        "testcases/output/{}/svg/security_topology.gv.svg".format(
            solution.get_folder_name()
        )
    )

    encoded = base64.b64encode(open(svg_file_path, "rb").read())
    svg = "data:image/svg+xml;base64,{}".format(encoded.decode())

    return svg


def get_derived_security_application_graphs(solution: Solution) -> Dict[str, str]:
    """
    Returns a dictionary mapping app_id's to html.img src strings of the application graphs
    """
    app_id_graph_b64_map = {}

    for app in solution.tc.A_sec.values():
        svg_file_path = Path(
            "testcases/output/{}/svg/{}.gv.svg".format(
                solution.get_folder_name(), app.id
            )
        )

        encoded = base64.b64encode(open(svg_file_path, "rb").read())
        svg = "data:image/svg+xml;base64,{}".format(encoded.decode())

        app_id_graph_b64_map[app.id] = svg

    return app_id_graph_b64_map

def get_derived_security_application_taskgraphs(solution: Solution) -> Dict[str, str]:
    """
    Returns a dictionary mapping app_id's to html.img src strings of the application taskgraphs
    """
    app_id_graph_b64_map = {}

    for app in solution.tc.A_sec.values():
        svg_file_path = Path(
            "testcases/output/{}/svg/taskgraph_{}.svg".format(
                solution.get_folder_name(), app.id
            )
        )

        encoded = base64.b64encode(open(svg_file_path, "rb").read())
        svg = "data:image/svg+xml;base64,{}".format(encoded.decode())

        app_id_graph_b64_map[app.id] = svg

    return app_id_graph_b64_map

def get_derived_security_stream_dataframe(solution: Solution) -> pd.DataFrame:
    """
    Returns a dataframe with information about the key streams: columns=["ID","Sender ES", "Receiver ESs", "Sender Task", "Receiver Tasks", "Size", "Period", "Type", "RL", "Secure?"]
    """
    columns = []
    for f_id in solution.tc.F.keys():
        stream = solution.tc.F[f_id]
        if stream.type == EStreamType.KEY:
            row = []
            # ID
            row.append(stream.id)
            row.append(stream.sender_es_id)

            # Receiver ESs
            id_string = ""
            for recv_id in stream.receiver_es_ids:
                id_string += recv_id + ", "
            id_string = id_string[:-2]
            row.append(id_string)

            row.append(stream.sender_task_id)

            #Receiver Tasks
            task_string = ""
            for recv_id in stream.receiver_task_ids:
                task_string += recv_id + ", "
            task_string = task_string[:-2]
            row.append(task_string)


            row.append(
                "{} = {} + {} (OH) + {} (MAC)".format(
                    stream.size,
                    stream.message_size,
                    stream.frame_overhead_size,
                    stream.mac_size,
                )
            )
            row.append(stream.period)
            row.append(stream.type.name)
            row.append(stream.rl)
            row.append(stream.is_secure)

            columns.append(row)

    return pd.DataFrame(
        columns,
        columns=[
            "ID",
            "Sender ES",
            "Receiver ESs",
            "Sender Task",
            "Receiver Tasks",
            "Size",
            "Period",
            "Type",
            "RL",
            "Secure?",
        ],
    )


def get_derived_security_task_dataframe(solution: Solution) -> pd.DataFrame:
    """
    Returns a dataframe with information about security tasks: columns=["ID", "Period (us)", "WCET (us)", "ES", "Key Release ES"]
    """
    columns = []
    for task in solution.tc.T.values():
        if task.type == ETaskType.KEY_RELEASE or task.type == ETaskType.KEY_VERIFICATION:
            row = []

            row.append(task.id)
            row.append(task.period)
            row.append(task.exec_time)
            row.append(task.src_es_id)

            if isinstance(task, key_verification_task):
                row.append(task.corr_release_task_es_id)
            else:
                row.append("/")

            columns.append(row)

    return pd.DataFrame(
        columns, columns=["ID", "Period (us)", "WCET (us)", "ES", "Key Release ES"]
    )

def get_solution_general_info_dataframe(solution: Solution) -> pd.DataFrame:
    """
    Returns a dataframe with general information of the testcase: columns=["Testcase Name", "# ES", "# Streams", "# Signals", "# Tasks"]
    """
    columns = []
    row = []

    row.append(solution.tc.name)
    row.append(len(solution.tc.ES))
    row.append(len(solution.tc.SW))
    row.append(len(solution.tc.F))
    row.append(len(solution.tc.T))

    columns.append(row)

    return pd.DataFrame(
        columns, columns=["Testcase Name", "# ES", "# Streams", "# Signals", "# Tasks"]
    )


def get_solution_mode_description(solution: Solution) -> str:
    """
    Returns a text describing the current running mode
    """

    return solution.input_params.mode.describe()


def get_solution_results_info_dataframe(solution: Solution) -> pd.DataFrame:
    """
    Returns a dataframe of the results: columns=["Laxity Sum", "Bandwidth use (Mean,%)", "CPU use (Mean,%)",
    "Optimization Time (ms)", "Total Runtime (ms)", "E2E-Delay Sum", "Pint", "Hyperperiod"]
    """

    columns = []
    row = []

    row.append("{:d}".format(solution.laxity_total))
    row.append("{:.2f}".format(solution.bandwidth_used_percentage_total * 100))
    row.append("{:.2f}".format(solution.cpu_used_percentage_total * 100))
    row.append("{:.0f}".format(solution.timing_object.get_optimization_time()))
    row.append("{:.0f}".format(solution.timing_object.get_total_time()))
    row.append("{:d}".format(solution.e2e_delays_total))
    row.append("{:d}".format(solution.tc.Pint))
    row.append("{:d}".format(solution.tc.hyperperiod))

    columns.append(row)

    return pd.DataFrame(
        columns,
        columns=[
            "Laxity Sum",
            "Bandwidth use (Mean,%)",
            "CPU use (Mean,%)",
            "Optimization Time (ms)",
            "Total Runtime (ms)",
            "E2E-Delay Sum",
            "Pint",
            "Hyperperiod"
        ],
    )


def get_solution_results_optimization_status_dataframe(
    solution: Solution,
) -> pd.DataFrame:
    """
    Returns a dataframe about the returned status of the different optimizations: columns=["Routing","Pint", "Scheduling"]
    """
    columns = []
    row = []

    row.append(solution.getStatusRouting())
    row.append(solution.getStatusPint())
    row.append(solution.getStatusScheduling())

    columns.append(row)
    return pd.DataFrame(columns, columns=["Routing", "Pint", "Scheduling"])


def get_solution_functionpath_dataframe(solution: Solution) -> pd.DataFrame:
    """
    Returns a dataframe about functionpaths: columns=["Function Path ID", "Deadline", "Latency", "Laxity"]
    """
    columns = []
    row = []

    for fp in solution.tc.FP.values():
        row = []
        row.append(fp.id)

        row.append(fp.deadline)

        laxity = -1
        latency = -1
        if solution.tc.schedule != None:
            if fp.id in solution.tc.schedule.laxities_val:
                laxity = solution.tc.schedule.laxities_val[fp.id]
                latency = fp.deadline - laxity
        row.append(latency)
        row.append(laxity)
        columns.append(row)

    return pd.DataFrame(
        columns,
        columns=["Function Path ID", "Deadline (us)", "Latency (us)", "Laxity (us)"],
    )


def get_solution_inputparam_info_dataframe(solution: Solution) -> pd.DataFrame:
    """
    Returns a dataframe about testcase parameters: columns=["MTU (Byte)", "Frame Overhead (Byte)", "MAC Length (Byte)", "TESLA Key Length (Byte)"]
    """
    columns = []
    row = []

    row.append(solution.tc.W_f_max)
    row.append(solution.tc.OH)

    row.append(solution.tc.W_mac)
    row.append(solution.tc.key_length)

    columns.append(row)

    return pd.DataFrame(
        columns,
        columns=[
            "MTU (Byte)",
            "Frame Overhead (Byte)",
            "MAC Length (Byte)",
            "TESLA Key Length (Byte)",
        ],
    )


def get_solution_timing_info_dataframe(solution: Solution) -> pd.DataFrame:
    """
    Returns a dataframe about timing information of the testcase run: columns=[
        "Testcase Parsing (ms)",
        "Creating Variables - Routing (ms)", "Creating Constraints - Routing (ms)", "Optimizing - Routing (ms)",
        "Creating Variables - Pint (ms)", "Creating Constraints - Pint (ms)", "Optimizing - Pint (ms)",
        "Creating Variables - Scheduling (ms)", "Creating Constraints - Scheduling (ms)", "Optimizing - Scheduling (ms)",
        "Creating Variables - Simulated Annealing (ms)", "Optimizing - Simulated Annealing (ms)",
        "Serializing Solution (ms)"]
    """
    columns = []
    row = []

    row.append("{:.2f}".format(solution.timing_object.time_parsing))
    row.append("{:.2f}".format(solution.timing_object.time_creating_vars_routing))
    row.append(
        "{:.2f}".format(solution.timing_object.time_creating_constraints_routing)
    )
    row.append("{:.2f}".format(solution.timing_object.time_optimizing_routing))

    row.append("{:.2f}".format(solution.timing_object.time_creating_vars_pint))
    row.append("{:.2f}".format(solution.timing_object.time_creating_constraints_pint))
    row.append("{:.2f}".format(solution.timing_object.time_optimizing_pint))

    row.append("{:.2f}".format(solution.timing_object.time_creating_vars_scheduling))
    row.append(
        "{:.2f}".format(solution.timing_object.time_creating_constraints_scheduling)
    )
    row.append("{:.2f}".format(solution.timing_object.time_optimizing_scheduling))

    row.append("{:.2f}".format(solution.timing_object.time_creating_vars_simulated_annealing))
    row.append("{:.2f}".format(solution.timing_object.time_optimizing_simulated_annealing))

    row.append("{:.2f}".format(solution.timing_object.time_serializing_solution))

    columns.append(row)

    return pd.DataFrame(
        columns,
        columns=[
            "Testcase Parsing (ms)",
            "Creating Variables - Routing (ms)",
            "Creating Constraints - Routing (ms)",
            "Optimizing - Routing (ms)",
            "Creating Variables - Pint (ms)",
            "Creating Constraints - Pint (ms)",
            "Optimizing - Pint (ms)",
            "Creating Variables - Scheduling (ms)",
            "Creating Constraints - Scheduling (ms)",
            "Optimizing - Scheduling (ms)",
            "Creating Variables - Simulated Annealing (ms)",
            "Optimizing - Simulated Annealing (ms)",
            "Serializing Solution (ms)",
        ],
    )

def get_solution_routing_info_dataframe(solution: Solution) -> pd.DataFrame:
    """
    Returns a dataframe with route information: columns=["Stream ID","Cost","Route Length","Overlap Amount","Overlap Links"]
    """
    columns = []

    for r_info in solution.tc.R_info.values():
        row = []

        row.append(r_info.route.stream.id)
        row.append(r_info.cost)
        row.append(r_info.route_len)

        row.append(r_info.overlap_number)
        row.append(set_to_string(r_info.overlap_links))

        columns.append(row)

    return pd.DataFrame(
        columns,
        columns=[
            "Stream ID",
            "Cost",
            "Route Length",
            "Overlap Amount",
            "Overlap Links"
        ],
    )


def get_solution_routing_cytoscape(solution: Solution) -> cyto.Cytoscape:
    """
    Returns a cytoscape object showing the network topology and stream routing
    """

    # elements
    elements = []
    nodes = []
    edges = []

    for n in solution.tc.N.values():
        el = {}
        el["data"] = {"id": n.id, "label": n.id}
        if isinstance(n, end_system):
            el["classes"] = "ES"
        else:
            el["classes"] = "SW"
        nodes.append(el)

    for l in solution.tc.L.values():
        el = {}
        el["data"] = {"source": l.src.id, "target": l.dest.id}
        el["classes"] = "link"
        edges.append(el)

    for f_id, mtree in solution.tc.R.items():
        for l in mtree.get_all_links(solution.tc):
            el = {}
            el["data"] = {"source": l.src.id, "target": l.dest.id}
            el["classes"] = f_id
            edges.append(el)

    elements = flatten([nodes, edges])

    # stylesheet

    stylesheet = flatten(
        [
            _cytoscape_base_stylesheet(),
            _cytoscape_base_stream_selectors(solution.tc.F_routed.keys()),
        ]
    )

    cyto.load_extra_layouts()
    graph = cyto.Cytoscape(
        id="cytoscape-routing-graph",
        layout={"name": "cose"},
        style={"width": "100%", "height": "800px"},
        elements=elements,
        stylesheet=stylesheet,
    )

    return graph


def _cytoscape_route_colorset() -> List[str]:
    # https://clrs.cc/
    color_set = [
        "#FF851B",
        "#39CCCC",
        "#2ECC40",
        "#01FF70",
        "#FFDC00",
        "#0074D9",
        "#DDDDDD" "#85144b",
        "#3D9970",
        "#F012BE",
        "#B10DC9",
        "#AAAAAA",
        "#FF4136",
        "#7FDBFF",
    ]
    return color_set


def _cytoscape_base_stylesheet() -> List[Dict]:
    stylesheet = [
        {"selector": "node", "style": {"content": "data(label)"}},
        {"selector": ".link", "style": {"line-color": "black"}},
        {
            "selector": ".ES",
            "style": {"shape": "round-rectangle", "background-color": "lightblue"},
        },
        {
            "selector": ".SW",
            "style": {"shape": "rectangle", "background-color": "lightgreen"},
        },
    ]
    return stylesheet


def _cytoscape_base_stream_selectors(stream_ids: Iterable) -> List[Dict]:
    selectors = []
    i = 0
    for f_id in stream_ids:
        selectors.append({"selector": ".{}".format(f_id), "style": {"display": "none"}})
        i += 1
    return selectors


def get_solution_schedule_plotly(solution: Solution) -> Optional[go.Figure]:
    """
    Returns a plotly figure of the schedule
    """
    solution = solution

    if solution.tc.schedule:
        tick_distance = solution.tc.Pint
        if tick_distance > 0:
            fig = go.Figure(
                layout={
                    "barmode": "stack",
                    "xaxis": {
                        "automargin": True,
                        "tickmode": "linear",
                        "tick0": 0,
                        "dtick": tick_distance,
                    },
                    "yaxis": {"automargin": True},
                },
            )
        else:
            fig = go.Figure(
                layout={
                    "barmode": "stack",
                    "xaxis": {
                        "automargin": True
                    },
                    "yaxis": {"automargin": True},
                },
            )

        """
        fig.update_layout(
        font=dict(
            family="Liberation Sans",
            size=44,
            color="#000000"
        )
        )
        """

        block_types = [
            "app_task",
            "key_rel_task",
            "key_ver_task",
            "normal_stream",
            "key_stream",
        ]
        block_durations = {}
        block_linkids = {}
        block_hovers = {}
        block_offsets = {}
        block_texts = {}

        for i in block_types:
            block_durations[i] = []
            block_linkids[i] = []
            block_hovers[i] = []
            block_offsets[i] = []
            block_texts[i] = []

        # Tasks
        for task in solution.tc.T.values():
            if task.type == ETaskType.NORMAL:
                index = "app_task"
            elif task.type == ETaskType.KEY_RELEASE:
                index = "key_rel_task"
            elif task.type == ETaskType.KEY_VERIFICATION:
                index = "key_ver_task"
            else:
                index = "INVALID"

            for i_period in range(int(solution.tc.hyperperiod / task.period)):
                offset = (
                    i_period * task.period + solution.tc.schedule.o_t_val[task.id]
                )
                length = task.exec_time

                block_durations[index].append(length)
                block_hovers[index].append(
                    "{}\nStart: {}\nEnd: {}".format(task.id, offset, offset + length)
                )
                block_linkids[index].append(str(solution.tc.N[task.src_es_id]))
                block_offsets[index].append(offset)
                block_texts[index].append(task.id)

            # Streams
            for l_or_n_id in itertools.chain(
                solution.tc.L.keys(), solution.tc.N.keys()
            ):
                for f in solution.tc.F_routed.values():
                    if solution.tc.schedule.is_stream_using_link_or_node(
                        f.id, l_or_n_id
                    ):
                        l_or_n = None
                        if l_or_n_id in solution.tc.L:
                            l_or_n = solution.tc.L[l_or_n_id]
                        elif l_or_n_id in solution.tc.N:
                            l_or_n = solution.tc.N[l_or_n_id]
                        assert l_or_n != None

                        if f.type == EStreamType.KEY:
                            index = "key_stream"
                        else:
                            index = "normal_stream"

                        for i_period in range(int(solution.tc.hyperperiod / f.period)):
                            offset = (
                                i_period * f.period
                                + solution.tc.schedule.o_f_val[l_or_n_id][f.id]
                            )
                            length = solution.tc.schedule.c_f_val[l_or_n_id][f.id]

                            block_durations[index].append(length)
                            block_hovers[index].append(
                                "{}\nStart: {}\nEnd: {}".format(
                                    f.id, offset, offset + length
                                )
                            )
                            block_linkids[index].append(str(l_or_n))
                            block_offsets[index].append(offset)

                            block_texts[index].append(f.id)


        for ind in block_types:
            if ind == "app_task":
                color = "#1f77b4"  # muted blue
            elif ind == "key_rel_task":
                color = "#9467bd"  # muted purple
            elif ind == "key_ver_task":
                color = "#2ca02c"  # cooked asparagus green
            elif ind == "normal_stream":
                color = "#d62728"  # brick red
            elif ind == "key_stream":
                color = "#ff7f0e"  # safety orange

            fig.add_bar(
                x=block_durations[ind],
                y=block_linkids[ind],
                base=block_offsets[ind],
                orientation="h",
                name=ind,
                textfont=dict(color="white"),
                text=block_texts[ind],
                textposition="inside",
                textangle=0,
                insidetextanchor="middle",
                marker_color=color,
                hoverinfo="text",
                hovertext=block_hovers[ind],
            )

        if tick_distance > 0:
            for x in range(1, int(solution.tc.hyperperiod / tick_distance)):
                fig.add_shape(
                    # Line reference to the axes
                    type="line",
                    xref="x",
                    yref="paper",
                    x0=x * tick_distance,
                    y0=0,
                    x1=x * tick_distance,
                    y1=1,
                    line=dict(color="Black", width=3, dash="dot"),
                )

        return fig
    return None
