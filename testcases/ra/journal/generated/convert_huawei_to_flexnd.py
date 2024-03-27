import os
import random
from pathlib import Path
from re import sub

from input.model.application import application, EApplicationType
from input.model.task import task, ETaskType
from utils.serializer import create_flex_network_description

from input.model.route import route

from input.model.stream import stream, EStreamType

from input.model.link import link

from input.model.nodes import end_system, switch

from input.testcase import Testcase


mapped_task_numbers = {
    "TC1":4,
    "TC2":6,
    "TC3":8,
    "TC4":6,
    "TC5":8,
    "TC6":12,
    "TC7":8,
    "TC8":12,
    "TC9":16,
    "TC10":32,
    "TC11":48,
    "TC12":64,
}

tc_number = 12
for i in range(1,tc_number+1):
    tc = Testcase(f"TC{i}")
    nodes = {}
    ES = {}
    links = {}
    routes = {}

    max_task_period_percentage = 0.01

    tc.W_f_max = 1500
    tc.OH = 0

    flows = open(f"{i-1}_flows.txt", "r").read()
    topo = open(f"{i-1}_topo.txt", "r").read()

    tc.link_speed = 125 # 1000 mbit/s

    topo_lines = topo.split("\n")
    topo_lines = [l.replace("_","-") for l in topo_lines] # replace _ with - to avoid conflicts in TSNConf

    for l in topo_lines:
        l_properties = l.split(",")
        l_type = l_properties[0]

        if l_type == "vertex":
            v_type = l_properties[1]
            v_name = l_properties[2]
            mac_exec_time = 10
            max_utilization = 0.75
            wcet_factor = 1
            if v_type == "PLC":
                nd = end_system(v_name, mac_exec_time, max_utilization, wcet_factor, "EndSystem")
                nodes[v_name] = nd
                ES[v_name] = nd
                tc.add_to_datastructures(nd)
            elif v_type == "SWITCH":
                nd = switch(v_name)
                nodes[v_name] = nd
                tc.add_to_datastructures(nd)
            else:
                raise NotImplementedError
        elif l_type == "edge":
            e_sender = l_properties[2].split(".")[0] # strip off port
            e_receiver = l_properties[3].split(".")[0] # strip off port
            # create bidirectional link
            lnk1 = link(f"link_{e_sender}_{e_receiver}", nodes[e_sender], nodes[e_receiver], tc.link_speed)
            lnk2 = link(f"link_{e_receiver}_{e_sender}", nodes[e_receiver], nodes[e_sender], tc.link_speed)
            tc.add_to_datastructures(lnk1)
            tc.add_to_datastructures(lnk2)
        else:
            pass

    # Give ES types
    es_list = list(ES.values())
    random.shuffle(es_list)
    es_nr = len(es_list)
    for j in range(int(es_nr/2)):
        es_list[j].type = "EndSystem_Edge_Verifier" # half of ES are edge/verifier
    for k in range(int(es_nr/2), int(es_nr/2) + int(es_nr/4)):
        es_list[k].type = "EndSystem_Prover" # one fourth are provers


    flow_lines = flows.split("\n")
    flow_lines = [mll.replace("_","-") for mll in flow_lines if not mll == ""] # replace _ with - to avoid conflicts in TSNConf

    for flow_l in flow_lines:
        flow_properties = flow_l.split(",")
        id = flow_properties[3].strip()
        type = flow_properties[4].strip()
        sender_id = flow_properties[5].strip()
        receiver_id = flow_properties[6].strip()
        period = int(flow_properties[8].strip())
        deadline = int(flow_properties[10].strip())
        size = int(flow_properties[12].strip())

        if type == "ISOCHRONOUS":
            # Create app for flow
            app = application(f"app_{id}", period, EApplicationType.NORMAL)

            # Create sender & receiver task
            t_wcet = random.randint(1, int(max_task_period_percentage * period))
            t_sender = task(f"t-{app.id}-sender", app.id, sender_id, t_wcet, period, 0, ETaskType.NORMAL, [])
            t_wcet = random.randint(1, int(max_task_period_percentage * period))
            t_receiver = task(f"t-{app.id}-receiver", app.id, receiver_id, t_wcet, period, 0, ETaskType.NORMAL, [])

            rl = 1
            secure = False
            message_size = size
            mac_size = 0
            overhead = 0
            s = stream(id, app.id, sender_id, [receiver_id], t_sender.id,[t_receiver.id],
                       message_size + mac_size + overhead, app.period, rl, secure, message_size, mac_size, overhead,
                       EStreamType.NORMAL)
            tc.add_to_datastructures(app)
            tc.add_to_datastructures(t_sender)
            tc.add_to_datastructures(t_receiver)
            tc.add_to_datastructures(s)

    # add mapped tasks
    period = 4000
    for j in range(mapped_task_numbers[f"TC{i}"]):
        app = application(f"app_mapped_task{j}", period, EApplicationType.NORMAL)

        # Create sender & receiver task
        t_wcet = random.randint(1, int(max_task_period_percentage * period))
        t_mapped_es = random.choice(list(tc.ES.keys()))
        t = task(f"t-mapped-{j}", app.id, t_mapped_es, t_wcet, period, 0, ETaskType.NORMAL, [])

        tc.add_to_datastructures(app)
        tc.add_to_datastructures(t)

    create_flex_network_description(Path(f"{tc.name}.flex_network_description"), tc)