sf = open("submit.sh", "w")
a = {"" : "", " --no_security" : "nosec", " --no_redundancy" : "nored", "  --no_security --no_redundancy" : "noboth"}

job = f"""#!/bin/sh
### General options
### -- specify queue --
#BSUB -q compute
### -- set the job Name --
#BSUB -J nikre_sa_batches
### -- ask for number of cores (default: 1) --
#BSUB -n 1
### -- specify that the cores must be on the same host --
#BSUB -R "span[hosts=1]"
### -- specify that we need 16GB of memory per core/slot --
#BSUB -R "rusage[mem=16GB] select[avx2]"
### -- specify that we want the job to get killed if it exceeds 3 GB per core/slot --
#BSUB -M 32GB
### -- set walltime limit: hh:mm --
#BSUB -W 00:30
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
#BSUB -oo out_batches.out
#BSUB -eo out_batches.err

module load python3/3.9.5
cd ../TSNConf
source .venv/bin/activate

"""

for i in range(4):
    for j in range(25):
        for args in a.keys():
            testcase = f"testcases/impact/batch{i}{j}.flex_network_description"
            walltime = "00:12"
            cutoff_time = 0

            line = f"python3 -m main {testcase} --mode SA_ROUTING_SA_SCHEDULING_COMB --aggregate batch{i}_{a[args]}.csv --timeout_scheduling {cutoff_time} --a 50000 --b 10000{args}\n"
            job += line

fname = f"jobs/job_sa_batches.sh"
f = open(f"{fname}", "w")
f.write(job)
f.close()

sf.write(f"bsub < {fname}\n")
sf.close()
