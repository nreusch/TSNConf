def maximize_laxity(model):
    cost = model.model.NewIntVar(0, len(model.tc.A) * model.tc.hyperperiod, f"cost")
    model.model.Add(cost == sum(model.app_cost.values()))

    model.model.Minimize(cost)