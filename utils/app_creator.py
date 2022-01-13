import random as random
from typing import Tuple, List, Dict

import networkx as nx
from networkx import weakly_connected_components

from input.model.application import application, EApplicationType
from input.model.stream import stream, EStreamType
from input.model.task import task, ETaskType

import subprocess

import graphviz
import subprocess
import matplotlib.pyplot as plt
import time

def create_simple_apps(app_name_prefix: str, config, es_utilization_dict):
    # Creates a simple application with 2 zero wcet tasks and one stream between them
    period = random.choice(config.periods)

    # Create the application datastructure
    app = application(app_name_prefix, period, EApplicationType.NORMAL)
    tasks = {}
    streams = []

    # Create tasks from DAG nodes
    send_t_wcet = 1
    send_t_es_id = find_random_es(es_utilization_dict, send_t_wcet / period, config)
    t_send = task(f"t-{app.id}-send", app.id, send_t_es_id, send_t_wcet, period, 0,
             ETaskType.NORMAL)  # Don't use underscores in task name

    recv_t_wcet = 1
    recv_t_es_id = find_random_es(es_utilization_dict, recv_t_wcet / period, config, send_t_es_id)
    t_recv = task(f"t-{app.id}-recv", app.id, recv_t_es_id, recv_t_wcet, period, 0,
             ETaskType.NORMAL)  # Don't use underscores in task name

    tasks[t_send.id] = t_send
    tasks[t_recv.id] = t_recv

    # Create streams from DAG edges
    stream_id = f"s-{t_send.id}"  # Don't use underscores in stream name
    message_size = random.randint(config.stream_min_size, config.stream_max_size - config.frame_overhead)
    mac_size = 0
    overhead = config.frame_overhead
    rl = 1
    secure = False

    s = stream(stream_id, app.id, t_send.src_es_id, [t_recv.src_es_id], t_send.id, [t_recv.id],
               message_size + mac_size + overhead, app.period, rl, secure, message_size, mac_size, overhead,
               EStreamType.NORMAL)
    streams.append(s)

    return (app, tasks.values(), streams)


def get_dag_from_ggen(task_count: int, tree_depth: int, connection_probability: float, container_id):
    # using https://github.com/perarnau/ggen
    # run vagrant container
    # map apps/ folder to /apps on the vagrant box
    # vagrant global-status to determine id

    cmd = f'vagrant ssh -c "ggen --log-level 0 generate-graph lbl {task_count} {tree_depth} {connection_probability} > /apps/app.dot" {container_id}'

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    process.communicate()

    G = nx.DiGraph(nx.drawing.nx_pydot.read_dot("utils/apps/app.dot"))

    return G

def create_dags(task_count: int, tree_depth: int, connection_probability: float, app_name, container_id):
    # using https://github.com/perarnau/ggen
    # run vagrant container
    # map apps/ folder to /apps on the vagrant box
    # vagrant global-status to determine id

    cmd = f'vagrant ssh -c "ggen --log-level 0 generate-graph lbl {task_count} {tree_depth} {connection_probability} > /apps/{app_name}.dot" {container_id}'

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    process.communicate()

    G = nx.DiGraph(nx.drawing.nx_pydot.read_dot("utils/apps/app.dot"))

    return G

def find_random_es(es_utilization_dict: Dict[str, float], task_utilization: float, config, exclude_es_id="") -> str:
    random_es = random.choice(list(es_utilization_dict.keys()))
    while random_es == exclude_es_id or es_utilization_dict[random_es]+task_utilization >= config.max_es_utilization:
        random_es = random.choice(list(es_utilization_dict.keys()))
    es_utilization_dict[random_es] += task_utilization

    return random_es

def create_apps(app_name_prefix: str, config, es_utilization_dict: Dict[str, float], task_count: int, use_existing_dag, container_id, existing_dag_random=True) -> List[Tuple[application, List[task], List[stream]]]:
    print(f"Creating apps with {task_count} tasks")

    # Create a random DAG using the ggen tool
    if not use_existing_dag:
        G = get_dag_from_ggen(task_count, random.randint(config.min_app_depth, config.max_app_depth), config.app_task_connection_probability, container_id)
    else:
        if existing_dag_random:
            r = random.randint(0, 9)
        else:
            r = 1
        G = nx.DiGraph(nx.drawing.nx_pydot.read_dot(f"../../utils/apps/dag{r}.dot"))

    # Split seperate parts of the DAG into seperate applications
    sgs = [G.subgraph(c) for c in weakly_connected_components(G)]

    lst = []
    i = 0
    for SG in sgs:
        # Choose a random period
        period = random.choice(config.periods)

        # Create the application datastructure
        app = application(app_name_prefix + f"{i}", period, EApplicationType.NORMAL)
        tasks = {}
        streams = []

        # Create tasks from DAG nodes
        for n in SG:
            t_wcet = random.randint(1, int(config.max_task_period_percentage * period))
            t_es_id = find_random_es(es_utilization_dict, t_wcet / period, config)
            t = task(f"t-{app.id}-{n}", app.id, t_es_id, t_wcet, period, 0, ETaskType.NORMAL) # Don't use underscores in task name
            tasks[n] = t
            SG.nodes[n]["ES"] = t_es_id

        # Create streams from DAG edges
        streams = create_streams(SG, app, config, tasks)

        # Draw graph
        pos = nx.drawing.nx_pydot.graphviz_layout(SG, prog="dot")
        nx.draw(SG, pos, labels=nx.get_node_attributes(SG, 'ES'), font_size=16 )
        edge_labels = dict([((n1, n2), SG[n1][n2]["s"])
                            for n1, n2 in SG.edges if "s" in SG[n1][n2]])
        nx.draw_networkx_edge_labels(SG, pos=pos, edge_labels=edge_labels)
        plt.ion()
        plt.show()
        plt.pause(0.001)

        lst.append((app, tasks.values(), streams))

        i += 1

    return lst


def create_streams(G: nx.DiGraph, app: application, config, tasks: Dict[str, task]) -> List[stream]:
    streams = []

    for n in G:
        t = tasks[n]
        stream_id = f"s-{t.id}" # Don't use underscores in stream name

        receiver_es_ids = []
        receiver_task_ids = []
        for n_recv in G.neighbors(n):
            if G.nodes[n_recv]["ES"] != G.nodes[n]["ES"]:
                receiver_es_ids.append(G.nodes[n_recv]["ES"])
                receiver_task_ids.append(tasks[n_recv].id)
                G[n][n_recv]["s"] = stream_id

        if len(receiver_task_ids) > 0:
            if random.randint(1, 100) < config.stream_secure_chance * 100:
                secure = True
                rl = random.randint(1, config.stream_max_rl)
                message_size = random.randint(1, config.stream_max_size - config.mac_length - config.frame_overhead)
                mac_size = config.mac_length
                overhead = config.frame_overhead
            else:
                secure = False
                rl = 1
                message_size = random.randint(config.stream_min_size, config.stream_max_size - config.frame_overhead)
                mac_size = 0
                overhead = config.frame_overhead

            s = stream(stream_id, app.id, t.src_es_id, receiver_es_ids, t.id, receiver_task_ids,
                       message_size + mac_size + overhead, app.period, rl, secure, message_size, mac_size, overhead, EStreamType.NORMAL)
            streams.append(s)

    return streams
