#!/bin/bash
#SBATCH --job-name=diffdock_sweep
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --output=%x_%j.log
#SBATCH --time=1-00:00:00
# Submit with: sbatch full_sweep.sbatch
# Runs unattended -- safe to log out; check progress with `squeue -u $USER`
# or by tailing the %x_%j.log file this creates.
#
# Single --protein_ligand_csv batch call for all 189 pairs -- loads the ESM
# model once instead of once per pair (confirmed via DiffDock's README: the
# CSV format supports multiple distinct proteins in one run, not just one
# protein with multiple ligands).

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate diffdock

python ~/hackathon/cluster/build_sweep_csv.py

cd ~/DiffDock
python -m inference \
    --config default_inference_args.yaml \
    --protein_ligand_csv ~/hackathon/data/full_sweep_input.csv \
    --out_dir ~/hackathon/results/full_sweep/
