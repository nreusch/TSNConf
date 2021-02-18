import sys
from functools import reduce
from math import gcd
from pathlib import Path
from time import time
from typing import Dict, List

from intervaltree import IntervalTree
from networkx import DiGraph

from input.model.application import application
from input.model.nodes import end_system, node
from input.model.route import route

PRINT_CONSTRAINT_DESCRIPTION = False
PRINT_CONSTRAINT_VALUES = True
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

def sorted_complement(tree, start=None, end=None) -> IntervalTree:
    result = IntervalTree()
    if start is None:
        start = tree.begin()
    if end is None:
        end = tree.end()

    result.addi(start, end)  # using input tree bounds
    for iv in tree:
        result.chop(iv[0], iv[1])
    return sorted(result)

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
