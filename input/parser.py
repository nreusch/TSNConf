import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from input.model.application import application
from input.model.function_path import function_path
from input.model.link import link
from input.model.nodes import end_system, switch
from input.model.route import route
from input.model.schedule import schedule
from input.model.stream import stream
from input.model.task import task
from input.testcase import Testcase
from input.input_parameters import InputParameters


@dataclass
class tesla_parameters:
    security_task_initial_period: int
    key_frame_initial_period: int
    security_app_initial_period: int


def _parse_device(n: ET.Element, tc: Testcase):
    nd = None
    if n.attrib["type"] == "topo:EndSystem" or n.attrib["type"] == "EndSystem":
        nd = end_system.from_xml_node(n)
    elif n.attrib["type"] == "topo:Switch" or n.attrib["type"] == "Switch":
        nd = switch.from_xml_node(n)
    assert nd != None

    tc.add_to_datastructures(nd)


def _parse_link(n: ET.Element, tc: Testcase):
    l = link.from_xml_node(n, tc.N)
    tc.add_to_datastructures(l)


def _parse_application(n: ET.Element, tc: Testcase, input_params: InputParameters):
    app_id = n.attrib["name"]
    app_period = int(n.attrib["period"])

    App = application.from_xml_node(n)
    tc.add_to_datastructures(App)

    for app_node in n:
        if app_node.tag == "tasks":
            # Parse TASKS
            for task_n in app_node:
                t = task.from_xml_node(task_n, app_id, app_period)

                tc.add_to_datastructures(t)
        elif app_node.tag == "streams":
            # Parse STREAMS
            for stream_n in app_node:
                # We get a list of streams (one copy per RL)
                s_list = stream.list_from_xml_node(stream_n, tc.T, tc.W_mac, tc.OH, app_id)

                for s in s_list:
                    if input_params.no_redundancy:
                        if s.get_id_prefix() in tc.F_red:
                            # if no redundancy, skip redundant copies of streams
                            pass
                        else:
                            tc.add_to_datastructures(s)
                    else:
                        tc.add_to_datastructures(s)
        else:
            raise NotImplementedError()

def _parse_route(n: ET.Element, tc: Testcase):
    # if no redundancy/security, skip routes of streams which are not considered
    if n.attrib["stream"] in tc.F:
        r = route.from_xml_node(n, tc.F, tc.L_from_nodes)
        tc.add_to_datastructures(r)


def _parse_schedule(n: ET.Element, tc: Testcase):
    s = schedule.from_xml_node(n, tc.N, tc.T, tc.F, tc.L_from_nodes)
    tc.add_to_datastructures(s)


def _parse_function_path(n: ET.Element, tc: Testcase):
    fp = function_path.from_xml_node(n, tc.T)
    tc.add_to_datastructures(fp)


def parse_to_model(input_params: InputParameters) -> Testcase:
    """
    Parses a given testcase file into a testcase object using our model
    """

    # 1. Initialize testcase object
    tc = Testcase(input_params.tc_name)

    # 2. Parse
    # noinspection PyTypeChecker
    xml_tree = ET.parse(Path(input_params.tc_path))
    xml_root = xml_tree.getroot()

    # 2.1 Parse root tag
    if "mtu" in xml_root.attrib:
        tc.W_f_max = int(xml_root.attrib["mtu"])
    else:
        tc.W_f_max = 1500

    if "mac_length" in xml_root.attrib:
        tc.W_mac = int(xml_root.attrib["mac_length"])
    else:
        tc.W_mac = 16

    if "key_length" in xml_root.attrib:
        tc.key_length = int(xml_root.attrib["key_length"])
    else:
        tc.key_length = 16

    if "frame_overhead" in xml_root.attrib:
        tc.OH = int(xml_root.attrib["frame_overhead"])
    else:
        tc.OH = 22

    # 2.2 Parse inner tags
    for n in xml_root:
        if n.tag == "device":
            _parse_device(n, tc)
        elif n.tag == "link":
            _parse_link(n, tc)
        elif n.tag == "application":
            if "type" in n.attrib and n.attrib["type"] == "KEY" and input_params.no_security:
                # If no security, don' parse key apps
                pass
            else:
                _parse_application(n, tc, input_params)
        elif n.tag == "path":
            _parse_function_path(n, tc)
        elif n.tag == "route":
            _parse_route(n, tc)
        elif n.tag == "schedule":
            _parse_schedule(n, tc)
        else:
            raise NotImplementedError()

    # 3. Finalize testcase
    tc.finalize()

    return tc
