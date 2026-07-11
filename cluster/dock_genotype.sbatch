#!/bin/bash
#SBATCH --job-name=dock_genotype
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --output=dock_%j.log
#SBATCH --time=20:00:00
# Dock ONE new genotype into its OWN input/output/pose dirs — never touches the master full sweep.
# Submit with the three paths + rep count exported, e.g.:
#   sbatch --export=ALL,\
# SWEEP_CSV=$HOME/hackathon/data/EGFRC797S_input.csv,\
# SCORES_OUT=$HOME/hackathon/results/EGFRC797S_scores.csv,\
# REP_ROOT=$HOME/hackathon/results/replicates_EGFRC797S,\
# N_REPS=8 dock_genotype.sbatch
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate diffdock
echo "genotype dock: SWEEP_CSV=$SWEEP_CSV  SCORES_OUT=$SCORES_OUT  N_REPS=$N_REPS"
python ~/hackathon/cluster/replicate_and_rescore.py
