import copy
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Union

from networkx import DiGraph, shortest_path

from input.model.link import link
from input.model.nodes import node, end_system, switch
from input.model.stream import stream


class route:
    def __init__(self, f: stream):
        self.stream : stream = f
        self.paths : Dict[str, List[Tuple[str,str]]] = {} # maps receiver ES id to path, if initialized from node mapping
        self._DAG = DiGraph()

    def init_from_node_mapping(self, node_mapping: Dict[str, List[Tuple[str, str]]]):
        """
        node_mapping: List of tuples which map node.id to successor node.id in route. id=-1 signals no connection
        """
        self.paths = copy.copy(node_mapping)

        for recv_es_id, tpl_lst in node_mapping.items():
            for tpl in tpl_lst:
                if tpl[0] != -1 and tpl[1] != -1:
                    if tpl[0] != tpl[1]:
                        if tpl[0] not in self._DAG:
                            self._DAG.add_node(tpl[0])
                        if tpl[1] not in self._DAG:
                            self._DAG.add_node(tpl[1])
                        self._DAG.add_edge(tpl[0], tpl[1])

    def init_from_x_res_vector(
        self, x_res_vector: Dict[str, str]
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

        for es_recv_id in self.stream.receiver_es_ids:
            self.paths[es_recv_id] = []
            n_id = es_recv_id
            p_id = x_res_vector[n_id]
            while n_id != self.stream.sender_es_id:
                self.paths[es_recv_id].insert(0, (p_id, n_id))
                n_id = p_id
                if n_id == self.stream.sender_es_id:
                    break
                p_id = x_res_vector[n_id]

    def get_all_links(self, tc) -> List[link]:
        return [tc.L_from_nodes[tpl[0]][tpl[1]] for tpl in self._DAG.edges]

    def get_all_nodes(self, tc):
        return [tc.N[n] for n in self._DAG.nodes if isinstance(tc.N[n], end_system)]

    def get_all_switches(self, tc):
        return [tc.SW[n] for n in self._DAG.nodes if isinstance(tc.N[n], switch)]

    def get_all_links_dfs(self, tc) -> List[link]:
        l = []
        alredy_added = []
        for _, tpl_list in self.paths.items():
            for tpl in tpl_list:
                if tpl not in alredy_added:
                    l.append(tc.L_from_nodes[tpl[0]][tpl[1]])
                    alredy_added.append(tpl)
        return l

    def get_all_es_and_links_dfs(self, tc) -> List[Union[node, link]]:
        """
        Get a list of all ES and links on the route in DFS-traversal
        """
        l = []
        alredy_added = []
        for _, tpl_list in self.paths.items():
            for tpl in tpl_list:
                if tpl not in alredy_added:
                    if tpl[0] in tc.ES and tpl[0] not in alredy_added:
                        l.append(tc.ES[tpl[0]])
                        alredy_added.append(tpl[0])

                    l.append(tc.L_from_nodes[tpl[0]][tpl[1]])
                    alredy_added.append(tpl)

                    if tpl[1] in tc.ES and tpl[1] not in alredy_added:
                        l.append(tc.ES[tpl[1]])
                        alredy_added.append(tpl[1])
        return l

    def get_all_es_and_links(self, tc) -> List[Union[node, link]]:
        es = self.get_all_nodes(tc)
        links = self.get_all_links(tc)
        es.extend(links)
        return es

    def get_total_length(self) -> int:
        return len(self._DAG.size())

    def get_successor_nodes_for_node(self, node_id: str, tc) -> List[node]:
        n = []
        for l in self.get_successor_links_for_node(node_id, tc):
            n.append(l.dest)
        return n


    def get_successor_links_for_node(self, node_id: str, tc) -> Optional[List[link]]:
        """
        :return: List of successor links
        """
        if node_id in self._DAG:
            return [tc.L_from_nodes[node_id][succ_node_id] for succ_node_id in self._DAG.successors(node_id)]
        else:
            return []

    def get_successor_links(self, l_or_es_id: str, tc) -> Optional[List[link]]:
        """
        :return: List of successor links
        """
        if l_or_es_id in tc.L:
            l = tc.L[l_or_es_id]
            return self.get_successor_links_for_node(l.dest.id, tc)
        elif l_or_es_id in tc.N:
            return self.get_successor_links_for_node(l_or_es_id, tc)
        else:
            return []

    def get_predeccessor_links_for_node(self, node_id: str, tc)  -> Optional[List[link]]:
        """

        :param l_or_es_id: link or es id
        :return: Set of predecessor links
        """
        if node_id in self._DAG:
            return [tc.L_from_nodes[pred_node_id][node_id] for pred_node_id in self._DAG.predecessors(node_id)]
        else:
            return []

    def get_predeccessor_link(self, l_or_es_id: str, tc) -> Optional[List[link]]:
        """
        :return: List of predecessor links
        """
        if l_or_es_id in tc.L:
            l = tc.L[l_or_es_id]
            if l_or_es_id in tc.L and l.src.id != self.stream.sender_es_id:
                # Search for path that contains l_or_es
                # Return predecessor
                for es_id, tpl_list in self.paths.items():
                    try:
                        index = tpl_list.index((l.src.id, l.dest.id))
                        tpl = tpl_list[index - 1]
                        return [tc.L_from_nodes[tpl[0]][tpl[1]]]
                    except ValueError:
                        pass
        elif l_or_es_id in tc.N and l_or_es_id in self.paths:
            # Select path for l_or_es
            # Return last link of path
            tpl = self.paths[l_or_es_id][-1]
            return [tc.L_from_nodes[tpl[0]][tpl[1]]]

        return []

    def get_predeccessor_link_or_es(self, l_or_es_id: str, tc) -> List[Union[link, end_system]]:
        """
        :return: List of predecessor links and es
        """
        if l_or_es_id in tc.L:
            l = tc.L[l_or_es_id]
            if l.src.id == self.stream.sender_es_id:
                # if first link on route, return source ES
                return [tc.ES[self.stream.sender_es_id]]
            else:
                # Search for path that contains l_or_es
                # Return predecessor
                for es_id, tpl_list in self.paths.items():
                    try:
                        index = tpl_list.index((l.src.id, l.dest.id))
                        tpl = tpl_list[index-1]
                        return [tc.L_from_nodes[tpl[0]][tpl[1]]]
                    except (IndexError, ValueError):
                        pass
        elif l_or_es_id in tc.N and l_or_es_id in self.paths:
            # Select path for l_or_es
            # Return last link of path
            tpl = self.paths[l_or_es_id][-1]
            return [tc.L_from_nodes[tpl[0]][tpl[1]]]

        return []

    def is_link_in_tree(self, src_id: str, dest_id: str) -> bool:
        """
        :return: True, if link is part of multicast tree
        """
        return self._DAG.has_edge(src_id, dest_id)

    def is_node_in_tree(self, node_id: str) -> bool:
        """
        :return: True, if node is part of multicast tree
        """
        return node_id in self._DAG

    def is_in_tree(self, l_or_es_id: str, tc):
        if l_or_es_id in tc.L:
            l = tc.L[l_or_es_id]
            return self.is_link_in_tree(l.src.id, l.dest.id)
        elif l_or_es_id in tc.N:
            return self.is_node_in_tree(l_or_es_id)
        else:
            return False

    def get_links_along_route_towards(self, dest_node_id: str, tc) -> List[link]:
        sp = shortest_path(self._DAG, source=self.stream.sender_es_id, target=dest_node_id)
        ret_l = []
        for i in range(len(sp)-1):
            ret_l.append(tc.L_from_nodes[sp[i]][sp[i+1]])
        return ret_l

    def xml_string(self, tc):
        r = '<route stream="{}">\n'.format(self.stream.id)
        for link in self.get_all_links_dfs(tc):
            r += '\t<link src="{}" dest="{}" />\n'.format(link.src.id, link.dest.id)
        r += "</route>"
        return r

    @classmethod
    def from_xml_node(cls, n: ET.Element, tc):
        r = cls(tc.F[n.attrib["stream"]])
        x_res_vec = {}
        for link_n in n:
            src_id = link_n.attrib["src"]
            dest_id = link_n.attrib["dest"]

            x_res_vec[dest_id] = src_id
        r.init_from_x_res_vector(x_res_vec)
        return r


@dataclass
class route_info:
    def __init__(self, r: route, route_len: int, overlap_number: int, overlap_links: set):
        self.route = r
        self.route_len = route_len
        self.overlap_number = overlap_number
        self.overlap_links = overlap_links
