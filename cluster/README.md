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

## DiffDock confidence score — sign convention
Confidence values are typically **negative**; higher (less negative) = better (`c>0` high, `−1.5<c<0` moderate, `c<−1.5` low). rank1 = best by construction. `rank1_confidence-0.25.sdf` means confidence −0.25 (the `-` is the sign). Verified against DiffDock source. **Full interpretation + the five WT-vs-mutant delta caveats that govern the stats layer are in [`../docs/docking_score_notes.md`](../docs/docking_score_notes.md) — read that before computing any delta.**

## Known environment.yml bug (already patched into setup_diffdock_env.sh)
DiffDock's `environment.yml` has THREE separate `pip:` blocks under `dependencies:` — conda only honors the *last* one, so `conda env create` silently installs gradio but drops torch/e3nn/torch-geometric (block 1) and openfold (block 2). `setup_diffdock_env.sh` now detects and re-installs both dropped blocks automatically.

`openfold` itself failed to build (needs `nvcc`/`CUDA_HOME`, not just the driver) — turned out to be **unneeded**: DiffDock's docking-from-existing-structure path only uses `fair-esm` for sequence embeddings, not ESMFold/openfold (that's only for predicting structure from raw sequence, which we don't need since we already have real PDB structures). Skipped it; inference ran fine without it.

## Full sweep — ready to run
[`build_sweep_csv.py`](build_sweep_csv.py) + [`full_sweep.sbatch`](full_sweep.sbatch): builds one CSV with all 27 drugs × 7 structures (189 rows: `complex_name, protein_path, ligand_description`) and runs DiffDock's native `--protein_ligand_csv` batch mode — one process launch for all 189 pairs, not 189 separate ones, so the ESM model loads once instead of 189 times. Confirmed via DiffDock's README that the CSV format supports multiple distinct proteins per file, not just multiple ligands against one protein.

Push to gandalf: `rsync -avz cluster/ gandalf.berkeley.edu:~/hackathon/cluster/`, then `sbatch full_sweep.sbatch` from the gandalf terminal — runs unattended, no terminal needs to stay open. Output lands in `~/hackathon/results/full_sweep/<drug>__<pdb>/`.

**This is a single-pass sweep — a Wednesday known-answer *direction* check** (does erlotinib's score drop on T790M, does osimertinib hold, etc.). It is NOT the statistically rigorous version. DiffDock is stochastic and its 10 poses are one draw, not independent estimates (see `docs/docking_score_notes.md` caveats 3–4), so Thursday's stats layer must **re-run each pair N≥5–10 times** to establish the run-to-run noise floor before any WT-vs-mutant delta is trusted. Replicates require editing a copied YAML, not a CLI flag (the YAML overrides CLI — caveat 5).

(An earlier naive per-pair-subprocess version of this script was replaced once the CSV batch mode was confirmed to exist — no reason to pay the reload cost 189 times when one call does it.)

## gnina rescoring — the affinity proxy (DiffDock sweep must be done first)
DiffDock confidence is pose-quality, not affinity. gnina rescores each rank1 pose into a real predicted binding affinity — the number the four-bucket classification rests on.

1. **Install** (gandalf login node): [`setup_gnina.sh`](setup_gnina.sh) — downloads the prebuilt binary to `~/hackathon/bin/gnina`, no compiling.
2. **One-pair test first** (inside `srun --pty --partition=gpu --gpus=1 /bin/bash`): [`test_gnina_one.sh`](test_gnina_one.sh) — confirms the binary runs, GPU/CNN works, and scores parse, before looping 189. gnina reads the heavy-atom receptor PDB and protonates internally via OpenBabel (this is the dock-time protonation deferred in `structure_prep.py`, applied uniformly to all 7 receptors).
3. **Full rescore** (from `~/hackathon/cluster`): `sbatch rescore.sbatch` → [`rescore_gnina.py`](rescore_gnina.py) loops all 189, writes `~/hackathon/results/gnina_scores.csv` (drug, category, pdb, target, state, diffdock_confidence, gnina_affinity, gnina_minimize_rmsd, gnina_cnn_score, gnina_cnn_affinity). Pull it back with `rsync` for the stats layer.

**Uses `gnina --minimize`, not `--score_only`.** DiffDock's raw poses carry minor steric clashes; scoring them as-is gave a spurious *positive* affinity (+0.27 kcal/mol for erlotinib on WT-EGFR — its own target). `--minimize` does a local in-pocket relaxation first (no box, no re-docking), giving −7.2 kcal/mol as expected. `gnina_minimize_rmsd` records how far each pose moved (QC — a large value flags a raw pose that needed a big fix, worth reviewing).

Score directions: `gnina_affinity` kcal/mol, **more negative = better**; `gnina_cnn_score` 0–1 pose quality, higher = better; `gnina_cnn_affinity` predicted pK, higher = better.

## Then: known-answer validation (Wed success test)
From `gnina_scores.csv`, check the direction: erlotinib/gefitinib affinity should worsen WT→T790M; osimertinib should hold; sotorasib should be strong on G12C (6OIM) — and **watch sotorasib vs apo 4LDJ** for the induced-fit risk (scope §6.3). Single-pass direction check only; replicate-based stats are Thursday.
