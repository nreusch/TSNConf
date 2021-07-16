import itertools

from input.input_parameters import InputParameters
from input.model.stream import stream, EStreamType
from input.model.task import ETaskType


def init_variables(model, security: bool):
    # --- Init Stream Vars
    for l_or_n_id in itertools.chain(model.tc.L.keys(), model.tc.N.keys()):
        model.o_f[l_or_n_id] = {}
        model.c_f[l_or_n_id] = {}
        model.a_f[l_or_n_id] = {}

    for f_id in model.tc.F_routed.keys():
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

    for app_id in model.tc.A.keys():
        model.app_cost[app_id] = model.model.NewIntVar(0, model.tc.hyperperiod, f"app_cost_{app_id}")
