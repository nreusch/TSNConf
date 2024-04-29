import itertools

from input.input_parameters import InputParameters
from input.model.schedule import schedule
from input.model.stream import stream, EStreamType
from input.model.task import ETaskType
from utils.utilities import debug_print


def init_without_schedule(model, security):
    # --- Init Stream Vars
    for l_or_n_id in itertools.chain(model.tc.L.keys(), model.tc.N.keys()):
        model.o_f[l_or_n_id] = {}
        model.c_f[l_or_n_id] = {}
        model.a_f[l_or_n_id] = {}

    scheduled_tasks = 0
    scheduled_streams = 0
    scheduled_apps = 0

    for f_id in model.tc.F_routed.keys():
        scheduled_streams += 1
        for l_or_n_id in itertools.chain(model.tc.L.keys(), model.tc.N.keys()):
            if model.mtrees[f_id].is_in_tree(l_or_n_id, model.tc):
                f: stream = model.tc.F[f_id]

                period = f.period

                model.o_f[l_or_n_id][f_id] = model.model.NewIntVar(
                    0, period, "o_{}_{}".format(f_id, l_or_n_id)
                )
                model.c_f[l_or_n_id][f_id] = model.model.NewIntVar(
                    0, period, "c_{}_{}".format(f_id, l_or_n_id)
                )
                model.a_f[l_or_n_id][f_id] = model.model.NewIntVar(
                    0, period, "a_{}_{}".format(f_id, l_or_n_id)
                )


            else:
                model.o_f[l_or_n_id][f_id] = model.model.NewConstant(0)
                model.c_f[l_or_n_id][f_id] = model.model.NewConstant(0)
                model.a_f[l_or_n_id][f_id] = model.model.NewConstant(0)

        if security:
            model.phi_f[f_id] = model.model.NewIntVar(
                0, int(model.tc.hyperperiod / model.Pint), "phi_{}".format(f_id)
            )

    # --- Init Task Vars
    for t_id, t in model.tc.T.items():
        period = t.period

        model.o_t[t_id] = model.model.NewIntVar(
            0, period, "o_{}".format(t_id)
        )
        model.a_t[t_id] = model.model.NewIntVar(
            0, period, "a_{}".format(t_id)
        )

        scheduled_tasks += 1

    for app_id in model.tc.A.keys():
        model.app_cost[app_id] = model.model.NewIntVar(0, model.tc.hyperperiod, f"app_cost_{app_id}")
        scheduled_apps += 1

    print(f"Scheduling {scheduled_tasks} tasks, {scheduled_streams} streams, {scheduled_apps} apps")


def init_with_schedule(model, existing_schedule, security):
    # --- Init Stream Vars
    for l_or_n_id in itertools.chain(model.tc.L.keys(), model.tc.N.keys()):
        model.o_f[l_or_n_id] = {}
        model.c_f[l_or_n_id] = {}
        model.a_f[l_or_n_id] = {}

    scheduled_tasks = 0
    given_tasks = 0
    scheduled_streams = 0
    given_streams = 0
    scheduled_apps = 0
    given_apps = 0

    for f_id in model.tc.F_routed.keys():
        if f_id not in existing_schedule.phi_f_val:
            scheduled_streams += 1
        else:
            given_streams += 1

        for l_or_n_id in itertools.chain(model.tc.L.keys(), model.tc.N.keys()):
            if model.mtrees[f_id].is_in_tree(l_or_n_id, model.tc):
                f: stream = model.tc.F[f_id]

                period = f.period

                if f_id in existing_schedule.phi_f_val:
                    # The stream is in the existing schedule, set variables as constants
                    model.o_f[l_or_n_id][f_id] = model.model.NewConstant(
                        existing_schedule.o_f_val[l_or_n_id][f_id]
                    )
                    model.c_f[l_or_n_id][f_id] = model.model.NewConstant(
                        existing_schedule.c_f_val[l_or_n_id][f_id]
                    )
                    model.a_f[l_or_n_id][f_id] = model.model.NewConstant(
                        existing_schedule.a_f_val[l_or_n_id][f_id]
                    )
                else:
                    model.o_f[l_or_n_id][f_id] = model.model.NewIntVar(
                        0, period, "o_{}_{}".format(f_id, l_or_n_id)
                    )
                    model.c_f[l_or_n_id][f_id] = model.model.NewIntVar(
                        0, period, "c_{}_{}".format(f_id, l_or_n_id)
                    )
                    model.a_f[l_or_n_id][f_id] = model.model.NewIntVar(
                        0, period, "a_{}_{}".format(f_id, l_or_n_id)
                    )
            else:
                model.o_f[l_or_n_id][f_id] = model.model.NewConstant(0)
                model.c_f[l_or_n_id][f_id] = model.model.NewConstant(0)
                model.a_f[l_or_n_id][f_id] = model.model.NewConstant(0)

        if security:
            if f_id in existing_schedule.phi_f_val:
                # The stream is in the existing schedule, set variable as constants
                model.phi_f[f_id] = model.model.NewConstant(
                    existing_schedule.phi_f_val[f_id]
                )
            else:
                model.phi_f[f_id] = model.model.NewIntVar(
                    0, int(model.tc.hyperperiod / model.Pint), "phi_{}".format(f_id)
                )


    # --- Init Task Vars
    for t_id, t in model.tc.T.items():
        period = t.period
        if t_id in existing_schedule.o_t_val:
            given_tasks += 1
            # The task is in the existing schedule, set variable as constants
            model.o_t[t_id] = model.model.NewConstant(
                existing_schedule.o_t_val[t_id]
            )
            model.a_t[t_id] = model.model.NewConstant(
                existing_schedule.a_t_val[t_id]
            )
        else:
            model.o_t[t_id] = model.model.NewIntVar(
                t.arrival_time, period, "o_{}".format(t_id)
            )
            model.a_t[t_id] = model.model.NewIntVar(
                t.arrival_time+t.exec_time, period, "a_{}".format(t_id)
            )
            scheduled_tasks += 1

    for app_id in model.tc.A.keys():
        if app_id in existing_schedule.app_costs:
            # The app is in the existing schedule, set variable as constants
            model.app_cost[app_id] = model.model.NewConstant(existing_schedule.app_costs[app_id])
            given_apps += 1
        else:
            model.app_cost[app_id] = model.model.NewIntVar(0, model.tc.hyperperiod, f"app_cost_{app_id}")
            scheduled_apps += 1

    debug_print(f"Already scheduled: {given_tasks} tasks, {given_streams} streams, {given_apps} apps")
    debug_print(f"Scheduling {scheduled_tasks} tasks, {scheduled_streams} streams, {scheduled_apps} apps")

def init_variables(model, existing_schedule: schedule, security: bool):
    if existing_schedule is None:
        init_without_schedule(model, security)
    else:
        init_with_schedule(model, existing_schedule, security)

