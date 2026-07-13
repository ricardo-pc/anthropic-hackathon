#!/bin/bash
#SBATCH --job-name=diffdock_library_screen
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --output=%x_%j.log
#SBATCH --time=20:00:00
# Coarse repurposing-library screen: dock the WHOLE drug panel (curated 27 + ~300 approved library)
# against WT (3POZ) + the resistant double mutant (5UGC) only, ONE replicate each. This is the cheap
# first pass -- it tells you which approved drugs bind the mutant and shift on it, so you only spend
# the expensive 10-replicate run on the handful worth credible intervals.
#
# Submit and walk away:   cd ~/hackathon/cluster && sbatch library_screen.sbatch
# Watch progress:         squeue -u $USER          # or: tail -f diffdock_library_screen_*.log
# Runs unattended; safe to log out. Writes to a SEPARATE scores file so it never collides with the
# existing full-replicate data (gnina_scores_replicates.csv).

# --- what to dock, where to put it (kept separate from the full-sweep files) ---
export SWEEP_STRUCTURES="3POZ,5UGC"                                   # WT + resistant double only
export SWEEP_OUT="$HOME/hackathon/data/library_screen_input.csv"     # DiffDock input CSV
export SWEEP_CSV="$SWEEP_OUT"                                         # replicate runner reads this
export REP_ROOT="$HOME/hackathon/results/library_screen"             # fresh pose dir
export SCORES_OUT="$HOME/hackathon/results/gnina_scores_library.csv" # fresh scores file
export N_REPS=1                                                       # coarse screen: one pass

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate diffdock

# 1) build the restricted DiffDock input (327 drugs x 2 receptors), 2) dock + gnina-rescore it
python "$HOME/hackathon/cluster/build_sweep_csv.py"
python "$HOME/hackathon/cluster/replicate_and_rescore.py"

echo "=== library screen done. scores -> $SCORES_OUT ==="
