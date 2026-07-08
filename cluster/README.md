# Cluster — Berkeley SCF GPU (`roo`)

Confirmed working Jul 8: SCF account has access to the general-access GPU partition. `roo` = NVIDIA Titan Xp, 12 GB VRAM, driver 570.124.06, CUDA 12.8, reached instantly (idle, no queue) via:
```
srun --pty --partition=gpu --gpus=1 /bin/bash
```
12 GB is enough for DiffDock inference. This is the primary docking backend; RunPod/CPU-smina are the fallback if `roo` is ever busy/preempted (see [`../docs/scope.md`](../docs/scope.md)).

Claude Code cannot reach this cluster directly (no loaded SSH identity in its shell, likely Duo-gated) — these are reference commands to run yourself in the VS Code SSH terminal, not automated scripts Claude executes.

## One-time setup
1. **Push data to Berkeley** (run from a normal Mac terminal, not the VS Code remote session):
   ```
   rsync -avz data/structures/prepared/ gandalf.berkeley.edu:~/hackathon/data/structures/prepared/
   rsync -avz data/drugs.csv gandalf.berkeley.edu:~/hackathon/data/drugs.csv
   ```
2. **Install DiffDock** (run on gandalf, login node — no GPU needed for this step): [`setup_diffdock_env.sh`](setup_diffdock_env.sh)

## Proof-of-wiring test (today's Block E bar) — PASSED Jul 8
One drug × one structure end-to-end. See [`test_one_pair.sh`](test_one_pair.sh) for the exact commands (erlotinib vs. wild-type EGFR 3POZ). Result: 10 poses, best = rank1 at confidence **-0.25** (DiffDock's own descending sort — verified against source, see below), landing in DiffDock's documented "moderate confidence" band. Working end-to-end.

## DiffDock confidence score — sign convention (read this before interpreting ANY result)
Confidence values are typically **negative**. Per DiffDock's own FAQ: `c > 0` high confidence, `-1.5 < c < 0` moderate, `c < -1.5` low. **Higher (less negative) = better.** Output filenames like `rank1_confidence-0.25.sdf` — that `-` is a minus sign on the number, not a separator; easy to misread as "0.25" at a glance. Verified against DiffDock's actual sort code (`inference.py`): `np.argsort(confidence)[::-1]` then `rank1 = confidence[0]` of that descending-sorted array, i.e. rank1 *is* the highest (best) confidence, by construction. Read the sign carefully every time — this determines whether the whole four-bucket classification (robust/improved/weakened/non-binder) points the right direction.

## Known environment.yml bug (already patched into setup_diffdock_env.sh)
DiffDock's `environment.yml` has THREE separate `pip:` blocks under `dependencies:` — conda only honors the *last* one, so `conda env create` silently installs gradio but drops torch/e3nn/torch-geometric (block 1) and openfold (block 2). `setup_diffdock_env.sh` now detects and re-installs both dropped blocks automatically.

`openfold` itself failed to build (needs `nvcc`/`CUDA_HOME`, not just the driver) — turned out to be **unneeded**: DiffDock's docking-from-existing-structure path only uses `fair-esm` for sequence embeddings, not ESMFold/openfold (that's only for predicting structure from raw sequence, which we don't need since we already have real PDB structures). Skipped it; inference ran fine without it.

## Full sweep — ready to run
[`build_sweep_csv.py`](build_sweep_csv.py) + [`full_sweep.sbatch`](full_sweep.sbatch): builds one CSV with all 27 drugs × 7 structures (189 rows: `complex_name, protein_path, ligand_description`) and runs DiffDock's native `--protein_ligand_csv` batch mode — one process launch for all 189 pairs, not 189 separate ones, so the ESM model loads once instead of 189 times. Confirmed via DiffDock's README that the CSV format supports multiple distinct proteins per file, not just multiple ligands against one protein.

Push to gandalf: `rsync -avz cluster/ gandalf.berkeley.edu:~/hackathon/cluster/`, then `sbatch full_sweep.sbatch` from the gandalf terminal — runs unattended, no terminal needs to stay open. Output lands in `~/hackathon/results/full_sweep/<drug>__<pdb>/`.

(An earlier naive per-pair-subprocess version of this script was replaced once the CSV batch mode was confirmed to exist — no reason to pay the reload cost 189 times when one call does it.)

## Next after the sweep runs
- Install gnina (rescoring — the actual reported number, not DiffDock's own confidence).
- Known-answer validation: confirm erlotinib fails on T790M and osimertinib holds (Wed success test).
