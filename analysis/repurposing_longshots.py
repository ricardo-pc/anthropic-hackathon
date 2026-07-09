#!/usr/bin/env python3
"""
Long-shot repurposing screen: did any non-oncology candidate turn up as a genuine
mutation-robust EGFR binder? A real hit = strong absolute affinity AND holds on the
resistant mutant AND a decent pose. EGFR only (KRAS is covalent-confounded).

Honest framing: this is hypothesis-generating (docking is a proxy), not a discovery.
Reads the 7-replicate table; reports per-drug means.
"""
import csv
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = list(csv.DictReader(open(f"{HERE}/data/gnina_scores_replicates.csv")))

aff, cnn, cat = defaultdict(list), defaultdict(list), {}
for r in rows:
    aff[(r["drug"], r["pdb"])].append(float(r["gnina_affinity"]))
    cnn[(r["drug"], r["pdb"])].append(float(r["gnina_cnn_score"]))
    cat[r["drug"]] = r["category"]

def mean(d, p, t):
    v = t.get((d, p))
    return sum(v) / len(v) if v else None

print("Calibration - approved EGFR drugs (absolute affinity, WT 3POZ -> resistant 5UGC):")
for d in ["erlotinib", "gefitinib", "osimertinib"]:
    print(f"  {d:12} WT {mean(d,'3POZ',aff):+.2f}  resistant {mean(d,'5UGC',aff):+.2f}  CNNpose {mean(d,'3POZ',cnn):.2f}")

print("\nLong shots (repurposing_candidate), ranked by EGFR-WT affinity:")
print(f"{'drug':13}{'WT':>8}{'resistant':>11}{'delta':>8}{'CNNpose':>9}  verdict")
data = []
for d in [x for x in cat if cat[x] == "repurposing_candidate"]:
    wt, mut, c = mean(d, "3POZ", aff), mean(d, "5UGC", aff), mean(d, "3POZ", cnn)
    data.append((wt, d, mut, mut - wt, c))
for wt, d, mut, delta, c in sorted(data):
    robust = abs(delta) < 0.8
    hit = wt < -6.5 and robust and c > 0.4
    verdict = "** robust EGFR binder, follow up **" if hit else \
              ("holds but weak/poor-pose" if robust else "loses on mutant")
    print(f"{d:13}{wt:>8.2f}{mut:>11.2f}{delta:>+8.2f}{c:>9.2f}  {verdict}")
print("\nNOTE: docking proxy, not measured affinity; small molecules can score deceptively.")
print("Propranolol/thalidomide are worth-a-look hypotheses, not established EGFR inhibitors.")
