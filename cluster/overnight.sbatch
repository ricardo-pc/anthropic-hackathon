#!/bin/bash
#SBATCH --job-name=diffdock_replicates
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --output=%x_%j.log
#SBATCH --time=20:00:00
# Overnight: N independent DiffDock replicate sweeps + gnina rescore -> one long CSV.
# Submit with: cd ~/hackathon/cluster && sbatch overnight.sbatch
# Resumable: if killed/preempted, re-submitting continues from the last finished rep.
# Harvest whatever completed by morning -- the bootstrap works with whatever N you get
# (more reps = tighter credible intervals; 6-8 is already solid).

export N_REPS=10
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate diffdock
python ~/hackathon/cluster/replicate_and_rescore.py
