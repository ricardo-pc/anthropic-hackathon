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

# --minimize (local relaxation then score), NOT --score_only: DiffDock's raw poses carry
# minor steric clashes that make --score_only report spurious POSITIVE affinities. Confirmed
# on this exact pair: --score_only gave +0.27 kcal/mol (nonsense for erlotinib on its own
# target); --minimize gave -7.2 kcal/mol. --minimize is a LOCAL opt (no box, no re-docking).
~/hackathon/bin/gnina \
    -r ~/hackathon/data/structures/prepared/3POZ_receptor.pdb \
    -l ~/hackathon/results/full_sweep/erlotinib__3POZ/rank1.sdf \
    --minimize

# Expect lines like:
#   Affinity: -7.22 -1.02 (kcal/mol)  <- first number = binding affinity (more negative = better)
#   RMSD: 1.90                         <- how far minimize moved the pose (QC; large = raw pose was bad)
#   CNNscore: 0.74                     <- CNN pose-quality (0-1, higher = better)
#   CNNaffinity: 7.14                  <- CNN predicted pK (higher = better)
