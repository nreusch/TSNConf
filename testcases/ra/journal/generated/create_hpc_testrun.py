import os
import sys
from shutil import copyfile

nr_tc = 12
hpc_wall_time = 10800

tunerTimeout = 92000 # doesnt work for some reason

for tc_name in [f"TC{i}" for i in range(1, nr_tc+1)]:
    # Create folder
    try:
        os.mkdir(tc_name)
    except:
        pass

    # Copy tune_hpc.sh 
    f = open(f"{tc_name}/tune_hpc.sh", "w")
    walltime = 10800 // 3600
    f.write(f"""#!/bin/sh
### General options
### -- specify queue --
###BSUB -q compute
### -- set the job Name --
#BSUB -J nikre_raext_{tc_name}
### -- ask for number of cores (default: 1) --
#BSUB -n 1
### -- specify that the cores must be on the same host --
#BSUB -R "span[hosts=1]"
### -- specify that we need 2GB of memory per core/slot --
#BSUB -R "rusage[mem=16GB] select[avx2]"
### -- specify that we want the job to get killed if it exceeds 3 GB per core/slot --
#BSUB -M 16GB
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
cd ~/TSNConf_RAExt/TSNConf
source ../.venv/bin/activate
python -m main testcases/ra/journal/generated/{tc_name}.flex_network_description --mode CP_ROUTING_CP_SCHEDULING_EXT --no_security --no_redundancy --timeout_routing 3600 --timeout_scheduling 3600 --aggregate results_raandext.csv
""")
    f.close()


