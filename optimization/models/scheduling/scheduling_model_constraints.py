import itertools
import math

from input.model.link import link
from input.model.nodes import end_system, switch
from input.model.stream import EStreamType
from input.model.task import ETaskType, key_verification_task
from utils.utilities import lcm


def add_constraints(model):
    # Streams
    # For each stream
    for f in model.tc.F.values():
        # For each link and node
        for l_or_es_id in model.mtrees[f.id].get_all_es_and_links():
            l_or_es = helper_link_or_node_from_id(model, l_or_es_id)
            assert l_or_es != None

            constrain_stream_end_time_equals_start_plus_exec_time(model, f, l_or_es_id)

            if isinstance(l_or_es, link):
                constrain_stream_exec_time_based_on_link_speed(
                    model, f, l_or_es, l_or_es_id
                )
                constrain_stream_MAC_key_release_interval(model, f, l_or_es_id)
            elif isinstance(l_or_es, end_system) and f.type != EStreamType.KEY:
                # Key streams are not executed on ES
                constrain_stream_exec_time_based_on_ES_hash_speed(model, f, l_or_es_id)

                if l_or_es_id in f.receiver_es_ids:
                    constrain_stream_MAC_verify_after_key_verify(model, f, l_or_es_id)

            constrain_stream_instance_dependency_between_links_on_route(
                model, f, l_or_es_id
            )

            # For each other stream, for which link or ES is on route
            for f2 in model.tc.F.values():
                if f.id != f2.id:
                    if model.mtrees[f2.id].is_in_tree(l_or_es_id):
                        constraint_streams_do_not_overlap(model, f, f2, l_or_es_id)
                        constrain_stream_tsn_frame_isolation(
                            model, f, f2, l_or_es, l_or_es_id
                        )

    # Tasks
    # For each task
    for t in model.tc.T.values():
        constrain_task_end_time_equals_start_plus_exec_time(model, t)
        constrain_task_do_not_overlap(model, t)
        constrain_task_outgoing_stream_dependency(model, t)
        constrain_task_incoming_stream_dependency(model, t)
        constrain_task_task_dependency(model, t)
        constrain_task_does_not_overlap_with_stream_MAC_operations(model, t)

    # Functions Paths
    # For each function path
    for fp in model.tc.FP.values():
        constrain_function_path_deadline(model, fp)


def add_simple_constraints(model):
    # Streams
    # For each stream
    for f in model.tc.F.values():
        # For each link and node
        for l_or_es_id in model.mtrees[f.id].get_all_es_and_links():
            l_or_es = helper_link_or_node_from_id(model, l_or_es_id)
            assert l_or_es != None

            constrain_stream_end_time_equals_start_plus_exec_time(model, f, l_or_es_id)

            if isinstance(l_or_es, link):
                constrain_stream_exec_time_based_on_link_speed(
                    model, f, l_or_es, l_or_es_id
                )
                constrain_stream_MAC_key_release_interval(model, f, l_or_es_id)
            elif isinstance(l_or_es, end_system) and f.type != EStreamType.KEY:
                # Key streams are not executed on ES
                constrain_stream_exec_time_based_on_ES_hash_speed(model, f, l_or_es_id)

                if l_or_es_id in f.receiver_es_ids:
                    constrain_stream_MAC_verify_after_key_verify(model, f, l_or_es_id)

            constrain_stream_instance_dependency_between_links_on_route(
                model, f, l_or_es_id
            )

            # For each other stream, for which link or ES is on route
            for f2 in model.tc.F.values():
                if f.id != f2.id:
                    if model.mtrees[f2.id].is_in_tree(l_or_es_id):
                        constraint_streams_do_not_overlap(model, f, f2, l_or_es_id)
                        constrain_stream_tsn_frame_isolation(
                            model, f, f2, l_or_es, l_or_es_id
                        )

    # Tasks
    # For each task
    for t in model.tc.T.values():
        constrain_task_end_time_equals_start_plus_exec_time(model, t)
        constrain_task_do_not_overlap(model, t)
        constrain_task_outgoing_stream_dependency(model, t)
        constrain_task_incoming_stream_dependency(model, t)
        constrain_task_task_dependency(model, t)
        constrain_task_does_not_overlap_with_stream_MAC_operations(model, t)

    # Functions Paths
    # For each function path
    for fp in model.tc.FP.values():
        # No deadline constraint for simple optimization
        # constrain_function_path_deadline(fp)
        pass


