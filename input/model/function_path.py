import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List

from input.model.task import task


def calculate_signal_level(path_n: ET.Element, _vertices):
    signal_level = 0
    previous_pe = _vertices[path_n[0].attrib["name"]].src_es_id
    for task_n in path_n:
        pe = _vertices[task_n.attrib["name"]].src_es_id
        if pe != previous_pe:
            signal_level += 1
        previous_pe = pe
    signal_level += 1

    return signal_level


@dataclass
class function_path:
    id: str
    app_id: str
    path: List[task]
    deadline: int
    signal_level: int  # number of tasks that receive signals

    def xml_string(self):
        s = '<path name="{}" deadline="{}">\n'.format(self.id, self.deadline)
        for t in self.path:
            s += '\t<task name="{}"/>\n'.format(t.id)
        s += "</path>"
        return s

    @classmethod
    def from_xml_node(cls, n: ET.Element, app_id: str, app_verticies: Dict):
        signal_level = calculate_signal_level(n, app_verticies)
        # Create path
        __tasks = []
        for path_task_n in n:
            __tasks.append(app_verticies[path_task_n.attrib["name"]])

        return cls(
            n.attrib["name"], app_id, __tasks, int(n.attrib["deadline"]), signal_level
        )
