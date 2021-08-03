import pandas as pd

batches = {
    "batch0" : "large streams, small tasks",
    "batch1" : "large streams, large tasks",
    "batch2" : "small streams, small tasks",
    "batch3" : "small streams, large tasks",
}

endings = {
    "" : (True, True),
    "nosec" : (False, True),
    "nored" : (True, False),
    "noboth" : (False, False)
}

dfs = {}

for batch_name, description in batches.items():
    for ending, tpl in endings.items():
        df = pd.read_csv(f"{batch_name}_{ending}.csv")

        if batch_name not in dfs:
            dfs[batch_name] = {}
            dfs[batch_name][ending] = df
        else:
            dfs[batch_name][ending] = df