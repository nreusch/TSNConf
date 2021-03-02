import random
import time
from pathlib import Path
from typing import Dict

import main
import utils.topology_creator as topology_creator
import dashboard.dash_outputter as dash_outputter
from input.input_parameters import InputParameters, EMode, Timeouts
from input.model.application import application, EApplicationType
from input.model.link import link
from input.model.nodes import end_system, switch
from input.model.task import task, ETaskType

from input.testcase import Testcase
from utils import serializer, app_creator


class testcase_config:
    def __init__(self):
        self.mtu = 1500
        self.frame_overhead = 22
        self.key_length = 16
        self.mac_length = 16
        self.mac_exec_time = 10
        self.link_speed = 125.0
        self.topo = "MESH"
        self.nr_es_per_sw = 2
        self.nr_sw = 2
        self.nr_comm_tasks_per_es = 4
        self.nr_free_tasks_per_es = 4
        self.periods = [1000, 2000]
        self.macrotick = 1
        self.utilization = 50
        self.util_weight_of_comm = 50
        self.interdep_perc = 0
        self.output_name = "test2"
        self.max_es_utilization = 0.7

        self.max_app_width = 4
        self.max_app_depth = 3
        self.max_task_period_percentage = 0.1
        self.max_multicast_count = 3

        self.stream_max_size = 1500
        self.stream_max_rl = 3
        self.stream_secure_chance = 0.3



def create_testcase():
    config = testcase_config()
    random.seed(time.time())
    nr_switches = 8
    nr_es = 4
    connections_per_sw = 3
    connections_per_es = 2

    nr_apps = 4
    free_app_percent = 0.5
    max_app_depth = 3 # how deep the dependecy tree goes. e.g 3: t1 -> t2 -> t3
    max_multicast_width = 2 # how wide one task multicasts. e.g. 2: t1 -> t2, t1 -> t3
    max_app_width = 3
    max_task_period_percentage = 0.1

    available_es = {}
    G, points_sw, points_es = topology_creator.generate_topology(nr_switches, nr_es, connections_per_sw, connections_per_es)

    tc = Testcase(f"{nr_switches}_SW_{nr_es}_ES")

    # ES
    for p in points_es:
        es = end_system(p.name, config.mac_exec_time)
        tc.add_to_datastructures(es)

        available_es[es.id] = 0

    # SW
    for p in points_sw:
        sw = switch(p.name)
        tc.add_to_datastructures(sw)

    # Links
    for nx_link in G.edges:
        src_id = nx_link[0]
        dest_id = nx_link[1]
        l = link(f"link_{src_id}_{dest_id}", tc.N[src_id], tc.N[dest_id], config.link_speed)
        tc.add_to_datastructures(l)
        l = link(f"link_{dest_id}_{src_id}", tc.N[dest_id], tc.N[src_id], config.link_speed)
        tc.add_to_datastructures(l)

    # Applications
    for i in range(nr_apps):
        nr_free_apps = int(free_app_percent*nr_apps)
        if i < nr_free_apps:
            # free apps
            period = random.choice(config.periods)
            app = application(f"FreeApp{i}", period, EApplicationType.NORMAL)

            t_wcet = random.randint(1, int(max_task_period_percentage*period))
            t_es_id = app_creator.find_random_es(available_es, t_wcet/period, config)
            t = task(f"Task_{app.id}", app.id, t_es_id, t_wcet, period, ETaskType.NORMAL)

            tc.add_to_datastructures(app)
            tc.add_to_datastructures(t)
        else:
            # communicating apps
            app, tasks, streams = app_creator.create_app(f"CommApp{i - nr_free_apps}", config, available_es)
            tc.add_to_datastructures(app)
            for t in tasks:
                tc.add_to_datastructures(t)
            for s in streams:
                tc.add_to_datastructures(s)

    serializer.create_flex_network_description(Path("../testcases/synthetic/" + tc.name + ".flex_network_description"), tc)
    print("Created new testcase: " + "testcases/synthetic/" + tc.name + ".flex_network_description")


    return "../testcases/synthetic/" + tc.name + ".flex_network_description"

if __name__ == "__main__":
    path = create_testcase()
    solution_object = main.run(InputParameters(EMode.VIEW, Timeouts(0, 0, 0), path, True, 8050, False, False))
    dash_outputter.run(solution_object)
