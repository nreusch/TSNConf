import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set

class route:
    def __init__(self, f):
        self.stream = f
        self._struct = {}  # es_or_l.id => set(successor es_or_l.id)
        self._struct_inv = {}  # es_or_l.id => set(predecessor es_or_l.id)

    def init_from_node_mapping(self, node_mapping: Set[Tuple[str, str]], tc_L_from_nodes: Dict):
        """
        node_mapping: List of tuples which map node.id to successor node.id in route
        """
        x_res = {}
        for tpl in node_mapping:
            x_res[tpl[1]] = tpl[0]

        x_res[self.stream.sender_es_id] = self.stream.sender_es_id

        self.init_from_x_res_vector(x_res, tc_L_from_nodes)

    def init_from_x_res_vector(
        self, x_res_vector: Dict[str, str], tc_L_from_nodes: Dict
    ):
        """
        x_res_vector: Maps node.id to predecessor node.id in route
        """
        f = self.stream

        paths = []
        for recv_es_id in f.receiver_es_ids:
            path = [recv_es_id]
            curr_node_id = recv_es_id

            while curr_node_id != f.sender_es_id:
                l_id = tc_L_from_nodes[x_res_vector[curr_node_id]][curr_node_id].id
                path.append(l_id)
                curr_node_id = x_res_vector[curr_node_id]

            path.append(f.sender_es_id)

            path.reverse()
            paths.append(path)

        for path in paths:
            for i in range(len(path)):
                es_or_l_id = path[i]
                if i < len(path) - 1:
                    next_n_l_id = path[i + 1]
                    if es_or_l_id not in self._struct:
                        self._struct[es_or_l_id] = set()
                    if next_n_l_id not in self._struct_inv:
                        self._struct_inv[next_n_l_id] = set()

                    self._struct[es_or_l_id].add(next_n_l_id)
                    self._struct_inv[next_n_l_id].add(es_or_l_id)
                else:
                    self._struct[es_or_l_id] = set()
                if i == 0:
                    self._struct_inv[es_or_l_id] = set()

    def get_all_links(self):
        return [el for set in self._struct.values() for el in set]

    def get_all_es_and_links(self):
        return [k for k in self._struct.keys()]

    def get_successor_links(self, l_or_es_id: str):
        """

        :param l_or_es_id: link or es id
        :return: Set of successor link or es ids
        """
        if l_or_es_id in self._struct:
            return self._struct[l_or_es_id]
        else:
            return None

    def get_predeccessor_links(self, l_or_es_id: str):
        """

        :param l_or_es_id: link or es id
        :return: Set of predecessor link or es ids
        """
        if l_or_es_id in self._struct_inv:
            return self._struct_inv[l_or_es_id]
        else:
            return None

    def is_in_tree(self, l_or_es_id: str):
        """

        :param l_or_es_id: link or es id
        :return: True, if link or es id is part of multicast tree
        """
        return l_or_es_id in self._struct

    def get_links_along_route(self, tc_L: Dict):
        """

        :param tc_L: Dict of all links of testcase
        :return: List of links along route, starting from stream sender ES
        """
        successor_links = [self.stream.sender_es_id]
        ret = []

        while not len(successor_links) <= 0:
            curr_l_or_es_ids = []
            curr_l_or_es_ids.extend(successor_links)
            successor_links = []

            for l_or_es_id in curr_l_or_es_ids:
                for succ_l_or_es_id in self._struct[l_or_es_id]:
                    if succ_l_or_es_id in tc_L:
                        # if successor is a link
                        ret.append(succ_l_or_es_id)
                        successor_links.append(succ_l_or_es_id)

        return ret

    def xml_string(self, tc_L: Dict):
        r = '<route stream="{}">\n'.format(self.stream.id)
        for link_id in self.get_links_along_route(tc_L):
            link = tc_L[link_id]
            r += '\t<link src="{}" dest="{}" />\n'.format(link.src.id, link.dest.id)
        r += "</route>"
        return r

    @classmethod
    def from_xml_node(cls, n: ET.Element, tc_F: Dict, tc_L_from_nodes: Dict):
        r = cls(tc_F[n.attrib["stream"]])
        x_res_vec = {}
        for link_n in n:
            src_id = link_n.attrib["src"]
            dest_id = link_n.attrib["dest"]

            x_res_vec[dest_id] = src_id
        r.init_from_x_res_vector(x_res_vec, tc_L_from_nodes)
        return r


@dataclass
class route_info:
    def __init__(self, r: route, cost: float, route_len: int, overlap_number: int, overlap_links: set):
        self.route = r
        self.cost = cost
        self.route_len = route_len
        self.overlap_number = overlap_number
        self.overlap_links = overlap_links
