from input.model.nodes import end_system
from utils.utilities import lcm


def maximize_extensibility(model):
    model.actual_distances = {}
    model.inverse_distances = {}

    for es in model.tc.ES.values():
        if es.is_edge_device() or es.is_verifier() or es.is_prover():
            for t in model.tc.T_g[es.id]:
                distances_t = []
                for t2 in model.tc.T_g[es.id]:
                    if t.id != t2.id:
                        P_t = t.period
                        P_t2 = t2.period

                        # +1 to also check distance to task instances in next hyperperiod
                        rg_a = range(int(lcm([P_t, P_t2]) / P_t)+1)
                        rg_b = range(int(lcm([P_t, P_t2]) / P_t2)+1)

                        o_t = model.o_t[t.id]
                        a_t = model.a_t[t.id]

                        o_t2 = model.o_t[t2.id]
                        a_t2 = model.a_t[t2.id]



                        for alph in rg_a:
                            for beta in rg_b:
                                dist = model.model.NewIntVar(0, 2*model.tc.hyperperiod,
                                                             f"dist_{es.id}_{t.id}_{t2.id}_{alph}_{beta}")
                                sum1 = model.model.NewIntVar(-2 * model.tc.hyperperiod, 2*model.tc.hyperperiod,
                                                             f"sum1_{es.id}_{t.id}_{t2.id}_{alph}_{beta}")
                                abs1 = model.model.NewIntVar(0, 2*model.tc.hyperperiod,
                                                             f"abs1_{es.id}_{t.id}_{t2.id}_{alph}_{beta}")
                                sum2 = model.model.NewIntVar(-1 * 2*model.tc.hyperperiod, 2*model.tc.hyperperiod,
                                                             f"sum2_{es.id}_{t.id}_{t2.id}_{alph}_{beta}")
                                abs2 = model.model.NewIntVar(0, 2*model.tc.hyperperiod,
                                                             f"abs2_{es.id}_{t.id}_{t2.id}_{alph}_{beta}")

                                model.model.Add(sum1 == (o_t + alph * P_t) - (a_t2 + beta * P_t2))
                                model.model.AddAbsEquality(abs1, sum1)
                                model.model.Add(sum2 == (o_t2 + beta * P_t2) - (a_t + alph * P_t))
                                model.model.AddAbsEquality(abs2, sum2)

                                model.model.AddMinEquality(dist, [abs1, abs2])
                                distances_t.append(dist)

                model.actual_distances[t.id] = model.model.NewIntVar(0, 2*model.tc.hyperperiod, f"dist_{t.id}")
                model.inverse_distances[t.id] = model.model.NewIntVar(0, 2*model.tc.hyperperiod, f"inv_dist_{t.id}")
                if len(distances_t) == 0:
                    model.model.Add(model.actual_distances[t.id] == model.tc.hyperperiod)
                else:
                    model.model.AddMinEquality(model.actual_distances[t.id], distances_t)
                model.model.Add(model.inverse_distances[t.id] == model.tc.hyperperiod - model.actual_distances[t.id])

    model.cost = model.model.NewIntVar(0, len(model.tc.A) * model.tc.hyperperiod + len(model.tc.T) * 2*model.tc.hyperperiod , f"cost")
    model.model.Add(model.cost == sum(model.inverse_distances.values()))
    model.model.Minimize(model.cost)

def maximize_laxity_and_extensibility(model):
    model.actual_distances = {}
    model.inverse_distances = {}

    for es in model.tc.ES.values():
        for t in model.tc.T_g[es.id]:
            distances_t = []
            for t2 in model.tc.T_g[es.id]:
                if t.id != t2.id:
                    P_t = t.period
                    P_t2 = t2.period

                    rg_a = range(int(lcm([P_t, P_t2]) / P_t))
                    rg_b = range(int(lcm([P_t, P_t2]) / P_t2))

                    o_t = model.o_t[t.id]
                    a_t = model.a_t[t.id]

                    o_t2 = model.o_t[t2.id]
                    a_t2 = model.a_t[t2.id]



                    for alph in rg_a:
                        for beta in rg_b:
                            dist = model.model.NewIntVar(0, model.tc.hyperperiod,
                                                         f"dist_{es.id}_{t.id}_{t2.id}_{alph}_{beta}")
                            sum1 = model.model.NewIntVar(-1 * model.tc.hyperperiod, model.tc.hyperperiod,
                                                         f"sum1_{es.id}_{t.id}_{t2.id}_{alph}_{beta}")
                            abs1 = model.model.NewIntVar(0, model.tc.hyperperiod,
                                                         f"abs1_{es.id}_{t.id}_{t2.id}_{alph}_{beta}")
                            sum2 = model.model.NewIntVar(-1 * model.tc.hyperperiod, model.tc.hyperperiod,
                                                         f"sum2_{es.id}_{t.id}_{t2.id}_{alph}_{beta}")
                            abs2 = model.model.NewIntVar(0, model.tc.hyperperiod,
                                                         f"abs2_{es.id}_{t.id}_{t2.id}_{alph}_{beta}")

                            model.model.Add(sum1 == (o_t + alph * P_t) - (a_t2 + beta * P_t2))
                            model.model.AddAbsEquality(abs1, sum1)
                            model.model.Add(sum2 == (o_t2 + beta * P_t2) - (a_t + alph * P_t))
                            model.model.AddAbsEquality(abs2, sum2)

                            model.model.AddMinEquality(dist, [abs1, abs2])
                            distances_t.append(dist)

            model.actual_distances[t.id] = model.model.NewIntVar(0, model.tc.hyperperiod, f"dist_{t.id}")
            model.inverse_distances[t.id] = model.model.NewIntVar(0, model.tc.hyperperiod, f"inv_dist_{t.id}")
            if len(distances_t) == 0:
                model.model.Add(model.actual_distances[t.id] == model.tc.hyperperiod)
            else:
                model.model.AddMinEquality(model.actual_distances[t.id], distances_t)
            model.model.Add(model.inverse_distances[t.id] == model.tc.hyperperiod - model.actual_distances[t.id])

    model.cost = model.model.NewIntVar(0, len(model.tc.A) * model.tc.hyperperiod + len(model.tc.T) * model.tc.hyperperiod , f"cost")
    model.model.Add(model.cost == sum(model.app_cost.values()) + sum(model.inverse_distances.values()))
    model.model.Minimize(model.cost)

def maximize_laxity(model):
    model.cost = model.model.NewIntVar(0, len(model.tc.A) * model.tc.hyperperiod, f"cost")
    model.model.Add(model.cost == sum(model.app_cost.values()))
    model.model.Minimize(model.cost)
