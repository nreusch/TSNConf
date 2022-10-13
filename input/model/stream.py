import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from typing import Dict


class EStreamType(Enum):
    NORMAL = 1

# Not immutable, since period=Pint is dynamically optimized
@dataclass
class stream:
    id: str

    sender_es_id: str
    receiver_es_ids: Dict[str, None]

    size: int # message_size + OH
    period: int

    message_size: int
    frame_overhead_size: int

    type: EStreamType

    priority: int

    deadline: int

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
        return '<stream name="{}" src="{}" dest="{}" size="{}" period="{}" type="{}" priority="{}" deadline="{}"/>\n'.format(
            self.get_id_prefix(),
            self.sender_es_id,
            ",".join([r_es_id for r_es_id in self.receiver_es_ids]),
            self.size,
            self.period,
            self.type.name,
            self.priority,
            self.deadline
        )

    @classmethod
    def list_from_xml_node(cls, n: ET.Element, tc_OH: int):
        ret_list = []

        if "priority" in n.attrib:
            priority = int(n.attrib["priority"])
        else:
            priority = 0

        if "src" in n.attrib:
            src_es_id = n.attrib["src"]

        if "dest" in n.attrib:
            receiver_es_ids = dict.fromkeys(n.attrib["dest"].replace(" ", "").split(","))

        message_size = int(n.attrib["size"])

        period = int(n.attrib["period"])

        if "type" in n.attrib:
            type = EStreamType[n.attrib["type"]]
        else:
            type = EStreamType["NORMAL"]

        if "deadline" in n.attrib:
            deadline = int(n.attrib["deadline"])
        else:
            deadline = period

        size = message_size + tc_OH

        id = n.attrib["name"]

        ret_list.append(cls(
            id,
            src_es_id,
            receiver_es_ids,
            size,
            period,
            message_size,
            tc_OH,
            type,
            priority,
            deadline
        ))

        return ret_list
