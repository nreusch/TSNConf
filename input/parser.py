import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from input.model.application import application
from input.model.function_path import function_path
from input.model.link import link
from input.model.nodes import end_system, switch
from input.model.route import route
from input.model.schedule import schedule
from input.model.signal import signal
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
                t = task.from_xml_node(task_n, app_id, app_period, input_params)

                tc.add_to_datastructures(t)
        elif app_node.tag == "signals":
            # Parse SIGNALS
            for signal_n in app_node:
                s = signal.from_xml_node(signal_n, tc.T, app_id, app_period, input_params)

                tc.add_to_datastructures(s)
        elif app_node.tag == "functionpaths":
            # Parse FUNCTION_PATHS
            for path_n in app_node:
                fp = function_path.from_xml_node(path_n, app_id, App.verticies)

                tc.add_to_datastructures(fp)
        else:
            raise NotImplementedError()


def _parse_stream(n, tc, input_params: InputParameters):
    st = stream.from_xml_node(n, tc.OH, tc.S_group)

    if input_params.no_redundancy:
        if st.get_id_prefix() in tc.F_red:
            # if no redundancy, skip redundant copies of streams
            pass
        else:
            tc.add_to_datastructures(st)
    else:
        tc.add_to_datastructures(st)




def _parse_route(n, tc):
    # if no redundancy/security, skip routes of streams which are not considered
    if n.attrib["stream"] in tc.F:
        r = route.from_xml_node(n, tc.F, tc.L_from_nodes)
        tc.add_to_datastructures(r)


def _parse_schedule(n, tc):
    s = schedule.from_xml_node(n, tc.N, tc.T, tc.F, tc.L_from_nodes)
    tc.add_to_datastructures(s)


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
    tc.W_f_max = int(xml_root.attrib["mtu"])
    tc.W_mac = int(xml_root.attrib["mac_length"])
    tc.key_length = int(xml_root.attrib["key_length"])
    tc.OH = int(xml_root.attrib["frame_overhead"])

    # 2.2 Parse inner tags
    for n in xml_root:
        if n.tag == "device":
            _parse_device(n, tc)
        elif n.tag == "link":
            _parse_link(n, tc)
        elif n.tag == "application":
            if n.attrib["type"] == "KEY" and input_params.no_security:
                # If no security, don' parse key apps
                pass
            else:
                _parse_application(n, tc, input_params)
        elif n.tag == "stream":
            if n.attrib["type"] == "KEY" and input_params.no_security:
                # If no security, don' parse key streams
                pass
            else:
                _parse_stream(n, tc, input_params)
        elif n.tag == "route":
            _parse_route(n, tc)
        elif n.tag == "schedule":
            _parse_schedule(n, tc)
        else:
            raise NotImplementedError()

    # 3. Finalize testcase
    tc.finalize()

    return tc
