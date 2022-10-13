import xml.etree.ElementTree as ET
from pathlib import Path

from input.model.link import link
from input.model.nodes import end_system, switch
from input.model.route import route
from input.model.stream import stream
from input.testcase import Testcase


def _parse_device(n: ET.Element, tc: Testcase):
    nd = None
    if n.attrib["type"] == "topo:EndSystem" or n.attrib["type"] == "EndSystem" or n.attrib["type"] == "EndSystem_Verifier" or n.attrib["type"] == "EndSystem_Prover":
        nd = end_system.from_xml_node(n)
    elif n.attrib["type"] == "topo:Switch" or n.attrib["type"] == "Switch" :
        nd = switch.from_xml_node(n)
    assert nd != None

    tc.add_to_datastructures(nd)


def _parse_link(n: ET.Element, tc: Testcase):
    l = link.from_xml_node(n, tc.N, tc.link_speed)
    tc.add_to_datastructures(l)


def _parse_stream(n: ET.Element, tc: Testcase):

    s_list = stream.list_from_xml_node(n, tc.OH)

    for s in s_list:
        tc.add_to_datastructures(s)

    return tc

def _parse_route(n: ET.Element, tc: Testcase):
    # if no redundancy/security, skip routes of streams which are not considered
    if n.attrib["stream"] in tc.F:
        r = route.from_xml_node(n, tc)
        tc.add_to_datastructures(r)


def _parse_schedule(n: ET.Element, tc: Testcase):
    pass


def parse_to_model(tc_name:str, tc_path: str) -> Testcase:
    """
    Parses a given testcase file into a testcase object using our model
    """

    # 1. Initialize testcase object
    tc = Testcase(tc_name)

    # 2. Parse
    # noinspection PyTypeChecker
    xml_tree = ET.parse(Path(tc_path))
    xml_root = xml_tree.getroot()

    # 2.1 Parse root tag
    if "mtu" in xml_root.attrib:
        tc.W_f_max = int(xml_root.attrib["mtu"])
    else:
        tc.W_f_max = 1500

    if "frame_overhead" in xml_root.attrib:
        tc.OH = int(xml_root.attrib["frame_overhead"])
    else:
        tc.OH = 22

    if "link_speed" in xml_root.attrib:
        tc.link_speed = float(xml_root.attrib["link_speed"])

    # 2.2 Parse inner tags
    for n in xml_root:
        if n.tag == "device":
            _parse_device(n, tc)
        elif n.tag == "link":
            _parse_link(n, tc)
        elif n.tag == "stream":
            _parse_stream(n, tc)
        elif n.tag == "route":
            _parse_route(n, tc)
        elif n.tag == "schedule":
            _parse_schedule(n, tc)
        else:
            raise NotImplementedError()



    return tc
