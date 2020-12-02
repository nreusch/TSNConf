import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple

from input.model.function_path import function_path
from input.model.signal import signal
from input.model.task import task


class EApplicationType(Enum):
    NORMAL = 1
    KEY = 2

@dataclass
class application:
    id: str
    verticies: Dict[str, task]  # task.id => task
    edges: Dict[str, Tuple]  # signal.id => (task1.id, task2.id)
    period: int
    type: EApplicationType
    function_paths: Dict[str, function_path]  # fp.id => fp
    authed_es_id: str

    def xml_string(self, S: Dict[str, signal]):
        s = ""
        if self.type == EApplicationType.NORMAL:
            s = '<application name="{}" period="{}" type="{}">\n'.format(
                self.id, self.period, self.type.name
            )
        elif self.type == EApplicationType.KEY:
            s = '<application name="{}" period="{}" type="{}" authed_es="{}">\n'.format(
                self.id, self.period, self.type.name, self.authed_es_id
            )
        else:
            raise ValueError("Application type not supported")

        s += "\t<tasks>\n"
        for t in self.verticies.values():
            s += "\t" * 2 + t.xml_string()
        s += "\t</tasks>\n"

        s += "\t<signals>\n"
        for sig_id in self.edges.keys():
            s += "\t" * 2 + S[sig_id].xml_string()
        s += "\t</signals>\n"

        if self.type == EApplicationType.NORMAL:
            s += "\t<functionpaths>\n"
            for fp in self.function_paths.values():
                strs = fp.xml_string().split("\n")
                for st in strs:
                    s += "\t\t" + st + "\n"
            s += "\t</functionpaths>\n"

        s += "</application>\n"

        return s

    @classmethod
    def from_xml_node(cls, n: ET.Element):
        id = n.attrib["name"]
        period = int(n.attrib["period"])
        type = EApplicationType[n.attrib["type"]]

        authed_es_id = ""
        if type == EApplicationType.KEY:
            authed_es_id = n.attrib["authed_es"]


        return cls(
            id,
            {},
            {},
            period,
            type,
            {},
            authed_es_id
        )

    @classmethod
    def from_params(cls, id: str, period: int, type: EApplicationType, authed_es_id=""):
        return cls(
            id,
            {},
            {},
            period,
            type,
            {},
            authed_es_id
        )