def constrain_stream_tsn_frame_isolation(model, f, f2, l_or_n, l_or_n_id):
    # Constrain X: TSN Frame Isolation
    # if link originates at switch
    if isinstance(l_or_n, link):
        if isinstance(l_or_n.src, switch):
            if f2.id != f.id:
                for l_prev_id in model.mtrees[f.id].get_predeccessor_links(l_or_n_id):
                    for l_prev2_id in model.mtrees[f2.id].get_predeccessor_links(
                        l_or_n_id
                    ):
                        if l_prev_id != l_prev2_id:
                            o_m_g = model.o_f[l_or_n_id][f.id]
                            o_m_g_prev = model.o_f[l_prev_id][f.id]
                            P_m = f.period

                            o_m2_g = model.o_f[l_or_n_id][f2.id]
                            o_m2_g_prev2 = model.o_f[l_prev2_id][f2.id]
                            P_m2 = f2.period

                            rg_a = range(int(lcm([P_m, P_m2]) / P_m))
                            rg_b = range(int(lcm([P_m, P_m2]) / P_m2))

                            for alph in rg_a:
                                for beta in rg_b:
                                    # For each pair of frame instances
                                    bl = model.model.NewBoolVar(
                                        "bl_fcstrt_{}_{}_{}_{}_{}".format(
                                            l_or_n_id, f.id, alph, f2.id, beta
                                        )
                                    )

                                    # Constraint 29 (TSN)
                                    model.model.Add(
                                        o_m2_g + alph * P_m2 <= o_m_g_prev + beta * P_m
                                    ).OnlyEnforceIf(bl)

                                    # Constraint 30 (TSN)
                                    model.model.Add(
                                        o_m_g + beta * P_m <= o_m2_g_prev2 + alph * P_m2
                                    ).OnlyEnforceIf(bl.Not())


def constrain_function_path_deadline(model, fp):
    # Constraint 1: Function path deadlines are held (42)
    des_t = fp.path[-1]
    src_t = fp.path[0]

    a_t_des = model.a_t[des_t.id]
    o_t_src = model.o_t[src_t.id]
    D = fp.deadline
    model.model.Add(a_t_des - o_t_src <= D)


def constrain_task_does_not_overlap_with_stream_MAC_operations(model, t):
    # Constraint 4: tasks do not overlap with stream MAC generation/verification
    for f in itertools.chain(
        model.tc.F_g_in[t.src_es_id], model.tc.F_g_out[t.src_es_id]
    ):
        P_f_m = model.tc.F[f.id].period
        P_t_i = model.tc.T[t.id].app_period

        rg_a = range(int(lcm([P_t_i, P_f_m]) / P_t_i))
        rg_b = range(int(lcm([P_t_i, P_f_m]) / P_f_m))

        o_t = model.o_t[t.id]
        a_t = model.a_t[t.id]

        o_f_g = model.o_f[t.src_es_id][f.id]
        a_f_g = model.a_f[t.src_es_id][f.id]

        for alph in rg_a:
            for beta in rg_b:
                bl = model.model.NewBoolVar(
                    "bl_{}_{}_{}_{}_{}".format(t.src_es_id, t.id, alph, f.id, beta)
                )

                # Constraint 40
                model.model.Add(
                    alph * P_t_i + a_t <= beta * P_f_m + o_f_g
                ).OnlyEnforceIf(bl)

                # Constraint 41
                model.model.Add(
                    beta * P_f_m + a_f_g <= alph * P_t_i + o_t
                ).OnlyEnforceIf(bl.Not())


def constrain_task_incoming_stream_dependency(model, t):
    # Constraint 3.2: incoming dependency between stream and task
    for f in model.tc.F_t_in[t.id]:
        model.model.Add(model.a_f[t.src_es_id][f.id] <= model.o_t[t.id])


def constrain_task_outgoing_stream_dependency(model, t):
    # Constraint 3.1: outgoing dependency between task and stream
    for f in model.tc.F_t_out[t.id]:
        model.model.Add(model.a_t[t.id] <= model.o_f[t.src_es_id][f.id])


def constrain_task_task_dependency(model, t):
    # Constraint 3.2 dependency between tasks, modeled by signals
    for group_id in t.groups:
        for s in model.tc.S_group[group_id]:
            assert t.id == s.src_task_id
            model.model.Add(model.a_t[t.id] <= model.o_t[s.dest_task_id])


def constrain_task_do_not_overlap(model, t):
    # Constraint 2: tasks do not overlap with other tasks
    for t2 in model.tc.T_g[t.src_es_id]:
        if t.id != t2.id:
            P_i = t.app_period
            P_i2 = t2.app_period

            rg_a = range(int(lcm([P_i, P_i2]) / P_i))
            rg_b = range(int(lcm([P_i, P_i2]) / P_i2))

            a_i = model.a_t[t.id]
            a_i2 = model.a_t[t2.id]

            for alph in rg_a:
                for beta in rg_b:
                    bl = model.model.NewBoolVar(
                        "bl_{}_{}_{}_{}".format(t.id, alph, t2.id, beta)
                    )
                    model.model.Add(
                        alph * P_i + a_i <= beta * P_i2 + a_i2
                    ).OnlyEnforceIf(bl)

                    model.model.Add(
                        beta * P_i2 + a_i2 <= alph * P_i + a_i
                    ).OnlyEnforceIf(bl.Not())


