#!/usr/bin/env python3
"""
Overnight job: N independent DiffDock replicate sweeps, each gnina-rescored, appended to
one long CSV -- so tomorrow only the (instant, CPU) Bayesian bootstrap remains.

Why replicates: DiffDock is stochastic (reverse diffusion from random noise, no fixed seed
in the default path). Re-running gives a DIFFERENT rank1 pose each time. The spread of the
rescored affinity across runs IS the run-to-run noise floor -- we cannot call any WT-vs-mutant
delta real until it clears that spread (docs/docking_score_notes.md, caveats 3-5).

Design:
  - one rep at a time: DiffDock full sweep -> gnina --minimize on each rank1 -> append rows.
  - resumable at the REP level: a rep already in the CSV is skipped; a rep whose poses exist
    (189 rank1.sdf) but weren't rescored skips straight to rescoring. So a killed/preempted
    job resumes without redoing finished work -- harvest whatever completed by morning.
  - safety: after rep 2, abort if it is byte-identical to rep 1 (would mean a fixed seed and
    a wasted night); log loudly instead of burning GPU on identical runs.

Env: N_REPS (default 10). Run via overnight.sbatch.
"""
import csv
import glob
import os
import re
import subprocess
import sys

HOME = os.path.expanduser("~")
DIFFDOCK = f"{HOME}/DiffDock"
# Paths are env-overridable so a single new genotype can be docked into ITS OWN input/output/pose
# dirs, never touching the master full-sweep files. Defaults reproduce the original full-sweep run.
CSV_IN = os.environ.get("SWEEP_CSV", f"{HOME}/hackathon/data/full_sweep_input.csv")
RECEPTORS = f"{HOME}/hackathon/data/structures/prepared"
GNINA = f"{HOME}/hackathon/bin/gnina"
DRUGS = f"{HOME}/hackathon/data/drugs.csv"
REP_ROOT = os.environ.get("REP_ROOT", f"{HOME}/hackathon/results/replicates")
OUT = os.environ.get("SCORES_OUT", f"{HOME}/hackathon/results/gnina_scores_replicates.csv")
N_REPS = int(os.environ.get("N_REPS", "10"))

PDB_META = {
    "3POZ": ("EGFR", "WT"), "8A2B": ("EGFR", "L858R"), "4I24": ("EGFR", "T790M"),
    "5UGC": ("EGFR", "L858R+T790M"), "8FMI": ("KRAS", "WT"), "4LDJ": ("KRAS", "G12C"),
    "6OIM": ("KRAS", "G12C+sotorasib"),
    # new modeled genotypes (see docs/new_genotypes.md)
    "EGFRC797S": ("EGFR", "C797S"), "EGFRG719S": ("EGFR", "G719S"),
    "EGFRTRIPLE": ("EGFR", "L858R+T790M+C797S"), "KRASG12D": ("KRAS", "G12D"),
}
FIELDS = ["rep", "drug", "category", "pdb", "target", "state", "diffdock_confidence",
          "gnina_affinity", "gnina_minimize_rmsd", "gnina_cnn_score", "gnina_cnn_affinity"]


def drug_categories():
    with open(DRUGS) as f:
        return {r["name"]: r["category"] for r in csv.DictReader(f)}


def parse_scores(text):
    def grab(pat):
        m = re.search(pat, text)
        return float(m.group(1)) if m else None
    return dict(
        gnina_affinity=grab(r"Affinity:\s*(-?\d+\.?\d*)"),
        gnina_minimize_rmsd=grab(r"RMSD:\s*(-?\d+\.?\d*)"),
        gnina_cnn_score=grab(r"CNNscore:\s*(-?\d+\.?\d*)"),
        gnina_cnn_affinity=grab(r"CNNaffinity:\s*(-?\d+\.?\d*)"),
    )


def diffdock_confidence(folder_path):
    for g in glob.glob(f"{folder_path}/rank1_confidence*.sdf"):
        m = re.search(r"confidence(-?\d+\.?\d*)", os.path.basename(g))
        if m:
            return float(m.group(1))
    return None


def reps_in_csv():
    if not os.path.exists(OUT):
        return set()
    with open(OUT) as f:
        return {int(r["rep"]) for r in csv.DictReader(f)}


def n_complexes():
    with open(CSV_IN) as f:
        return sum(1 for _ in csv.DictReader(f))


def rep_poses_complete(rep_dir):
    return len(glob.glob(f"{rep_dir}/*/rank1.sdf")) >= n_complexes()


def run_diffdock(rep_dir):
    subprocess.run(
        [sys.executable, "-m", "inference", "--config", "default_inference_args.yaml",
         "--protein_ligand_csv", CSV_IN, "--out_dir", rep_dir],
        cwd=DIFFDOCK, check=True,
    )


def rescore_rep(rep, rep_dir, cat):
    out_rows = []
    for folder in sorted(os.listdir(rep_dir)):
        path = f"{rep_dir}/{folder}"
        rank1 = f"{path}/rank1.sdf"
        if not os.path.isdir(path) or not os.path.exists(rank1):
            continue
        drug, pdb = folder.rsplit("__", 1)
        res = subprocess.run([GNINA, "-r", f"{RECEPTORS}/{pdb}_receptor.pdb",
                              "-l", rank1, "--minimize"], capture_output=True, text=True)
        sc = parse_scores(res.stdout)
        target, state = PDB_META.get(pdb, ("?", "?"))
        out_rows.append(dict(rep=rep, drug=drug, category=cat.get(drug, "?"), pdb=pdb,
                             target=target, state=state,
                             diffdock_confidence=diffdock_confidence(path), **sc))
    return out_rows


def main():
    os.makedirs(REP_ROOT, exist_ok=True)
    cat = drug_categories()
    done = reps_in_csv()
    fh = open(OUT, "a", newline="")
    writer = csv.DictWriter(fh, fieldnames=FIELDS)
    if os.stat(OUT).st_size == 0:
        writer.writeheader(); fh.flush()

    rep1_affs = None
    for rep in range(1, N_REPS + 1):
        if rep in done:
            print(f"rep {rep}: already in CSV, skipping", flush=True)
            continue
        rep_dir = f"{REP_ROOT}/run{rep:02d}"
        if rep_poses_complete(rep_dir):
            print(f"rep {rep}: poses already exist, rescoring only", flush=True)
        else:
            print(f"=== rep {rep}: DiffDock sweep -> {rep_dir} ===", flush=True)
            run_diffdock(rep_dir)
        print(f"=== rep {rep}: gnina rescore ===", flush=True)
        rows = rescore_rep(rep, rep_dir, cat)
        writer.writerows(rows); fh.flush()
        print(f"=== rep {rep}: appended {len(rows)} rows to {OUT} ===", flush=True)

        # seed-safety: abort if rep 2 is identical to rep 1 (fixed seed -> wasted night)
        affs = {(r["drug"], r["pdb"]): r["gnina_affinity"] for r in rows}
        if rep == 1:
            rep1_affs = affs
        elif rep1_affs is not None and affs == rep1_affs:
            print("!!! rep is byte-identical to rep 1 -- DiffDock appears to have a FIXED SEED. "
                  "Replicates would be useless. Aborting; investigate --seed / config.", flush=True)
            break

    fh.close()
    print(f"\nDone. Replicate scores in {OUT}")


if __name__ == "__main__":
    main()
