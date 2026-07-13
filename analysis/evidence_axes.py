#!/usr/bin/env python3
"""
Orthogonal evidence axes — reproduce the pathway-grounding + DepMap-dependency read for a genotype.

For a tumor's driver mutation, every docked drug gets two axes the docking never sees:
  - pathway grounding : is the drug's ESTABLISHED target in the driver's pathway / enzyme class?
  - DepMap dependency : is that target a gene lung adenocarcinoma actually needs (CRISPR essentiality)?

The point is orthogonality to the docking Delta. Run it and read the three-tier story on the double
mutant: on-target inhibitors corroborate on both axes, imatinib is in-class but hits no lung
dependency (its lead rests on the structural fit), and the statin/antidepressant/antibiotic "hits"
are off-pathway with no dependency — artifacts on both axes.

Usage:
    python analysis/evidence_axes.py                       # EGFR L858R+T790M
    python analysis/evidence_axes.py "KRAS G12C"
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import triage  # noqa: E402

PATH_W = {"aligned": "on-target ", "plausible": "in-class  ", "off-pathway": "off-path  "}
DEP_W = {"dependency": "lung dep ", "weak": "weak dep ", "none": "no dep   "}


def main():
    label = " ".join(sys.argv[1:]).strip() or "EGFR L858R+T790M"
    r = triage.triage(label)
    driver = r["target"]
    print(f"\nTUMOR {label}  (driver {driver})")
    print("Pathway grounding + DepMap dependency are ORTHOGONAL to the docking Delta below.\n")
    print(f"  {'drug':24}{'bucket':11}{'delta':>7}   {'pathway':10} {'depmap':9}  targets")
    print("  " + "-" * 92)
    # rank by mutant binding (strongest first), same as the triage table
    for d in r["drugs"]:
        e = d["evidence"]
        tgt = ", ".join(e["targets_display"]) or "(no human target)"
        print(f"  {d['drug']:24}{d['bucket']:11}{d['delta']:>+7.2f}   "
              f"{PATH_W[e['pathway']['status']]:10} {DEP_W[e['depmap']['status']]:9}  {tgt}")

    # the three-tier contrast, called out
    def pick(pred):
        return [d["drug"] for d in r["drugs"] if pred(d["evidence"])]
    corrob = pick(lambda e: e["pathway"]["status"] == "aligned" and e["depmap"]["status"] == "dependency")
    inbtwn = pick(lambda e: e["pathway"]["status"] == "plausible" and e["depmap"]["status"] == "weak")
    artif = pick(lambda e: e["pathway"]["status"] == "off-pathway" and e["depmap"]["status"] == "none")
    print("\n  corroborated (on-target + lung dependency):", ", ".join(corrob) or "none")
    print("  in-between  (in-class kinase, no lung dependency):", ", ".join(inbtwn) or "none")
    print("  artifacts   (off-pathway + no dependency):", ", ".join(artif[:8]),
          ("…" if len(artif) > 8 else ""))
    print("\nProvenance: data/gene_kb.json (DepMap LUAD dependency + KEGG pathway) and "
          "data/drug_targets.json (drug -> canonical target).")


if __name__ == "__main__":
    main()
