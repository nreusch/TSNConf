import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple, Set

from input.model.task import task


class EStreamType(Enum):
    NORMAL = 1
    KEY = 2


# Not immutable, since period=Pint is dynamically optimized
# Each stream carries one group from one task
@dataclass
class stream:
    id: str
    app_id: str

    sender_es_id: str
    receiver_es_ids: Dict[str, None]

    sender_task_id: str
    receiver_task_ids: Dict[str, None]

    size: int # message_size + mac_size + OH
    period: int  # =Pint for security streams
    rl: int
    is_secure: bool

    message_size: int
    mac_size: int
    frame_overhead_size: int

    type: EStreamType

    def is_self_stream(self):
        if len(self.receiver_es_ids.keys()) > 1:
            return False
        else:
            return list(self.receiver_es_ids.keys())[0] == self.sender_es_id

    def get_id_prefix(self):
        spl = self.id.split("_")
        if len(spl) == 1:
            return spl[0]
        else:
            return "_".join(spl[:-1])

    def xml_string(self):
        return '<stream name="{}" src="{}" dest="{}" sender_task="{}" receiver_tasks="{}" size="{}" period="{}" rl="{}" secure="{}" type="{}" />\n'.format(
            self.get_id_prefix(),
            self.sender_es_id,
            ",".join([r_es_id for r_es_id in self.receiver_es_ids]),
            self.sender_task_id,
            ",".join([t_id for t_id in self.receiver_task_ids]),
            self.size,
            self.period,
            self.rl,
            self.is_secure,
            self.type.name,
        )

    @classmethod
    def list_from_xml_node(cls, redundancy: bool, security: bool, n: ET.Element, tc_T: Dict[str, task], tc_W_mac: int, tc_OH: int, app_id: str = ""):
        ret_list = []

        if "rl" in n.attrib and redundancy:
            rl = int(n.attrib["rl"])
        else:
            rl = 1

        sender_task_id = n.attrib["sender_task"]
        receiver_task_ids = dict.fromkeys(n.attrib["receiver_tasks"].replace(" ", "").split(","))

        if "src" in n.attrib:
            src_es_id = n.attrib["src"]
        else:
            src_es_id = tc_T[sender_task_id].src_es_id

        if "dest" in n.attrib:
            receiver_es_ids = dict.fromkeys(n.attrib["dest"].replace(" ", "").split(","))
        else:
            receiver_es_ids = dict.fromkeys([tc_T[t_id].src_es_id for t_id in receiver_task_ids])

        message_size = int(n.attrib["size"])

        period = tc_T[sender_task_id].period

        if "type" in n.attrib:
            type = EStreamType[n.attrib["type"]]
        else:
            type = EStreamType["NORMAL"]


        if "secure" in n.attrib and security:
            if n.attrib["secure"] == "true" or n.attrib["secure"] == "True":
                is_secure = True
                mac_size = tc_W_mac
            else:
                is_secure = False
                mac_size = 0

        else:
            is_secure = False
            mac_size = 0


        size = message_size + mac_size + tc_OH

        for i in range(rl):
            id = n.attrib["name"] + f"_{i}"

            ret_list.append(cls(
                id,
                app_id,
                src_es_id,
                receiver_es_ids,
                sender_task_id,
                receiver_task_ids,
                size,
                period,
                rl,
                is_secure,
                message_size,
                mac_size,
                tc_OH,
                type,
            ))

        return ret_list
