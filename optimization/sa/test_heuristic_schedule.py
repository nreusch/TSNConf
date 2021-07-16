from intervaltree import Interval

from input.model.application import application, EApplicationType
from input.model.link import link
from input.model.nodes import end_system, switch
from input.model.route import route
from input.model.stream import stream, EStreamType
from input.model.task import task, ETaskType
from input.testcase import Testcase
from optimization.sa.heuristic_schedule import heuristic_schedule
from optimization.sa.task_graph import PrecedenceGraph, TaskGraphNode_Stream, TaskGraphNode_Task


def test_heuristic_schedule_single_period():
    tc = Testcase("UnitTestcase")

    es1 = end_system("ES1", 10)
    es2 = end_system("ES2", 10)
    sw1 = switch("SW1")

    l1 = link(f"link_{es1.id}_{sw1.id}", es1, sw1, 12.5)
    l2 = link(f"link_{sw1.id}_{es2.id}", sw1, es2, 12.5)

    app = application("App1", 1000, EApplicationType.NORMAL)
    app2 = application("App2", 500, EApplicationType.NORMAL)
    t1_app2 = task("t1_app2", app2.id, es1.id, 100, app2.period, ETaskType.NORMAL)
    t1 = task("t1", app.id, es1.id, 100, app.period, ETaskType.NORMAL)
    t11 = task("t11", app.id, es1.id, 100, app.period, ETaskType.NORMAL)
    t2 = task("t2", app.id, es2.id, 100, app.period, ETaskType.NORMAL)
    s = stream("s1", app.id, t1.src_es_id, {t2.src_es_id}, t1.id, {t2.id}, 100, 1000, 1, False, 78, 0, 22,
               EStreamType.NORMAL)
    r = route(s)
    r.init_from_node_mapping({(es1.id, sw1.id), (sw1.id, es2.id)})

    tc.add_to_datastructures(es1, es2, sw1, l1, l2, app, app2, t1_app2, t1, t11, t2, s, r)
    task_graph = PrecedenceGraph.from_applications(tc)

    # Check task_graph node count
    all_stream_tgns = [tgn for tgn in task_graph.nodes.values() if isinstance(tgn, TaskGraphNode_Stream)]
    all_task_tgns = [tgn for tgn in task_graph.nodes.values() if isinstance(tgn, TaskGraphNode_Task)]
    assert len(task_graph.nodes) == 5
    assert len(all_stream_tgns) == 1
    assert len(all_task_tgns) == 4

    # Check task_graph edges
    t1_app2_tgn = task_graph.get_task_tgn(t1_app2.id)
    t1_tgn = task_graph.get_task_tgn(t1.id)
    t11_tgn = task_graph.get_task_tgn(t11.id)
    t2_tgn = task_graph.get_task_tgn(t2.id)
    s_tgn = task_graph.get_stream_tgn(s.id)
    assert task_graph.DAG.has_edge(t1.id, s.id)
    assert task_graph.DAG.has_edge(s.id, t2.id)
    assert not task_graph.DAG.has_edge(t1.id, t2.id)

    # Test heuristic schedule
    heu_sched = heuristic_schedule(tc, task_graph)
    heu_sched.schedule(t1_tgn)
    heu_sched.schedule(t11_tgn)
    heu_sched.schedule(s_tgn)

    # Check block & start_time for t1
    assert sorted(heu_sched.Blocks[t1.src_es_id][t1.period])[0].begin == 0
    assert sorted(heu_sched.Blocks[t1.src_es_id][t1.period])[0].end == 100
    # assert heu_sched.StartTimes[t1_tgn.id][0] == (t1.src_es_id, 0)
    assert heu_sched.StartTimes[t1_tgn.id][0] == 0

    # Check block & start_time for s
    i = 0
    for l in r.get_all_links_dfs(tc):
        assert sorted(heu_sched.Blocks[l.id][s.period])[0].begin == 0
        assert sorted(heu_sched.Blocks[l.id][s.period])[0].end == l1.transmission_length(s.size)
        # assert heu_sched.StartTimes[s_tgn.id][i] == (l.id, 0)
        assert heu_sched.StartTimes[s_tgn.id][i] == 0
        i += 1

    # Check block & start_time for t11
    assert sorted(heu_sched.Blocks[t11.src_es_id][t11.period])[0].begin == 0
    assert sorted(heu_sched.Blocks[t11.src_es_id][t11.period])[0].end == 100
    assert sorted(heu_sched.Blocks[t11.src_es_id][t11.period])[1].begin == 100
    assert sorted(heu_sched.Blocks[t11.src_es_id][t11.period])[1].end == 200
    # assert heu_sched.StartTimes[t11_tgn.id][0] == (t11.src_es_id, 100)
    assert heu_sched.StartTimes[t11_tgn.id][0] == 100


