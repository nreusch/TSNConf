import pickle
from pathlib import Path

from graphviz import Digraph

from input.model.nodes import switch
from input.model.task import ETaskType
from input.testcase import Testcase
from optimization.sa.task_graph import PrecedenceGraph
from solution import solution_parser
from solution.solution import Solution
import networkx as nx

from utils.utilities import report_exception


def create_flex_network_description(output_file: Path, tc: Testcase):
    f = open(output_file, "w")
    f.write(tc.to_flex_network_description())
    f.close()

def aggregate_solution(csv_path: Path, solution: Solution):
    df = solution_parser.get_solution_results_info_dataframe(solution)

    if not csv_path.exists():
        df.to_csv(csv_path)
    else:
        df.to_csv(csv_path, mode="a", header=False)

def serialize_solution(base_path: Path, solution: Solution, visualize: bool) -> Path:
    """
    Serializes the given solution (pickle, network_description, graphs, optimization results...) into a folder and returns its path
    """
    path = base_path / solution.get_folder_name()
    path.mkdir(parents=True, exist_ok=True)

    # Pickle solution object
    with open(path / "solution.pickle", "wb") as f:
        # Pickle solution object
        pickle.dump(solution, f, pickle.HIGHEST_PROTOCOL)
        f.close()

    # Create flex_network_description
    create_flex_network_description(
        path
        / "{}_mode{}.flex_network_description".format(
            solution.input_params.tc_name, solution.input_params.mode.value
        ),
        solution.tc,
    )

    if visualize:
        # Create graphviz graphs
        svg_path = path / "svg"
        svg_path.mkdir(exist_ok=True)
        serialize_graphs(svg_path, solution)

        # Create plotly schedules
        fig = solution_parser.get_solution_schedule_plotly(solution)
        if fig is not None:
            fig.write_html(str(path / "schedule.html"))
            try:
                fig.write_image(str(path / "schedule.pdf"), width=1920, height=640, engine="kaleido")
            except Exception as e:
                raise e

    # Append to results.csv
    df = solution_parser.get_solution_results_info_dataframe(solution)
    df.insert(0, "Testcase Name", solution.get_folder_name())

    with open(base_path / "solutions.csv", "a") as f:
        df.to_csv(f, header=f.tell() == 0, index=False)

    return path


def deserialize_solution(path: Path) -> Solution:
    """
    Loads a solution object from a given pickle file
    """
    with open(path, "rb") as f:
        data = pickle.load(f)
        f.close()
        return data


def serialize_graphs(path: Path, solution: Solution):
    """
    Serialiazies the graphs (topology, applications) of the given solution to the given path
    """
    testcase = solution.tc
    # TODO: Handle no task case
    # Base - Topology
    dot = Digraph(comment="base_topology", node_attr={"shape": "record"})
    for node in testcase.N.values():
        if isinstance(node, switch):
            dot.node(node.id, label=node.id + " (SW)", shape="circle")
        else:
            task_list = testcase.T_g[node.id]
            task_list = [task for task in task_list if task.type == ETaskType.NORMAL]
            # Create task rows
            task_rows = []

            for i in range(0, len(task_list), 3):
                task_row = "{"
                task_row += task_list[i].id if i < len(task_list) else ""
                task_row += "|" + task_list[i + 1].id if i + 1 < len(task_list) else ""
                task_row += "|" + task_list[i + 2].id if i + 2 < len(task_list) else ""
                task_row += "}"
                task_rows.append(task_row)

            # Assemble label
            layout_label = "{"
            layout_label += node.id + " (ES)"
            for task_row in task_rows:
                layout_label += "|" + task_row
            layout_label += "}"

            dot.node(node.id, label=layout_label)

    for link in testcase.L.values():
        dot.edge(link.src.id, link.dest.id)

    try:
        dot.format = "pdf"
        dot.render(filename=path / ("base_topology.gv"))
    except Exception as e:
        report_exception(e)

    try:
        dot.format = "svg"
        dot.render(filename=path / ("base_topology.gv"))
    except Exception as e:
        report_exception(e)

    # TODO: Handle no task case
    # Security Topology
    dot = Digraph(comment="security_topology", node_attr={"shape": "record"})
    for node in testcase.N.values():
        if isinstance(node, switch):
            dot.node(node.id, label=node.id + " (SW)", shape="circle")
        else:
            task_list = testcase.T_g[node.id]
            task_list = [task for task in task_list if not task.type == ETaskType.NORMAL]
            # Create task rows
            task_rows = []

            for i in range(0, len(task_list), 3):
                task_row = "{"
                task_row += task_list[i].id if i < len(task_list) else ""
                task_row += "|" + task_list[i + 1].id if i + 1 < len(task_list) else ""
                task_row += "|" + task_list[i + 2].id if i + 2 < len(task_list) else ""
                task_row += "}"
                task_rows.append(task_row)

            # Assemble label
            layout_label = "{"
            layout_label += node.id + " (ES)"
            for task_row in task_rows:
                layout_label += "|" + task_row
            layout_label += "}"

            dot.node(node.id, label=layout_label)

    for link in testcase.L.values():
        dot.edge(link.src.id, link.dest.id)

    dot.format = "pdf"
    dot.render(filename=path / ("security_topology.gv"))
    dot.format = "svg"
    dot.render(filename=path / ("security_topology.gv"))

    # Application DAGs (base + security)
    existing_tuples = {}  # maps task tuples to index of dot items
    index = 0

    app_list = testcase.A.values()

    for app in app_list:
        dot = Digraph(comment=app.id)

        for task in app.verticies.values():
            dot.node(task.id)
            index += 1


        existing_streams = []
        for stream_id, tup_list in app.edges.items():
            stream = solution.tc.F[stream_id]

            if stream.get_id_prefix() not in existing_streams:
                for tup in tup_list:
                    dot.edge(tup[0], tup[1], label=" {}".format(stream_id))
                    existing_streams.append(stream.get_id_prefix())

        dot.format = "pdf"
        dot.render(filename=path / (app.id + ".gv"))
        dot.format = "svg"
        dot.render(filename=path / (app.id + ".gv"))

    # Application Task DAGs

    try:
        tg = PrecedenceGraph.from_applications(testcase)
        pdot = nx.drawing.nx_pydot.to_pydot(tg.DAG)
        pdot.write(path / ("precgraph" + ".gv"))
        pdot.write_png(path / ("precgraph" + ".png"))
        pdot.write_svg(path / ("precgraph" + ".svg"))
    except Exception as e:
        report_exception(e)