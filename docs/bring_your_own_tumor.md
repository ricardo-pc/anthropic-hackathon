# Bring your own tumor (and your own GPU)

The tool ships with a fixed panel of mutations, but nothing about it is hard-wired to them. If you
have a tumor whose driver mutation isn't in the list, you can add it yourself — the only heavy step,
the molecular docking, runs on **your** GPU, and the tool ingests the scores it produces.

This is the honest division of labor: **docking needs a GPU and is compute-heavy** (it stays on your
hardware — a lab cluster or a rented cloud GPU); **everything downstream is instant on a laptop** and
already built (stats, four-bucket triage, the dashboard, Claude's read).

At a glance:

```
your structures ──▶ dock on your GPU ──▶ append scores ──▶ register in config ──▶ triage
  (WT + mutant)      (cluster/ pipeline)   (one CSV)         (config/mutations.json)  (it appears)
```

---

## What you need

- The **wild-type** and **mutant** protein structures for your target, as PDB files (from the RCSB
  PDB, or a homology/AlphaFold model). Pick a wild-type reference and a mutant structure the way
  `docs/scope.md` describes — aligned on mutation-independent anchors, genotype verified from sequence.
- A machine with an **NVIDIA GPU** (≈12 GB VRAM is enough for DiffDock) to run the docking. No GPU on
  hand? A rented cloud GPU works — the `cluster/` scripts are SLURM-flavored but the commands inside
  are portable.

## Step 1 — Prepare the structures

Put the raw PDBs in `data/structures/raw/` and prepare receptors the same way the built-in ones were:

```bash
python src/structure_prep.py         # writes data/structures/prepared/<PDB>_receptor.pdb
python src/verify_prep.py            # sanity-checks the prepared receptors
```

You should end with `data/structures/prepared/<WT_PDB>_receptor.pdb` and `<MUT_PDB>_receptor.pdb`.

## Step 2 — Dock on your GPU

Run the documented DiffDock → gnina pipeline in [`cluster/`](../cluster/README.md) against the drug
panel (`data/drugs.csv`). In short:

1. Push your prepared structures + `data/drugs.csv` to the GPU box.
2. Run the sweep (`full_sweep.sbatch`), then the gnina rescore (`rescore.sbatch`), then the
   replicate runs (`overnight.sbatch`, N ≥ 5–10 — you need replicates for credible intervals, not a
   single stochastic pass; the cluster README explains why).
3. Pull the resulting rows back.

The output is rows in the same schema as `data/gnina_scores_replicates.csv`:

```
rep,drug,category,pdb,target,state,diffdock_confidence,gnina_affinity,gnina_minimize_rmsd,gnina_cnn_score,gnina_cnn_affinity
```

Use **`gnina --minimize`, not `--score_only`** (raw DiffDock poses clash and score falsely positive —
see `docs/docking_score_notes.md`).

## Step 3 — Append the scores

Append your new `pdb` rows (both the wild-type and the mutant structure, all drugs, all replicates)
to `data/gnina_scores_replicates.csv`. If your wild-type reference is one the tool already has
(e.g. EGFR `3POZ`), you only need to dock and append the **mutant** structure's rows.

## Step 4 — Register the genotype

Add one entry to [`config/mutations.json`](../config/mutations.json) — no code changes:

```json
"EGFR L747_P753delinsS": {
  "target": "EGFR",
  "wt": "3POZ",
  "mut": "YOUR_PDB",
  "note": "exon-19 deletion; sensitizing — optional caveat shown with the result"
}
```

Optionally add the label to a list under `"cancer_types"` so it shows up in the selector and the
dashboard's cancer-type menu. If a tumor carries two variants that each have an entry (say an L858R
and a T790M structure), a combined `"EGFR L858R+T790M"`-style label is recognized automatically when
both component variants are present — that's how the double mutant works.

## Step 5 — Validate, then triage

```bash
python src/check_registry.py "EGFR L747_P753delinsS"
```

This confirms both structures exist and both have enough replicate scores, and prints **READY** (or
tells you exactly what's missing). Once it's ready:

```bash
python src/triage.py "EGFR L747_P753delinsS"     # the leaderboard
python src/build_dashboard.py                     # your genotype now appears in the dashboard
python src/interpret.py "triage EGFR L747_P753delinsS"   # Claude's plain-English read
```

Your genotype is now a first-class citizen everywhere the built-in ones are: the CLI, the selector,
the dashboard, the interpretation agent, and the MCP tools.

---

## On-demand from the app: connect a GPU (RunPod)

The steps above are the manual pipeline. The MutationRx app (`app/server.py`) can also dispatch a
de-novo point mutation to a GPU on demand — the "Connect GPU" gate. Wiring:

1. **Build the docking image.** A Docker image with DiffDock + gnina + PyMOL + `cluster/runpod_handler.py`
   (the reference worker). It models the mutant (`cluster/model_mutant.py`), docks the panel, and
   gnina-rescores — the same steps as above, packaged for a GPU worker.
2. **Deploy it as a RunPod serverless endpoint** and note the **endpoint id**.
3. **Point MutationRx at it**, either way:
   - env: `RUNPOD_API_KEY=… RUNPOD_ENDPOINT_ID=… python app/server.py` (real docking active on start), or
   - in the app: type a genotype that isn't precomputed → the **Connect GPU** gate → paste the endpoint
     id + key. The key is used server-side only, never stored in the page or committed.
4. Ask for a point mutation (e.g. `EGFR G719S`); the job runs on your GPU and the result appears with a
   **modeled structure** tag. `MUTATIONRX_FAST=1` (default) docks a reduced panel for a few-minute run;
   set `0` for the full panel.

**Just want to see the flow without a GPU?** Start with `MUTATIONRX_DRYRUN=1 python app/server.py`. A
de-novo genotype then walks the whole pipeline and returns a result loudly flagged **dry run — not
real docking** (the wild-type stands in for the mutant). It proves the mechanics end-to-end; it is
never a real result.

## Honesty, unchanged

The same guardrails apply to your genotype as to the built-in ones: docking affinity is a **proxy**,
not a measured K<sub>d</sub> or clinical efficacy; robust repurposing hits are **hypotheses** for
wet-lab follow-up, never discoveries; and non-covalent docking cannot capture covalent mechanisms
(the KRAS G12C caveat). If your target binds covalently, put that in the `note` and read the numbers
with the same care.
