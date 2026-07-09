#!/bin/bash
# One-pair gnina rescore test -- confirm the binary runs, the GPU/CNN works, and we
# can read the scores, BEFORE looping over all 189. Run inside a GPU allocation:
#
#   srun --pty --partition=gpu --gpus=1 /bin/bash
#   bash ~/hackathon/cluster/test_gnina_one.sh
#
# gnina reads the heavy-atom receptor PDB and adds hydrogens internally via OpenBabel
# (this is the consistent dock-time protonation we deferred in structure_prep) -- so no
# separate receptor prep is needed. --score_only scores the pose exactly as DiffDock
# placed it (no re-docking, no box needed since the pose is already in the pocket).

~/hackathon/bin/gnina \
    -r ~/hackathon/data/structures/prepared/3POZ_receptor.pdb \
    -l ~/hackathon/results/full_sweep/erlotinib__3POZ/rank1.sdf \
    --score_only

# Expect lines like:
#   Affinity:   -7.1  (kcal/mol)   <- Vina-style empirical affinity (more negative = better)
#   CNNscore:    0.83               <- CNN pose-quality (0-1, higher = better)
#   CNNaffinity: 5.9                <- CNN predicted pK (higher = better)
# If CNN lines are missing but Affinity prints, the GPU/CNN path failed but the empirical
# score still works -- usable, just tell me and we'll decide whether to force CPU/empirical.
