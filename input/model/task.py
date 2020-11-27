import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from typing import Set

from input.input_parameters import InputParameters


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
    app_period: int
    rl: int  # redundancy level
    groups: Set[str]  # assigned in postprocessing. "task.id_group"
    # groupid "self" is reserved for non-routed signals
    type: ETaskType
    is_secure: bool

    def xml_string(self):
        return '<task name="{}" node="{}" wcet="{}" secure="{}" rl="{}" type="{}"/>\n'.format(
            self.id,
            self.src_es_id,
            self.exec_time,
            self.is_secure,
            self.rl,
            self.type.name,
        )

    @classmethod
    def from_xml_node(cls, n: ET.Element, app_id: str, app_period: int, input_params: InputParameters):
        id = n.attrib["name"]
        src_es_id = n.attrib["node"]
        wcet = int(n.attrib["wcet"])
        if "rl" in n.attrib and input_params.no_redundancy is False:
            rl = int(n.attrib["rl"])
        else:
            rl = 1

        secure = False
        if "secure" in n.attrib:
            if n.attrib["secure"] == "true" or n.attrib["secure"] == "True" and input_params.no_security is False:
                secure = True
            elif n.attrib["secure"] == "false" or n.attrib["secure"] == "False":
                secure = False

        return cls(
            id, app_id, src_es_id, wcet, app_period, rl, set(), ETaskType.NORMAL, secure
        )


@dataclass
class key_verification_task(task):
    corr_release_task_es_id: str

    def xml_string(self):
        return '<task name="{}" node="{}" wcet="{}" secure="{}" rl="{}" type="{}" release_es="{}"/>\n'.format(
            self.id,
            self.src_es_id,
            self.exec_time,
            self.is_secure,
            self.rl,
            self.type.name,
            self.corr_release_task_es_id,
        )
