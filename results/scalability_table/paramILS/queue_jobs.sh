declare -a arr=("tiny1" "tiny2" "tiny3" "small1" "small2" "small3" "medium1" "medium2" "medium3" "large1" "large2" "large3" "huge1" "huge2" "huge3" "giant1" "giant2" "giant3")

## now loop through the above array
for i in "${arr[@]}"
do
   cd $i
   bsub < tune_hpc.sh
   cd ..
   # or do whatever with individual element of the array
done
