import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum


@dataclass(
    frozen=True
)  # pretends class is immutable. Adds all arguments constructor and equals methods
class node:
    id: str

    def __repr__(self):
        return "[{}]".format(self.id)

    def __str__(self):
        return self.__repr__()

@dataclass(frozen=True)
class end_system(node):
    mac_exec_time: int
    max_utilization: float
    wcet_factor: float
    type: str

    def __repr__(self):
        return "[{}]".format(self.id)

    def __str__(self):
        return self.__repr__()

    def is_verifier(self):
        return "Verifier" in self.type

    def is_prover(self):
        return "Prover" in self.type

    def to_xml_string(self):
        return '<device name="{}" type="{}" mac_exec_time="{}" max_utilization="{}" wcet_factor="{}"/>\n'.format(
            self.id, self.type, self.mac_exec_time, self.max_utilization, self.wcet_factor
        )

    @classmethod
    def from_xml_node(cls, n: ET.Element):
        if "mac_exec_time" in n.attrib:
            met = int(n.attrib["mac_exec_time"])
        else:
            met = 10

        if "max_utilization" in n.attrib:
            max_util = float(n.attrib["max_utilization"])
        else:
            max_util = 1

        if "wcet_factor" in n.attrib:
            wcet_factor = float(n.attrib["wcet_factor"])
        else:
            wcet_factor = 1

        type = n.attrib["type"]

        return cls(n.attrib["name"], met, max_util, wcet_factor, type)


@dataclass(frozen=True)
class switch(node):
    def __repr__(self):
        return "[{}]".format(self.id)

    def __str__(self):
        return self.__repr__()

    def xml_string(self):
        return '<device name="{}" type="Switch"/>\n'.format(self.id)

    @classmethod
    def from_xml_node(cls, n: ET.Element):
        return cls(n.attrib["name"])
