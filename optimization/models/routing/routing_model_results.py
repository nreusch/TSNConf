def generate_result_structures(model, solver):
    x_res = {}
    y_res = {}
    link_weight_res = {}
    stream_weight_res = {}
    has_successor_res = {}
    link_capacity_res = {}
    capac_use_res = {}
    x_v_is_not_u_res = {}
    x_v_is_u_res = {}
    x_v_is_u_and_uses_bw_res = {}
    x_u_has_no_pred = {}
    stream_cost_res = {}

    # Read results

    solver.Value(model.total_cost)

    for f_id in model.tc.F.keys():
        x_res[
            f_id
        ] = {}  # x_res[f_id][n1_id] = n2_id, stream f_id uses link for n2_id to n1_id
        y_res[f_id] = {}
        link_weight_res[f_id] = {}
        has_successor_res[f_id] = {}
        x_v_is_not_u_res[f_id] = {}
        x_v_is_u_res[f_id] = {}
        x_v_is_u_and_uses_bw_res[f_id] = {}
        x_u_has_no_pred[f_id] = {}

        stream_cost_res[f_id] = solver.Value(model.stream_cost[f_id])

        for n_id in model.tc.N.keys():
            x_v_is_not_u_res[f_id][n_id] = {}
            x_v_is_u_res[f_id][n_id] = {}
            x_v_is_u_and_uses_bw_res[f_id][n_id] = {}
            f_int = model._StreamIDToIntMap[f_id]
            n_int = model._NodeIDToIntMap[n_id]

            x_u_has_no_pred[f_id][n_id] = solver.Value(
                model.x_v_has_predecessor[f_int][n_int]
            )
            if len(model.link_weights) > 0:
                link_weight_res[f_id][n_id] = solver.Value(
                    model.link_weights[f_id][n_id]
                )
            if len(model.stream_route_lens) > 0:
                stream_weight_res[f_id] = solver.Value(model.stream_route_lens[f_id])

            has_successor_res[f_id][n_id] = solver.Value(
                model.x_v_has_successor[f_int][n_int]
            )
            y_res[f_id][n_id] = solver.Value(model.y[f_int][n_int])

            val = solver.Value(model.x[f_int][n_int])
            if val != -1:
                x_res[f_id][n_id] = model._IntToNodeIDMap[
                    solver.Value(model.x[f_int][n_int])
                ]
            else:
                x_res[f_id][n_id] = -1

            for n2_id in model.tc.N.keys():
                n2_int = model._NodeIDToIntMap[n2_id]
                x_v_is_not_u_res[f_id][n_id][n2_id] = solver.Value(
                    model.x_v_is_not_u[f_int][n_int][n2_int]
                )
                x_v_is_u_res[f_id][n_id][n2_id] = solver.Value(
                    model.x_v_is_u[f_int][n_int][n2_int]
                )
                x_v_is_u_and_uses_bw_res[f_id][n_id][n2_id] = solver.Value(
                    model.x_v_is_u_and_uses_bandwidth[f_int][n_int][n2_int]
                )

    for n_id in model.tc.N.keys():
        link_capacity_res[n_id] = {}
        capac_use_res[n_id] = {}
        for conn_n_id in model.tc.N_conn[n_id]:
            capac_use_res[n_id][conn_n_id] = {}
            n_int = model._NodeIDToIntMap[n_id]
            conn_n_int = model._NodeIDToIntMap[conn_n_id]

            for f_id in model.tc.F.keys():
                f_int = model._StreamIDToIntMap[f_id]
                capac_use_res[n_id][conn_n_id][f_id] = solver.Value(
                    model.v_to_u_capc_use_of_f[conn_n_int][n_int][f_int]
                )

            link_capacity_res[n_id][conn_n_id] = solver.Value(
                model.link_capacity[conn_n_int][n_int]
            )
    return (
        has_successor_res,
        x_res,
        y_res,
        link_weight_res,
        stream_weight_res,
        link_capacity_res,
        capac_use_res,
    )
