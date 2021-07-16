import sys
from functools import reduce
from math import gcd
from pathlib import Path
from time import time
from typing import Dict, List

from intervaltree import IntervalTree, Interval
import networkx as nx
from networkx import DiGraph
from networkx.algorithms.shortest_paths.weighted import _weight_function
from networkx.algorithms.simple_paths import _bidirectional_dijkstra, PathBuffer, _bidirectional_shortest_path

from input.model.application import application
from input.model.nodes import end_system, node
from input.model.route import route

PRINT_CONSTRAINT_DESCRIPTION = False
PRINT_CONSTRAINT_VALUES = False
DEBUG = False


OUTPUT_PATH = Path("testcases/output/")

"""
Given a version number MAJOR.MINOR.PATCH, increment the:

MAJOR version when you make incompatible API changes,
MINOR version when you add functionality in a backwards compatible manner, and
PATCH version when you make backwards compatible bug fixes.
"""
VERSION = "0.6"

def report_exception(e):
    sys.stderr.write(str(e))


def lcm(a: List) -> int:
    lcm = a[0]
    for i in a[1:]:
        lcm = int(lcm * i / gcd(lcm, i))
    return int(lcm)


def list_gcd(list) -> int:
    x = reduce(gcd, list)
    return int(x)


def flatten(list_of_list: List[List]) -> List:
    return [val for sublist in list_of_list for val in sublist]


def flatten_dict(d: Dict, parent_key: str = "", sep: str = "_") -> Dict:
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        items.append((new_key, v))
    return dict(items)


def print_constraint(name: str, description: str, values: str):
    if DEBUG:
        if PRINT_CONSTRAINT_DESCRIPTION and PRINT_CONSTRAINT_VALUES:
            print(name + ": " + description + " -- " + values)
        elif PRINT_CONSTRAINT_DESCRIPTION:
            print(name + ": " + description)
        elif PRINT_CONSTRAINT_VALUES:
            print(name + ": " + values)


def debug_print(s: str):
    if DEBUG:
        print(s)


def print_model_stats(model_stats_string: str):
    if DEBUG:
        print(model_stats_string)
    # nr_vars = model_stats_string.split("\n")[1].split(" ")[1]

    # print("Variables: {}; Constraints:\n {}".format(nr_vars, "\n".join(model_stats_string.split("\n")[6:])))
    # print("Variables: {}".format(nr_vars))

def set_to_string(s: set):
    return ", ".join([str(x) for x in s])

def sorted_complement(tree, f, start=None, end=None) -> List[Interval]:
    result = IntervalTree()
    if start is None:
        start = tree.begin()
    if end is None:
        end = tree.end()

    result.addi(start, end)  # using input tree bounds
    for iv in tree:
        if  iv.begin == f.offset and iv.end == f.offset + f.length:
            pass
            # don't chop out the block of the frame itself (useful for latency optimization where f is already scheuduled somewhere)
        else:
            result.chop(iv[0], iv[1])
    return sorted(result)

def shortest_simple_paths_patched(G, source, target, ignore_nodes_init=None, ignore_edges_init=None, weight=None):
    """
    Extended version of the networkx shortest_simple_paths implementation.
    It takes additional arguments ignore_nodes, ignore_edges, which can be used to ignore certain nodes/edges during pathfinding.
    E.g. end systems
    """
    if source not in G:
        raise nx.NodeNotFound(f"source node {source} not in graph")

    if target not in G:
        raise nx.NodeNotFound(f"target node {target} not in graph")

    if weight is None:
        length_func = len
        shortest_path_func = _bidirectional_shortest_path
    else:
        wt = _weight_function(G, weight)

        def length_func(path):
            return sum(
                wt(u, v, G.get_edge_data(u, v)) for (u, v) in zip(path, path[1:])
            )

        shortest_path_func = _bidirectional_dijkstra

    listA = list()
    listB = PathBuffer()
    prev_path = None
    while True:
        if not prev_path:
            length, path = shortest_path_func(G, source, target, ignore_nodes=ignore_nodes_init, ignore_edges=ignore_edges_init, weight=weight)
            listB.push(length, path)
        else:
            ignore_nodes = set()
            if ignore_nodes_init:
                ignore_nodes.update(ignore_nodes_init)
            ignore_edges = set()
            if ignore_edges_init:
                ignore_edges.update(ignore_edges_init)
            for i in range(1, len(prev_path)):
                root = prev_path[:i]
                root_length = length_func(root)
                for path in listA:
                    if path[:i] == root:
                        ignore_edges.add((path[i - 1], path[i]))
                try:
                    length, spur = shortest_path_func(
                        G,
                        root[-1],
                        target,
                        ignore_nodes=ignore_nodes,
                        ignore_edges=ignore_edges,
                        weight=weight,
                    )
                    path = root[:-1] + spur
                    listB.push(root_length + length, path)
                except nx.NetworkXNoPath:
                    pass
                ignore_nodes.add(root[-1])

        if listB:
            path = listB.pop()
            yield path
            listA.append(path)
            prev_path = path
        else:
            break

class Timer:
    elapsed_time = 0

    def __init__(self):
        pass

    def __enter__(self):
        self.start = time()
        return None  # could return anything, to be used like this: with Timer("Message") as value:

    def __exit__(self, type, value, traceback):
        self.elapsed_time = (time() - self.start) * 1000  # milliseconds
        # print(self.message.format(self.elapsed_time))
