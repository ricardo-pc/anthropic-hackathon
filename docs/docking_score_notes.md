# Docking score interpretation — read before computing any WT-vs-mutant delta

*Verified against DiffDock main-branch source + README by the Claude Science Specialist (Jul 8). Full response in `claude-science/` vault. These govern the Thursday stats layer.*

## DiffDock confidence — the sign convention (verified)
- The confidence score is a **logit** from a separately-trained head estimating P(pose is correct, i.e. RMSD < 2 Å to true pose). Unbounded, routinely **negative**.
- **Higher (less negative) = better.** README bands: `c > 0` high, `−1.5 < c < 0` moderate, `c < −1.5` low.
- Output files `rankN_confidence-X.XX.sdf`: the `-` is the number's **sign**, not a separator. `rank1_confidence-0.25.sdf` = confidence **−0.25**.
- **rank1 = highest confidence, by construction.** Source (`inference.py`): `re_order = np.argsort(confidence)[::-1]` (descending) then labels rank1, rank2… in that order. If ranks ever came out ascending, that signals a corrupted file, not a real run.
- Our erlotinib-vs-WT-EGFR test: rank1 = −0.25 (upper-moderate). In-distribution (drug-like ligand + single kinase domain), so the bands apply as written.

## The real exposure: reading a WT−mutant *difference* of confidences as biology
The three interpretation facts above are correct — but a delta pipeline can still go wrong. Five caveats, all from the Specialist's source-grounded review:

1. **Confidence is not affinity; a delta of it, doubly so.** DiffDock confidence measures *pose-placement certainty*, not ΔG. Erlotinib failing on T790M is an affinity/kinetics effect — DiffDock can place a confident pose on a clinically non-productive binding mode. **Rescore rank1 with gnina** (already the plan) and treat that as the affinity proxy, not the confidence. Confidence ≠ resistance readout.
2. **Scores aren't comparable across complexes — and WT vs mutant ARE different complexes.** The README explicitly warns it's "hard to compare confidence across different complexes or conformations." Treat a WT−mutant Δconfidence as a **weak ordinal signal**, not a metric.
3. **The score is stochastic — establish the run-to-run noise floor FIRST.** Diffusion sampler, `samples_per_complex=10`, no seed enforced by default. Two runs on the *same* structure give different rank1 confidences. **Before attributing any WT−mutant Δ to biology, run each structure N times (≥5–10) and measure the within-structure spread. If the Δ is smaller than that spread, it's noise.** This is the single most important control and the easiest to skip — it's exactly what the Bayesian-bootstrap layer is for.
4. **The 10 poses are one sampling run, not an ensemble.** rank1…rank10 are the sorted samples of a single draw. The thresholds refer to rank1 (the top pose). Don't average all 10 into a "mean confidence" and compare those across WT/mutant — the tail poses are low-quality by design.
5. **Model/config must be byte-identical across every structure in a comparison.**
   - `default_inference_args.yaml` pins **v1.1** weights (DiffDock-L). Never compare across weight versions.
   - `--old_confidence_model` defaults True; `old_filtering_model: true` in the YAML. Same flags for every structure.
   - **The YAML overwrites CLI flags** (`--config` applied after argparse) — e.g. passing `--samples_per_complex 40` is silently ignored if that key is in the YAML. To change sampling depth, **edit a copied YAML**, and use the identical config file for every structure in the delta. (Directly relevant when we add replicate sampling for caveat 3.)

## Bottom line
Reading a single score: solved. The work Thursday is in the *delta*: noise floor before biology, identical model/config across structures, gnina rescore of rank1 as the affinity proxy, and never letting Δconfidence stand in for the clinical resistance fact (which remains the ground truth we validate *against*).
