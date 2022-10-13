import json
import pathlib
from collections import OrderedDict
from typing import DefaultDict

# This script parses end-2-end delays out of a results.json file, which is obtained by running this command
# scavetool export -f "name(pktSentFlowId:vector) OR name(pktRcvdFlowId:vector) OR name(pktRcvdDelay:vector)" -F JSON -o results-tc/results.json results-tc/

x = json.load(open(pathlib.Path("results-tc/results.json")))

x2 = list(x.values())[0]

print(f'Testcase: {x2["attributes"]["inifile"]}')

vector_list = x2["vectors"]

flow_id_send_times = {}
flow_id_recv_times = {}
flow_ids = {}
delays = {}

e2edelays = {}
for v in vector_list:
    es_name = v["module"].split(".")[1]
    if v["name"] == "pktSentFlowId:vector":
        for i in range(len(v["time"])):
            flow_id = v["value"][i]
            send_time = float(v["time"][i])
            if flow_id in flow_id_send_times:
                flow_id_send_times[flow_id].append(send_time)
            else:
                flow_id_send_times[flow_id] = [send_time]
    elif v["name"] == "pktRcvdFlowId:vector":
        flow_ids[es_name] = {}
        for i in range(len(v["time"])):
            flow_id = v["value"][i]
            recv_time = float(v["time"][i])
            flow_ids[es_name][recv_time] = flow_id
            if flow_id in flow_id_recv_times:
                flow_id_recv_times[flow_id].append(recv_time)
            else:
                flow_id_recv_times[flow_id] = [recv_time]

            if v["value"][i] not in e2edelays:
                e2edelays[flow_id] = []
    elif v["name"] == "pktRcvdDelay:vector":
        delays[es_name] = {}
        for i in range(len(v["time"])):
            delays[es_name][float(v["time"][i])] = v["value"][i]


flow_id_delay_times = {}
# Calculate e2e delays indirectly
print(flow_id_send_times)
print(flow_id_recv_times)
for flow_id, send_times_list in flow_id_send_times.items():
    recv_time_list = flow_id_recv_times[flow_id]
    flow_id_delay_times[flow_id] = []
    for i in range(len(recv_time_list)):
        flow_id_delay_times[flow_id].append(recv_time_list[i] - send_times_list[i])

# Calculate e2e delays directly
for es_id, dct in delays.items():
    for t,v in dct.items():
        stream_id = flow_ids[es_id][t]
        e2edelays[stream_id].append(v)

print(e2edelays)

for stream_id, delay_sum in e2edelays.items():
    e2edelays[stream_id] = sum(e2edelays[stream_id]) / len(e2edelays[stream_id])

print(flow_id_send_times)
print(flow_id_recv_times)

e2edelays = OrderedDict(sorted(e2edelays.items(), key=lambda t: t[0]))
print("End-to-end delays:")
for stream_id, e2edelay in e2edelays.items():
    print(f"Stream {stream_id}: {e2edelay*1000000:.2f}us (avg); {[f'{flow_id_send_times[stream_id][i]*1000000:.2f}-{flow_id_recv_times[stream_id][i]*1000000:.2f}' for i in range(len(flow_id_recv_times[stream_id]))]}")