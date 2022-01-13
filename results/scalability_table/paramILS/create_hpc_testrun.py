import os
import sys
from shutil import copyfile


hpc_wall_time = [36000, 36000, 36000, 36000, 36000, 36000, 36000, 36000, 36000, 82800, 82800, 82800, 82800, 82800, 82800, 82800, 82800, 82800] # seconds
hpc_wall_time = [3600*6 for i in range(18)]

cutoff_time = [600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 1200, 1200, 1200] # seconds

#N = 3
validN = 10

tunerTimeout = 92000 # doesnt work for some reason

#params
alpha = [0.999999, 0.9999,  0.99, 0.9, 0.8]
tstart = [10**4, 10**1, 1]
prmv = [0.1, 0.3, 0.5, 0.7, 0.9]
k = [5, 10, 15, 20, 30]
w = [5, 10, 1000]

i = 0
for tc_name in ["TC0_example", "TC1_automotive", "TC1_automotive_redundant", "TC2_zhao_case_study", "tiny1", "tiny2", "tiny3", "small1", "small2", "small3", "medium1", "medium2", "medium3", "large1", "large2", "large3", "huge1", "huge2", "huge3", "giant1", "giant2", "giant3"][0:4]:
    maxEvals = min(hpc_wall_time[i] // cutoff_time[i], len(alpha) * len(tstart) * len(prmv))
    # Create folder
    try:
        os.mkdir(tc_name)
    except:
        pass
    # Copy tune_hpc.sh 
    f = open(f"{tc_name}/tune_hpc.sh", "w")
    if hpc_wall_time[i] == 36000:
        walltime = "10"
    elif hpc_wall_time[i] == 72000:
        walltime = "20"
    else:
        walltime = str(hpc_wall_time[i] // 3600) 
    f.write(f"""#!/bin/sh
### General options
### -- specify queue --
###BSUB -q compute
### -- set the job Name --
#BSUB -J nikre_tuning_{tc_name}
### -- ask for number of cores (default: 1) --
#BSUB -n 1
### -- specify that the cores must be on the same host --
#BSUB -R "span[hosts=1]"
### -- specify that we need 2GB of memory per core/slot --
#BSUB -R "rusage[mem=16GB] select[avx2]"
### -- specify that we want the job to get killed if it exceeds 3 GB per core/slot --
#BSUB -M 32GB
### -- set walltime limit: hh:mm --
#BSUB -W {walltime}:00
### -- set the email address --
# please uncomment the following line and put in your e-mail address,
# if you want to receive e-mail notifications on a non-default address
##BSUB -u your_email_address
### -- send notification at start --
###BSUB -B
### -- send notification at completion --
###BSUB -N
### -- Specify the output and error file. %J is the job-id --
### -- -o and -e mean append, -oo and -eo mean overwrite --
#BSUB -oo out_tune%J.out
#BSUB -eo out_tune%J.err

module load python3/3.9.5
bash tune.sh placeholder_argument
""")
    f.close()

    # Copy tune_hpc.sh 
    copyfile("SA_wrapper.rb", f"{tc_name}/SA_wrapper.rb")

    # Create tune.sh
    f = open(f"{tc_name}/tune.sh", "w")
    f.write(f"ruby ../../paramils2.3.8-source/param_ils_2_3_run.rb -numRun 0 -scenariofile config.txt -validN {validN} -maxEvals {maxEvals} -pruning 0")
    f.close()

    f = open(f"{tc_name}/config.txt", "w")
    f.write(f"""algo = ruby SA_wrapper.rb
execdir = .
run_obj = approx
overall_obj = mean
cutoff_time = {cutoff_time[i]}
cutoff_length = max
tunerTimeout = {tunerTimeout}
paramfile = params.txt
outdir = paramils-out
instance_file = instances.txt
test_instance_file = instances.txt""")
    f.close()

    f = open(f"{tc_name}/instances.txt", "w")
    f.write(f"testcases/synthetic4/{tc_name}.flex_network_description")
    f.close()

    f = open(f"{tc_name}/params.txt", "w")
    f.write(f"""alpha {{{", ".join([str(e) for e in alpha])}}}[{alpha[0]}]
tstart {{{", ".join([str(e) for e in tstart])}}}[{tstart[0]}]
prmv {{{", ".join([str(e) for e in prmv])}}}[{prmv[0]}]
k {{{", ".join([str(e) for e in k])}}}[{k[0]}]
w {{{", ".join([str(e) for e in w])}}}[{w[0]}]""")
    f.close()
    
    i += 1