def constrain_task_end_time_equals_start_plus_exec_time(model, t):
    # Constraint 1: a_t = o_t + t.wcet
    model.model.Add(model.a_t[t.id] == model.o_t[t.id] + t.exec_time)


def helper_link_or_node_from_id(model, l_or_n_id):
    l_or_n = None
    if l_or_n_id in model.tc.L:
        l_or_n = model.tc.L[l_or_n_id]
    elif l_or_n_id in model.tc.N:
        l_or_n = model.tc.N[l_or_n_id]
    return l_or_n


def constrain_stream_end_time_equals_start_plus_exec_time(model, f, l_or_n_id):
    # Constraint 3: a_f = o_f + c_f (21)
    model.model.Add(
        model.a_f[l_or_n_id][f.id]
        == model.o_f[l_or_n_id][f.id] + model.c_f[l_or_n_id][f.id]
    )


def constraint_streams_do_not_overlap(model, f, f2, l_or_n_id):
    # Constraint 5: streams do not overlap on link or node (23,24)
    if f.id != f2.id:
        P_f_m = model.tc.F[f.id].period
        P_f_m2 = model.tc.F[f2.id].period

        rg_a = range(int(lcm([P_f_m, P_f_m2]) / P_f_m))
        rg_b = range(int(lcm([P_f_m, P_f_m2]) / P_f_m2))

        a_m_g = model.a_f[l_or_n_id][f.id]
        a_m2_g = model.a_f[l_or_n_id][f2.id]

        o_m_g = model.o_f[l_or_n_id][f.id]
        o_m2_g = model.o_f[l_or_n_id][f2.id]

        for alph in rg_a:
            for beta in rg_b:
                bl = model.model.NewBoolVar(
                    "bl_{}_{}_{}_{}_{}".format(l_or_n_id, f.id, alph, f2.id, beta)
                )
                model.model.Add(
                    alph * P_f_m + a_m_g <= beta * P_f_m2 + o_m2_g
                ).OnlyEnforceIf(bl)

                model.model.Add(
                    beta * P_f_m2 + a_m2_g <= alph * P_f_m + o_m_g
                ).OnlyEnforceIf(bl.Not())


def constrain_stream_instance_dependency_between_links_on_route(model, f, l_or_n_id):
    # Constraint 4: a_f_l1 < o_f_l2 if l2 is after l1 on route (22)
    successor_links = model.mtrees[f.id].get_successor_links(l_or_n_id)
    for l2_id in successor_links:
        model.model.Add(model.a_f[l_or_n_id][f.id] <= model.o_f[l2_id][f.id])


def constrain_stream_MAC_verify_after_key_verify(model, f, l_or_n_id):
    # Constraint 6: stream MAC verification starts after key verification
    for t in model.tc.T_sec_g[l_or_n_id]:
        if t.type == ETaskType.KEY_VERIFICATION and isinstance(t, key_verification_task):
            if t.corr_release_task_es_id == f.sender_es_id:
                a_t = model.a_t[t.id]
                phi_f = model.phi_f[f.id]
                o_f_g = model.o_f[l_or_n_id][f.id]
                model.model.Add(o_f_g >= a_t + phi_f * model.Pint)


def constrain_stream_exec_time_based_on_ES_hash_speed(model, f, l_or_n_id):
    # Constraint 2.1: c_f = n.mac_exec_time
    if f.is_secure:
        model.model.Add(
            model.c_f[l_or_n_id][f.id] == model.tc.ES[l_or_n_id].mac_exec_time
        )


def constrain_stream_MAC_key_release_interval(model, f, l_or_n_id):
    # Constraint 7: MAC release interval is after the interval where the steam is transmitted to the receiver ES (38)
    if (
        next(iter(model.mtrees[f.id].get_successor_links(l_or_n_id)))
        in f.receiver_es_ids
        and f.is_secure
    ):
        a_m_g = model.a_f[l_or_n_id][f.id]
        div = model.model.NewIntVar(
            0,
            int(model.tc.hyperperiod / model.Pint),
            "div_{}_{}".format(f.id, l_or_n_id),
        )
        model.model.AddDivisionEquality(div, a_m_g, model.Pint)

        model.model.Add(div < model.phi_f[f.id])


def constrain_stream_exec_time_based_on_link_speed(model, f, l_or_n, l_or_n_id):
    # Constraint 2: c_f = f.size/l.speed (18,19)
    f_size_times_1000 = f.size * 1000
    l_speed_times_1000 = int(l_or_n.speed * 1000)

    div = math.ceil(f_size_times_1000 / l_speed_times_1000)
    model.model.Add(model.c_f[l_or_n_id][f.id] == div)


def _constrain_stream_is_zero_outside_route(model, f, l_or_n_id):
    # Constraint 1: o_f, c_f, a_f = 0 for all links not on route (17)
    model.model.Add(model.o_f[l_or_n_id][f.id] == 0)
    model.model.Add(model.c_f[l_or_n_id][f.id] == 0)
    model.model.Add(model.a_f[l_or_n_id][f.id] == 0)
