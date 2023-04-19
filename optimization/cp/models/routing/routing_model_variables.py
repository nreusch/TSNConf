
from ortools.sat.python.cp_model import Domain

def init_optimization_variables(model, existing_routes = None):
    # task mapping
    for t_id, t in model.tc.T.items():
        if t.src_es_id != "":
            model.m_t[t_id] = model.model.NewConstant(model._NodeIDToIntMap[t.src_es_id])
        else:
            model.m_t[t_id] = model.model.NewIntVar(0, model.max_node_int-1, "m_{}".format(t_id))


        model.t_mapped_ES_is_v[t_id] = []
        for v_int in range(model.max_node_int):
            model.t_mapped_ES_is_v[t_id].append(model.model.NewBoolVar(f"{t_id}_is_mapped_on_{v_int}"))

    # link capacity
    for v_int in range(model.max_node_int):
        v_id = model._IntToNodeIDMap[v_int]

        model.ES_capacity.append(model.model.NewIntVar(0,1000, f"capac_{v_id}"))

        model.ES_capc_use_of_t.append([])
        for t_id, t in model.tc.T.items():
            if t.src_es_id == model._IntToNodeIDMap[v_int]:
                model.ES_capc_use_of_t[v_int].append(model.model.NewConstant(int((t.exec_time / t.period) * 1000)))
            else:
                model.ES_capc_use_of_t[v_int].append(model.model.NewIntVar(0, 1000, f"ES_capac_use_of_{t_id}_on_{v_int}"))

        model.v_to_u_capc_use_of_f.append([])
        model.link_capacity.append([])
        for u_int in range(model.max_node_int):
            model.v_to_u_capc_use_of_f[v_int].append([])
            u_id = model._IntToNodeIDMap[u_int]

            if (
                    u_id in model.tc.N_conn_inv[v_id]
                    and v_id in model.tc.L_from_nodes[u_id]
            ):
                # If there is link from u to v
                l = model.tc.L_from_nodes[u_id][v_id]
                model.link_capacity[v_int].append(
                    model.model.NewIntVar(
                        0, (int)(l.speed * 1000), "capac_v({})_u({})".format(v_id, u_id)
                    )
                )

                for f_int in range(model.max_stream_int):
                    f_id = model._IntToStreamIDMap[f_int]
                    model.v_to_u_capc_use_of_f[v_int][u_int].append(
                        model.model.NewIntVar(
                            0,
                            (int)(l.speed * 1000),
                            "capac_v({})_u({})_f({})".format(v_id, u_id, f_id),
                        )
                    )
            else:
                model.link_capacity[v_int].append(model.model.NewConstant(0))

                for f_int in range(model.max_stream_int):
                    model.v_to_u_capc_use_of_f[v_int][u_int].append(
                        model.model.NewConstant(0)
                    )

    # x,y, ...
    for f_int in range(model.max_stream_int):
        f = model.tc.F_routed[model._IntToStreamIDMap[f_int]]
        model.f_sender_is_v.append([])
        model.f_rcvr_is_v.append([])
        model.x.append([])
        model.y.append([])
        model.x_v_has_successor.append([])
        model.x_v_is_u.append([])
        model.x_v_is_not_u.append([])
        model.x_v_is_u_and_uses_bandwidth.append([])
        model.x_v_has_predecessor.append([])
        model.x_v_possible_domain_ids[f.id] = {}
        model.x_v_possible_domain[f.id] = {}
        for v_int in range(model.max_node_int):
            model.x_v_is_u[f_int].append([])
            model.x_v_is_not_u[f_int].append([])
            model.x_v_is_u_and_uses_bandwidth[f_int].append([])

            # f_sender_is_v
            model.f_sender_is_v[f_int].append(
                model.model.NewBoolVar("{}_sender_is_{}".format(f_int, v_int))
            )

            # f_rcvr_is_v
            model.f_rcvr_is_v[f_int].append(
                model.model.NewBoolVar("{}_rcvr_is_{}".format(f_int, v_int))
            )

            x_u_has_no_pred = model.model.NewBoolVar(
                "x_{}_{}_has_no_pred".format(f_int, v_int)
            )
            model.x_v_has_predecessor[f_int].append(x_u_has_no_pred)
            v = model.tc.N[model._IntToNodeIDMap[v_int]]

            # x
            possible_domain = [-1]
            possible_domain_strings = ["-1"]

            for u_int in range(model.max_node_int):
                x_v_is_not_u = model.model.NewBoolVar(
                    "x_{}({})_is_not_{}".format(f_int, v_int, u_int)
                )
                x_v_is_u = x_v_is_not_u.Not()
                model.x_v_is_not_u[f_int][v_int].append(x_v_is_not_u)
                model.x_v_is_u[f_int][v_int].append(x_v_is_u)

                x_v_is_u_and_uses_bandwidth = model.model.NewBoolVar(
                    "x_{}({})_is_{}_and_uses_bandwidth".format(f_int, v_int, u_int)
                )
                model.x_v_is_u_and_uses_bandwidth[f_int][v_int].append(
                    x_v_is_u_and_uses_bandwidth
                )

            for u_id in model.tc.N_conn_inv[v.id]:
                if u_id == v.id:
                    if v.id == f.sender_es_id or f.sender_es_id == "":
                        # Only append node itself for sender
                        possible_domain.append(model._NodeIDToIntMap[u_id])
                        possible_domain_strings.append(u_id)
                else:
                    possible_domain.append(model._NodeIDToIntMap[u_id])
                    possible_domain_strings.append(u_id)
            model.x[f_int].append(
                model.model.NewIntVarFromDomain(
                    Domain.FromValues(possible_domain), "x_{}({})".format(f.id, v.id)
                )
            )
            model.x_v_possible_domain[f.id][v.id] = possible_domain
            model.x_v_possible_domain_ids[f.id][v.id] = possible_domain_strings

            # y
            model.y[f_int].append(
                model.model.NewIntVar(
                    -1, model.max_node_int, "y_{}({})".format(f.id, v.id)
                )
            )
            # has_successor
            x_v_has_s = model.model.NewBoolVar(
                "x({})_{}_has_successor".format(v.id, f.id)
            )
            model.x_v_has_successor[f_int].append(x_v_has_s)


def init_helper_variables(model, existing_routes):
    int_id = 0
    for f_id in model.tc.F_routed.keys():
        if existing_routes != None:
            if f_id in existing_routes:
                continue
        model._StreamIDToIntMap[f_id] = int_id
        model._IntToStreamIDMap[int_id] = f_id
        int_id += 1
    model.max_stream_int = int_id
    int_id = 0
    for n_id in model.tc.N.keys():
        model._NodeIDToIntMap[n_id] = int_id
        model._IntToNodeIDMap[int_id] = n_id
        int_id += 1
    model.max_node_int = int_id
