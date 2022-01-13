from typing import Dict, List, Iterator, Tuple, Union, Generator, Optional

import networkx as nx
from networkx import DiGraph

from input.model.link import link
from input.model.nodes import end_system
from input.model.route import route
from input.model.stream import stream
from input.model.task import task

from tqdm.auto import tqdm


class TaskGraphNode:
    def __init__(self, id: str):
        self.id: str = id
        self.prev: Optional[TaskGraphNode] = None # previous element in order of application (This is not necessarily the predecessor in the application DAG!)
        self.next: Optional[TaskGraphNode] = None # next element in order of application (This is not necessarily the predecessor in the application DAG!)

    def __repr__(self):
        return f"(ID: {self.id}, Prev: {self.prev.id}, Next: {self.next.id})"

    def __str__(self):
        return self.__repr__()

class TaskGraphNode_Task(TaskGraphNode):
    def __init__(self, id: str, t: task):
        self.t = t
        self.es_id: str = t.src_es_id
        TaskGraphNode.__init__(self, id)

class TaskGraphNode_Stream(TaskGraphNode):
    def __init__(self, id: str, s: stream):
        self.s = s
        TaskGraphNode.__init__(self, id)

class TopologicalTaskGraphApp:
    def __init__(self, app_id: str, appDAG: DiGraph, task_graph):
        self.app_id = app_id
        self.appDAG = appDAG
        self.task_graph: PrecedenceGraph = task_graph
        self.internal_order = []

        for tgn_id in nx.topological_sort(appDAG):
            self.internal_order.append(tgn_id)

    def __repr__(self):
        return f"TGA_{self.app_id}"

