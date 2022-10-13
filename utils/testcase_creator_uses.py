import random
from pathlib import Path
from typing import Dict, List

from input.model.route import route

from input.model.stream import stream, EStreamType

from input.model.link import link
from input.model.nodes import end_system, switch

from input.testcase import Testcase
from utils import serializer
import networkx as nx


largest_guard_bands = {}

def find_stream_placement(message_size: int, period: int, priority, G: nx.DiGraph, link_bw_util: Dict[str, List[float]], largest_guard_bands, cutoff_util, tc):
    found = False
    es_send = ""
    es_recv = ""
    r = []

    iter = 0
    while not found and iter < 100:
        iter += 1
        es_send, es_recv = random.sample(tc.ES.keys(), 2)

        rt = nx.shortest_path(G, es_send, es_recv, weight="weight")

        # calculate all utils & check that they don't exceed certain values
        utils = []
        for i in range(len(rt)-1):
            a = rt[i]
            b = rt[i+1]
            l_id = f"l_{a}_{b}"
            send_time = tc.L[l_id].transmission_length(message_size)
            if link_bw_util[l_id][priority] + send_time/period > 1:
                break
            elif link_bw_util[l_id][priority] + send_time/period >= cutoff_util:
                G.remove_edge(a,b)
                break
            utils.append(send_time/period)

        # if all utils are fine, add them to G
        if len(utils) == len(rt)-1:
            found = True
            for i in range(len(rt) - 1):
                a = rt[i]
                b = rt[i + 1]
                l_id = f"l_{a}_{b}"
                send_time = tc.L[l_id].transmission_length(message_size)
                G[a][b]["weight"] + (send_time/period)*100
                # Add/change guard band
                if largest_guard_bands[l_id][priority] == 0:
                    link_bw_util[l_id][priority] += send_time/period
                    largest_guard_bands[l_id][priority] = send_time/period
                elif send_time/period > largest_guard_bands[l_id][priority]:
                    link_bw_util[l_id][priority] += send_time/period - largest_guard_bands[l_id][priority]
                    largest_guard_bands[l_id][priority] = send_time/period
                link_bw_util[l_id][priority] += (send_time/period)

    if not found:
        raise ValueError(f"Couldn't find any feasible stream in {iter} iterations")
    return es_send, es_recv, rt

def create_testcases(topo_type, target_util, cutoff_util, name, nr_es, nr_sw, es_per_sw, link_speed, stream_periods, deadline_factor, stream_priorities, min_stream_size, max_stream_size, tc_amount, path):
    # Create topology
    if topo_type == "mesh":
        G = nx.DiGraph()

        # ES
        for j in range(nr_es):
            G.add_node(f"ES{j}")

        # SW
        for k in range(nr_sw):
            G.add_node(f"SW{k}")

        # Links
        # connect es to switches
        for k in range(nr_sw):
            for l in range(es_per_sw):
                src_id = f"ES{k * es_per_sw + l}"
                dest_id = f"SW{k}"
                G.add_edge(src_id, dest_id, weight=0)
                G.add_edge(dest_id, src_id, weight=0)

        # connect each switch
        for k in range(nr_sw):
            for k_2 in range(nr_sw):
                if k != k_2:
                    src_id = f"SW{k}"
                    dest_id = f"SW{k_2}"
                    G.add_edge(src_id, dest_id, weight=0)
    else:
        raise ValueError


    for i in range(tc_amount):
        tc = Testcase(f"{topo_type}_{name}_{i}")
        tc.link_speed = link_speed
        tc.W_f_max = 1500
        tc.W_mac = 0
        tc.key_length = 0
        tc.OH = 0

        link_bw_util = {}
        largest_guard_bands = {}

        # ES
        for j in range(nr_es):
            es = end_system(f"ES{j}", 0, "EndSystem")
            tc.add_to_datastructures(es)


        # SW
        for k in range(nr_sw):
            sw = switch(f"SW{k}")
            tc.add_to_datastructures(sw)

        # Links
        # connect es to switches
        for k in range(nr_sw):
            for l in range(es_per_sw):
                src_id = f"ES{k*es_per_sw+l}"
                dest_id = f"SW{k}"
                l = link(f"l_{src_id}_{dest_id}", tc.N[src_id], tc.N[dest_id], link_speed)
                tc.add_to_datastructures(l)
                link_bw_util[l.id] = [0,0,0,0,0,0,0,0]
                largest_guard_bands[l.id] = [0,0,0,0,0,0,0,0]
                l = link(f"l_{dest_id}_{src_id}", tc.N[dest_id], tc.N[src_id], link_speed)
                tc.add_to_datastructures(l)
                link_bw_util[l.id] = [0,0,0,0,0,0,0,0]
                largest_guard_bands[l.id] = [0,0,0,0,0,0,0,0]

        # connect each switch to all other switches
        for k in range(nr_sw):
            for k_2 in range(nr_sw):
                if k != k_2:
                    src_id = f"SW{k}"
                    dest_id = f"SW{k_2}"
                    l = link(f"l_{src_id}_{dest_id}", tc.N[src_id], tc.N[dest_id], link_speed)
                    tc.add_to_datastructures(l)
                    link_bw_util[l.id] = [0,0,0,0,0,0,0,0]
                    largest_guard_bands[l.id] = [0,0,0,0,0,0,0,0]

        print(f"Created topology with {nr_es} ES, {nr_sw} SW and {es_per_sw} ES per SW")

        # Streams
        avg_util = 0
        m = 0
        while avg_util < target_util:
            stream_id = f"s{m}"  # Don't use underscores in stream name
            message_size = random.randint(min_stream_size, max_stream_size)
            period = random.choice(stream_periods)
            priority = random.choice(stream_priorities)

            src_es_id, recv_es_id, r = find_stream_placement(message_size, period, priority, G, link_bw_util, largest_guard_bands, cutoff_util, tc)

            deadline = deadline_factor*period
            overhead = 0

            s = stream(stream_id, src_es_id, [recv_es_id],
                       message_size, period, message_size, overhead,
                       EStreamType.NORMAL, priority, deadline)
            tc.add_to_datastructures(s)

            rt = route(s)
            node_mapping = {}
            node_mapping[recv_es_id] = [(r[n], r[n+1]) for n in range(len(r)-1)]
            rt.init_from_node_mapping(node_mapping)
            tc.add_to_datastructures(rt)

            port_utils = []
            for port_id, util_list in link_bw_util.items():
                port_utils.append(sum(util_list))

            avg_util = sum(port_utils) / len(port_utils)
            #print(f"Added stream {m}, avg. utilization is {avg_util}/{target_util}")
            m += 1

        p = path / (tc.name + ".flex_network_description")
        serializer.create_flex_network_description(p, tc)
        print(f"Created testcase at: {p}")
        print(f"Streams: {len(tc.F.values())}")

topo_type = "mesh"
target_util = 0.5
cutoff_util = 0.7
name = "large"
nr_es = 48
nr_sw = 8
es_per_sw = 6
link_speed = 12.5
deadline_factor = 10
stream_periods = [1000, 2000, 5000, 10000] #us
stream_priorities = [0,1,2,3,4]
min_stream_size = 64
max_stream_size = 1500
tc_amount = 50
path = Path(f"testcases/{topo_type}/{name}50/")

create_testcases(topo_type, target_util, cutoff_util, name, nr_es, nr_sw, es_per_sw, link_speed, stream_periods, deadline_factor, stream_priorities, min_stream_size, max_stream_size, tc_amount, path)