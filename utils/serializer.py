import os
import pickle
import random
import shutil
from pathlib import Path

import networkx as nx
from graphviz import Digraph

from input.model.nodes import switch
from input.testcase import Testcase
from solution import solution_parser
from solution.solution import Solution
from utils.utilities import report_exception


def create_flex_network_description(output_file: Path, tc: Testcase):
    f = open(output_file, "w")
    f.write(tc.to_flex_network_description())
    f.close()

def create_luxi_files_multi_window(output_folder: Path, tc: Testcase, sol):

    try:
        luxi_path_in = output_folder / "in"
        luxi_path_out = output_folder / "out"
        luxi_path_in.mkdir(exist_ok=True)
        luxi_path_out.mkdir(exist_ok=True)

        f_sched = open(luxi_path_in / "historySCHED1.txt", "w")
        f_msg = open(luxi_path_in / "msg.txt", "w")
        f_rate = open(luxi_path_in / "rate.txt", "w")
        f_vls = open(luxi_path_in / "vls.txt", "w")

        gcl = luxi_sched_from_multiwindow_solution(tc, sol)
        msg, rate, vls = tc.to_luxi_files()
        f_sched.write(gcl)
        f_msg.write(msg)
        f_rate.write(rate)
        f_vls.write(vls)

        f_sched.close()
        f_msg.close()
        f_rate.close()
        f_vls.close()

    except Exception as e:
        raise e

def create_luxi_files_single_window(output_folder: Path, tc: Testcase, sched):

    try:
        luxi_path_in = output_folder / "in"
        luxi_path_out = output_folder / "out"
        luxi_path_in.mkdir(exist_ok=True)
        luxi_path_out.mkdir(exist_ok=True)

        f_sched = open(luxi_path_in / "historySCHED1.txt", "w")
        f_msg = open(luxi_path_in / "msg.txt", "w")
        f_rate = open(luxi_path_in / "rate.txt", "w")
        f_vls = open(luxi_path_in / "vls.txt", "w")

        sched = luxi_sched_from_sasolution(tc, sched)
        msg, rate, vls = tc.to_luxi_files()
        f_sched.write(sched)
        f_msg.write(msg)
        f_rate.write(rate)
        f_vls.write(vls)

        f_sched.close()
        f_msg.close()
        f_rate.close()
        f_vls.close()
    except Exception as e:
        raise e


def luxi_sched_from_sasolution(tc: Testcase, sched):
    sched_strings = []
    for l_id in tc.F_l_out.keys():
        l = tc.L[l_id]
        if l.src.id in tc.SW:
            sched_strings.append(f"{l.src.id},{l.dest.id}")
            for w in sched.W[l_id].values():
                if w.length > 0:
                    sched_strings.append(f"{w.offset}\t{w.end}\t{w.period}\t{w.priority}")
            sched_strings.append("")
    sched_strings.append("#")
    return "\n".join(sched_strings)

def luxi_sched_from_multiwindow_solution(tc: Testcase, sol):
    # ordering doesnt matter
    sched_strings = []
    for l_id, dct in sol.schedule.items():
        l = tc.L[l_id]
        sched_strings.append(f"{l.src.id},{l.dest.id}")
        for priority, wnd_list in dct.items():
            for wnd in wnd_list:
                if wnd.length > 0:
                    sched_strings.append(f"{wnd.offset}\t{wnd.end}\t{wnd.period}\t{priority}")
                else:
                    raise ValueError
        sched_strings.append("")
    sched_strings.append("#")
    return "\n".join(sched_strings)

def aggregate_solution(csv_path: Path, solution: Solution):
    df = solution_parser.get_solution_results_info_dataframe(solution)

    if not csv_path.exists():
        df.to_csv(csv_path)
    else:
        df.to_csv(csv_path, mode="a", header=False)

