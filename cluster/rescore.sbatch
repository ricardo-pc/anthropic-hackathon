#!/bin/bash
#SBATCH --job-name=gnina_rescore
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --output=%x_%j.log
#SBATCH --time=04:00:00
# Submit with: cd ~/hackathon/cluster && sbatch rescore.sbatch
# Fast (score-only, no docking) -- 189 single-pose rescores. GPU is for gnina's CNN scoring.

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate diffdock   # only for a consistent python3; gnina itself is a standalone binary

python ~/hackathon/cluster/rescore_gnina.py
