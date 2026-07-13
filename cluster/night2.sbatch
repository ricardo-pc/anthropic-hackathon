#!/bin/bash
#SBATCH --job-name=diffdock_candidates
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --output=%x_%j.log
#SBATCH --time=20:00:00
# Night 2: replicate the library-screen candidate hits at N=10 against WT (3POZ) + the resistant
# double (5UGC), so each gets a real 95% credible interval and can be triaged alongside the curated
# panel. This is the expensive-but-focused pass, run ONLY on the ~35 drugs the cheap screen flagged.
#
# 35 drugs x 2 structures x 10 reps = 700 docking runs.
# RESUMABLE at the replicate level: if killed/preempted, just `sbatch night2.sbatch` again and it
# continues from the last finished rep (it tracks completed reps in the scores file). Safe to log out.
#
# Submit and walk away:   cd ~/hackathon/cluster && sbatch night2.sbatch
# Watch:                  squeue -u $USER    # or: tail -f diffdock_candidates_*.log

export SWEEP_DRUGS="$HOME/hackathon/data/candidates.csv"            # the ~35 candidate drugs only
export SWEEP_STRUCTURES="3POZ,5UGC"                                 # WT + resistant double
export SWEEP_OUT="$HOME/hackathon/data/candidates_input.csv"       # DiffDock input CSV
export SWEEP_CSV="$SWEEP_OUT"                                       # replicate runner reads this
export REP_ROOT="$HOME/hackathon/results/candidates"               # fresh pose dir
export SCORES_OUT="$HOME/hackathon/results/gnina_scores_candidates.csv"  # fresh scores file
export N_REPS=10                                                    # full replicates -> credible intervals

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate diffdock

# 1) build the restricted DiffDock input (35 drugs x 2 receptors), 2) dock x10 + gnina-rescore
python "$HOME/hackathon/cluster/build_sweep_csv.py"
python "$HOME/hackathon/cluster/replicate_and_rescore.py"

echo "=== night 2 done. replicate scores -> $SCORES_OUT ==="
