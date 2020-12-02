<<<<<<< HEAD
def maximize_laxity(model, do_simple_scheduling):
    model.laxities = {}
    laxity_list = []
    for fp in model.tc.FP.values():
        app_id = fp.app_id

        if app_id not in model.laxities:
            model.laxities[app_id] = {}

        first_task = fp.path[0]
        last_task = fp.path[-1]
        o_src_task = model.o_t[first_task.id]
        o_dest_task = model.o_t[last_task.id]
        laxity = model.model.NewIntVar(
            fp.deadline - model.tc.hyperperiod,
            fp.deadline,
            "laxity_{}_{}_{}".format(app_id, first_task.id, last_task.id),
        )
        model.model.Add(
            laxity == fp.deadline + o_src_task - (o_dest_task + last_task.exec_time)
        )
        laxity_list.append(laxity)
        model.laxities[app_id][fp.id] = laxity

    if not do_simple_scheduling:
        model.model.Maximize(sum(laxity_list))
    """
    e2e_delays = []
    for aut_app in self.tc.A_app.values():
        o_i_list = []
        a_i_list = []
        for t_id in aut_app.verticies.keys():
            o_i_list.append(self.o_t[t_id])
            a_i_list.append(self.a_t[t_id])
        start_time = model.NewIntVar(0, self.tc.hyperperiod, "start_time_{}".format(aut_app.id))
        model.AddMinEquality(start_time, o_i_list)

        end_time = model.NewIntVar(0, self.tc.hyperperiod, "end_time_{}".format(aut_app.id))
        model.AddMaxEquality(end_time, a_i_list)

        e2e_delay = model.NewIntVar(0, self.tc.hyperperiod, "e2e_delay_{}".format(aut_app.id))
        model.Add(e2e_delay == end_time - start_time)
        self.e2e_delays[aut_app.id] = e2e_delay
        e2e_delays.append(e2e_delay)

    link_bws_used = []
    for link in self.tc.L_net.values():
        f_bws_used = []
        for f_id, c_m_g in self.c_f[link.id].items():
            f_bw_used = model.NewIntVar(0, self.tc.hyperperiod, "bw_used_{}_{}".format(link.id, f_id))
            P_m = self.tc.F[f_id].app_period
            factor = int(self.tc.hyperperiod / P_m)

            model.Add(f_bw_used == c_m_g * factor)
            f_bws_used.append(f_bw_used)
        link_bw_used = model.NewIntVar(0, self.tc.hyperperiod, "bw_used_{}".format(link.id))
        model.Add(link_bw_used == sum(f_bws_used))
        self.bandwidth_used[link.id] = link_bw_used
        link_bws_used.append(link_bw_used)

    pes_cpu_used = []
    for pe_id, task_list in self.tc.T_g.items():
        task_wcet_list = [task.exec_time for task in task_list]
        pe_cpu_used = model.NewIntVar(0, self.tc.hyperperiod, "cpu_used_{}".format(pe_id))
        model.Add(pe_cpu_used == sum(task_wcet_list))

        self.cpu_used[pe_id] = pe_cpu_used
        pes_cpu_used.append(pe_cpu_used)
    return link_bws_used, e2e_delays, laxities
    # TODO: Instead of flatten put flat dict into testcase
    """
=======
def maximize_laxity(model, do_simple_scheduling):
    model.laxities = {}
    laxity_list = []
    for fp in model.tc.FP.values():
        app_id = fp.app_id

        if app_id not in model.laxities:
            model.laxities[app_id] = {}

        first_task = fp.path[0]
        last_task = fp.path[-1]
        o_src_task = model.o_t[first_task.id]
        o_dest_task = model.o_t[last_task.id]
        laxity = model.model.NewIntVar(
            fp.deadline - model.tc.hyperperiod,
            fp.deadline,
            "laxity_{}_{}_{}".format(app_id, first_task.id, last_task.id),
        )
        model.model.Add(
            laxity == fp.deadline + o_src_task - (o_dest_task + last_task.exec_time)
        )
        laxity_list.append(laxity)
        model.laxities[app_id][fp.id] = laxity

    if not do_simple_scheduling:
        model.model.Maximize(sum(laxity_list))
    """
    e2e_delays = []
    for aut_app in self.tc.A_app.values():
        o_i_list = []
        a_i_list = []
        for t_id in aut_app.verticies.keys():
            o_i_list.append(self.o_t[t_id])
            a_i_list.append(self.a_t[t_id])
        start_time = model.NewIntVar(0, self.tc.hyperperiod, "start_time_{}".format(aut_app.id))
        model.AddMinEquality(start_time, o_i_list)

        end_time = model.NewIntVar(0, self.tc.hyperperiod, "end_time_{}".format(aut_app.id))
        model.AddMaxEquality(end_time, a_i_list)

        e2e_delay = model.NewIntVar(0, self.tc.hyperperiod, "e2e_delay_{}".format(aut_app.id))
        model.Add(e2e_delay == end_time - start_time)
        self.e2e_delays[aut_app.id] = e2e_delay
        e2e_delays.append(e2e_delay)

    link_bws_used = []
    for link in self.tc.L_net.values():
        f_bws_used = []
        for f_id, c_m_g in self.c_f[link.id].items():
            f_bw_used = model.NewIntVar(0, self.tc.hyperperiod, "bw_used_{}_{}".format(link.id, f_id))
            P_m = self.tc.F[f_id].app_period
            factor = int(self.tc.hyperperiod / P_m)

            model.Add(f_bw_used == c_m_g * factor)
            f_bws_used.append(f_bw_used)
        link_bw_used = model.NewIntVar(0, self.tc.hyperperiod, "bw_used_{}".format(link.id))
        model.Add(link_bw_used == sum(f_bws_used))
        self.bandwidth_used[link.id] = link_bw_used
        link_bws_used.append(link_bw_used)

    pes_cpu_used = []
    for pe_id, task_list in self.tc.T_g.items():
        task_wcet_list = [task.exec_time for task in task_list]
        pe_cpu_used = model.NewIntVar(0, self.tc.hyperperiod, "cpu_used_{}".format(pe_id))
        model.Add(pe_cpu_used == sum(task_wcet_list))

        self.cpu_used[pe_id] = pe_cpu_used
        pes_cpu_used.append(pe_cpu_used)
    return link_bws_used, e2e_delays, laxities
    # TODO: Instead of flatten put flat dict into testcase
    """
>>>>>>> d0ef51724e3e61cce9e2f3fd620358723f13e8ed
