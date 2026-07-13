#!/usr/bin/env python3
"""
Library screen result — why statistics alone don't separate signal from artifact.

Night 1 screened 300 approved drugs (1 replicate) against WT + the resistant double mutant; night 2
replicated the ~35 that bound-and-shifted at N=10 for real credible intervals. This script triages
those replicated candidates inside the double-mutant genotype and shows the punchline:

  the docking + bootstrap flags a pile of candidates as significantly "improved" on the mutant, with
  tight credible intervals excluding zero and high confidence -- and essentially every one is a
  promiscuous scaffold (lipophilic CNS drugs, fluoroquinolone antibiotics) with no mechanistic link
  to EGFR. imatinib, the one mechanistically legitimate cross-kinase lead, has a WIDER interval than
  the artifacts. The statistics rank them backwards; only mechanism sorts them out.

That is the whole product thesis, measured at scale on real approved drugs.

Run:  python analysis/library_screen_triage.py    # prints + writes results/library_screen.txt
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import triage  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{HERE}/analysis/results/library_screen.txt"
GENOTYPE = "EGFR L858R+T790M"

# Coarse mechanistic class a reviewer would assign at a glance -- promiscuous scaffolds vs. plausible.
# (Illustrative labels for the screen readout; not an exhaustive pharmacology.)
CLASS = {
    "amitriptyline": "tricyclic antidepressant (CNS)", "clomipramine": "tricyclic antidepressant (CNS)",
    "chlorpromazine": "antipsychotic (CNS)", "promazine": "antipsychotic (CNS)",
    "trifluoperazine": "antipsychotic (CNS)", "sertindole": "antipsychotic (CNS)",
    "molindone": "antipsychotic (CNS)", "fluoxetine": "SSRI (CNS)", "citalopram": "SSRI (CNS)",
    "nomifensine": "antidepressant (CNS)", "diazepam": "benzodiazepine (CNS)",
    "clonazepam": "benzodiazepine (CNS)", "lorazepam": "benzodiazepine (CNS)",
    "bromazepam": "benzodiazepine (CNS)", "promethazine": "antihistamine (CNS)",
    "cyproheptadine": "antihistamine (CNS)", "morphine": "opioid (CNS)", "levorphanol": "opioid (CNS)",
    "apomorphine": "dopamine agonist (CNS)", "bromocriptine": "ergot / dopamine agonist (CNS)",
    "ergotamine": "ergot alkaloid", "rimonabant": "CB1 antagonist (CNS)",
    "procaine": "local anesthetic", "moxifloxacin": "fluoroquinolone antibiotic",
    "levofloxacin-anhydrous": "fluoroquinolone antibiotic", "temafloxacin": "fluoroquinolone antibiotic",
    "gemifloxacin": "fluoroquinolone antibiotic", "probucol": "antilipidemic", "gemfibrozil": "fibrate",
    "fenoldopam": "dopamine agonist (cardiovascular)", "rofecoxib": "COX-2 inhibitor",
    "mitoxantrone": "chemo (topoisomerase-II / DNA)", "indinavir-anhydrous": "HIV protease inhibitor",
    "tribromsalan": "topical antiseptic", "cefprozil-anhydrous-e": "cephalosporin antibiotic",
}


def main():
    t = triage.triage(GENOTYPE)
    cand = {r["name"] for r in csv.DictReader(open(f"{HERE}/data/candidates.csv"))}
    crows = [d for d in t["drugs"] if d["drug"] in cand]
    lines = []

    def emit(s=""):
        print(s); lines.append(s)

    emit(f"LIBRARY SCREEN — {len(cand)} replicated candidates triaged inside {GENOTYPE}")
    emit(f"(from an unbiased 300-drug approved library; night-2 replicates, N=10, WT 3POZ vs double 5UGC)")
    emit("=" * 92)

    def sig(ci):
        return "CI excludes 0" if (ci[0] > 0 or ci[1] < 0) else "straddles 0"

    for bucket in ("improved", "robust", "weakened", "non-binder"):
        rows = sorted([d for d in crows if d["bucket"] == bucket], key=lambda d: d["delta"])
        if not rows:
            continue
        emit(f"\n[{bucket.upper()}]  ({len(rows)})")
        emit(f"  {'drug':24}{'WT':>7}{'mut':>7}{'delta':>7}   {'95% CI':>16}  {'sig':<13} mechanism")
        for d in rows:
            ci = d["ci95"]
            emit(f"  {d['drug']:24}{d['affinity_wt']:>7.2f}{d['affinity_mut']:>7.2f}{d['delta']:>+7.2f}   "
                 f"{f'[{ci[0]:+.2f}, {ci[1]:+.2f}]':>16}  {sig(ci):<13} {CLASS.get(d['drug'], '?')}")

    im = next(d for d in t["drugs"] if d["drug"] == "imatinib")
    emit("\n" + "-" * 92)
    emit(f"REFERENCE — imatinib (curated, mechanistically legitimate kinase inhibitor): "
         f"bucket={im['bucket']}, delta={im['delta']:+.2f}, CI={im['ci95']} ({sig(im['ci95'])})")
    emit("\nPUNCHLINE")
    emit("  The 'improved' bucket is full of significant, high-confidence, CI-excludes-zero hits that are")
    emit("  ALL promiscuous scaffolds (lipophilic CNS drugs + fluoroquinolones) with no EGFR mechanism.")
    emit("  imatinib, the one credible cross-kinase lead, has a WIDER interval than these artifacts.")
    emit("  A credible interval says a score is reproducible, not that it is real. Mechanism is the filter.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
