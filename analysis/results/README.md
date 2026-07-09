# Results — statistical validation

Bayesian bootstrap (7 independent DiffDock replicates, gnina --minimize rescored) on the
WT-vs-mutant affinity delta, BH-FDR across drugs. Full output: `bootstrap_deltas_7reps.txt`.
Regenerate: `python analysis/bootstrap_deltas.py` (reads `data/gnina_scores_replicates.csv`).

## Headline — EGFR resistance reproduced with credible intervals (the demo Act 1)
Comparison: WT (3POZ) → resistant double mutant L858R+T790M (5UGC). delta>0 = binds worse.

| Drug | delta (kcal/mol) | 95% CI | BH-FDR | verdict |
|---|---|---|---|---|
| erlotinib | +1.90 | [+1.83, +1.97] | <0.001 | **resistance** — CI excludes 0 |
| gefitinib | +1.37 | [+1.05, +1.65] | <0.001 | **resistance** — CI excludes 0 |
| osimertinib | +0.02 | [−0.44, +0.46] | 0.896 | **holds** — CI includes 0 |

First-gen inhibitors lose binding on the resistant tumor (significant); osimertinib holds
(not significant). The intervals are cleanly separated — the "confident call, not a coin
flip" result the demo needs. Matches the known clinical fact (docs/known_answers.md).

## Key secondary findings
- **The single T790M structure (4I24) gives the WRONG story** — gefitinib (−0.94), osimertinib
  (−0.97), afatinib (−0.98) all *improve*, opposite of reality. Only the clinically-correct
  L858R+T790M double (5UGC) reproduces resistance. Quantitative proof the double-mutant
  choice (Claude Science Specialist, scope §6.2) was essential, not cosmetic.
- **KRAS G12C confounded as predicted** — the G12C drugs bind the *apo* mutant (4LDJ) WORSE
  than WT KRAS (adagrasib +2.29, divarasib +2.39, sotorasib +0.54): non-covalent docking
  can't capture the Cys12 covalent selectivity. Honest limitation; demo leads on EGFR.
- **Wide/erratic CIs are the QC-flagged pairs** — the large deltas (sorafenib +24.9, ponatinib
  +17.6 on 6OIM) are the positive-affinity, high-minimize-RMSD poses from the QC check
  (known_answer_check.py); the bootstrap correctly renders them as low-confidence, not signal.

## Caveats (per docs/docking_score_notes.md)
Docking affinity is a proxy, not a measured Kd; the bootstrap quantifies *sampling* uncertainty
in that proxy, not its accuracy vs. experiment. 7 replicates; more would tighten intervals
marginally but the headline is already conclusive.
