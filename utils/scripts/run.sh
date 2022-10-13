#!/bin/bash
# Use this script to run an omnet testcase and export the results to json
# Run in MingWenv provided by Omnet
#  run.sh ../../../ ../../../../inet TC1.ini
nesting_dir="../../../"
inet_dir="../../../../inet"
testcase_path=TC*.ini
"$nesting_dir"/simulations/nesting.exe -m -u Cmdenv -n .:"$nesting_dir"/src:"$inet_dir"/src:"$inet_dir"/examples:"$inet_dir"/tutorials:"$inet_dir"/showcases:"$nesting_dir"/simulations/ -l "$inet_dir"/src/inet -l "$nesting_dir"/src/nesting $testcase_path
scavetool export -f "name(pktSentFlowId:vector) OR name(pktRcvdFlowId:vector) OR name(pktRcvdDelay:vector)" -F JSON -o results-tc/results.json results-tc/General-#0.vec
PYTHONPATH=/mingw64/bin/
python3.6 parse_results.py