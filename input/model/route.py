import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set, Optional, Union

from networkx import DiGraph, shortest_path
import networkx as nx

from input.model.link import link
from input.model.nodes import node
from input.model.stream import stream


class route:
    def __init__(self, f: stream):
        self.stream : stream = f
        self._DAG = DiGraph()

    def init_from_node_mapping(self, node_mapping: Set[Tuple[str, str]], tc_L_from_nodes: Dict):
        """
        node_mapping: List of tuples which map node.id to successor node.id in route. id=-1 signals no connection
        """
        for tpl in node_mapping:
            if tpl[0] != -1 and tpl[1] != -1:
                if tpl[0] != tpl[1]:
                    if tpl[0] not in self._DAG:
                        self._DAG.add_node(tpl[0])
                    if tpl[1] not in self._DAG:
                        self._DAG.add_node(tpl[1])
                    self._DAG.add_edge(tpl[0], tpl[1])

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
        x_res_vector: Maps node.id to predecessor node.id in route. id=-1 signals no connection
        """
        for a, b in x_res_vector.items():
            if a != -1 and b != -1:
                if a != b:
                    if a not in self._DAG:
                        self._DAG.add_node(a)
                    if b not in self._DAG:
                        self._DAG.add_node(b)
                    self._DAG.add_edge(b, a)

    def get_all_links(self, tc_L_from_nodes) -> List[link]:
        return [tc_L_from_nodes[tpl[0]][tpl[1]] for tpl in self._DAG.edges]

    def get_all_nodes(self, tc_N):
        return [tc_N[n] for n in self._DAG.nodes]

    def get_all_links_dfs(self, tc_L_from_nodes) -> List[link]:
        return [tc_L_from_nodes[tpl[0]][tpl[1]] for tpl in nx.dfs_edges(self._DAG, source=self.stream.sender_es_id)]

    def get_all_es_and_links(self, tc_N, tc_L_from_nodes) -> List[Union[node, link]]:
        es = self.get_all_nodes(tc_N)
        links = self.get_all_links(tc_L_from_nodes)
        es.extend(links)
        return es

    def get_total_length(self) -> int:
        return len(self._DAG.size())

    def get_successor_links_for_node(self, node_id: str, tc_L_from_nodes) -> Optional[List[link]]:
        """
        :return: List of successor link or es ids
        """
        if node_id in self._DAG:
            return [tc_L_from_nodes[node_id][succ_node_id] for succ_node_id in self._DAG.successors(node_id)]
        else:
            return []

    def get_successor_links(self, l_or_es_id: str, tc_N, tc_L, tc_L_from_nodes) -> Optional[List[link]]:
        """
        :return: List of successor link or es ids
        """
        if l_or_es_id in tc_L:
            l = tc_L[l_or_es_id]
            return self.get_successor_links_for_node(l.dest.id, tc_L_from_nodes)
        elif l_or_es_id in tc_N:
            return self.get_successor_links_for_node(l_or_es_id, tc_L_from_nodes)
        else:
            return []

    def get_predeccessor_links_for_node(self, node_id: str, tc_L_from_nodes)  -> Optional[List[link]]:
        """

        :param l_or_es_id: link or es id
        :return: Set of predecessor link or es ids
        """
        if node_id in self._DAG:
            return [tc_L_from_nodes[pred_node_id][node_id] for pred_node_id in self._DAG.predecessors(node_id)]
        else:
            return []

    def get_predeccessor_links(self, l_or_es_id: str, tc_N, tc_L, tc_L_from_nodes) -> Optional[List[link]]:
        """
        :return: List of predecessor link or es ids
        """
        if l_or_es_id in tc_L:
            l = tc_L[l_or_es_id]
            return self.get_predeccessor_links_for_node(l.src.id, tc_L_from_nodes)
        elif l_or_es_id in tc_N:
            return self.get_predeccessor_links_for_node(l_or_es_id, tc_L_from_nodes)
        else:
            return []

    def is_link_in_tree(self, src_id: str, dest_id: str) -> bool:
        """
        :return: True, if link is part of multicast tree
        """
        return self._DAG.has_edge(src_id, dest_id)

    def is_node_in_tree(self, node_id: str) -> bool:
        """
        :return: True, if link is part of multicast tree
        """
        return node_id in self._DAG

    def is_in_tree(self, l_or_es_id: str, tc_N: Dict, tc_L: Dict):
        if l_or_es_id in tc_L:
            l = tc_L[l_or_es_id]
            return self.is_link_in_tree(l.src.id, l.dest.id)
        elif l_or_es_id in tc_N:
            return self.is_node_in_tree(l_or_es_id)
        else:
            return False

    def get_links_along_route_towards(self, dest_node_id: str, tc_L_from_nodes: Dict) -> List[link]:
        sp = shortest_path(self._DAG, source=self.stream.sender_es_id, target=dest_node_id)
        ret_l = []
        for i in range(len(sp)-1):
            ret_l.append(tc_L_from_nodes[sp[i]][sp[i+1]])
        return ret_l

    def xml_string(self, tc_L_from_nodes: Dict):
        r = '<route stream="{}">\n'.format(self.stream.id)
        for link in self.get_all_links_dfs(tc_L_from_nodes):
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
