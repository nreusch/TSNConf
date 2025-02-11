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


class testcase_generation_config:
    def __init__(self):
        self.mtu = 1500
        self.frame_overhead = 22
        self.key_length = 16
        self.mac_length = 16
        self.mac_exec_time = 10
        self.link_speed = 125.0
        self.topo = "MESH"

        self.nr_sw = 2
        self.nr_es = 4
        self.connections_per_sw = 1 # how many other switches a switch will be connected to
        self.connections_per_es = 2


        self.periods = [1000, 2000]
        self.macrotick = 1
        self.utilization = 50
        self.util_weight_of_comm = 50
        self.interdep_perc = 0
        self.max_es_utilization = 0.7

        self.nr_dags = 4
        self.nr_tasks = 4
        self.max_task_period_percentage = 0.08
        self.min_app_depth = 2
        self.max_app_depth = 3 # how deep the dependecy tree goes. e.g 3: t1 -> t2 -> t3
        self.app_task_connection_probability = 0.5
        self.max_task_period_percentage = 0.1
        self.max_multicast_count = 3

        self.stream_min_size = 1
        self.stream_max_size = 1500
        self.stream_max_rl = 2
        self.stream_secure_chance = 0.3

        self.name = "name"

def create_testcase_with_topology_and_dags_and_apps(config, path, G, points_sw, points_es, app_lst, es_utilization_dict, container_id):
    random.seed(time.time())


    tc = Testcase(config.name)
    tc.W_f_max = config.mtu
    tc.W_mac = config.mac_length
    tc.key_length = config.key_length
    tc.OH = config.frame_overhead

    # ES
    for p in points_es:
        es = end_system(p.name, config.mac_exec_time, "EndSystem")
        tc.add_to_datastructures(es)

    # SW
    for p in points_sw:
        sw = switch(p.name)
        tc.add_to_datastructures(sw)

    # Links
    for nx_link in G.edges:
        src_id = nx_link[0]
        dest_id = nx_link[1]
        l = link(f"l_{src_id}_{dest_id}", tc.N[src_id], tc.N[dest_id], config.link_speed)
        tc.add_to_datastructures(l)
        l = link(f"l_{dest_id}_{src_id}", tc.N[dest_id], tc.N[src_id], config.link_speed)
        tc.add_to_datastructures(l)

    # Applications


    for lst in app_lst:
        # communicating apps
        # Use existing DAGs!
        for el in lst:
            app = el[0]
            tasks = el[1]
            streams = el[2]
            tc.add_to_datastructures(app)
            for t in tasks:
                tc.add_to_datastructures(t)
            for s in streams:
                tc.add_to_datastructures(s)

    tc.highest_communication_depth = max([app.get_communication_depth() for app in tc.A_app.values()])
    serializer.create_flex_network_description(path, tc)
    print(f"Created testcase at: {path.absolute()}")
    print(
        f"Tasks {len(tc.T)}; Streams {len(tc.F)}; Apps {len(tc.A)}; Average ES utilization {sum(es_utilization_dict.values()) / len(es_utilization_dict.values())}")
    print("-" * 50)

    return path

def create_testcase_with_topology_and_dags(config, path, G, points_sw, points_es, container_id, existing_dag_random=True):
    random.seed(time.time())

    es_utilization_dict = {}

    tc = Testcase(config.name)
    tc.W_f_max = config.mtu
    tc.W_mac = config.mac_length
    tc.key_length = config.key_length
    tc.OH = config.frame_overhead

    # ES
    for p in points_es:
        es = end_system(p.name, config.mac_exec_time, "EndSystem")
        tc.add_to_datastructures(es)

        es_utilization_dict[es.id] = 0

    # SW
    for p in points_sw:
        sw = switch(p.name)
        tc.add_to_datastructures(sw)

    # Links
    for nx_link in G.edges:
        src_id = nx_link[0]
        dest_id = nx_link[1]
        l = link(f"l_{src_id}_{dest_id}", tc.N[src_id], tc.N[dest_id], config.link_speed)
        tc.add_to_datastructures(l)
        l = link(f"l_{dest_id}_{src_id}", tc.N[dest_id], tc.N[src_id], config.link_speed)
        tc.add_to_datastructures(l)

    # Applications
    tasks_per_app = config.nr_tasks // config.nr_dags

    for i in range(config.nr_dags):
        # communicating apps
        # Use existing DAGs!
        lst = app_creator.create_apps(f"app{i}", config, es_utilization_dict, tasks_per_app, True, container_id, existing_dag_random)

        for el in lst:
            app = el[0]
            tasks = el[1]
            streams = el[2]
            tc.add_to_datastructures(app)
            for t in tasks:
                tc.add_to_datastructures(t)
            for s in streams:
                tc.add_to_datastructures(s)

    tc.highest_communication_depth = max([app.get_communication_depth() for app in tc.A_app.values()])
    serializer.create_flex_network_description(path, tc)
    print(f"Created testcase at: {path.absolute()}")
    print(
        f"Tasks {len(tc.T)}; Streams {len(tc.F)}; Apps {len(tc.A)}; Average ES utilization {sum(es_utilization_dict.values()) / len(es_utilization_dict.values())}")
    print("-" * 50)

    return path

