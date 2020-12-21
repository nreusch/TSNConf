from typing import Any, Dict, List, Set

from input.model.application import (EApplicationType, application)
from input.model.function_path import function_path
from input.model.link import link
from input.model.nodes import end_system, node, switch
from input.model.route import route, route_info
from input.model.schedule import schedule
from input.model.stream import EStreamType, stream
from input.model.task import ETaskType, task
from utils.utilities import lcm


class Testcase:
    def __init__(self, name: str):
        self.name: str = name
        self.schedule: schedule = None

        self.Pint: int = 0

        self.W_f_max: int = -1  # MTU
        self.OH: int = -1  # frame overhead
        self.hyperperiod = 0
        self.W_mac: int = -1  # MAC length
        self.key_length: int = -1  # TESLA key length

        self.F: Dict[str, stream] = {}  # All streams. stream.id => stream
        self.F_routed: Dict[str, stream] = {} # All routed/scheduled streams. stream-id => stream
        self.F_red: Dict[
            str, List[stream]
        ] = (
            {}
        )  # All redundant copies of a stream. stream.id (without suffix) => List[stream]
        self.F_g_out: Dict[
            str, List[stream]
        ] = {}  # Mapping ES to outgoing streams. ES.id => [stream]
        self.F_g_in: Dict[
            str, List[stream]
        ] = {}  # Mapping ES to incoming streams. ES.id => [stream]
        self.F_t_out: Dict[
            str, List[stream]
        ] = {}  # Mapping task to outgoing streams. task.id => [stream]
        self.F_t_in: Dict[
            str, List[stream]
        ] = {}  # Mapping task to incoming streams. task.id => [stream]

        self.R: Dict[str, route] = {}  # All routes. stream.id => route
        self.R_info: Dict[str, route_info] = {}  # All routes. stream.id => route_info

        self.N: Dict[str, node] = {}  # All nodes. node.id => nodes
        self.N_conn: Dict[
            str, Set[str]
        ] = {}  # All nodes. node.id => Set of nodes that n points at. Includes n
        self.N_conn_inv: Dict[
            str, Set[str]
        ] = {}  # All nodes. n.id => Set of nodes that point at n. Includes n

        self.ES: Dict[str, end_system] = {}  # All end systems. es.id => end_system

        self.SW: Dict[str, switch] = {}  # All switches. sw.id => switch
        self.L: Dict[str, link] = {}  # All links. link.id => link
        self.L_from_nodes: Dict[
            str, Dict[str, link]
        ] = {}  # Link from n1 to n2 or None. n1.id => Dict[n2.id -> link]

        self.A: Dict[str, application] = {}  # All applications. app.id => application
        self.A_app: Dict[
            str, application
        ] = {}  # All normal applications. app.id => normal_application
        self.FP: Dict[
            str, function_path
        ] = {}  # All function paths. fp.id => function_path

        self.T: Dict[str, task] = {}  # All tasks. task.id => task
        self.T_normal: Dict[
            str, List[task]
        ] = (
            {}
        )  # All normal tasks from normal applications. normal_application.id => [task]
        self.T_g: Dict[
            str, List[task]
        ] = {}  # Mapping ES to its tasks. node.id => [task]
        self.T_standalone: Dict[str, task] = {} # All tasks outside applications

        self.F_sec: Dict[str, stream] = {} # All streams from security applications. security_application.id => [stream]
        self.T_sec: Dict[str, task] = {}  # All key tasks. task.id -> task
        self.T_sec_g: Dict[str, List[task]] = {}  # All key tasks. node.id => [task]
        self.A_sec: Dict[
            str, application
        ] = {}  # All security applications. security_application.id => application

    def finalize(self):
        self.hyperperiod = lcm([t.period for t in self.T.values()])

    def add_to_datastructures(self, x: Any):
        """
        Adds any object which is part of the model_old to the testcase and all its datastructures
        """
        if isinstance(x, stream):
            self.F[x.id] = x

            if x.app_id != "":
                self.A[x.app_id].add_edges(x)

            self.F_t_out[x.sender_task_id].append(x)
            for task_id in x.receiver_task_ids:
                self.F_t_in[task_id].append(x)

            # if x is a routed/scheduled stream
            if len(x.receiver_es_ids) > 1 or list(x.receiver_es_ids)[0] != x.sender_es_id:
                self.F_routed[x.id] = x

                self.F_g_out[x.sender_es_id].append(x)
                for es_id in x.receiver_es_ids:
                    self.F_g_in[es_id].append(x)


                if x.get_id_prefix() in self.F_red:
                    self.F_red[x.get_id_prefix()].append(x)
                else:
                    self.F_red[x.get_id_prefix()] = [x]

                if x.type == EStreamType.KEY:
                    self.F_sec[x.id] = x
        elif isinstance(x, route):
            self.R[x.stream.id] = x
        elif isinstance(x, route_info):
            self.R_info[x.route.stream.id] = x
        elif isinstance(x, schedule):
            self.schedule = x
        elif isinstance(x, node):
            self.N[x.id] = x
            self.N_conn[x.id] = set()
            self.N_conn_inv[x.id] = set()
            self.L_from_nodes[x.id] = {}

            if isinstance(x, end_system):
                self.N_conn[x.id].add(x.id)
                self.N_conn_inv[x.id].add(x.id)
                self.ES[x.id] = x
                self.F_g_in[x.id] = []
                self.F_g_out[x.id] = []
                self.T_g[x.id] = []
                self.T_sec_g[x.id] = []
            elif isinstance(x, switch):
                self.SW[x.id] = x
        elif isinstance(x, link):
            self.L[x.id] = x
            self.L_from_nodes[x.src.id][x.dest.id] = x
            self.N_conn[x.src.id].add(x.dest.id)
            self.N_conn_inv[x.dest.id].add(x.src.id)
        elif isinstance(x, application):
            self.A[x.id] = x
            if x.type == EApplicationType.NORMAL:
                self.A_app[x.id] = x
                #
                self.T_normal[x.id] = []
            elif x.type == EApplicationType.KEY:
                self.A_sec[x.id] = x
        elif isinstance(x, function_path):
            self.FP[x.id] = x
        elif isinstance(x, task):
            self.T[x.id] = x
            self.T_g[x.src_es_id].append(x)
            self.F_t_out[x.id] = []
            self.F_t_in[x.id] = []

            if x.app_id == "":
                self.T_standalone[x.id] = x
            else:
                self.A[x.app_id].add_vertex(x)
                if x.type == ETaskType.NORMAL:
                    self.T_normal[x.app_id].append(x)

            if x.type == ETaskType.KEY_VERIFICATION or x.type == ETaskType.KEY_RELEASE:
                self.T_sec[x.id] = x
                self.T_sec_g[x.src_es_id].append(x)

    def to_flex_network_description(self):
        s = ""
        s += "<!-- mtu, overhead, mac_length in Byte. All times in us-->\n"
        s += '<NetworkDescription mtu="{}" frame_overhead="{}" key_length="{}" mac_length="{}">\n'.format(
            self.W_f_max, self.W_mac, self.key_length, self.OH
        )
        s += "\t<!-- Expected order: devices, links, applications(tasks, signals, (functionpaths)), streams, routes, schedule-->\n"

        # Devices
        for sw in self.SW.values():
            s += "\t{}".format(sw.xml_string())

        for es in self.ES.values():
            s += "\t{}".format(es.to_xml_string())

        # Links
        s += "\n\t<!-- Links are directional. speed = byte/us -->\n"

        for n, l_dict in self.L_from_nodes.items():
            for l in l_dict.values():
                s += "\t{}".format(l.xml_string())

        # Applications
        s += "\n\t<!-- period&wcet is in us, size in Byte-->\n"

        for app in self.A.values():
            strs = app.xml_string(self.F).split("\n")
            for st in strs:
                s += "\t" + st + "\n"

        s += "\n"

        # Function Paths
        for fp in self.FP.values():
            strs = fp.xml_string().split("\n")
            for st in strs:
                s += "\t" + st + "\n"

        s += "\n"

        # Routes
        for route in self.R.values():
            strs = route.xml_string(self.L_from_nodes).split("\n")
            for st in strs:
                s += "\t" + st + "\n"

        s += "\n"
        # Schedule
        schedule = self.schedule
        if schedule != None:
            strs = schedule.xml_string(self.N, self.L, self.T, self.F_sec).split("\n")
            for st in strs:
                s += "\t" + st + "\n"
        s += "</NetworkDescription>"
        return s
