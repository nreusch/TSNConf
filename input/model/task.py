import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class ETaskType(Enum):
    NORMAL = 1
    KEY_RELEASE = 2
    KEY_VERIFICATION = 3
    EDGE = 4


@dataclass
class task:
    id: str
    app_id: str
    src_es_id: str
    exec_time: int
    period: int
    arrival_time: int
    type: ETaskType
    allowed_assignments: List[str] # mapping tasks to a list of ES they can be mapped to task.id => [ES.id]

    def __repr__(self):
        return f"{self.id}"
    def xml_string(self):
        return '<task name="{}" node="{}" wcet="{}" period="{}" arrival_time="{}" type="{}"/>\n'.format(
            self.id,
            self.src_es_id,
            self.exec_time,
            self.period,
            self.arrival_time,
            self.type.name,
        )

    @classmethod
    def from_xml_node(cls, n: ET.Element, app_id: str = "", app_period: int = -1):
        id = n.attrib["name"]
        wcet = int(n.attrib["wcet"])

        if "node" in n.attrib:
            src_es_id = n.attrib["node"]
        else:
            src_es_id = ""

        if "allowed_assignments" in n.attrib:
            allowed_assignments = n.attrib["allowed_assignments"].replace(" ", "").split(",")
        else:
            allowed_assignments = []

        if app_id != "" and app_period != -1:
            period = app_period
        else:
            period = int(n.attrib["period"])

        if "type" in n.attrib:
            type = ETaskType[n.attrib["type"]]
        else:
            type = ETaskType["NORMAL"]

        if "arrival_time" in n.attrib:
            arrival_time = int(n.attrib["arrival_time"])
        else:
            arrival_time = 0

        return cls(
            id, app_id, src_es_id, wcet, period, arrival_time, type, allowed_assignments
        )


@dataclass
class key_verification_task(task):
    corr_release_task_es_id: str

    def xml_string(self):
        return '<task name="{}" node="{}" wcet="{}" period="{}" arrival_time="{}" type="{}" release_es="{}"/>\n'.format(
            self.id,
            self.src_es_id,
            self.exec_time,
            self.period,
            self.arrival_time,
            self.type.name,
            self.corr_release_task_es_id,
        )
