import itertools
import xml.etree.ElementTree as ET
from typing import Dict


class schedule:
    @classmethod
    def from_solver(cls, solver, scheduling_model):
        c = cls()

        for l_or_n_id in itertools.chain(
            scheduling_model.tc.L.keys(), scheduling_model.tc.N.keys()
        ):
            c.o_f_val[l_or_n_id] = {}
            c.c_f_val[l_or_n_id] = {}
            c.a_f_val[l_or_n_id] = {}
            for f in scheduling_model.tc.F.values():
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

        for t in scheduling_model.tc.T.values():
            c.o_t_val[t.id] = solver.Value(scheduling_model.o_t[t.id])
            c.a_t_val[t.id] = solver.Value(scheduling_model.a_t[t.id])

        for fp in scheduling_model.tc.FP.values():
            app_id = fp.app_id
            if app_id not in c.laxities_val:
                c.laxities_val[app_id] = {}

            c.laxities_val[app_id][fp.id] = solver.Value(
                scheduling_model.laxities[app_id][fp.id]
            )

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

        self.laxities_val: Dict[
            str, Dict[str, int]
        ] = {}  # app.id -> Dict(fp.id -> val)

    def is_stream_using_link_or_node(self, f_id, l_or_n_id):
        return self.c_f_val[l_or_n_id][f_id] != 0

    def xml_string(self, tc_N: Dict, tc_L: Dict, tc_T: Dict, tc_Fsec):
        # Preperation
        link_to_o_t_map, link_to_a_t_map = self._map_t_to_links(tc_T)

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
            if l_or_n_id in tc_L:
                l_or_n = tc_L[l_or_n_id]
                s += '\t<link src="{}" dest="{}">\n'.format(
                    l_or_n.src.id, l_or_n.dest.id
                )
            elif l_or_n_id in tc_N:
                l_or_n = tc_N[l_or_n_id]
                s += '\t<link src="{}" dest="{}">\n'.format(l_or_n.id, l_or_n.id)
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
                        s += '\t\t<block start="{}" duration="{}" end="{}" creator="{}"/>\n'.format(
                            o_t, a_t - o_t, a_t, t_id
                        )
            # - Streams
            if l_or_n_id in self.o_f_val:
                for f_id, o_f in self.o_f_val[l_or_n_id].items():
                    c_f = self.c_f_val[l_or_n_id][f_id]
                    a_f = self.a_f_val[l_or_n_id][f_id]

                    if c_f > 0:
                        s += '\t\t<block start="{}" duration="{}" end="{}" creator="{}"/>\n'.format(
                            o_f, c_f, a_f, f_id
                        )

            # Link Footer
            s += "\t</link>\n"

        # Phi
        s += "\t<key_release_intervals>\n"

        for f_id, phi in self.phi_f_val.items():
            # NOTE: security/key streams have no associated key stream and thus no phi
            if f_id not in tc_Fsec:
                s += '\t\t<phi stream_id="{}" value="{}"/>\n'.format(f_id, phi)

        s += "\t</key_release_intervals>\n"

        # Laxities
        s += "\t<laxities>\n"
        for app_id, fp_dict in self.laxities_val.items():
            for fp_id, fp_val in fp_dict.items():
                s += '\t\t<lax app_id="{}" fp_id="{}" value="{}"/>\n'.format(
                    app_id, fp_id, fp_val
                )
        s += "\t</laxities>\n"

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
                link_to_a_t_map[node_id][t_id] = self.o_t_val[t_id]
            else:
                link_to_o_t_map[node_id][t_id] = self.o_t_val[t_id]
                link_to_a_t_map[node_id][t_id] = self.a_t_val[t_id]

        return link_to_o_t_map, link_to_a_t_map

    @classmethod
    def from_xml_node(
        cls, n: ET.Element, tc_N: Dict, tc_T: Dict, tc_F: Dict, tc_Lfromnodes: Dict
    ):
        c = cls()

        for n_child in n:
            if n_child.tag == "link":
                src_n_id = n_child.attrib["src"]
                dest_n_id = n_child.attrib["dest"]

                if src_n_id == dest_n_id:
                    # Node
                    l_or_n = tc_N[src_n_id]
                else:
                    l_or_n = tc_Lfromnodes[src_n_id][dest_n_id]

                c.o_f_val[l_or_n.id] = {}
                c.c_f_val[l_or_n.id] = {}
                c.a_f_val[l_or_n.id] = {}

                for n_block in n_child:
                    start = int(n_block.attrib["start"])
                    duration = int(n_block.attrib["duration"])
                    end = int(n_block.attrib["end"])
                    creator_id = n_block.attrib["creator"]

                    if creator_id in tc_T:
                        # task
                        c.o_t_val[creator_id] = start
                        c.a_t_val[creator_id] = end
                    elif creator_id in tc_F:
                        # stream
                        c.o_f_val[l_or_n.id][creator_id] = start
                        c.c_f_val[l_or_n.id][creator_id] = duration
                        c.a_f_val[l_or_n.id][creator_id] = end
            elif n_child.tag == "key_release_intervals":
                for n_phi in n_child:
                    stream_id = n_phi.attrib["stream_id"]
                    value = int(n_phi.attrib["value"])

                    c.phi_f_val[stream_id] = value
            elif n_child.tag == "laxities":
                for n_lax in n_child:
                    app_id = n_lax.attrib["app_id"]
                    fp_id = n_lax.attrib["fp_id"]
                    value = int(n_lax.attrib["value"])

                    if app_id not in c.laxities_val:
                        c.laxities_val[app_id] = {}

                    c.laxities_val[app_id][fp_id] = value
