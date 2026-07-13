#!/usr/bin/env python3
"""
Orthogonal evidence axes — the "should I believe this docking hit?" layer.

Docking answers "does the drug fit the mutant pocket?" (the Delta). These two axes answer a
DIFFERENT question, using data the docking never sees, so a coincidental score can be caught:

  1. Pathway grounding  — is the drug's ESTABLISHED molecular target in the same signaling
                          pathway / enzyme class as the tumor's driver? (mechanistic coherence)
  2. DepMap dependency  — is that target a genetic dependency this cancer actually needs, from
                          DepMap CRISPR essentiality in lung adenocarcinoma? (does the cancer need it)

The point is orthogonality. A statin can dock well (good Delta) yet be off-pathway and hit no
dependency (both axes red) => almost certainly a docking artifact. An on-target inhibitor is
aligned + a real dependency (both green). imatinib is the interesting middle: same kinase class
(plausible) but its own targets aren't lung dependencies (weak) => the lead rests entirely on the
structural EGFR cross-binding the docking found, which is exactly how it should be read.

Data: data/drug_targets.json (drug -> canonical human targets) + data/gene_kb.json (gene ->
pathway + LUAD dependency). Provenance and honesty notes live in those files. Pure lookups, no
network, deterministic.
"""
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GENE_KB = os.path.join(HERE, "data", "gene_kb.json")
_DRUG_TARGETS = os.path.join(HERE, "data", "drug_targets.json")

_cache = {}


def _load():
    if not _cache:
        with open(_GENE_KB) as f:
            kb = json.load(f)
        with open(_DRUG_TARGETS) as f:
            dt = json.load(f)
        _cache["genes"] = kb["genes"]
        _cache["driver_axis"] = kb.get("driver_axis", "RTK-RAS-MAPK")
        _cache["drugs"] = dt["drugs"]
    return _cache


def _gene(sym):
    return _load()["genes"].get(sym)


def targets_for(drug):
    """Canonical human target gene symbols for a drug (['NONE'] if unmapped)."""
    rec = _load()["drugs"].get(drug)
    if not rec:
        return ["NONE"], None
    return rec.get("targets") or ["NONE"], rec.get("class")


def _pathway_axis(targets, driver):
    """aligned | plausible | off-pathway, relative to the tumor's driver gene."""
    axis = _load()["driver_axis"]
    driver_kb = _gene(driver)
    driver_pathway = driver_kb["pathway"] if driver_kb else axis
    real = [g for g in targets if g not in ("NONE", "BACTERIAL", "VIRAL")]

    if driver in targets:
        return dict(status="aligned",
                    detail=f"the drug's own target is {driver}, the tumor's driver")
    same = [g for g in real if (_gene(g) or {}).get("pathway") == driver_pathway]
    if same:
        klass = "kinase class" if all((_gene(g) or {}).get("kinase") for g in same) else "pathway"
        names = ", ".join(same[:3])
        return dict(status="plausible",
                    detail=f"targets {names} in the same {driver_pathway} {klass} as {driver}, "
                           f"not {driver} itself")
    if not real:
        pw = (_gene(targets[0]) or {}).get("pathway", "no annotated human target")
        return dict(status="off-pathway", detail=f"{pw}; unrelated to {driver}")
    pw = (_gene(real[0]) or {}).get("pathway", "unknown")
    return dict(status="off-pathway",
                detail=f"target pathway is {pw}, unrelated to the {driver} driver")


_DEP_RANK = {"selective": 3, "weak": 2, "housekeeping": 1, "none": 0, "na": -1}


