# Results - Impact Evaluation
Fulfilling the security and redundancy requirements of applications introduces extra tasks and streams that need to be routed and scheduled, leading to an overhead compared to the case when we would ignore those security and redundancy requirements. In this set of experiments, we were interested to evaluate the overhead of fulfilling the redundancy and security requirements compared to the case these are ignored. These overheads were measured on solution cost, available bandwidth, and CPU resources.

The following files are provided:
- Results of individual batches as .csv
- The script to create jobs on DTU's high performance cluster: create_jobs.py
- A jupyter notebook showcasing the calculation of Table. IV in the paper: impact_analysis.ipynb
- The tables as csv: impact_results.csv

The used testcases can be found in: testcases/impact/