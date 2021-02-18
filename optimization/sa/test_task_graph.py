from input.model.application import application, EApplicationType
from input.model.link import link
from input.model.nodes import end_system, switch
from input.model.route import route
from input.model.stream import stream, EStreamType
from input.model.task import task, ETaskType
from input.testcase import Testcase
from optimization.sa.task_graph import TaskGraph, TopologicalTaskGraphOrder


def test_get_topological_order():
    # one applications
    tc = Testcase("UnitTestcase")

    es1 = end_system("ES1", 10)
    es2 = end_system("ES2", 10)
    sw1 = switch("SW1")

    l1 = link(f"link_{es1.id}_{sw1.id}", es1, sw1, 12.5)
    l2 = link(f"link_{sw1.id}_{es2.id}", sw1, es2, 12.5)

    app = application("App1", 1000, EApplicationType.NORMAL)
    t1 = task("t1", app.id, es1.id, 100, app.period, ETaskType.NORMAL)
    t2 = task("t2", app.id, es2.id, 100, app.period, ETaskType.NORMAL)
    s = stream("s1", app.id, t1.src_es_id, {t2.src_es_id}, t1.id, {t2.id}, 100, 1000, 1, False, 78, 0, 22,
               EStreamType.NORMAL)
    r = route(s)
    r.init_from_node_mapping({(es1.id, sw1.id), (sw1.id, es2.id)})

    tc.add_to_datastructures(es1, es2, sw1, l1, l2, app, t1, t2, s, r)
    task_graph = TaskGraph.from_applications(tc)

    tgo = task_graph.get_topological_order()
    assert isinstance(tgo, TopologicalTaskGraphOrder)
    assert tgo.list == ["t1", "s1", "t2"]
    assert tgo.app_list == [(app.id, ["t1", "s1", "t2"])]

    t1_tgn = task_graph.nodes[t1.id]
    t2_tgn = task_graph.nodes[t2.id]
    s_tgn = task_graph.nodes[s.id]

    assert t1_tgn.prev == None and t1_tgn.next == s_tgn
    assert s_tgn.prev == t1_tgn and s_tgn.next == t2_tgn
    assert t2_tgn.prev == s_tgn and t2_tgn.next == None

def test_get_topological_order2():
    # two applications
    tc = Testcase("UnitTestcase")

    es1 = end_system("ES1", 10)
    es2 = end_system("ES2", 10)
    sw1 = switch("SW1")

    l1 = link(f"link_{es1.id}_{sw1.id}", es1, sw1, 12.5)
    l2 = link(f"link_{sw1.id}_{es2.id}", sw1, es2, 12.5)

    app = application("App1", 1000, EApplicationType.NORMAL)
    t1 = task("t1", app.id, es1.id, 100, app.period, ETaskType.NORMAL)
    t2 = task("t2", app.id, es2.id, 100, app.period, ETaskType.NORMAL)
    s = stream("s1", app.id, t1.src_es_id, {t2.src_es_id}, t1.id, {t2.id}, 100, 1000, 1, False, 78, 0, 22,
               EStreamType.NORMAL)
    r = route(s)
    r.init_from_node_mapping({(es1.id, sw1.id), (sw1.id, es2.id)})
    tc.add_to_datastructures(es1, es2, sw1, l1, l2, app, t1, t2, s, r)

    app2 = application("App2", 1000, EApplicationType.NORMAL)
    t11 = task("t11", app2.id, es1.id, 100, app.period, ETaskType.NORMAL)
    t22 = task("t22", app2.id, es2.id, 100, app.period, ETaskType.NORMAL)
    s2 = stream("s2", app2.id, t11.src_es_id, {t22.src_es_id}, t11.id, {t22.id}, 100, 1000, 1, False, 78, 0, 22,
               EStreamType.NORMAL)
    r2 = route(s2)
    r2.init_from_node_mapping({(es1.id, sw1.id), (sw1.id, es2.id)})
    tc.add_to_datastructures(app2, t11, t22, s2, r2)

    task_graph = TaskGraph.from_applications(tc)

    tgo = task_graph.get_topological_order()
    assert isinstance(tgo, TopologicalTaskGraphOrder)
    assert tgo.list == ["t1", "s1", "t2", "t11", "s2", "t22"]
    assert tgo.app_list == [(app.id, ["t1", "s1", "t2"]), (app2.id, ["t11", "s2", "t22"])]

    t1_tgn = task_graph.nodes[t1.id]
    t2_tgn = task_graph.nodes[t2.id]
    s_tgn = task_graph.nodes[s.id]
    t11_tgn = task_graph.nodes[t11.id]

    assert t1_tgn.prev == None and t1_tgn.next == s_tgn
    assert s_tgn.prev == t1_tgn and s_tgn.next == t2_tgn
    assert t2_tgn.prev == s_tgn and t2_tgn.next == t11_tgn
    assert t11_tgn.prev == t2_tgn