def _depmap_axis(targets, driver):
    """dependency | weak | none, driver-aware. Green only when the drug engages the tumor's own
    driver and that driver is a selective LUAD dependency; an oncogenic target that is not this
    tumor's dependency (another oncogenic kinase, or a dependency only in a different genotype) is
    amber; a non-oncology / housekeeping / non-human target is grey."""
    axis = _load()["driver_axis"]
    driver_kb = _gene(driver)
    if driver in targets and driver_kb and driver_kb["depmap"]["class"] == "selective":
        d = driver_kb["depmap"]
        return dict(status="dependency", gene_effect=d["gene_effect"],
                    detail=f"{driver} is a selective lung-adenocarcinoma dependency "
                           f"({d['context']}); this drug engages it")
    # best-ranked target by dependency class
    ranked = sorted(((_DEP_RANK.get((_gene(g) or {}).get("depmap", {}).get("class", "na"), -1), g)
                     for g in targets), reverse=True)
    best_rank, best = ranked[0]
    bdep = (_gene(best) or {}).get("depmap", {})
    # oncogenic kinase in the driver's own signaling axis (a real cancer target somewhere, e.g. ABL1/
    # KIT for imatinib) — amber even when it's not a LUAD dependency, distinct from a psychiatric drug
    onco_kinases = [g for g in targets
                    if (_gene(g) or {}).get("kinase") and (_gene(g) or {}).get("pathway") == axis]
    if best_rank >= 2:  # a dependency in some (other) genotype, but not this tumor's driver
        return dict(status="weak", gene_effect=bdep.get("gene_effect"),
                    detail=bdep.get("note", "an oncogenic target, but not this tumor's dependency"))
    if onco_kinases:
        names = ", ".join(onco_kinases[:3])
        return dict(status="weak", gene_effect=bdep.get("gene_effect"),
                    detail=f"targets {names} — oncogenic kinases, but not lung-adenocarcinoma "
                           f"dependencies; the lead rests on the structural fit, not a known vulnerability")
    if best_rank == 1:  # housekeeping / pan-essential
        return dict(status="none", gene_effect=bdep.get("gene_effect"),
                    detail=bdep.get("note", "broadly essential, not a cancer-selective dependency"))
    return dict(status="none", gene_effect=bdep.get("gene_effect"),
                detail=bdep.get("note", "not a lung-adenocarcinoma dependency"))


def annotate_drug(drug, driver):
    """Full evidence-axis annotation for one drug against a driver gene (EGFR / KRAS)."""
    targets, klass = targets_for(drug)
    display = [g for g in targets if g not in ("NONE", "BACTERIAL", "VIRAL")]
    return dict(
        targets=targets,
        targets_display=display,
        target_class=klass,
        pathway=_pathway_axis(targets, driver),
        depmap=_depmap_axis(targets, driver),
    )


def annotate_result(result):
    """Add an `evidence` block to every drug in a triage result dict (uses result['target'] as the
    driver gene). Mutates and returns the dict. Safe to call on any triage_structures() output."""
    driver = result.get("target")
    for d in result.get("drugs", []):
        d["evidence"] = annotate_drug(d["drug"], driver)
    return result


# one-line human summary, for the CLI and the Claude interpretation layer
_PATH_WORD = {"aligned": "on-target", "plausible": "same class/pathway", "off-pathway": "off-pathway"}
_DEP_WORD = {"dependency": "a LUAD dependency", "weak": "not a LUAD dependency", "none": "no cancer dependency"}


def summary_line(drug, driver):
    a = annotate_drug(drug, driver)
    tgt = ", ".join(a["targets_display"]) or "no annotated human target"
    return (f"{drug}: targets {tgt}. Pathway {_PATH_WORD[a['pathway']['status']]} "
            f"({a['pathway']['detail']}). DepMap: {_DEP_WORD[a['depmap']['status']]} "
            f"({a['depmap']['detail']}).")


if __name__ == "__main__":
    import sys
    driver = sys.argv[1] if len(sys.argv) > 1 else "EGFR"
    drugs = sys.argv[2:] or ["osimertinib", "erlotinib", "imatinib", "sorafenib",
                             "simvastatin", "propranolol", "fluoxetine", "moxifloxacin"]
    print(f"driver = {driver}\n" + "-" * 72)
    for d in drugs:
        print(summary_line(d, driver))
