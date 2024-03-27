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

        self.Pint: int = -1

        self.W_f_max: int = -1  # MTU
        self.OH: int = -1  # frame overhead
        self.hyperperiod = 0
        self.W_mac: int = -1  # MAC length
        self.key_length: int = -1  # TESLA key length
        self.highest_communication_depth = -1

        self.Periods: set = set()

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
        self.ES_verifier: Dict[str, end_system] = {}  # All end systems. es.id => end_system
        self.ES_prover: Dict[str, end_system] = {}  # All end systems. es.id => end_system

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
        self.T_release: Dict[str, task] = {} # key release tasks for ES. es.id => task
        self.T_verify: Dict[str, Dict[str, task]] = {}# key verify tasks for ES pai. es.id => Dict[es.id => task]
        self.A_sec: Dict[
            str, application
        ] = {}  # All security applications. security_application.id => application

    def add_to_datastructures(self, *X : Any):
        """
        Adds any object which is part of the model to the testcase and all its datastructures
        """
        for x in X:
            if isinstance(x, stream):
                if x.id in self.F:
                    raise ValueError(f"Cannot add stream {x.id} a second time")
                self.F[x.id] = x

                if x.app_id != "":
                    self.A[x.app_id].add_edges(x, self)

                self.F_t_out[x.sender_task_id].append(x)
                for task_id in x.receiver_task_ids:
                    self.F_t_in[task_id].append(x)

                # if x is a routed/scheduled stream, i.e. sender and receiver might be different
                if len(x.receiver_es_ids) > 1 or list(x.receiver_es_ids)[0] != x.sender_es_id or (x.sender_es_id == "" or list(x.receiver_es_ids)[0] == ""):
                    self.F_routed[x.id] = x

                    if x.sender_es_id != "":
                        self.F_g_out[x.sender_es_id].append(x)
                    for es_id in x.receiver_es_ids:
                        if es_id != "":
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
                if x.id in self.N:
                    raise ValueError(f"Cannot add node {x.id} a second time")

                self.N[x.id] = x
                self.N_conn[x.id] = set()
                self.N_conn_inv[x.id] = set()
                self.L_from_nodes[x.id] = {}

                if isinstance(x, end_system):
                    self.N_conn[x.id].add(x.id)
                    self.N_conn_inv[x.id].add(x.id)
                    self.ES[x.id] = x
                    if x.is_verifier():
                        self.ES_verifier[x.id] = x
                    elif x.is_prover():
                        self.ES_prover[x.id] = x
                    self.F_g_in[x.id] = []
                    self.F_g_out[x.id] = []
                    self.T_g[x.id] = []
                    self.T_sec_g[x.id] = []
                elif isinstance(x, switch):
                    self.SW[x.id] = x
            elif isinstance(x, link):
                if x.id in self.L:
                    raise ValueError(f"Cannot add link {x.id} a second time")
                self.L[x.id] = x
                self.L_from_nodes[x.src.id][x.dest.id] = x
                self.N_conn[x.src.id].add(x.dest.id)
                self.N_conn_inv[x.dest.id].add(x.src.id)
            elif isinstance(x, application):
                if x.id in self.A:
                    raise ValueError(f"Cannot add app {x.id} a second time")
                self.A[x.id] = x
                if x.period not in self.Periods:
                    self.Periods.add(x.period)
                    self.hyperperiod = lcm(list([p for p in self.Periods if p > 0]))
                if x.type == EApplicationType.NORMAL or x.type == EApplicationType.EDGE:
                    self.A_app[x.id] = x
                    #
                    self.T_normal[x.id] = []
                elif x.type == EApplicationType.KEY:
                    self.A_sec[x.id] = x
            elif isinstance(x, function_path):
                self.FP[x.id] = x
            elif isinstance(x, task):
                if x.id in self.T:
                    raise ValueError(f"Cannot add task {x.id} a second time")
                self.T[x.id] = x
                if x.src_es_id != "":
                    self.T_g[x.src_es_id].append(x)
                    x.allowed_assignments = [x.src_es_id]
                else:
                    # if there are no allowed assignments given, all ES are allowed for mapping
                    if len(x.allowed_assignments) == 0 or x.allowed_assignments == None:
                        x.allowed_assignments = list(self.ES.keys())

                self.F_t_out[x.id] = []
                self.F_t_in[x.id] = []

                if x.app_id == "":
                    self.T_standalone[x.id] = x
                else:
                    self.A[x.app_id].add_vertex(x)
                    if x.type == ETaskType.NORMAL or x.type == ETaskType.EDGE:
                        self.T_normal[x.app_id].append(x)

                if x.type == ETaskType.KEY_RELEASE:
                    self.T_sec[x.id] = x
                    if x.src_es_id != "":
                        self.T_sec_g[x.src_es_id].append(x)
                        self.T_release[x.src_es_id] = x

                if x.type == ETaskType.KEY_VERIFICATION:
                    self.T_sec[x.id] = x
                    if x.src_es_id != "":
                        self.T_sec_g[x.src_es_id].append(x)

                    if x.corr_release_task_es_id not in self.T_verify:
                        self.T_verify[x.corr_release_task_es_id] = {}
                    self.T_verify[x.corr_release_task_es_id][x.src_es_id] = x

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
            strs = route.xml_string(self).split("\n")
            for st in strs:
                s += "\t" + st + "\n"

        s += "\n"
        # Schedule
        schedule = self.schedule
        if schedule != None:
            strs = schedule.xml_string(self).split("\n")
            for st in strs:
                s += "\t" + st + "\n"
        s += "</NetworkDescription>"
        return s

    def clear_routes(self):
        self.R = {}
        self.R_info = {}

    def to_luxi_files(self):
        sched = ""
        msg = ""
        portbu = ""
        rate = ""
        vls = ""

        # vls
        # create a virtual link for each stream route
        s_to_vl_map = {}
        vl_number = 0
        vl_strings = ["#generated"]
        for s in self.F.values():
            if s.id in self.R:
                links = self.R[s.id].get_all_links_dfs(self)
                s_to_vl_map[s.id] = vl_number
                vl_string = f"vl{vl_number} : "
                vl_number += 1
                for l in links:
                    vl_string += f"{l.src.id},{l.dest.id} ; "
                vl_strings.append(vl_string)
        vls = "\n".join(vl_strings)

        # msg
        # create a message for each stream copy
        msg_strings = ["#!R id, size(byte), deadline, <virtual link id>, type [TT, RC], [period | rate] (us), [offset | ] [packed | fragmented]"]
        for s in self.F.values():
            if s.id in s_to_vl_map:
                msg_string = f"{s.id}, {s.size}, {s.period}, vl{s_to_vl_map[s.id]}, TT,0, {s.period}"
            else:
                msg_string = f"{s.id}, {s.size}, {s.period}, NOTROUTED, TT,0, {s.period}"
            msg_strings.append(msg_string)
        msg = "\n".join(msg_strings)

        # sched
        # for each link (including es -> sw links) list blocks
        if self.schedule == None:
            raise ValueError("Can't serialize to Luxi format. Schedule missing")

        port_occupations = {}
        sched_strings = []

        for l in self.L.values():
            if l.id in self.schedule.o_f_val:
                port_occupations[l.id] = 0
                sched_strings.append(f"{l.src.id},{l.dest.id}")
                offsets = []
                offset_to_af_and_stream_id = {}
                for f_id, o_f in self.schedule.o_f_val[l.id].items():
                    a_f = self.schedule.a_f_val[l.id][f_id]
                    f = self.F[f_id]

                    if a_f != o_f:
                        for i_period in range(int(self.hyperperiod / f.period)):
                            port_occupations[l.id] += a_f-o_f
                            o = i_period * f.period + o_f
                            a = i_period * f.period + a_f
                            offsets.append(o)
                            offset_to_af_and_stream_id[o] = (a, f_id, i_period)

                for o in sorted(offsets):
                    sched_string = f"{o}\t{offset_to_af_and_stream_id[o][0]}\t{offset_to_af_and_stream_id[o][1]}\t{offset_to_af_and_stream_id[o][2]}"
                    sched_strings.append(sched_string)
                sched_strings.append("")
        sched = "\n".join(sched_strings)

        # rate
        # we assume that each link has the same rate
        link_speeds = {l.speed for l in self.L.values()}
        if len(link_speeds) > 1:
            raise ValueError("Can't serialize to Luxi format. Different link speeds found")

        link_speed = link_speeds.pop() * 8

        rate = f"# link rate\n{link_speed}"

        # portbu
        # multiply link_speed by inverse of port occupation percent
        portbu_strings = ["#leftover bandwidth usage for each egress port (Mb/s)"]
        for l in self.L.values():
            if l.id in port_occupations:
                portbu_strings.append(f"{l.src.id},{l.dest.id}:{link_speed - (port_occupations[l.id]/self.hyperperiod * link_speed)}")
        portbu = "\n".join(portbu_strings)

        return sched, msg, portbu, rate, vls