def create_testcase(config, path, container_id):
    G, points_sw, points_es = topology_creator.generate_topology(config.nr_sw, config.nr_es, config.connections_per_sw,
                                                                 config.connections_per_es)
    random.seed(time.time())

    es_utilization_dict = {}

    tc = Testcase(config.name)
    tc.W_f_max = config.mtu
    tc.W_mac = config.mac_length
    tc.key_length = config.key_length
    tc.OH = config.frame_overhead

    # ES
    for p in points_es:
        es = end_system(p.name, config.mac_exec_time, "EndSystem")
        tc.add_to_datastructures(es)

        es_utilization_dict[es.id] = 0

    # SW
    for p in points_sw:
        sw = switch(p.name)
        tc.add_to_datastructures(sw)

    # Links
    for nx_link in G.edges:
        src_id = nx_link[0]
        dest_id = nx_link[1]
        l = link(f"l_{src_id}_{dest_id}", tc.N[src_id], tc.N[dest_id], config.link_speed)
        tc.add_to_datastructures(l)
        l = link(f"l_{dest_id}_{src_id}", tc.N[dest_id], tc.N[src_id], config.link_speed)
        tc.add_to_datastructures(l)

    # Applications
    tasks_per_app = config.nr_tasks // config.nr_dags

    for i in range(config.nr_dags):
        # communicating apps
        lst = app_creator.create_apps(f"app{i}", config, es_utilization_dict, tasks_per_app, False, container_id)

        for el in lst:
            app = el[0]
            tasks = el[1]
            streams = el[2]
            tc.add_to_datastructures(app)
            for t in tasks:
                tc.add_to_datastructures(t)
            for s in streams:
                tc.add_to_datastructures(s)

    tc.highest_communication_depth = max([app.get_communication_depth() for app in tc.A_app.values()])
    serializer.create_flex_network_description(path, tc)
    print(f"Created testcase at: {path.absolute()}")
    print(
        f"Tasks {len(tc.T)}; Streams {len(tc.F)}; Apps {len(tc.A)}; Average ES utilization {sum(es_utilization_dict.values()) / len(es_utilization_dict.values())}")
    print("-" * 50)

    return path

def create_testcase_without_tasks(config, nr_streams, path, show_topology=True):
    G, points_sw, points_es = topology_creator.generate_topology(config.nr_sw, config.nr_es, config.connections_per_sw,
                                                                 config.connections_per_es, show_topology)
    random.seed(time.time())

    print(f"Create topology graph with {config.nr_sw} switches and {config.nr_es} end systems")

    tc = Testcase(config.name)
    tc.W_f_max = config.mtu
    tc.W_mac = config.mac_length
    tc.key_length = config.key_length
    tc.OH = config.frame_overhead

    es_utilization_dict = {}
    # ES
    for p in points_es:
        es = end_system(p.name, config.mac_exec_time, "EndSystem")
        tc.add_to_datastructures(es)

        es_utilization_dict[es.id] = 0

    # SW
    for p in points_sw:
        sw = switch(p.name)
        tc.add_to_datastructures(sw)

    # Links
    for nx_link in G.edges:
        src_id = nx_link[0]
        dest_id = nx_link[1]
        l = link(f"l_{src_id}_{dest_id}", tc.N[src_id], tc.N[dest_id], config.link_speed)
        tc.add_to_datastructures(l)
        l = link(f"l_{dest_id}_{src_id}", tc.N[dest_id], tc.N[src_id], config.link_speed)
        tc.add_to_datastructures(l)

    # Applications
    for i in range(nr_streams):
        print(f"Created simple app for stream {i}")
        # communicating apps
        tpl = app_creator.create_simple_apps(f"app{i}", config, es_utilization_dict)

        app = tpl[0]
        tasks = tpl[1]
        streams = tpl[2]
        tc.add_to_datastructures(app)
        for t in tasks:
            tc.add_to_datastructures(t)
        for s in streams:
            tc.add_to_datastructures(s)

    tc.highest_communication_depth = max([app.get_communication_depth() for app in tc.A_app.values()])
    serializer.create_flex_network_description(path, tc)
    print(f"Created testcase at: {path.absolute()}")
    print(
        f"Tasks {len(tc.T)}; Streams {len(tc.F)}; Apps {len(tc.A)}; Average ES utilization {sum(es_utilization_dict.values()) / len(es_utilization_dict.values())}")
    print("-" * 50)

    return path