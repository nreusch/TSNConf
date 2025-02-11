from ortools.sat.python.cp_model import Domain

from input.model.nodes import end_system
from input.model.stream import EStreamType

# TODO: support streams between unmapped tasks becoming self-streams, i.e. eliminated

def add_constraints(model, redundancy, allow_overlap):
    # HELPER CONSTRAINTS
    for f_int in range(model.max_stream_int):
        for v_int in range(model.max_node_int):
            f = model.tc.F_routed[model._IntToStreamIDMap[f_int]]

            # bool: node v is sender ES of f
            v_is_f_sender = model.f_sender_is_v[f_int][v_int]
            v_is_f_rcvr = model.f_rcvr_is_v[f_int][v_int]

            model.model.Add(v_int == model.m_t[f.sender_task_id]).OnlyEnforceIf(v_is_f_sender)
            model.model.Add(v_int != model.m_t[f.sender_task_id]).OnlyEnforceIf(
                v_is_f_sender.Not()
            )

            # bools: node v is receiver ES of f
            model.model.Add(v_int == model.m_t[list(f.receiver_task_ids.keys())[0]]).OnlyEnforceIf(v_is_f_rcvr)
            model.model.Add(v_int != model.m_t[list(f.receiver_task_ids.keys())[0]]).OnlyEnforceIf(
                v_is_f_rcvr.Not()
            ) # TODO: Support multicast

    for f_int in range(model.max_stream_int):
        for v_int in range(model.max_node_int):
            f = model.tc.F_routed[model._IntToStreamIDMap[f_int]]
            v = model.tc.N[model._IntToNodeIDMap[v_int]]

            x_v_has_s = model.x_v_has_successor[f_int][v_int]
            if isinstance(v, end_system):
                # Sender and Receivers have guaranteed successor
                # Sender: x(v) = v, y(v) = 0
                # Receivers: x(v) != -1

                v_is_f_sender = model.f_sender_is_v[f_int][v_int]
                v_is_f_rcvr = model.f_rcvr_is_v[f_int][v_int]

                # Stream sender has itself as successor

                model.model.Add(x_v_has_s == 1).OnlyEnforceIf(v_is_f_sender)
                model.model.Add(model.x[f_int][v_int] == v_int).OnlyEnforceIf(v_is_f_sender)
                model.model.Add(model.y[f_int][v_int] == 0).OnlyEnforceIf(v_is_f_sender)

                # Stream receivers have successors
                model.model.Add(x_v_has_s == 1).OnlyEnforceIf(v_is_f_rcvr)
                model.model.Add(model.x[f_int][v_int] != -1).OnlyEnforceIf(
                    x_v_has_s
                ).OnlyEnforceIf(v_is_f_rcvr)

                # Other ES have no successors
                model.model.Add(model.x[f_int][v_int] == -1).OnlyEnforceIf(v_is_f_rcvr.Not()).OnlyEnforceIf(v_is_f_sender.Not())
                # ???
                """ without task mapping:
                if v.id == f.sender_es_id:
                    model.model.Add(x_v_has_s == 1)
                    model.model.Add(model.x[f_int][v_int] == v_int)
                    model.model.Add(model.y[f_int][v_int] == 0)
                elif v.id in f.receiver_es_ids:
                    model.model.Add(x_v_has_s == 1)
                    model.model.Add(model.x[f_int][v_int] != -1).OnlyEnforceIf(
                        x_v_has_s
                    )
                else:
                    # All other ES have guaranteed no successor
                    model.model.Add(x_v_has_s == 0)
                    model.model.Add(model.x[f_int][v_int] == -1).OnlyEnforceIf(
                        x_v_has_s.Not()
                    )
                """
            else:
                # All switches can, but don't have to have a successor
                model.model.Add(model.x[f_int][v_int] != -1).OnlyEnforceIf(x_v_has_s)
                model.model.Add(model.x[f_int][v_int] == -1).OnlyEnforceIf(
                    x_v_has_s.Not()
                )

            model.x_v_has_successor[f_int][v_int] = x_v_has_s

    # TASK MAPPING CONSTRAINTS
    i = 0
    for t_id, t in model.tc.T.items():
        # tasks may only be mapped to allowed_assignment nodes
        if t.src_es_id == "":
            for n_id in model.tc.N.keys():
                if n_id not in t.allowed_assignments:
                    model.model.Add(model.m_t[t_id] != model._NodeIDToIntMap[n_id])

        for v_int in range(model.max_node_int):
            v = model.tc.N[model._IntToNodeIDMap[v_int]]
            wcet_factor = 1
            if v.id in model.tc.ES:
                wcet_factor = model.tc.ES[v.id].wcet_factor
            t_mapped_ES_is_v = model.t_mapped_ES_is_v[t_id][v_int]
            model.model.Add(model.m_t[t_id] == v_int).OnlyEnforceIf(t_mapped_ES_is_v)
            model.model.Add(model.m_t[t_id] != v_int).OnlyEnforceIf(t_mapped_ES_is_v.Not())

            model.model.Add(
                model.ES_capc_use_of_t[v_int][i]
                == int((t.exec_time / t.period) * wcet_factor * 1000)
            ).OnlyEnforceIf(t_mapped_ES_is_v)
            model.model.Add(
                model.ES_capc_use_of_t[v_int][i]
                == 0
            ).OnlyEnforceIf(t_mapped_ES_is_v.Not())

        i += 1

    for v_int in range(model.max_node_int):
        model.model.Add(
            model.ES_capacity[v_int]
            == sum(model.ES_capc_use_of_t[v_int])
        )

        # ES capcity may not be exceeded
        if model._IntToNodeIDMap[v_int] in model.tc.ES:
            model.model.Add(
                model.ES_capacity[v_int]
                <= (int)(model.tc.ES[model._IntToNodeIDMap[v_int]].max_utilization * 1000)
            )


    # NORMAL CONSTRAINTS
    for f_int in range(model.max_stream_int):
        model.x_v_is_not_u.append([])  #
        model.x_v_is_u.append([])
        model.x_v_is_u_and_uses_bandwidth.append([])
        for v_int in range(model.max_node_int):
            model.x_v_is_not_u[f_int].append([])  #
            model.x_v_is_u[f_int].append([])  #
            model.x_v_is_u_and_uses_bandwidth[f_int].append([])
            f = model.tc.F_routed[model._IntToStreamIDMap[f_int]]
            v = model.tc.N[model._IntToNodeIDMap[v_int]]

            v_is_f_sender = model.f_sender_is_v[f_int][v_int]


            # Constraint 1: x(v) != -1 => y(v) = y(x(v)) + 1 -> Avoid cycles
            if v.id != f.sender_es_id:
                # necessary, because otherwise AddElement breaks if the possible domain of a node is only -1
                if (
                    len(model.x_v_possible_domain[f.id][v.id]) > 1
                    or model.x_v_possible_domain[f.id][v.id][0] != -1
                ):
                    x_v = model.model.NewIntVarFromDomain(
                        Domain.FromValues(model.x_v_possible_domain[f.id][v.id]),
                        "x_{}({})_temp".format(f.id, v.id),
                    )
                    model.model.Add(x_v == model.x[f_int][v_int]).OnlyEnforceIf(
                        model.x_v_has_successor[f_int][v_int]
                    )
                    y_of_x_v = model.model.NewIntVar(
                        -1, model.max_node_int, "y(x({}))_{}".format(v.id, f.id)
                    )

                    model.model.AddElement(x_v, model.y[f_int], y_of_x_v)

                    y_v_is_y_x_v_plus_1 = model.model.NewBoolVar(
                        "y({})_f_plus_one".format(v.id, f.id)
                    )
                    model.model.Add(
                        model.y[f_int][v_int] == y_of_x_v + 1
                    ).OnlyEnforceIf(y_v_is_y_x_v_plus_1)
                    model.model.Add(
                        model.y[f_int][v_int] != y_of_x_v + 1
                    ).OnlyEnforceIf(y_v_is_y_x_v_plus_1.Not())

                    model.model.AddImplication(
                        model.x_v_has_successor[f_int][v_int], y_v_is_y_x_v_plus_1
                    ).OnlyEnforceIf(v_is_f_sender.Not())

            # Constraint 2: x(u) == -1 => x(v) != u
            # If a node has no successor, it has no predecessor
            # Also means: x(v) == u => x(u) != -1 (Contrapositive) (a => b, !b => !a)
            # If a node has a predecessor, it has a successor
            for u_int in range(model.max_node_int):
                u = model.tc.N[model._IntToNodeIDMap[u_int]]
                x_u_has_successor = model.x_v_has_successor[f_int][u_int]
                x_v_is_u = model.x_v_is_u[f_int][v_int][u_int]
                x_v_is_not_u = model.x_v_is_not_u[f_int][v_int][u_int]

                model.model.Add(model.x[f_int][v_int] != u_int).OnlyEnforceIf(
                    x_v_is_not_u
                )
                model.model.Add(model.x[f_int][v_int] == u_int).OnlyEnforceIf(x_v_is_u)

                x_v_is_u_and_uses_bandwidth = model.x_v_is_u_and_uses_bandwidth[f_int][
                    v_int
                ][u_int]
                model.model.Add(x_v_is_u_and_uses_bandwidth == 0).OnlyEnforceIf(
                    x_v_is_not_u
                )

                # For each redundant copy of a stream, create a list of the x_v_is_u_and_uses_bandwidth boolean variables, and set their sum to 1
                # This will only allow one of the redundant copies to use bandwidth on a link
                # sum(x_v_is_u_list) > 0 => sum(x_v_is_u_and_uses_bw)  == 1
                x_v_is_u_and_uses_bandwidth_list = [x_v_is_u_and_uses_bandwidth]
                x_v_is_u_list = [x_v_is_u]

                if redundancy:
                    if f.rl > 1:
                        for f_2 in model.tc.F_red[f.get_id_prefix()]:
                            if f_2.id != f.id:
                                f2_int = model._StreamIDToIntMap[f_2.id]
                                x_v_is_u_and_uses_bandwidth_list.append(
                                    model.x_v_is_u_and_uses_bandwidth[f2_int][v_int][u_int]
                                )
                                x_v_is_u_list.append(model.x_v_is_u[f2_int][v_int][u_int])
                stream_uses_link = model.model.NewBoolVar(
                    "sum_of_x_{}({})_is_{}_is_greater_0".format(f_int, v_int, u_int)
                )
                exactly_one_copy_uses_bw = model.model.NewBoolVar(
                    "sum_of_x_{}({})_is_{}_and_uses_bw_is_1".format(f_int, v_int, u_int)
                )
                model.model.Add(sum(x_v_is_u_list) > 0).OnlyEnforceIf(stream_uses_link)
                model.model.Add(sum(x_v_is_u_list) == 0).OnlyEnforceIf(
                    stream_uses_link.Not()
                )
                model.model.Add(
                    sum(x_v_is_u_and_uses_bandwidth_list) == 1
                ).OnlyEnforceIf(exactly_one_copy_uses_bw)
                model.model.Add(
                    sum(x_v_is_u_and_uses_bandwidth_list) == 0
                ).OnlyEnforceIf(exactly_one_copy_uses_bw.Not())
                model.model.AddImplication(stream_uses_link, exactly_one_copy_uses_bw)

                # Constraint 7.1: Streams may not exceed link capacity
                # if f is not using the link, capacity use is 0
                model.model.Add(
                    model.v_to_u_capc_use_of_f[v_int][u_int][f_int] == 0
                ).OnlyEnforceIf(x_v_is_not_u)
                model.model.Add(
                    model.v_to_u_capc_use_of_f[v_int][u_int][f_int] == 0
                ).OnlyEnforceIf(x_v_is_u_and_uses_bandwidth.Not())
                # if there is link from u to v
                if (
                    u.id in model.tc.N_conn_inv[v.id]
                    and v.id in model.tc.L_from_nodes[u.id]
                ):
                    period = f.period

                    model.model.Add(
                        model.v_to_u_capc_use_of_f[v_int][u_int][f_int]
                        == int((f.size / period) * 1000)
                    ).OnlyEnforceIf(x_v_is_u).OnlyEnforceIf(x_v_is_u_and_uses_bandwidth)

                model.model.AddImplication(x_u_has_successor.Not(), x_v_is_not_u)

            # Constraint 6: Redundant copies of each streams should not have common links

            if redundancy and not allow_overlap:
                if f.rl > 1:
                    if v.id != f.sender_es_id:
                        for f_2 in model.tc.F_red[f.get_id_prefix()]:
                            if f_2.id != f.id:
                                f_2_int = model._StreamIDToIntMap[f_2.id]
                                model.model.Add(
                                    model.x[f_int][v_int] != model.x[f_2_int][v_int]
                                ).OnlyEnforceIf(
                                    model.x_v_has_successor[f_int][v_int]
                                ).OnlyEnforceIf(
                                    model.x_v_has_successor[f_2_int][v_int]
                                ).OnlyEnforceIf(
                                    model.v_is_f_sender[f_int][v_int].Not()
                                )

    # Constraint 7.2: Streams may not exceed link capacity (upper bound is implicit through link_capacity domain)
    for v_int in range(model.max_node_int):
        for u_int in range(model.max_node_int):
            model.model.Add(
                model.link_capacity[v_int][u_int]
                == sum(model.v_to_u_capc_use_of_f[v_int][u_int])
            )

    for f_int in range(model.max_stream_int):
        f = model.tc.F_routed[model._IntToStreamIDMap[f_int]]
        for u_int in range(model.max_node_int):
            u = model.tc.N[model._IntToNodeIDMap[u_int]]

            x_v_is_u_list = [
                model.x_v_is_u[f_int][v_int][u_int]
                for v_int in range(model.max_node_int)
            ]

            u_is_f_rcvr = model.f_rcvr_is_v[f_int][u_int]

            model.model.Add(sum(x_v_is_u_list) == 0).OnlyEnforceIf(
                model.x_v_has_predecessor[f_int][u_int].Not()
            )
            model.model.Add(sum(x_v_is_u_list) > 0).OnlyEnforceIf(
                model.x_v_has_predecessor[f_int][u_int]
            )

            x_u_has_successor = model.x_v_has_successor[f_int][u_int]
            # If u has no predecessors, it can't have successor, if it's not the receiver of f
            model.model.AddImplication(
                model.x_v_has_predecessor[f_int][u_int].Not(),
                x_u_has_successor.Not(),
            ).OnlyEnforceIf(u_is_f_rcvr.Not())

            # if u is f receiver, it has no predecessors
            model.model.Add(model.x_v_has_predecessor[f_int][u_int] == 0).OnlyEnforceIf(u_is_f_rcvr)


            """ without task mapping
            if not u.id in f.receiver_es_ids:

                model.model.Add(sum(x_v_is_u_list) == 0).OnlyEnforceIf(
                    model.x_v_has_predecessor[f_int][u_int].Not()
                )
                model.model.Add(sum(x_v_is_u_list) > 0).OnlyEnforceIf(
                    model.x_v_has_predecessor[f_int][u_int]
                )


                x_u_has_successor = model.x_v_has_successor[f_int][u_int]
                # If u has no predecessors, it can't have successor
                model.model.AddImplication(
                    model.x_v_has_predecessor[f_int][u_int].Not(),
                    x_u_has_successor.Not(),
                )
            else:
                model.model.Add(model.x_v_has_predecessor[f_int][u_int] == 0)
            """
