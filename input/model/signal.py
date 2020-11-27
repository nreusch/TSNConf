import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from typing import Dict

from input.input_parameters import InputParameters


class ESignalType(Enum):
    NORMAL = 1
    KEY = 2


@dataclass
class signal:
    id: str
    app_id: str
    src_task_id: str
    dest_task_id: str
    sender_es_id: str
    receiver_es_id: str
    size: int
    app_period: int
    group: str  # groupid "self" is reserved for non-routed signals
    rl: int
    type: ESignalType
    is_secure: bool

    def is_self_signal(self):
        return self.sender_es_id == self.receiver_es_id

    def is_secure(self):
        return self.is_secure

    def xml_string(self):
        return '<signal name="{}" src="{}" dest="{}" size="{}" group="{}" secure="{}" rl="{}" type="{}"/>\n'.format(
            self.id,
            self.src_task_id,
            self.dest_task_id,
            self.size,
            self.group,
            self.is_secure,
            self.rl,
            self.type.name,
        )

    @classmethod
    def from_xml_node(cls, n: ET.Element, tc_T: Dict, app_id: str, app_period: int, input_params: InputParameters):
        id = n.attrib["name"]
        src_task_id = n.attrib["src"]
        src_task = tc_T[src_task_id]
        dest_task_id = n.attrib["dest"]
        sender_es_id = tc_T[src_task_id].src_es_id
        receiver_es_id = tc_T[dest_task_id].src_es_id
        size = int(n.attrib["size"])
        group = n.attrib["group"]

        if not group.startswith(src_task_id):
            group = f"{src_task_id}_{group}"

        is_secure = False
        if "secure" in n.attrib:
            if n.attrib["secure"] == "true" or n.attrib["secure"] == "True" and input_params.no_security is False:
                is_secure = True
            elif n.attrib["secure"] == "false" or n.attrib["secure"] == "False":
                is_secure = False
        else:
            is_secure = src_task.is_secure

        rl = 1
        if "rl" in n.attrib:
            if input_params.no_redundancy is False:
                rl = int(n.attrib["rl"])
        else:
            rl = src_task.rl

        return cls(
            id,
            app_id,
            src_task_id,
            dest_task_id,
            sender_es_id,
            receiver_es_id,
            size,
            app_period,
            group,
            rl,
            ESignalType.NORMAL,
            is_secure,
        )
