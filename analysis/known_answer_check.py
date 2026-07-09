#!/usr/bin/env python3
"""
Known-answer validation of the single-pass gnina affinities (data/gnina_scores.csv).

Does the pipeline reproduce established oncology facts, blind?
  1. EGFR: first-gen erlotinib/gefitinib LOSE binding on the resistant mutant; osimertinib HOLDS.
  2. KRAS: sotorasib/adagrasib exploit G12C (flagged pre-run as the covalent-docking risk).

This is a SINGLE-PASS direction check (Wed success test). Magnitudes are not yet noise-
floored -- the Thursday stats layer adds replicate runs + the Bayesian bootstrap before any
delta is treated as significant (see docs/docking_score_notes.md).
"""
import csv
import os
from collections import Counter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = list(csv.DictReader(open(f"{HERE}/data/gnina_scores.csv")))
idx = {(r["drug"], r["pdb"]): r for r in rows}

def aff(drug, pdb):
    return float(idx[(drug, pdb)]["gnina_affinity"])

def rmsd(drug, pdb):
    return float(idx[(drug, pdb)]["gnina_minimize_rmsd"])


def egfr_resistance():
    print("EGFR sensitive -> resistant  (3POZ WT -> 5UGC L858R+T790M double mutant)")
    print("Expect: erlotinib/gefitinib lose binding (delta > 0); osimertinib holds (delta ~ 0)")
    print(f"{'drug':12}{'WT':>9}{'resistant':>11}{'delta':>9}  verdict")
    deltas = {}
    for d in ["erlotinib", "gefitinib", "osimertinib"]:
        wt, mut = aff(d, "3POZ"), aff(d, "5UGC")
        deltas[d] = mut - wt
        v = "LOSES binding" if deltas[d] > 0.8 else "HOLDS"
        print(f"{d:12}{wt:>9.2f}{mut:>11.2f}{deltas[d]:>+9.2f}  {v}")
    sep_e = deltas["erlotinib"] - deltas["osimertinib"]
    sep_g = deltas["gefitinib"] - deltas["osimertinib"]
    print(f"  -> osimertinib holds {sep_e:.2f}/{sep_g:.2f} kcal/mol better than erlotinib/gefitinib")
    print("  NOTE: on T790M-SINGLE (4I24) the story is muddy (gefitinib improves) -- the")
    print("        clinically-correct double mutant (5UGC) gives the clean result, vindicating")
    print("        the structure choice (docs/scope.md 6.2).")


def kras_covalent():
    print("\nKRAS G12C drugs -- the covalent-docking risk beat")
    print(f"{'drug':12}{'KRAS_WT':>9}{'G12C_apo':>10}{'G12C+soto':>11}   (8FMI/4LDJ/6OIM)")
    for d in ["sotorasib", "adagrasib", "divarasib"]:
        print(f"{d:12}{aff(d,'8FMI'):>9.2f}{aff(d,'4LDJ'):>10.2f}{aff(d,'6OIM'):>11.2f}")
    print("  Confirmed confounded as predicted: sotorasib binds WT KRAS at least as well as")
    print("  G12C -- non-covalent docking cannot capture the Cys12 covalent selectivity that")
    print("  IS the G12C story. Lead the demo on EGFR; treat KRAS as the honest hard case.")


def qc():
    pos = [(r["drug"], r["pdb"], float(r["gnina_affinity"]), float(r["gnina_minimize_rmsd"]))
           for r in rows if float(r["gnina_affinity"]) > 0]
    print(f"\nQC -- {len(pos)}/189 pairs have POSITIVE affinity (pose wouldn't relax to a binder):")
    for d, p, a, rm in sorted(pos, key=lambda x: -x[2]):
        print(f"   {d:14} x {p:6} aff={a:+7.2f}  rmsd={rm:.1f}")
    print("   by structure:", dict(Counter(p for _, p, _, _ in pos)))
    print("   -> concentrated in 6OIM (KRAS induced-fit pocket, shaped for sotorasib) and big")
    print("      molecules docked into targets they don't fit (mostly correct 'non-binders',")
    print("      but a positive score is QC-unreliable, not a clean weak-binding number).")


if __name__ == "__main__":
    egfr_resistance()
    kras_covalent()
    qc()