class PrecedenceGraph:
    def __init__(self, DAG: DiGraph, nodes: Dict[str, TaskGraphNode]):
        self.DAG: DiGraph = DAG
        self.keyDAGs: List[Tuple[DiGraph, str]] = [] # Tuple[DAG, app.id]
        self.normalDAGs: List[Tuple[DiGraph, str]] = [] # Tuple[DAG, app.id]
        self.nodes: Dict[str, TaskGraphNode] = nodes

        self.order: Tuple[List[TopologicalTaskGraphApp], List[TopologicalTaskGraphApp]] = [] # Tuple[keyTGAs, normalTGAs]

    def initial_order(self) -> Tuple[List[TopologicalTaskGraphApp], List[TopologicalTaskGraphApp]]:
        """
        Return a list TopologicalTaskGraphApps, prioritizing key applications
        """
        order = ([], [])

        for tpl in self.keyDAGs:
            keyDAG = tpl[0]
            app_id = tpl[1]
            ttg_app = TopologicalTaskGraphApp(app_id, keyDAG, self)
            order[0].append(ttg_app)

        for tpl in self.normalDAGs:
            normalDAG = tpl[0]
            app_id = tpl[1]
            ttg_app = TopologicalTaskGraphApp(app_id, normalDAG, self)
            order[1].append(ttg_app)

        self.order = order

    def get_predecessors_ids(self, task_id: str) -> Iterator[str]:
        """
        Returns a list of tgn_ids for all predecessor tasks
        """
        return self.DAG.predecessors(task_id)

    def get_successors_ids(self, task_id: str) -> Iterator[str]:
        """
        Returns a list of tgn_ids for all successor tasks
        """
        return self.DAG.successors(task_id)

    def get_stream_tgn(self, stream_id: str) -> TaskGraphNode_Stream:
        return self.nodes[f"{stream_id}"]

    def get_task_tgn(self, task_id: str) -> TaskGraphNode_Task:
        return self.nodes[task_id]

    def get_tgn_by_id(self, tgn_id: str) -> TaskGraphNode:
        return self.nodes[tgn_id]

    def _add_application_interconnect_method(self, app, tc):
        # Interconnect method: Connect secure message to key apps
        # Add all tasks as nodes to the DAG
        for t in app.verticies.values():
            tgn_id = t.id
            tgn = TaskGraphNode_Task(tgn_id, t)
            self.DAG.add_node(tgn_id)
            self.nodes[tgn_id] = tgn

        # For each stream
        for s_id in app.edges.keys():
            s = tc.F[s_id]

            if s.is_self_stream():
                # Simply add edges for self-streams
                self.DAG.add_edge(s.sender_task_id, list(s.receiver_task_ids)[0])
            else:
                t_sender_id = s.sender_task_id

                # For secure streams: add a node for sender ES (For the MAC generation)
                if s.is_secure:
                    tgn_sender = TaskGraphNode_Stream(
                        f"{s_id}_{s.sender_es_id}",
                        s
                    )
                    self.DAG.add_node(tgn_sender.id)
                    self.nodes[tgn_sender.id] = tgn_sender
                    self.DAG.add_edge(t_sender_id, tgn_sender.id)
                else:
                    tgn_sender = self.nodes[t_sender_id]


                # Add a node for the stream
                tgn_id = f"{s_id}"
                tgn = TaskGraphNode_Stream(tgn_id, s)
                self.DAG.add_node(tgn_id)
                self.nodes[tgn_id] = tgn

                # Connect it to sender task
                # For secure streams: Connect it to MAC generation task
                self.DAG.add_edge(tgn_sender.id, tgn.id)

                # Connect stream node with receiver task nodes
                for reciever_t_id in s.receiver_task_ids:
                    receiver_es_id = self.nodes[reciever_t_id].es_id

                    # For secure streams: add a node for each receiver ES (MAC verification)
                    if s.is_secure:
                        tgn_receiver = TaskGraphNode_Stream(
                            f"{s_id}_{receiver_es_id}",
                            s
                        )
                        self.DAG.add_node(tgn_receiver.id)
                        self.nodes[tgn_receiver.id] = tgn_receiver
                        self.DAG.add_edge(tgn_receiver.id, reciever_t_id)

                        # For secure streams: connect the graph to the key application graph
                        key_release_task = tc.T_release[s.sender_es_id]
                        key_verify_task = tc.T_verify[s.sender_es_id][receiver_es_id]
                        # TODO: Connect to correct key application, not first ones
                        self.DAG.add_edge(tgn.id, key_release_task.id)
                        self.DAG.add_edge(key_verify_task.id, tgn_receiver.id)
                    else:
                        tgn_receiver = self.nodes[reciever_t_id]

                    self.DAG.add_edge(tgn.id, tgn_receiver.id)

    def _add_application_seperate_method(self, app, tc) -> DiGraph:
        # Seperate method: All applications are seperate

        appDAG = DiGraph()
        # Add all tasks as nodes to the DAG
        for t in app.verticies.values():
            tgn_id = t.id
            tgn = TaskGraphNode_Task(tgn_id, t)
            appDAG.add_node(tgn_id)
            self.nodes[tgn_id] = tgn

        # For each stream
        for s_id in app.edges.keys():
            s = tc.F[s_id]

            if s.is_self_stream():
                # Simply add edges for self-streams
                appDAG.add_edge(s.sender_task_id, list(s.receiver_task_ids)[0])
            else:
                t_sender_id = s.sender_task_id
                tgn_sender = self.nodes[t_sender_id]

                # Add a node for the stream
                tgn_id = f"{s_id}"
                tgn = TaskGraphNode_Stream(tgn_id, s)
                appDAG.add_node(tgn_id)
                self.nodes[tgn_id] = tgn

                # Connect it to sender task
                appDAG.add_edge(tgn_sender.id, tgn.id)

                # Connect stream node with receiver task nodes
                for reciever_t_id in s.receiver_task_ids:
                    tgn_receiver = self.nodes[reciever_t_id]
                    appDAG.add_edge(tgn.id, tgn_receiver.id)

        self.DAG.update(appDAG.edges, appDAG.nodes)
        if app.id in tc.A_sec:
            self.keyDAGs.append((appDAG, app.id))
        elif app.id in tc.A_app:
            self.normalDAGs.append((appDAG, app.id))
        else:
            raise ValueError


    @classmethod
    def from_applications(cls, tc):
        DAG = DiGraph()
        nodes = {}

        c = cls(
            DAG,
            nodes
        )

        # First add key apps, so they exist and can be connected when creating normal apps
        print("-" * 20 + " Creating task graph for key apps")
        for app in tqdm(tc.A_sec.values()):
            c._add_application_seperate_method(app, tc)

        print("-"*20 + " Creating task graph for normal apps")
        # Add normal apps
        for app in tqdm(tc.A_app.values()):
            c._add_application_seperate_method(app, tc)


        c.initial_order()
        return c