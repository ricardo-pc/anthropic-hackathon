#!/usr/bin/env python3
"""
Validate the tumor registry against what's actually on disk — the ingestion check for "bring your
own tumor". For every mutation in config/mutations.json (or one you name), it confirms the wild-type
and mutant structures exist and that both have docking scores in the replicate CSV, then tells you
whether the tool can triage that genotype yet (and if not, exactly what's missing).

Run this after you add an entry to config/mutations.json and drop in your docking scores.

Usage:
  python src/check_registry.py                    # check every registry entry
  python src/check_registry.py "EGFR L858R+T790M" # check just one
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import triage  # noqa: E402

STRUCT = f"{triage.HERE}/data/structures/prepared"
MIN_REPS = 2  # need at least this many replicate runs per drug for a credible interval


def _structure_ok(pdb):
    return os.path.exists(f"{STRUCT}/{pdb}_receptor.pdb")


def _scores(aff, pdb):
    """(number of drugs scored against this structure, minimum replicate count across them)."""
    drugs = {d for (d, p) in aff if p == pdb}
    reps = [len(aff[(d, pdb)]) for d in drugs]
    return len(drugs), (min(reps) if reps else 0)


def check_one(label, aff):
    spec = triage.MUTATIONS[label]
    wt, mut = spec["wt"], spec["mut"]
    print(f"\n{label}  (target {spec.get('target','?')})")
    ok = True
    for role, pdb in [("WT    ", wt), ("mutant", mut)]:
        s_ok = _structure_ok(pdb)
        ndrugs, minrep = _scores(aff, pdb)
        s_scores = ndrugs > 0 and minrep >= MIN_REPS
        ok = ok and s_ok and s_scores
        struct_txt = "ok" if s_ok else f"MISSING ({STRUCT}/{pdb}_receptor.pdb)"
        if ndrugs == 0:
            score_txt = "none in data/gnina_scores_replicates.csv"
        else:
            score_txt = f"{ndrugs} drugs x >={minrep} reps" + ("" if minrep >= MIN_REPS
                        else f"  (need >= {MIN_REPS} reps)")
        print(f"  {role} {pdb:9} structure: {struct_txt:20} scores: {score_txt}")
    # how many drugs triage will actually rank (scored against BOTH states)
    both = {d for (d, p) in aff if p == wt} & {d for (d, p) in aff if p == mut}
    if ok:
        print(f"  => READY — triage will rank {len(both)} drugs")
    else:
        print("  => NOT READY — prepare the structure and/or run docking; "
              "see docs/bring_your_own_tumor.md")
    return ok


def main():
    aff, _, _, _ = triage._load()
    labels = sys.argv[1:] or list(triage.MUTATIONS)
    all_ok = True
    for label in labels:
        if label not in triage.MUTATIONS:
            print(f"\n{label!r}: not in the registry. Known: {list(triage.MUTATIONS)}")
            all_ok = False
            continue
        all_ok = check_one(label, aff) and all_ok
    print(f"\n{'All checked entries are triage-ready.' if all_ok else 'Some entries are not ready (see above).'}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
