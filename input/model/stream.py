import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple


class EStreamType(Enum):
    NORMAL = 1
    KEY = 2


# Not immutable, since period=Pint is dynamically optimized
# Each stream carries one group from one task
@dataclass
class stream:
    id: str
    sender_es_id: str
    receiver_es_ids: set
    sender_task_id: str
    receiver_task_ids: set
    group_id: str
    size: int  # = size of ONE signal for multicast
    period: int  # =Pint for security frames
    rl: int  # = rl of sending task
    is_secure: bool
    message_size: int
    mac_size: int
    frame_overhead_size: int
    signal_sizes: List[Tuple[str, int]]  # "s1,s2" -> 20
    type: EStreamType

    def get_id_prefix(self):
        return "_".join(self.id.split("_")[:-1])

    def xml_string(self):
        return '<stream name="{}" src="{}" dest="{}" sender_task="{}" receiver_tasks="{}" group="{}" size="{}" period="{}" rl="{}" type="{}" secure="{}" mac_size="{}"/>'.format(
            self.id,
            self.sender_es_id,
            ",".join([r_es_id for r_es_id in self.receiver_es_ids]),
            self.sender_task_id,
            ",".join([t_id for t_id in self.receiver_task_ids]),
            self.group_id,
            self.size,
            self.period,
            self.rl,
            self.type.name,
            self.is_secure,
            self.mac_size,
        )

    @classmethod
    def from_xml_node(cls, n: ET.Element, tc_OH: int, tc_S_group: Dict):
        id = n.attrib["name"]
        src_es_id = n.attrib["src"]
        receiver_es_ids = set(n.attrib["dest"].split(","))
        sender_task_id = n.attrib["sender_task"]
        receiver_task_ids = set(n.attrib["receiver_tasks"].split(","))
        group_id = n.attrib["group"]
        size = int(n.attrib["size"])
        period = int(n.attrib["period"])
        rl = int(n.attrib["rl"])
        type = EStreamType[n.attrib["type"]]

        if "secure" in n.attrib:
            if n.attrib["secure"] == "true" or n.attrib["secure"] == "True":
                is_secure = True
            else:
                is_secure = False

        mac_size = 0
        if "mac_size" in n.attrib:
            mac_size = int(n.attrib["mac_size"])

        some_signal = tc_S_group[group_id][0]

        return cls(
            id,
            src_es_id,
            receiver_es_ids,
            sender_task_id,
            receiver_task_ids,
            group_id,
            size,
            period,
            rl,
            is_secure,
            size,
            mac_size,
            tc_OH,
            [(",".join(s.id for s in tc_S_group[group_id]), some_signal.size)],
            type,
        )
