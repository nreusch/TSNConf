import sys
import pandas as pd
from pathlib import Path

out_file = Path(sys.argv[1])

names =  ["tiny1", "tiny2", "tiny3", "small1", "small2", "small3", "medium1", "medium2", "medium3", "large1", "large2", "large3", "huge1", "huge2", "huge3", "giant1", "giant2", "giant3"]
names = ["TC1_automotive_redundant", "TC2_zhao_case_study"]

columns=[
            "Index",
            "Testcase",
            "Security",
            "Redundancy",
            "Method",
            "# ES",
            "# Switches",
            "# Streams",
            "# Receiver Tasks",
            "# Tasks",
            "Total cost",
            "Routing cost",
            "Scheduling cost",
            "Normal application latency",
            "Infeasible Apps",
            "Bandwidth use (Mean,%)",
            "CPU use (Mean,%)",
            "Optimization Time (ms)",
            "First feasible solution time (ms)",
            "Total Runtime (ms)",
            "Infeasible apps",
            "Overlapping number",
            "Stream with overlap",
            "Tstart",
            "alpha",
            "Prmv",
            "k",
            "a",
            "b",
            "w"
        ]

df_best = None

for tc_name in names:
    try:
        for method in ["SA_ROUTING_SA_SCHEDULING_COMB", "CP_ROUTING_CP_SCHEDULING"][0:1]:
            try:
                df = pd.read_csv(f"{tc_name}.csv", delimiter=",", names=columns, header=None, skiprows=1)
                df_method = df.loc[df["Method"] == method]
                if not df_method.empty:
                    max_row = df_method["Total cost"].argmin()

                    df_row = df_method[max_row:max_row+1]
                    print(tc_name)
                    print(df_row["Total cost"])
                    if not out_file.exists():
                        df_row.to_csv(out_file)
                    else:
                        df_row.to_csv(out_file, mode="a", header=False)
                    print()
            except Exception as e:
                 print(e)
        
    except Exception as e:
        raise e



