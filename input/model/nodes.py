import xml.etree.ElementTree as ET
from dataclasses import dataclass


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

    def __repr__(self):
        return "[{}]".format(self.id)

    def __str__(self):
        return self.__repr__()

    def to_xml_string(self):
        return '<device name="{}" type="EndSystem" mac_exec_time="{}"/>\n'.format(
            self.id, self.mac_exec_time
        )

    @classmethod
    def from_xml_node(cls, n: ET.Element):
        return cls(n.attrib["name"], int(n.attrib["mac_exec_time"]))


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