def test_heuristic_schedule_multiple_period():
    tc = Testcase("UnitTestcase")

    es1 = end_system("ES1", 10)
    es2 = end_system("ES2", 10)
    sw1 = switch("SW1")

    l1 = link(f"link_{es1.id}_{sw1.id}", es1, sw1, 12.5)
    l2 = link(f"link_{sw1.id}_{es2.id}", sw1, es2, 12.5)

    app = application("App1", 1000, EApplicationType.NORMAL)
    app2 = application("App2", 500, EApplicationType.NORMAL)
    t1_app2 = task("t1_app2", app2.id, es1.id, 100, app2.period, ETaskType.NORMAL)
    t1 = task("t1", app.id, es1.id, 100, app.period, ETaskType.NORMAL)

    tc.add_to_datastructures(es1, es2, sw1, l1, l2, app, app2, t1_app2, t1)
    task_graph = PrecedenceGraph.from_applications(tc)

    # Check task_graph node count
    all_stream_tgns = [tgn for tgn in task_graph.nodes.values() if isinstance(tgn, TaskGraphNode_Stream)]
    all_task_tgns = [tgn for tgn in task_graph.nodes.values() if isinstance(tgn, TaskGraphNode_Task)]
    assert len(task_graph.nodes) == 2
    assert len(all_stream_tgns) == 0
    assert len(all_task_tgns) == 2

    t1_app2_tgn = task_graph.get_task_tgn(t1_app2.id)
    t1_tgn = task_graph.get_task_tgn(t1.id)

    # Test heuristic schedule
    heu_sched = heuristic_schedule(tc, task_graph)
    heu_sched.schedule(t1_app2_tgn)
    heu_sched.schedule(t1_tgn)

    # Check block & start_time for t1 & t1_app2
    assert sorted(heu_sched.Blocks[t1.src_es_id][t1.period]) == sorted(
        {Interval(0, 100), Interval(100, 200), Interval(500, 600)})
    assert sorted(heu_sched.Blocks[t1_app2.src_es_id][t1_app2.period]) == sorted({Interval(0, 100), Interval(100, 200)})

    # assert heu_sched.StartTimes[t1_app2_tgn.id][0] == (t1.src_es_id, 0)
    assert heu_sched.StartTimes[t1_app2_tgn.id][0] == 0
    # assert heu_sched.StartTimes[t1_tgn.id][0] == (t1.src_es_id, 100)
    assert heu_sched.StartTimes[t1_tgn.id][0] == 100


def test__create_frames_singlecast():
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

    tc.add_to_datastructures(es1, es2, sw1, l1, l2, app,  t1, t2, s, r)
    task_graph = PrecedenceGraph.from_applications(tc)
    t1_tgn = task_graph.get_task_tgn(t1.id)
    t2_tgn = task_graph.get_task_tgn(t2.id)
    s_tgn = task_graph.get_stream_tgn(s.id)

    heu_sched = heuristic_schedule(tc, task_graph)

    # Test t1
    heu_sched.frames[t1_tgn.id] = heu_sched._create_frames(t1_tgn)
    assert t1_tgn.id in heu_sched.frames
    assert t1.src_es_id in heu_sched.frames[t1_tgn.id]
    assert heu_sched.frames[t1_tgn.id][t1.src_es_id].prev_frame is None
    assert len(heu_sched.frames[t1_tgn.id][t1.src_es_id].next_frames) == 0

    # Test s
    heu_sched.frames[s_tgn.id] = heu_sched._create_frames(s_tgn)
    assert s_tgn.id in heu_sched.frames
    for l in r.get_all_links_dfs(tc):
        assert l.id in heu_sched.frames[s_tgn.id]
        for l_prev in r.get_predeccessor_link(l.id, tc):
            assert heu_sched.frames[s_tgn.id][l.id].prev_frame == heu_sched.frames[s_tgn.id][l_prev.id]
        for l_next in r.get_successor_links(l.id, tc):
            assert heu_sched.frames[s_tgn.id][l_next.id] in heu_sched.frames[s_tgn.id][l.id].next_frames

