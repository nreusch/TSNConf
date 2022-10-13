from typing import Any, Dict, List, Set

from utils.utilities import lcm

from input.model.link import link
from input.model.nodes import end_system, node, switch
from input.model.route import route, route_info
from input.model.stream import stream


class Testcase:
    def __init__(self, name: str):
        self.name: str = name
        self.schedule = None

        self.W_f_max: int = -1  # MTU
        self.OH: int = -1  # frame overhead
        self.hyperperiod = 0
        self.highest_communication_depth = -1
        self.link_speed: float = -1

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

        self.F_l_out: Dict[
            str, List[str]
        ] = {}  # Mapping links to passing streams. l.id => [stream.id]


        self.F_sw_out: Dict[
            str, List[str]
        ] = {} # Mapping switches to passing streams. sw.id => [stream.id]
        self.F_prio: Dict[
            int, List[str]
        ] = {}  # Mapping priorities to streams. priority => [stream.id]

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
        self.SW_port: Dict[str, Set[str]] = {} # Represents used ports. sw.id => set(es/sw ids)
        self.L: Dict[str, link] = {}  # All links. link.id => link
        self.L_from_nodes: Dict[
            str, Dict[str, link]
        ] = {}  # Link from n1 to n2 or None. n1.id => Dict[n2.id -> link]

        self.min_windows_sizes: Dict[str, Dict[int, int]] = {} # l_id -> Dict[priority -> min_size]

    def add_to_datastructures(self, *X : Any):
        """
        Adds any object which is part of the model to the testcase and all its datastructures
        """
        for x in X:
            if isinstance(x, stream):
                if x.id in self.F:
                    raise ValueError(f"Cannot add stream {x.id} a second time")
                self.F[x.id] = x

                if x.priority not in self.F_prio:
                    self.F_prio[x.priority] = [x]
                else:
                    self.F_prio[x.priority].append(x)

                if x.period not in self.Periods:
                    self.Periods.add(x.period)
                    self.hyperperiod = lcm(list([p for p in self.Periods if p > 0]))

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

            elif isinstance(x, route):
                self.R[x.stream.id] = x

                for l in x.get_all_links_dfs(self):
                    if l.id in self.F_l_out:
                        self.F_l_out[l.id].append(x.stream.id)
                    else:
                        self.F_l_out[l.id] = [x.stream.id]

                    if l.src.id in self.SW:
                        if l.src.id in self.F_sw_out:
                            self.F_sw_out[l.src.id].append(x.stream.id)
                        else:
                            self.F_sw_out[l.src.id] = [x.stream.id]

                        if l.src.id in self.SW_port:
                            self.SW_port[l.src.id].add(l.dest.id)
                        else:
                            self.SW_port[l.src.id] = {l.dest.id}

                    # Set min window size to maximimum send time of all stream in queue
                    if x.stream.priority not in self.min_windows_sizes[l.id]:
                        self.min_windows_sizes[l.id][x.stream.priority] = 0

                    self.min_windows_sizes[l.id][x.stream.priority] = max(self.min_windows_sizes[l.id][x.stream.priority], l.transmission_length(x.stream.size))
            elif isinstance(x, route_info):
                self.R_info[x.route.stream.id] = x
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
                    self.F_g_in[x.id] = []
                    self.F_g_out[x.id] = []
                elif isinstance(x, switch):
                    self.SW[x.id] = x
                    self.SW_port[x.id] = set()
            elif isinstance(x, link):
                if x.id in self.L:
                    raise ValueError(f"Cannot add link {x.id} a second time")
                self.L[x.id] = x
                self.L_from_nodes[x.src.id][x.dest.id] = x
                self.N_conn[x.src.id].add(x.dest.id)
                self.N_conn_inv[x.dest.id].add(x.src.id)
                self.min_windows_sizes[x.id] = {}

    def to_flex_network_description(self):
        s = ""
        s += "<!-- mtu, overhead, mac_length in Byte. All times in us-->\n"
        s += '<NetworkDescription mtu="{}" frame_overhead="{}" key_length="{}" mac_length="{}" link_speed="{}">\n'.format(
            self.W_f_max, 0, 0, self.OH, self.link_speed
        )
        s += "\t<!-- Expected order: devices, links, streams, routes, schedule-->\n"

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

        # Streams
        s += "\n\t<!-- period is in us, size in Byte-->\n"

        for str in self.F.values():
            s += "\t{}".format(str.xml_string())

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
        msg = ""
        rate = ""
        vls = ""

        # vls
        # create a virtual link for each stream route
        s_to_vl_map = {}
        vl_number = 0
        vl_strings = ["#generated"]
        for s in self.F.values():
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
        msg_strings = ["#id, size(byte), deadline (us), <virtual link id>, TT, priority, period (us)"]
        for s in self.F.values():
            msg_string = f"{s.id}, {s.size}, {s.period}, vl{s_to_vl_map[s.id]}, TT, {s.priority}, {s.period}"
            msg_strings.append(msg_string)
        msg = "\n".join(msg_strings)

        # rate
        # we assume that each link has the same rate
        if self.link_speed != -1:
            link_speed = self.link_speed * 8
        else:
            link_speeds = {l.speed for l in self.L.values()}
            if len(link_speeds) > 1:
                raise ValueError("Can't serialize to Luxi format. Different link speeds found")

            link_speed = float(link_speeds.pop()) * 8

        rate = f"# link rate\n{int(link_speed)}"

        # portbu
        # multiply link_speed by inverse of port occupation percent
        """
        portbu_strings = ["#leftover bandwidth usage for each egress port (Mb/s)"]
        for l in self.L.values():
            if l.id in port_occupations:
                portbu_strings.append(f"{l.src.id},{l.dest.id}:{link_speed - (port_occupations[l.id]/self.hyperperiod * link_speed)}")
        portbu = "\n".join(portbu_strings)
        """
        return msg, rate, vls

