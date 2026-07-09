#!/usr/bin/env python3
"""
Bayesian bootstrap on the WT-vs-mutant affinity delta, with BH-FDR across drugs.
CPU, instant. Runs on the overnight replicate CSV (data/gnina_scores_replicates.csv);
falls back to the single-pass CSV for a plumbing smoke-test (point estimates only, no CI).

Method (Rubin 1981 Bayesian bootstrap): for a drug's WT affinities and mutant affinities
(one value per replicate), draw Dirichlet(1,...,1) weights over each set, take the weighted
means, and the delta = weighted_mean(mutant) - weighted_mean(WT). Repeat B times to get a
posterior on the delta; report the 95% credible interval and P(delta>0). Affinity is
kcal/mol (more negative = better), so delta>0 means the mutant binds WORSE (resistance).

Then BH-FDR across drugs within each comparison, using a two-sided tail probability.
"""
import csv
import os
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPL = f"{HERE}/data/gnina_scores_replicates.csv"
SINGLE = f"{HERE}/data/gnina_scores.csv"
B = 10000
RNG = np.random.default_rng(0)

# WT-vs-mutant comparisons per target: (label, wt_pdb, mut_pdb)
COMPARISONS = [
    ("EGFR WT->L858R",          "3POZ", "8A2B"),
    ("EGFR WT->T790M(single)",  "3POZ", "4I24"),
    ("EGFR WT->L858R+T790M",    "3POZ", "5UGC"),   # the headline resistance beat
    ("KRAS WT->G12C(apo)",      "8FMI", "4LDJ"),
    ("KRAS WT->G12C(sotorasib)","8FMI", "6OIM"),
]


def load(path):
    scores = defaultdict(list)  # (drug, pdb) -> [affinity per replicate]
    cat = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            a = r["gnina_affinity"]
            if a not in (None, ""):
                scores[(r["drug"], r["pdb"])].append(float(a))
            cat[r["drug"]] = r["category"]
    return scores, cat


def bayes_boot_delta(wt, mut):
    """Posterior samples of mean(mut) - mean(wt) via Bayesian bootstrap."""
    wt, mut = np.asarray(wt), np.asarray(mut)
    out = np.empty(B)
    for i in range(B):
        ww = RNG.dirichlet(np.ones(len(wt)))
        wm = RNG.dirichlet(np.ones(len(mut)))
        out[i] = mut @ wm - wt @ ww
    return out


def bh_fdr(pvals):
    """Benjamini-Hochberg adjusted p-values."""
    p = np.asarray(pvals)
    n = len(p)
    order = np.argsort(p)
    adj = np.empty(n)
    prev = 1.0
    for rank, idx in enumerate(reversed(order), start=1):
        k = n - rank + 1
        prev = min(prev, p[idx] * n / k)
        adj[idx] = prev
    return adj


def main():
    path = REPL if os.path.exists(REPL) else SINGLE
    single_pass = path == SINGLE
    scores, cat = load(path)
    n_reps = max((len(v) for v in scores.values()), default=0)
    print(f"Loaded {path.split('/')[-1]}  (max replicates per pair: {n_reps})")
    if single_pass:
        print("** SINGLE-PASS smoke test: point deltas only, no credible intervals. **")
        print("   (Run overnight.sbatch first for the real replicate-based version.)\n")

    for label, wt_pdb, mut_pdb in COMPARISONS:
        drugs = sorted({d for (d, p) in scores if p in (wt_pdb, mut_pdb)})
        rows = []
        for d in drugs:
            wt = scores.get((d, wt_pdb), [])
            mut = scores.get((d, mut_pdb), [])
            if not wt or not mut:
                continue
            point = float(np.mean(mut) - np.mean(wt))
            if single_pass or len(wt) < 2 or len(mut) < 2:
                rows.append((d, cat[d], point, None, None, None))
            else:
                post = bayes_boot_delta(wt, mut)
                lo, hi = np.percentile(post, [2.5, 97.5])
                p_gt0 = float(np.mean(post > 0))
                two_sided = 2 * min(p_gt0, 1 - p_gt0)
                rows.append((d, cat[d], point, lo, hi, two_sided))

        print(f"\n=== {label} ===   (delta>0 = mutant binds worse = resistance)")
        if rows and rows[0][5] is not None:
            pvals = [r[5] for r in rows]
            fdr = bh_fdr(pvals)
            print(f"{'drug':14}{'cat':22}{'delta':>8}{'95% CI':>18}{'BH-FDR':>9}")
            for (d, c, pt, lo, hi, _), q in sorted(zip(rows, fdr), key=lambda x: x[0][2], reverse=True):
                star = " *" if q < 0.05 and (lo > 0 or hi < 0) else ""
                print(f"{d:14}{c:22}{pt:>+8.2f}   [{lo:>+5.2f},{hi:>+5.2f}]{q:>9.3f}{star}")
        else:
            print(f"{'drug':14}{'cat':22}{'delta (point)':>14}")
            for d, c, pt, *_ in sorted(rows, key=lambda x: x[2], reverse=True):
                print(f"{d:14}{c:22}{pt:>+14.2f}")


if __name__ == "__main__":
    main()
