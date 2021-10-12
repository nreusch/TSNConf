import xml.etree.ElementTree as ET
from enum import Enum
from typing import Dict, Tuple, List, Set

from networkx import DiGraph
import networkx as nx

from input.model.stream import stream
from input.model.task import task


class EApplicationType(Enum):
    NORMAL = 1
    KEY = 2
    EDGE = 3

class application:
    def __init__(self, id: str, period: int, type: EApplicationType, authed_es_id: str = ""):
        self.id: str = id
        self.period: int = period
        self.type: EApplicationType = type
        self.authed_es_id: str = authed_es_id

        self.verticies: Dict[str, task] = {}  # task.id => task
        self.edges: Dict[str, List[Tuple]] = {}  # stream.id => List[(task1.id, task2.id)]
        self.edges_from_nodes: Dict[str, Dict[str, List[str]]] = {}  # task1.id => (task2.id => List[stream.id])
        self._DAG: DiGraph = DiGraph()

        self.root_vertex_ids: Dict[str, None] = {}
        self.leaf_vertex_ids: Dict[str, None] = {}

    def __repr__(self):
        return "app({})".format(self.id)

    def __str__(self):
        return self.__repr__()

    def _update_roots_and_leafs(self):
        self.root_vertex_ids.clear()
        self.leaf_vertex_ids.clear()

        for t_id in self.verticies.keys():
            if self.in_degree(t_id) == 0:
                self.root_vertex_ids[t_id] = None
            if self.out_degree(t_id) == 0:
                self.leaf_vertex_ids[t_id] = None

    def add_vertex(self, t: task):
        self.verticies[t.id] = t
        self._DAG.add_node(t.id)

        self._update_roots_and_leafs()

    def add_edges(self, s: stream, tc):
        for dest_task_id in s.receiver_task_ids:
            if s.id not in self.edges:
                self.edges[s.id] = [(s.sender_task_id, dest_task_id)]
            else:
                self.edges[s.id].append((s.sender_task_id, dest_task_id))

            if s.sender_task_id not in self.edges_from_nodes:
                self.edges_from_nodes[s.sender_task_id] = {}

            if dest_task_id not in self.edges_from_nodes[s.sender_task_id]:
                self.edges_from_nodes[s.sender_task_id][dest_task_id] = [s.id]
            else:
                self.edges_from_nodes[s.sender_task_id][dest_task_id].append(s.id)

            # Weigh edges for self-streams as 0, so it is easy to determine the communication depth
            if tc.T[s.sender_task_id].src_es_id != tc.T[dest_task_id].src_es_id:
                self._DAG.add_edge(s.sender_task_id, dest_task_id, weight=1)
            else:
                self._DAG.add_edge(s.sender_task_id, dest_task_id, weight=0)

        self._update_roots_and_leafs()

    def get_communication_depth(self):
        # Weigh edges for self-streams as 0, so it is easy to determine the communication depth
        return nx.dag_longest_path_length(self._DAG)

    def get_stream_id_list_from_x_to_y(self, x: str, y: str) -> List[str]:
        return self.edges_from_nodes[x][y]

    def get_predecessors_ids(self, task_id: str):
        """
        Returns a list of task_ids for all predecessor tasks
        """
        return self._DAG.predecessors(task_id)

    def get_successors_ids(self, task_id: str):
        """
        Returns a list of task_ids for all successor tasks
        """
        return self._DAG.successors(task_id)

    def get_topological_order(self):
        l = []
        for t_id in nx.topological_sort(self._DAG):
            l.append(t_id)
        return l

    def in_degree(self, t_id: str) -> int:
        return self._DAG.in_degree(t_id)

    def out_degree(self, t_id: str) ->int :
        return self._DAG.out_degree(t_id)

    def xml_string(self, tc_F: Dict[str, stream]):
        s = ""
        if self.type == EApplicationType.NORMAL or self.type == EApplicationType.EDGE:
            s = '<application name="{}" period="{}" type="{}">\n'.format(
                self.id, self.period, self.type.name
            )
        elif self.type == EApplicationType.KEY:
            s = '<application name="{}" period="{}" type="{}" authed_es="{}">\n'.format(
                self.id, self.period, self.type.name, self.authed_es_id
            )
        else:
            raise ValueError("Application type not supported")

        s += "\t<tasks>\n"
        for t in self.verticies.values():
            s += "\t" * 2 + t.xml_string()
        s += "\t</tasks>\n"

        s += "\t<streams>\n"
        serialized_prefixes = []
        for s_id in self.edges.keys():
            if tc_F[s_id].get_id_prefix() not in serialized_prefixes:
                s += "\t" * 2 + tc_F[s_id].xml_string()
                serialized_prefixes.append(tc_F[s_id].get_id_prefix())
        s += "\t</streams>\n"

        s += "</application>\n"

        return s

    @classmethod
    def from_xml_node(cls, n: ET.Element):
        id = n.attrib["name"]
        period = int(n.attrib["period"])

        if "type" in n.attrib:
            type = EApplicationType[n.attrib["type"]]
        else:
            type = EApplicationType["NORMAL"]

        authed_es_id = ""
        if type == EApplicationType.KEY:
            authed_es_id = n.attrib["authed_es"]


        return cls(
            id,
            period,
            type,
            authed_es_id
        )

    @classmethod
    def from_params(cls, id: str, period: int, type: EApplicationType, authed_es_id=""):
        return cls(
            id,
            period,
            type,
            authed_es_id
        )