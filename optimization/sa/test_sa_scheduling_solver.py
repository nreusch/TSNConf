from networkx import DiGraph

from optimization.sa.sa_scheduling_solver import SASchedulingSolution
from optimization.sa.task_graph import TopologicalTaskGraphApp


def test_switch_random_normal_apps():
    tga1 = TopologicalTaskGraphApp("App1", DiGraph(), None)
    tga2 = TopologicalTaskGraphApp("App2", DiGraph(), None)
    raw_order = ([], [tga1, tga2])

    order = SASchedulingSolution(raw_order)

    assert order.order == ([], [tga1, tga2])
    order.switch_random_normal_apps()
    assert order.order == ([], [tga2, tga1])
