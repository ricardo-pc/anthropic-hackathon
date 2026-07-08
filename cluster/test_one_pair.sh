#!/bin/bash
# Reference commands for the Block E proof-of-wiring test: ONE drug (erlotinib)
# docked against ONE structure (wild-type EGFR, 3POZ). Not the full 27-drug x
# 7-structure sweep -- that comes after this passes.
#
# Run interactively inside a GPU allocation (conda needs the normal login-shell
# init to activate correctly, which a plain non-interactive `srun cmd` skips):
#
#   srun --pty --partition=gpu --gpus=1 /bin/bash
#   conda activate diffdock
#   cd ~/DiffDock
#   mkdir -p ~/hackathon/results/test_erlotinib_3POZ
#   python -m inference \
#       --config default_inference_args.yaml \
#       --protein_path ~/hackathon/data/structures/prepared/3POZ_receptor.pdb \
#       --ligand "C#Cc1cccc(Nc2ncnc3cc(OCCOC)c(OCCOC)cc23)c1" \
#       --out_dir ~/hackathon/results/test_erlotinib_3POZ/
#
# erlotinib SMILES above is the RDKit-canonicalized form from data/drugs.csv --
# same string the rest of the pipeline uses, so this test is representative.
#
# Success = the out_dir contains ranked pose files (rank1.sdf etc.) with a
# confidence score. That confirms DiffDock + the prepared receptor + the pocket
# definition all actually work together end-to-end.
#
# Remember: exit the srun session when done to free the GPU for others.
