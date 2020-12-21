import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict

from input.model.nodes import node


@dataclass(frozen=True)
class link:
    id: str
    src: node
    dest: node
    speed: float

    def __repr__(self):
        return "[{},{}]".format(self.src.id, self.dest.id)

    def __str__(self):
        return self.__repr__()

    def transmission_length(self, bytes: int):
        """
        Returns the amount of time it takes to transmit x bytes on this link
        """
        return math.ceil(bytes / self.speed)

    def xml_string(self):
        return '<link src="{}" dest="{}" speed="{:.2f}"/>\n'.format(
            self.src.id, self.dest.id, self.speed
        )

    @classmethod
    def from_xml_node(cls, n: ET.Element, tc_N: Dict):
        v_a = n.attrib["src"]
        v_b = n.attrib["dest"]
        id = "link_{}_{}".format(
            v_a, v_b
        )  # This format is required by security application signal parsing

        return cls(id, tc_N[v_a], tc_N[v_b], float(n.attrib["speed"]))