def test__create_frames_multicast():
    tc = Testcase("UnitTestcase")

    es1 = end_system("ES1", 10)
    es2 = end_system("ES2", 10)
    es3 = end_system("ES3", 10)
    sw1 = switch("SW1")

    l1 = link(f"link_{es1.id}_{sw1.id}", es1, sw1, 12.5)
    l2 = link(f"link_{sw1.id}_{es2.id}", sw1, es2, 12.5)
    l3 = link(f"link_{sw1.id}_{es3.id}", sw1, es3, 12.5)

    app = application("App1", 1000, EApplicationType.NORMAL)
    t1 = task("t1", app.id, es1.id, 100, app.period, ETaskType.NORMAL)
    t2 = task("t2", app.id, es2.id, 100, app.period, ETaskType.NORMAL)
    t3 = task("t3", app.id, es3.id, 100, app.period, ETaskType.NORMAL)
    s = stream("s1", app.id, t1.src_es_id, {t2.src_es_id, t3.src_es_id}, t1.id, {t2.id, t3.id}, 100, 1000, 1, False, 78, 0, 22,
               EStreamType.NORMAL)
    r = route(s)
    r.init_from_node_mapping({(es1.id, sw1.id), (sw1.id, es2.id), (sw1.id, es3.id)})

    tc.add_to_datastructures(es1, es2, es3, sw1, l1, l2, l3, app,  t1, t2, t3, s, r)
    task_graph = PrecedenceGraph.from_applications(tc)
    t1_tgn = task_graph.get_task_tgn(t1.id)
    s_tgn = task_graph.get_stream_tgn(s.id)

    heu_sched = heuristic_schedule(tc, task_graph)

    # Test t1
    heu_sched.frames[t1_tgn.id] = heu_sched._create_frames(t1_tgn)
    assert t1_tgn.id in heu_sched.frames
    assert t1.src_es_id in heu_sched.frames[t1_tgn.id]
    assert heu_sched.frames[t1_tgn.id][t1.src_es_id].prev_frame is None
    assert len(heu_sched.frames[t1_tgn.id][t1.src_es_id].next_frames) == 0

    # Test s
    heu_sched.frames[s_tgn.id] = heu_sched._create_frames(s_tgn)
    assert s_tgn.id in heu_sched.frames
    for l in r.get_all_links_dfs(tc):
        assert l.id in heu_sched.frames[s_tgn.id]
        for l_prev in r.get_predeccessor_link(l.id, tc):
            assert heu_sched.frames[s_tgn.id][l.id].prev_frame == heu_sched.frames[s_tgn.id][l_prev.id]
        for l_next in r.get_successor_links(l.id, tc):
            assert heu_sched.frames[s_tgn.id][l_next.id] in heu_sched.frames[s_tgn.id][l.id].next_frames

