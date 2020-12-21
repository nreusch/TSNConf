import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum

class ETaskType(Enum):
    NORMAL = 1
    KEY_RELEASE = 2
    KEY_VERIFICATION = 3


@dataclass
class task:
    id: str
    app_id: str
    src_es_id: str
    exec_time: int
    period: int
    type: ETaskType

    def xml_string(self):
        return '<task name="{}" node="{}" wcet="{}" period="{}" type="{}"/>\n'.format(
            self.id,
            self.src_es_id,
            self.exec_time,
            self.period,
            self.type.name,
        )

    @classmethod
    def from_xml_node(cls, n: ET.Element, app_id: str = "", app_period: int = -1):
        id = n.attrib["name"]
        src_es_id = n.attrib["node"]
        wcet = int(n.attrib["wcet"])

        if app_id != "" and app_period != -1:
            period = app_period
        else:
            period = int(n.attrib["period"])

        if "type" in n.attrib:
            type = ETaskType[n.attrib["type"]]
        else:
            type = ETaskType["NORMAL"]

        return cls(
            id, app_id, src_es_id, wcet, period, type
        )


@dataclass
class key_verification_task(task):
    corr_release_task_es_id: str

    def xml_string(self):
        return '<task name="{}" node="{}" wcet="{}" period="{}" type="{}" release_es="{}"/>\n'.format(
            self.id,
            self.src_es_id,
            self.exec_time,
            self.period,
            self.type.name,
            self.corr_release_task_es_id,
        )
