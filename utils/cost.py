from typing import List, Tuple, Dict


def cost_SA_scheduling_solution(sol, tc, b, infeasible_tga, latencies: Dict[str, int]):
    # latencies only contains latencies of feasible applications
    return b * len(infeasible_tga) + sum(latencies.values())

def cost_schedule(tc, b):
    # TODO: infeasbile streams instead of apps
    total_cost = 0
    infeasible_apps = 0
    for app_id in tc.A.keys():
        if app_id in tc.schedule.app_costs:
            app_latency = tc.schedule.app_costs[app_id]

            total_cost += app_latency
        else:
            # if app is not in app_costs it was infeasible (including over deadline)
            total_cost += b
            infeasible_apps += 1

    return total_cost, infeasible_apps

def cost_parameters_for_stream(s, sol, tc):
    combined_path = create_path(s, sol)
    route_len = len(combined_path)
    overlap_amount, overlap_links = overlaps(s.id, combined_path, sol, tc)
    return route_len, overlap_amount, overlap_links


def overlaps(stream_id: str, combined_path: List[Tuple[str, str]], sol, tc) -> Tuple[int, set]:
    s = tc.F_routed[stream_id]

    overlap_amount = 0
    overlap_links = set()
    for stream_red_copy in tc.F_red[s.get_id_prefix()]:
        if stream_red_copy != s:
            combined_path_red = create_path(stream_red_copy, sol)

            for tpl in combined_path_red:
                if tpl in combined_path:
                    overlap_amount += 1
                    overlap_links.add(tc.L_from_nodes[tpl[0]][tpl[1]])

    return overlap_amount, overlap_links

def create_path(s, sol):
    combined_path = []
    for es_recv_id, path in sol.paths[s.id].items():
        for i in range(len(path) - 1):
            if (path[i], path[i + 1]) not in combined_path:
                combined_path.append((path[i], path[i + 1]))
    return combined_path