def test__create_frames_secure():
    tc = Testcase("UnitTestcase")

    es1 = end_system("ES1", 10)
    es2 = end_system("ES2", 10)
    sw1 = switch("SW1")

    l1 = link(f"link_{es1.id}_{sw1.id}", es1, sw1, 12.5)
    l2 = link(f"link_{sw1.id}_{es2.id}", sw1, es2, 12.5)

    app = application("App1", 1000, EApplicationType.NORMAL)
    t1 = task("t1", app.id, es1.id, 100, app.period, ETaskType.NORMAL)
    t2 = task("t2", app.id, es2.id, 100, app.period, ETaskType.NORMAL)
    s = stream("s1", app.id, t1.src_es_id, {t2.src_es_id}, t1.id, {t2.id}, 100, 1000, 1, True, 78, 0, 22,
               EStreamType.NORMAL)
    r = route(s)
    r.init_from_node_mapping({(es1.id, sw1.id), (sw1.id, es2.id)})

    tc.add_to_datastructures(es1, es2, sw1, l1, l2, app,  t1, t2, s, r)
    task_graph = PrecedenceGraph.from_applications(tc)
    t1_tgn = task_graph.get_task_tgn(t1.id)
    s_tgn = task_graph.get_stream_tgn(s.id)

    heu_sched = heuristic_schedule(tc, task_graph)

    # Test t1
    heu_sched.frames[t1_tgn.id] = heu_sched._create_frames(t1_tgn)
    assert t1_tgn.id in heu_sched.frames
    assert t1.src_es_id in heu_sched.frames[t1_tgn.id]
    assert heu_sched.frames[t1_tgn.id][t1.src_es_id].prev_frame is None
    assert len(heu_sched.frames[t1_tgn.id][t1.src_es_id].next_frames) == 0

    # Test s
    heu_sched.frames[s_tgn.id] = heu_sched._create_frames(s_tgn)
    assert s_tgn.id in heu_sched.frames
    for l in r.get_all_es_and_links_dfs(tc):
        assert l.id in heu_sched.frames[s_tgn.id]
        for l_prev in r.get_predeccessor_link(l.id, tc):
            assert heu_sched.frames[s_tgn.id][l.id].prev_frame == heu_sched.frames[s_tgn.id][l_prev.id]
        for l_next in r.get_successor_links(l.id, tc):
            assert heu_sched.frames[s_tgn.id][l_next.id] in heu_sched.frames[s_tgn.id][l.id].next_frames

def test__create_frames_secure_multicast():
    tc = Testcase("UnitTestcase")

    es1 = end_system("ES1", 10)
    es2 = end_system("ES2", 10)
    es3 = end_system("ES3", 10)
    sw1 = switch("SW1")

    l1 = link(f"link_{es1.id}_{sw1.id}", es1, sw1, 12.5)
    l2 = link(f"link_{sw1.id}_{es2.id}", sw1, es2, 12.5)
    l3 = link(f"link_{sw1.id}_{es3.id}", sw1, es3, 12.5)

    app = application("App1", 1000, EApplicationType.NORMAL)
    t1 = task("t1", app.id, es1.id, 100, app.period, ETaskType.NORMAL)
    t2 = task("t2", app.id, es2.id, 100, app.period, ETaskType.NORMAL)
    t3 = task("t3", app.id, es3.id, 100, app.period, ETaskType.NORMAL)
    s = stream("s1", app.id, t1.src_es_id, {t2.src_es_id, t3.src_es_id}, t1.id, {t2.id, t3.id}, 100, 1000, 1, True, 78, 0, 22,
               EStreamType.NORMAL)
    r = route(s)
    r.init_from_node_mapping({(es1.id, sw1.id), (sw1.id, es2.id), (sw1.id, es3.id)})

    tc.add_to_datastructures(es1, es2, es3, sw1, l1, l2, l3, app,  t1, t2, t3, s, r)
    task_graph = PrecedenceGraph.from_applications(tc)
    t1_tgn = task_graph.get_task_tgn(t1.id)
    s_tgn = task_graph.get_stream_tgn(s.id)

    heu_sched = heuristic_schedule(tc, task_graph)

    # Test t1
    heu_sched.frames[t1_tgn.id] = heu_sched._create_frames(t1_tgn)
    assert t1_tgn.id in heu_sched.frames
    assert t1.src_es_id in heu_sched.frames[t1_tgn.id]
    assert heu_sched.frames[t1_tgn.id][t1.src_es_id].prev_frame is None
    assert len(heu_sched.frames[t1_tgn.id][t1.src_es_id].next_frames) == 0

    # Test s
    heu_sched.frames[s_tgn.id] = heu_sched._create_frames(s_tgn)
    assert s_tgn.id in heu_sched.frames
    for l in r.get_all_es_and_links_dfs(tc):
        assert l.id in heu_sched.frames[s_tgn.id]
        for l_prev in r.get_predeccessor_link(l.id, tc):
            assert heu_sched.frames[s_tgn.id][l.id].prev_frame == heu_sched.frames[s_tgn.id][l_prev.id]
        for l_next in r.get_successor_links(l.id, tc):
            assert heu_sched.frames[s_tgn.id][l_next.id] in heu_sched.frames[s_tgn.id][l.id].next_frames