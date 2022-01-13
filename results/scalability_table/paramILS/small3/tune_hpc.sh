#!/bin/sh
### General options
### -- specify queue --
#BSUB -q compute
### -- set the job Name --
#BSUB -J nikre_tuning_small3
### -- ask for number of cores (default: 1) --
#BSUB -n 1
### -- specify that the cores must be on the same host --
#BSUB -R "span[hosts=1]"
### -- specify that we need 2GB of memory per core/slot --
#BSUB -R "rusage[mem=16GB] select[avx2]"
### -- specify that we want the job to get killed if it exceeds 3 GB per core/slot --
#BSUB -M 32GB
### -- set walltime limit: hh:mm --
#BSUB -W 6:00
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
