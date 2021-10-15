import itertools
import xml.etree.ElementTree as ET
from typing import Dict

from intervaltree import IntervalTree, Interval

from input.model.link import link
from input.model.nodes import end_system
from input.model.route import route
from input.model.stream import stream
from input.model.task import task
from optimization.sa.task_graph import PrecedenceGraph
from utils.utilities import sorted_complement, debug_print


class schedule:
    @classmethod
    def from_heuristic_schedule_and_task_graph(cls, heu_sched, task_graph: PrecedenceGraph, tc, infeasible_tga):
        c = cls()

        for f in tc.F_routed.values():
            for l_or_es in tc.R[f.id].get_all_es_and_links(tc):
                tgn = task_graph.get_stream_tgn(f.id)
                if tgn.id in heu_sched.frames:
                    if l_or_es.id in heu_sched.frames[tgn.id]:
                        if l_or_es.id not in c.o_f_val:
                            c.o_f_val[l_or_es.id] = {}
                            c.c_f_val[l_or_es.id] = {}
                            c.a_f_val[l_or_es.id] = {}

                        # TODO: phi value
                        #if f.id in scheduling_model.phi_f:
                        #    c.phi_f_val[f.id] = solver.Value(scheduling_model.phi_f[f.id])
                        if tgn.id in heu_sched.frames:
                            if l_or_es.id in heu_sched.frames[tgn.id]:
                                c.o_f_val[l_or_es.id][f.id] = heu_sched.frames[tgn.id][l_or_es.id].offset
                                c.c_f_val[l_or_es.id][f.id] = heu_sched.frames[tgn.id][l_or_es.id].length
                                c.a_f_val[l_or_es.id][f.id] = heu_sched.frames[tgn.id][l_or_es.id].offset + heu_sched.frames[tgn.id][l_or_es.id].length

                                if isinstance(l_or_es, end_system):
                                    if l_or_es.id not in c.cpu_use:
                                        c.cpu_use[l_or_es.id] = heu_sched.frames[tgn.id][l_or_es.id].length / heu_sched.frames[tgn.id][l_or_es.id].period
                                    else:
                                        c.cpu_use[l_or_es.id] += heu_sched.frames[tgn.id][l_or_es.id].length / heu_sched.frames[tgn.id][l_or_es.id].period
                                elif isinstance(l_or_es, link):
                                    if l_or_es.id not in c.bw_use:
                                        c.bw_use[l_or_es.id] = heu_sched.frames[tgn.id][l_or_es.id].length / heu_sched.frames[tgn.id][l_or_es.id].period
                                    else:
                                        c.bw_use[l_or_es.id] += heu_sched.frames[tgn.id][l_or_es.id].length / heu_sched.frames[tgn.id][l_or_es.id].period
        for t in tc.T.values():
            tgn = task_graph.get_task_tgn(t.id)
            if tgn.id in heu_sched.frames:
                if t.src_es_id in heu_sched.frames[tgn.id]:
                    c.o_t_val[t.id] = heu_sched.frames[tgn.id][t.src_es_id].offset
                    c.a_t_val[t.id] = heu_sched.frames[tgn.id][t.src_es_id].offset + heu_sched.frames[tgn.id][t.src_es_id].length

                    if t.src_es_id not in c.cpu_use:
                        c.cpu_use[t.src_es_id] = heu_sched.frames[tgn.id][t.src_es_id].length / heu_sched.frames[tgn.id][t.src_es_id].period
                    else:
                        c.cpu_use[t.src_es_id] += heu_sched.frames[tgn.id][t.src_es_id].length / heu_sched.frames[tgn.id][t.src_es_id].period

        for app in tc.A.values():
            if app.id not in infeasible_tga:
                c.app_costs[app.id] = max([c.a_t_val[t_id] for t_id in app.verticies.keys()]) - min([c.o_t_val[t_id] for t_id in app.verticies.keys()])

        return c

    @classmethod
    def from_cp_solver(cls, solver, scheduling_model, tc):
        c = cls()

        for l_or_n_id in itertools.chain(
            scheduling_model.tc.L.keys(), scheduling_model.tc.N.keys()
        ):
            c.o_f_val[l_or_n_id] = {}
            c.c_f_val[l_or_n_id] = {}
            c.a_f_val[l_or_n_id] = {}
            for f in scheduling_model.tc.F_routed.values():
                if f.id in scheduling_model.phi_f:
                    c.phi_f_val[f.id] = solver.Value(scheduling_model.phi_f[f.id])
                c.o_f_val[l_or_n_id][f.id] = solver.Value(
                    scheduling_model.o_f[l_or_n_id][f.id]
                )
                c.c_f_val[l_or_n_id][f.id] = solver.Value(
                    scheduling_model.c_f[l_or_n_id][f.id]
                )
                c.a_f_val[l_or_n_id][f.id] = solver.Value(
                    scheduling_model.a_f[l_or_n_id][f.id]
                )

                length = c.c_f_val[l_or_n_id][f.id]
                period = f.period
                if l_or_n_id in tc.ES:
                    l_or_es = tc.ES[l_or_n_id]
                    if l_or_es.id not in c.cpu_use:
                        c.cpu_use[l_or_es.id] = length / period
                    else:
                        c.cpu_use[l_or_es.id] += length / period
                elif l_or_n_id in tc.L:
                    l_or_es = tc.L[l_or_n_id]
                    if l_or_es.id not in c.bw_use:
                        c.bw_use[l_or_es.id] = length / period
                    else:
                        c.bw_use[l_or_es.id] += length / period

        for t in scheduling_model.tc.T.values():
            c.o_t_val[t.id] = solver.Value(scheduling_model.o_t[t.id])
            c.a_t_val[t.id] = solver.Value(scheduling_model.a_t[t.id])

            l_or_es = tc.ES[t.src_es_id]
            length = c.a_t_val[t.id] - c.o_t_val[t.id]
            period = t.period
            if l_or_es.id not in c.cpu_use:
                c.cpu_use[l_or_es.id] = length / period
            else:
                c.cpu_use[l_or_es.id] += length / period

        for app in scheduling_model.tc.A.values():
            c.app_costs[app.id] = max([c.a_t_val[t_id] for t_id in app.verticies.keys()]) - min([c.o_t_val[t_id] for t_id in app.verticies.keys()])

        return c

    def __init__(self):
        # l_or_n_id -> (f_id -> val)
        self.o_f_val: Dict[str, Dict[str, int]] = {}
        self.c_f_val: Dict[str, Dict[str, int]] = {}
        self.a_f_val: Dict[str, Dict[str, int]] = {}

        # f_id -> val
        self.phi_f_val: Dict[str, int] = {}
        # t_id -> val
        self.o_t_val: Dict[str, int] = {}
        self.a_t_val: Dict[str, int] = {}

        self.app_costs: Dict[
            str, int
        ] = {}  # Dict(app.id -> val)

        self.bw_use: Dict[
            str, float
        ] = {} # Dict(link.id -> val)

        self.cpu_use: Dict[
            str, float
        ] = {}  # Dict(es.id -> val)

    def is_stream_using_link_or_node(self, f_id, l_or_n_id):
        if l_or_n_id in self.c_f_val and f_id in self.c_f_val[l_or_n_id]:
            return self.c_f_val[l_or_n_id][f_id] != 0
        else:
            return False

    def get_Extensibility_metrics(self, tc):
        res = {}

        for es in tc.ES.values():
            if not es.is_prover():
                ivs = []
                for t in tc.T_g[es.id]:
                    ivs.append((self.o_t_val[t.id], self.a_t_val[t.id]))
                iv_tree = IntervalTree.from_tuples(ivs)
                iv_tree.merge_overlaps(strict=False)
                iv_lengths = [iv.end - iv.begin for iv in iv_tree]
                worst_case_response_time = max(iv_lengths) if len(iv_lengths) > 0 else 0

                average_response_time = 0
                for iv_length in iv_lengths:
                    average_response_time += (iv_length*(iv_length+1)) / 2
                average_response_time = average_response_time / len(iv_lengths)
                debug_print(f"{es.id}")
                debug_print(f"Intervals: {iv_tree}")
                debug_print(f"{(worst_case_response_time, average_response_time)}")
                res[es.id] = (worst_case_response_time, average_response_time)

        return res

    def get_RA_metrics(self, tc):
        # average longest time interval not attested
        # average time spent attesting
        res = {}

        for es_prover in tc.ES_prover.values():
            ivs = []
            for t in tc.T_g[es_prover.id]:
                ivs.append((self.o_t_val[t.id], self.a_t_val[t.id]))
            iv_tree = IntervalTree.from_tuples(ivs)
            iv_tree.merge_overlaps(strict=False)
            iv_lengths = [iv.end - iv.begin for iv in iv_tree]
            max_non_attested_time = max(iv_lengths) if len(iv_lengths) > 0 else 0
            slacks = sorted_complement(iv_tree, start=0, end=tc.hyperperiod)
            slack_lengths = [iv.end - iv.begin for iv in slacks]

            # Calculate the best block size for the maximum attestation time
            # Iterate through all slack sizes, choosing the one with maximum attestation time
            time_spent_attesting = 0
            block_length = 0
            slack_lengths_already_checked = set()
            for sl in slack_lengths:
                if sl not in slack_lengths_already_checked:
                    cur_time_spent_attesting = 0
                    for sl2 in slack_lengths:
                        if sl <= sl2:
                            cur_time_spent_attesting += sl
                    slack_lengths_already_checked.add(sl)
                    if cur_time_spent_attesting > time_spent_attesting:
                        time_spent_attesting = cur_time_spent_attesting
                        block_length = sl

            print(f"{es_prover.id}")
            print(f"Slacks: {slacks}")
            print(f"{(max_non_attested_time, time_spent_attesting, block_length)}")
            res[es_prover.id] = (max_non_attested_time, time_spent_attesting, block_length)

        return res

    def xml_string(self, tc):
        # Preperation
        link_to_o_t_map, link_to_a_t_map = self._map_t_to_links(tc.T)

        all_links_or_nodes = []
        for k in link_to_o_t_map.keys():
            all_links_or_nodes.append(k)
        for k in self.o_f_val.keys():
            if k not in link_to_o_t_map:
                all_links_or_nodes.append(k)

        # Creating string
        s = "<schedule>\n"

        for l_or_n_id in all_links_or_nodes:
            # Create link header
            if l_or_n_id in tc.L:
                l_or_n = tc.L[l_or_n_id]
                s += '\t<link src="{}" dest="{}">\n'.format(
                    l_or_n.src.id, l_or_n.dest.id
                )
            elif l_or_n_id in tc.N:
                l_or_n = tc.N[l_or_n_id]
                s += '\t<node src="{}" dest="{}">\n'.format(l_or_n.id, l_or_n.id)
            else:
                raise ValueError(
                    f"{l_or_n_id} is neither node or link in the given testcase"
                )

            # Add blocks

            # - Tasks
            if l_or_n_id in link_to_o_t_map:
                for t_id, o_t in link_to_o_t_map[l_or_n_id].items():
                    a_t = link_to_a_t_map[l_or_n_id][t_id]

                    if a_t > 0:
                        t = tc.T[t_id]
                        for i_period in range(int(tc.hyperperiod / t.period)):
                            s += '\t\t<block start="{}" duration="{}" end="{}" creator="{}"/>\n'.format(
                                o_t+i_period*t.period, a_t - o_t, a_t+i_period*t.period, t_id
                            )
            # - Streams
            if l_or_n_id in self.o_f_val:
                for f_id, o_f in self.o_f_val[l_or_n_id].items():
                    c_f = self.c_f_val[l_or_n_id][f_id]
                    a_f = self.a_f_val[l_or_n_id][f_id]

                    if c_f > 0:
                        f = tc.F[f_id]
                        for i_period in range(int(tc.hyperperiod / f.period)):
                            s += '\t\t<block start="{}" duration="{}" end="{}" creator="{}"/>\n'.format(
                                o_f+i_period*f.period, c_f, a_f+i_period*f.period, f_id
                            )

            # Link Footer
            if l_or_n_id in tc.L:
                s += "\t</link>\n"
            elif l_or_n_id in tc.N:
                s += "\t</node>\n"


        # Phi
        s += "\t<key_release_intervals>\n"

        for f_id, phi in self.phi_f_val.items():
            # NOTE: security/key streams have no associated key stream and thus no phi
            if f_id not in tc.F_sec:
                s += '\t\t<phi stream_id="{}" value="{}"/>\n'.format(f_id, phi)

        s += "\t</key_release_intervals>\n"

        # App costs
        s += "\t<costs>\n"
        for app_id, cost in self.app_costs.items():
            s += '\t\t<cost app_id="{}" value="{}"/>\n'.format(
                app_id, cost
            )
        s += "\t</costs>\n"

        s += "</schedule>"
        return s

    def _map_t_to_links(self, tc_T):
        link_to_o_t_map = {}
        link_to_a_t_map = {}
        for t_id in self.o_t_val.keys():
            node_id = tc_T[t_id].src_es_id

            if not node_id in link_to_o_t_map:
                link_to_o_t_map[node_id] = {}
                link_to_o_t_map[node_id][t_id] = self.o_t_val[t_id]
                link_to_a_t_map[node_id] = {}
                link_to_a_t_map[node_id][t_id] = self.a_t_val[t_id]
            else:
                link_to_o_t_map[node_id][t_id] = self.o_t_val[t_id]
                link_to_a_t_map[node_id][t_id] = self.a_t_val[t_id]

        return link_to_o_t_map, link_to_a_t_map

    @classmethod
    def from_xml_node(
        cls, n: ET.Element, tc
    ):
        c = cls(tc)

        for n_child in n:
            if n_child.tag == "link":
                src_n_id = n_child.attrib["src"]
                dest_n_id = n_child.attrib["dest"]

                if src_n_id == dest_n_id:
                    # Node
                    l_or_n = tc.N[src_n_id]
                else:
                    l_or_n = tc.L_from_nodes[src_n_id][dest_n_id]

                c.o_f_val[l_or_n.id] = {}
                c.c_f_val[l_or_n.id] = {}
                c.a_f_val[l_or_n.id] = {}

                for n_block in n_child:
                    start = int(n_block.attrib["start"])
                    duration = int(n_block.attrib["duration"])
                    end = int(n_block.attrib["end"])
                    creator_id = n_block.attrib["creator"]

                    if creator_id in tc.T:
                        # task
                        c.o_t_val[creator_id] = start
                        c.a_t_val[creator_id] = end
                    elif creator_id in tc.F:
                        # stream
                        c.o_f_val[l_or_n.id][creator_id] = start
                        c.c_f_val[l_or_n.id][creator_id] = duration
                        c.a_f_val[l_or_n.id][creator_id] = end
            elif n_child.tag == "key_release_intervals":
                for n_phi in n_child:
                    stream_id = n_phi.attrib["stream_id"]
                    value = int(n_phi.attrib["value"])

                    c.phi_f_val[stream_id] = value
            elif n_child.tag == "costs":
                for n_cost in n_child:
                    app_id = n_cost.attrib["app_id"]
                    value = int(n_cost.attrib["value"])

                    c.app_costs[app_id] = value
