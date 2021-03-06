import itertools

from input.input_parameters import InputParameters


def init_variables(model, input_params: InputParameters):
    # --- Init Stream Vars
    for l_or_n_id in itertools.chain(model.tc.L.keys(), model.tc.N.keys()):
        model.o_f[l_or_n_id] = {}
        model.c_f[l_or_n_id] = {}
        model.a_f[l_or_n_id] = {}

    for f_id in model.tc.F_routed.keys():
        for l_or_n_id in itertools.chain(model.tc.L.keys(), model.tc.N.keys()):
            if model.mtrees[f_id].is_in_tree(l_or_n_id, model.tc):
                f = model.tc.F[f_id]
                model.o_f[l_or_n_id][f_id] = model.model.NewIntVar(
                    0, f.period, "o_{}_{}".format(f_id, l_or_n_id)
                )
                model.c_f[l_or_n_id][f_id] = model.model.NewIntVar(
                    0, f.period, "c_{}_{}".format(f_id, l_or_n_id)
                )
                model.a_f[l_or_n_id][f_id] = model.model.NewIntVar(
                    0, f.period, "a_{}_{}".format(f_id, l_or_n_id)
                )
            else:
                model.o_f[l_or_n_id][f_id] = model.model.NewConstant(0)
                model.c_f[l_or_n_id][f_id] = model.model.NewConstant(0)
                model.a_f[l_or_n_id][f_id] = model.model.NewConstant(0)

        if not input_params.no_security:
            model.phi_f[f_id] = model.model.NewIntVar(
                0, int(model.tc.hyperperiod / model.Pint), "phi_{}".format(f_id)
            )

    # --- Init Task Vars
    for t_id, task in model.tc.T.items():
        model.o_t[t_id] = model.model.NewIntVar(
            0, task.period, "o_{}".format(t_id)
        )
        model.a_t[t_id] = model.model.NewIntVar(
            0, task.period, "a_{}".format(t_id)
        )
