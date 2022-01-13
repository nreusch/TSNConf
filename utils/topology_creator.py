import networkx as nx
import matplotlib.pyplot as plt
import math
from typing import List, Dict, Tuple
import itertools
import random

class MyPoint():
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.name = ""

        self.connections: List[MyPoint] = []

        self.distances: Dict[MyPoint] = {}  # connected points are removed from here

    def distance_to(self, other_point):
        return math.sqrt(math.pow(abs(self.x - other_point.x), 2) + math.pow(abs(self.y - other_point.y), 2))

    def get_closest_not_connected_point(self):
        return [k for k, v in sorted(self.distances.items(), key=lambda item: item[1])][0]

    def connect(self, p2):
        self.connections.append(p2)
        self.distances.pop(p2)

    def __repr__(self):
        return f"Point({self.x},{self.y})"


def create_points(nr_switches, nr_es):
    points: List[MyPoint] = []
    max_x = nr_switches + nr_es
    max_y = max_x
    # Create a nr_switches x nr_switches 2d space
    samples = random.sample(list(itertools.combinations(range(1, max_x), 2)), nr_switches + nr_es)

    for i in range(len(samples)):
        if i < nr_switches:
            p = MyPoint(samples[i][0], samples[i][1])
            points.append(p)

            # Connect switches bidirectional
            for j in range(i):
                p2 = points[j]
                dstnc = p.distance_to(p2)
                p.distances[p2] = dstnc
                p2.distances[p] = dstnc

            p.name = f"SW{i}"
        else:
            p = MyPoint(samples[i][0], samples[i][1])
            points.append(p)

            # Connect ES only from ES to switch
            for j in range(nr_switches):
                p2 = points[j]
                dstnc = p.distance_to(p2)
                p.distances[p2] = dstnc

            p.name = f"ES{i-nr_switches}"

    return points[:nr_switches], points[nr_switches:]


def connect_switches(points, nr_switches, nr_es, connections_per_sw):
    for k in range(nr_switches):
        p = points[k]
        conn_count = len(p.connections)
        for l in range(connections_per_sw - conn_count):
            p2 = p.get_closest_not_connected_point()
            p.connect(p2)
            p2.connect(p)

    return points


def connect_es_to_switches(points_es, connections_per_es):
    for p in points_es:
        for i in range(connections_per_es):
            p2 = p.get_closest_not_connected_point()
            p.connect(p2)

    return points_es


def generate_topology(nr_switches, nr_es, connections_per_sw, connections_per_es, show_topology=False) -> Tuple[nx.Graph, List[MyPoint], List[MyPoint]]:
    finished = False
    while not finished:
        points_sw, points_es = create_points(nr_switches, nr_es)
        points_sw = connect_switches(points_sw, nr_switches, nr_es, connections_per_sw)
        points_es = connect_es_to_switches(points_es, connections_per_es)
        G = nx.Graph()

        color_map = []
        for p in points_sw:
            G.add_node(p.name)
            color_map.append("blue")

        for p in points_es:
            G.add_node(p.name)
            color_map.append("red")

        for p in itertools.chain(points_sw, points_es):
            for p2 in p.connections:
                G.add_edge(p.name, p2.name)

        print("Found possible graph. Is connected: " + str(nx.is_connected(G)))
        finished = nx.is_connected(G)

    if show_topology:
        pos = nx.spring_layout(G, seed=3068)
        nx.draw(G, pos=pos, with_labels=True, node_color=color_map)
        plt.ion()
        plt.show()
        plt.pause(0.001)

    return G, points_sw, points_es
