from typing import Dict

from utils.utilities import flatten


def add_optimization_goal(model, existing_routes):
    # max route length + 10 * max amount of overlaps
    upper_bound_stream_cost = model.max_node_int + 10 * (model.max_stream_int * model.max_node_int)
    upper_bound_total_cost = model.max_stream_int * upper_bound_stream_cost

    _create_cost_variable_route_length(model)
    _create_cost_variable_overlap(model, existing_routes)


    # Set cost for each stream
    for f_int in range(model.max_stream_int):
        stream_id = model._IntToStreamIDMap[f_int]

        model.stream_cost[stream_id] = model.model.NewIntVar(
            0, upper_bound_stream_cost, "stream_cost_{}".format(f_int)
        )
        model.model.Add(
            model.stream_cost[stream_id] == 10 * sum(model.stream_overlaps[stream_id]) + model.stream_route_lens[stream_id]
        )


    # Cost
    model.total_cost = model.model.NewIntVar(
        0, upper_bound_total_cost, "total_cost"
    )
    model.model.Add(model.total_cost == sum(model.stream_cost.values()))
    model.model.Minimize(model.total_cost)


def _create_cost_variable_route_length(model):
    for f_int in range(model.max_stream_int):
        f = model.tc.F_routed[model._IntToStreamIDMap[f_int]]
        all_used_links = flatten(model.x_v_is_u[f_int])

        stream_route_len = model.model.NewIntVar(
            0, model.max_node_int, "stream_route_weight_{}".format(f.id)
        )
        model.model.Add(stream_route_len == sum(all_used_links) - 1) # substract 1 to not count source self link
        model.stream_route_lens[f.id] = stream_route_len


def _create_cost_variable_overlap(model, existing_routes):
    for stream_id_prefix, stream_list in model.tc.F_red.items():
        for stream in stream_list:
            model.stream_overlaps[stream.id] = []
        if existing_routes != None:
            f_int_list = [model._StreamIDToIntMap[s.id] for s in stream_list if s.id not in existing_routes]
        else:
            f_int_list = [model._StreamIDToIntMap[s.id] for s in stream_list]
        model.link_occupations[stream_id_prefix] = {}

        for v_int in range(model.max_node_int):
            v = model.tc.N[model._IntToNodeIDMap[v_int]]

            # Use node ids instead of int!
            model.link_occupations[stream_id_prefix][v.id] = {}

            for u_id in model.tc.N_conn[v.id]:
                u_int = model._NodeIDToIntMap[u_id]
                # switch u and v here to get connections FROM v to u
                x_v_is_u_list = [model.x_v_is_u[f_int][u_int][v_int] for f_int in f_int_list]

                model.link_occupations[stream_id_prefix][v.id][u_id] = model.model.NewIntVar(0, len(stream_list),
                                                                                             "link_occupation_{}_{}_{}".format(
                                                                                                 stream_id_prefix, v.id,
                                                                                                 u_id))
                model.model.Add(model.link_occupations[stream_id_prefix][v.id][u_id] == sum(x_v_is_u_list))

                for f_int in f_int_list:
                    stream_id = model._IntToStreamIDMap[f_int]
                    stream = model.tc.F_routed[stream_id]

                    model.stream_overlaps[stream_id].append(model.model.NewIntVar(0, len(stream_list) - 1,
                                                                                  "stream_{}_overlap_on_{}_{}".format(
                                                                                      f_int, v_int, u_int)))

                    if u_id != stream.sender_es_id:
                        model.model.Add(model.stream_overlaps[stream_id][-1] == sum(x_v_is_u_list) - 1).OnlyEnforceIf(
                            model.x_v_is_u[f_int][u_int][v_int])
                        model.model.Add(model.stream_overlaps[stream_id][-1] == 0).OnlyEnforceIf(
                            model.x_v_is_u[f_int][u_int][v_int].Not())
                    else:
                        model.model.Add(model.stream_overlaps[stream_id][-1] == 0)