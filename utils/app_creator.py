import random as random
from typing import Tuple, List, Dict

import networkx as nx
from networkx.drawing.nx_pydot import graphviz_layout

from input.model.application import application, EApplicationType
from input.model.stream import stream, EStreamType
from input.model.task import task, ETaskType
import matplotlib.pyplot as plt



def find_random_es(available_es: Dict[str, float], task_utilization: float, config) -> str:
    random_es = random.choice(list(available_es.keys()))
    available_es[random_es] += task_utilization

    if available_es[random_es] >= config.max_es_utilization:
        if available_es[random_es] > 1:
            raise ValueError("ES utilization > 1")
        available_es.pop(random_es)

    return random_es

def create_app(name, config, available_es) -> Tuple[application, List[task], List[stream]]:
    period = random.choice(config.periods)
    app = application(name, period, EApplicationType.NORMAL)
    tasks = []
    streams = []
    layers = random.randint(2, config.max_app_depth)
    task_count = random.randint(layers, layers * config.max_app_width)

    cuts = random.sample(range(1, task_count), layers - 1)
    cuts.append(0)
    cuts.append(task_count)
    cuts = sorted(cuts)

    G = nx.DiGraph()

    print(f"Layers: {layers}")
    print(f"Task count: {task_count}")

    tasks_for_layer: List[List[task]] = []

    for i in range(layers):
        tasks_for_layer.append([])
        print(f"Layer {i}, creating tasks: ", end="")
        for j in range(cuts[i], cuts[i + 1]):
            # Create tasks
            print(f"{j},", end="")
            t_wcet = random.randint(1, int(config.max_task_period_percentage * period))
            t_es_id = find_random_es(available_es, t_wcet / period, config)
            t = task(f"Task_{app.id}_{j}", app.id, t_es_id, t_wcet, period, ETaskType.NORMAL)
            tasks_for_layer[i].append(t)
            tasks.append(t)
            G.add_node(t.id)

        print()

    # If not last layer, connect each task to next layer
    for i in range(layers-1):
        for t in tasks_for_layer[i]:
            conn_count = random.randint(1, min(config.max_multicast_count,len(tasks_for_layer[i+1])))

            dest_tasks = random.sample(tasks_for_layer[i+1], conn_count)

            # Create stream
            receiver_es_ids = [t_dest.src_es_id for t_dest in dest_tasks]
            receiver_task_ids = [t_dest.id for t_dest in dest_tasks]

            for rtid in receiver_task_ids:
                G.add_edge(t.id, rtid)

            if random.randint(1, 100) < config.stream_secure_chance*100:
                secure = True
                rl = random.randint(1, config.stream_max_rl)
                size = random.randint(1, config.stream_max_size - config.mac_length)
            else:
                secure = False
                rl = 1
                size = random.randint(1, config.stream_max_size)
            s = stream(f"Stream_{app.id}_{t.id}", app.id, t.src_es_id, receiver_es_ids, t.id, receiver_task_ids, size+config.frame_overhead, period, rl, secure, size-config.mac_length, config.mac_length, config.frame_overhead, EStreamType.NORMAL)
            streams.append(s)

    plt.figure()
    pos = graphviz_layout(G, prog="dot")
    nx.draw(G, pos=pos, with_labels=True)
    plt.ion()
    plt.show()
    plt.pause(0.001)
    return app, tasks, streams