def create_omnet_files(omnet_path: Path, solution: Solution):
    tc = solution.tc
    eth_addresses = {} # es_id -> eth_address
    flow_ids = {} # stream_id -> flow_id
    ports = {} # node_id -> [node_id]
    RANDOM_OFFSETS = True

    # Copy scripts
    shutil.copyfile(Path("utils/scripts/run.sh"), omnet_path / "run.sh")
    shutil.copyfile(Path("utils/scripts/parse_results.py"), omnet_path / "parse_results.py")

    # .ini
    f = open(omnet_path / f"{tc.name}.ini", "w")
    t = []
    t.append("[General]")
    t.append("network = TC")
    t.append("record-eventlog = true")
    t.append("debug-on-errors = true")
    t.append("result-dir = results-tc")
    t.append("sim-time-limit = " + str(tc.hyperperiod) + "us")
    t.append("**.displayAddresses = true")
    t.append("**.verbose = true")

    counter = 1
    for es in tc.ES.values():
        assert len(str(counter)) <= 12
        address = "0"*(12-len(str(counter))) + str(counter)
        address = "-".join([address[2*i:2*i+2] for i in range(6)])
        t.append("**." + es.id + ".eth.address = \"" + address + "\"")
        eth_addresses[es.id] = address
        counter += 1

    t.append("**.SW*.processingDelay.delay = 0us")
    t.append("**.filteringDatabase.database = xmldoc(\"Routing.xml\", \"/filteringDatabases/\")")

    portnumbers = {}
    for l_id in tc.F_l_out.keys():
        l = tc.L[l_id]
        if l.src.id in tc.SW:
            if l.src.id not in portnumbers:
                portnumbers[l.src.id] = 0
            else:
                portnumbers[l.src.id] += 1

            t.append("**." + l.src.id + ".eth[" + str(portnumbers[l.src.id]) + "].queue.gateController.initialSchedule = xmldoc(\"S.xml\", \"/schedules/switch[@name='" + l.src.id + "']/port[@id='" + str(portnumbers[l.src.id]) + "']/schedule\") ")


    t.append("**.SW*.eth[*].queue.numberOfQueues = 8")
    t.append("**.SW*.eth[*].queue.tsAlgorithms[*].typename = \"StrictPriority\"")
    t.append("**.SW*.eth[*].mac.enablePreemptingFrames = false")
    t.append("**.ES*.trafGenSchedApp.initialSchedule = xmldoc(\"Flows.xml\")")

    f.write("\n".join(t))
    f.close()

    # .ned
    f = open(omnet_path / f"{tc.name}.ned", "w")
    t = []

    #t.append(f"package nesting.simulations.examples_multi.{tc.name};")
    t.append("import ned.DatarateChannel;")
    t.append("import nesting.node.ethernet.VlanEtherHostQ;")
    t.append("import nesting.node.ethernet.VlanEtherHostSched;")
    t.append("import nesting.node.ethernet.VlanEtherSwitchPreemptable;")
    t.append("network TC")
    t.append("{")
    t.append("types:")
    t.append("channel C extends DatarateChannel")
    t.append("{")
    t.append("delay = 0us;")
    t.append(f"datarate = {int(tc.link_speed*8)}Mbps;")
    t.append("}")
    t.append("submodules:")
    for sw in tc.SW.values():
        t.append(sw.id + ": VlanEtherSwitchPreemptable {")
        t.append("gates:")
        t.append("ethg["+str(len(tc.SW_port[sw.id]))+"];")
        t.append("}")

    for es in tc.ES.values():
        t.append(es.id + ": VlanEtherHostSched {")
        t.append("}")

    t.append("connections:")

    for n_id in tc.N.keys():
        ports[n_id] = []

    for sw_id in tc.SW.keys():
        i = 0
        for n2_id in tc.L_from_nodes[sw_id].keys():
            if sw_id not in ports[n2_id]:
                if n2_id in tc.ES:
                    t.append(sw_id + ".ethg[" + str(len(ports[sw_id])) + "] <--> C <--> " + n2_id + ".ethg;")
                else:
                    t.append(sw_id + ".ethg[" + str(len(ports[sw_id])) + "] <--> C <--> " + n2_id + ".ethg[" + str(len(ports[n2_id])) + "];")
                    ports[n2_id].append(sw_id)

                ports[sw_id].append(n2_id)

    t.append("}")
    f.write("\n".join(t))
    f.close()

    # Flows.xml
    f = open(omnet_path / "Flows.xml", "w")
    t = []

    t.append('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
    t.append("<schedules>")
    t.append(f"\t<defaultcycle>{tc.hyperperiod}us</defaultcycle>")
    flow_id = 1
    for es_id, stream_list in tc.F_g_out.items():
        if len(stream_list) > 0:
            t.append(f'\t<host name="{es_id}">')
            t.append(f'\t\t<cycle>{tc.hyperperiod}us</cycle>')

            random_offsets = {}
            for s in stream_list:
                if RANDOM_OFFSETS:
                    random_offsets[s.id] = random.randint(0, s.period)
                else:
                    random_offsets[s.id] = 0

            entries = {} # contains entries indexed by start time
            for s in stream_list:
                for instance in range(tc.hyperperiod//s.period):
                    e = []
                    e.append('\t\t<entry>')
                    e.append(f'\t\t\t<flowId>{flow_id}</flowId>')
                    e.append(f'\t\t\t<start>{instance*s.period+random_offsets[s.id]}us</start>')
                    e.append(f'\t\t\t<queue>{0}</queue>')
                    e.append(f'\t\t\t<dest>{eth_addresses[list(s.receiver_es_ids.keys())[0]]}</dest>')
                    e.append(f'\t\t\t<size>{s.size}B</size>')
                    e.append('\t\t</entry>')
                    if instance*s.period+random_offsets[s.id] not in entries:
                        entries[instance*s.period+random_offsets[s.id]] = [e]
                    else:
                        entries[instance*s.period+random_offsets[s.id]].append(e)
                flow_ids[s.id] = flow_id
                flow_id += 1
            # append entries sorted by start time (apparently necessary for omnet)
            for key in sorted(entries):
                for e in entries[key]:
                    t.extend(e)
            t.append(f'\t</host>')
    t.append("</schedules>")
    f.write("\n".join(t))
    f.close()

    # Routing.xml
    # one entry for each flow passing through switch, with destination mac and ethg connected to that destination
    f = open(omnet_path / "Routing.xml", "w")
    t = []

    t.append('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
    t.append("<filteringDatabases>")
    for sw_id, stream_list in tc.F_sw_out.items():
        t.append(f'\t<filteringDatabase id="{sw_id}">')
        t.append(f'\t\t<static>')
        t.append(f'\t\t\t<forward>')
        for s_id in stream_list:
            s = tc.F[s_id]
            r = tc.R[s_id]
            for succ_node in r.get_successor_nodes_for_node(sw_id, tc):
                t.append(f'\t\t\t\t<individualAddress macAddress="{eth_addresses[list(s.receiver_es_ids.keys())[0]]}" port="{ports[sw_id].index(succ_node.id)}"/>')
        t.append(f'\t\t\t</forward>')
        t.append(f'\t\t</static>')
        t.append(f'\t</filteringDatabase>')
    t.append("</filteringDatabases>")

    f.write("\n".join(t))
    f.close()

    # Schedule xml
    f = open(omnet_path / f"S.xml", "w")
    t = []
    port_xmls = {}
    for sw_id in tc.SW.keys():
        port_xmls[sw_id] = []
    # CAUTION: This only works for non-overlapping windows

    t.append("<schedules>")
    t.append(f"\t<defaultcycle>{tc.hyperperiod}us</defaultcycle>")
    for l_id, window_list in solution.scheduling_solution.W.items():
        l = tc.L[l_id]
        sw_id = l.src.id
        port_id = ports[sw_id].index(l.dest.id)
        sched_s = []

        sched_s.append(f'\t\t<port id="{port_id}">')
        sched_s.append(f'\t\t\t<schedule cycleTime="{tc.hyperperiod}us">')
        cur_pos = 0
        for tup in solution.scheduling_solution.get_length_list_for_port(l_id):
            l = tup[0][0] - cur_pos # window start - cur_pos
            if l > 0:
                sched_s.append("\t\t\t\t<entry>")
                sched_s.append(f"\t\t\t\t\t<length>{l}us</length>")
                sched_s.append(f"\t\t\t\t\t<bitvector>00000000</bitvector>")
                sched_s.append("\t\t\t\t</entry>")

            sched_s.append("\t\t\t\t<entry>")
            sched_s.append(f"\t\t\t\t\t<length>{tup[0][1] - tup[0][0]}us</length>")
            priority = tup[1]

            # handle weird case that priorities 0 and 1 are switched
            if priority == 0:
                priority = 1
            elif priority == 1:
                priority = 0

            index = 7-priority
            sched_s.append(f"\t\t\t\t\t<bitvector>{'00000000'[:index] + '1' + '00000000'[index+1:]}</bitvector>")
            sched_s.append("\t\t\t\t</entry>")
            cur_pos = tup[0][1]

        sched_s.append(f'\t\t\t</schedule>')
        sched_s.append("\t\t</port>")
        port_xmls[sw_id].append((port_id, sched_s))

    for sw_id, tpl_list in port_xmls.items():
        if len(tpl_list) > 0:
            tpl_list.sort(key= lambda tpl: tpl[0])
            t.append(f'\t<switch name="{sw_id}">')
            for tpl in tpl_list:
                t.extend(tpl[1])
            t.append(f'\t</switch>')


    t.append("</schedules>")
    f.write("\n".join(t))
    f.close()


def minimal_serialize_solution(base_path: Path, solution: Solution, visualize: bool) -> Path:
    """
    Serializes the given solution (pickle, network_description, graphs, optimization results...) into a folder and returns its path
    """
    path = base_path / solution.get_folder_name()
    path.mkdir(parents=True, exist_ok=True)


    df = solution_parser.get_solution_results_info_dataframe(solution)
    df.to_csv(path / "result.csv")

    # Also append to aggregate file
    try:
        if not solution.input_params.aggregate_path == "":
            if not solution.input_params.aggregate_path.exists():
                df.to_csv(solution.input_params.aggregate_path)
            else:
                df.to_csv(solution.input_params.aggregate_path, mode="a", header=False)

            print(
                "-" * 20
                + " Appended results to {}".format(solution.input_params.aggregate_path)
            )
    except Exception as e:
        pass

    return path

def serialize_solution(base_path: Path, solution: Solution, visualize: bool) -> Path:
    """
    Serializes the given solution (pickle, network_description, graphs, optimization results...) into a folder and returns its path
    """
    path = base_path / solution.get_folder_name()
    path.mkdir(parents=True, exist_ok=True)

    # Pickle solution object
    with open(path / "solution.pickle", "wb") as f:
        # Pickle solution object
        pickle.dump(solution, f, pickle.HIGHEST_PROTOCOL)
        f.close()

    print(
        "-" * 20
        + " Pickled solution"
    )

    # Create Luxi WCD files
    luxi_path = path / "luxi"
    luxi_path.mkdir(exist_ok=True)

    create_luxi_files_single_window(
        luxi_path,
        solution.tc,
        solution.scheduling_solution
    )

    print(
        "-" * 20
        + " Created files for Luxi Zhao WCD analysis"
    )

    # Create Omnet++ files
    omnet_path = path / "omnet"
    omnet_path.mkdir(exist_ok=True)

    omnet_path_tc = path / "omnet" / solution.tc.name
    omnet_path_tc.mkdir(exist_ok=True)

    create_omnet_files(
        omnet_path_tc,
        solution
    )

    print(
        "-" * 20
        + " Created Omnet files"
    )

    # Copy Omnet++ files to simulation dir
    try:
        p = "C:\\Users\\phd\\Desktop\\omnet_workspace\\nesting\\simulations\\examples_multi\\" + solution.tc.name
        if os.path.exists(p):
            shutil.rmtree(p)
        shutil.copytree(path / "omnet" / solution.tc.name, p)
        print(
            "-" * 20
            + f" Copied Omnet files to {p}"
        )
    except Exception:
        pass



    # Create flex_network_description

    create_flex_network_description(
        path
        / "{}_mode{}.flex_network_description".format(
            solution.input_params.tc_name, solution.input_params.mode.value
        ),
        solution.tc,
    )

    print(
        "-" * 20
        + " Created flex_network_description"
    )



    if visualize:
        # Create graphviz graphs
        svg_path = path / "svg"
        svg_path.mkdir(exist_ok=True)
        serialize_graphs(svg_path, solution)

        # Create plotly schedules
        """
        fig = solution_parser.get_solution_schedule_plotly(solution)
        if fig is not None:
            fig.write_html(str(path / "schedule.html"))
            try:
                fig.write_image(str(path / "schedule.pdf"), width=1920, height=640, engine="kaleido")
            except Exception as e:
                raise e
        """
        print(
            "-" * 20
            + " Created graphs"
        )



    # Append to solutions.csv
    try:
        df = solution_parser.get_solution_results_info_dataframe(solution)
        df.insert(0, "Testcase Name", solution.get_folder_name())

        with open(base_path / "solutions.csv", "a") as f:
            df.to_csv(f, header=f.tell() == 0, index=False)

        print(
            "-" * 20
            + " Appended results to {}".format(base_path / "solutions.csv")
        )
    except Exception as e:
        pass

    # Also append to aggregate file
    try:
        if not solution.input_params.aggregate_path == "":
            if not solution.input_params.aggregate_path.exists():
                df.to_csv(solution.input_params.aggregate_path)
            else:
                df.to_csv(solution.input_params.aggregate_path, mode="a", header=False)

        print(
            "-" * 20
            + " Appended results to {}".format(solution.input_params.aggregate_path)
        )
    except Exception as e:
        pass

    return path


def deserialize_solution(path: Path) -> Solution:
    """
    Loads a solution object from a given pickle file
    """
    with open(path, "rb") as f:
        data = pickle.load(f)
        f.close()
        return data


def serialize_graphs(path: Path, solution: Solution):
    """
    Serialiazies the graphs (topology, applications) of the given solution to the given path
    """
    testcase = solution.tc
    # TODO: Handle no task case
    # Base - Topology
    dot = Digraph(comment="base_topology", node_attr={"shape": "record"})
    for node in testcase.N.values():
        if isinstance(node, switch):
            dot.node(node.id, label=node.id + " (SW)", shape="circle")
        else:
            dot.node(node.id, label=node.id + " (ES)", shape="square")

    for link in testcase.L.values():
        dot.edge(link.src.id, link.dest.id)

    try:
        dot.format = "pdf"
        dot.render(filename=path / ("base_topology.gv"))
    except Exception as e:
        report_exception(e)

    try:
        dot.format = "svg"
        dot.render(filename=path / ("base_topology.gv"))
    except Exception as e:
        report_exception(e)