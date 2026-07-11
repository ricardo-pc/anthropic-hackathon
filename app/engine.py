#!/usr/bin/env python3
"""
Compute engine — turns a triage REQUEST into a plan and a result, deciding cached-vs-compute.

A request is one of:
  - {"kind": "mutation", "label": "EGFR L858R+T790M"}   a registry genotype (precomputed)
  - {"kind": "tumor",    "sample_id": "TCGA-L9-A50W-01"} a cached real TCGA tumor (precomputed)
  - {"kind": "denovo",   "target": "EGFR", "mutation": "G719S"}  an arbitrary point mutation

The whole point of the "actual tool" is the denovo path: if we already have the structures + docking
scores for a genotype, it resolves from cache instantly; if not, it must MODEL the mutant structure
from the wild-type and DOCK the panel on a GPU — a real background job of staged work. This module
owns that decision and the pipeline stages; the GPU dispatch itself lives behind `GpuBackend` so the
demo can run fully on cache while a real backend (RunPod / your own SSH GPU) is plugged in for real.

Honesty carries through unchanged: docking affinity is a proxy; results from a MODELED mutant
structure are lower-confidence than from a crystal structure and are labeled as such.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import triage  # noqa: E402
import tcga  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Default wild-type reference structure per target (used when modeling a de-novo point mutant).
# Derived from the registry so it stays consistent with the curated set.
def _default_wt():
    wt = {}
    for spec in triage.MUTATIONS.values():
        wt.setdefault(spec["target"], spec["wt"])
    return wt


TARGET_WT = _default_wt()
POINT_MUT = re.compile(r"^[A-Z]\d+[A-Z]$")  # e.g. G719S, L858R, T790M — a single-residue substitution

# the honest pipeline, in order; the denovo (real-compute) path runs all of them
STAGES = [
    "Resolving genotype",
    "Modeling mutant structure",
    "Docking the panel (wild-type + mutant)",
    "Rescoring poses (gnina)",
    "Bootstrapping credible intervals",
    "Classifying & explaining",
]


class NeedsGpu(Exception):
    """Raised when a request requires real docking but no GPU backend is configured/allowed."""


def _claude_blob():
    try:
        import json
        p = f"{HERE}/data/claude_reads.json"
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _claude_read(key):
    return _claude_blob().get("reads", {}).get(key)


def _claude_model():
    return _claude_blob().get("__model", "Claude")


def _known_label_for(target, mutation):
    """If a registry label already covers this exact point mutation, return it (=> cached)."""
    want = f"{target} {mutation}"
    for label in triage.MUTATIONS:
        if label == want:
            return label
    return None


def resolve(req):
    """Resolve a request to a plan dict without doing heavy work.

    Returns keys: kind, label (display), target, cached (bool), modeled (bool), needs_compute (bool),
    plus 'error' if the request is malformed / unsupported.
    """
    kind = req.get("kind")
    if kind == "mutation":
        label = req.get("label", "")
        if label not in triage.MUTATIONS:
            return {"error": f"unknown mutation {label!r}", "known": list(triage.MUTATIONS)}
        return dict(kind=kind, label=label, target=triage.MUTATIONS[label]["target"],
                    cached=True, modeled=False, needs_compute=False)
    if kind == "tumor":
        sid = req.get("sample_id", "")
        try:
            sample = tcga.load_sample(sid)          # metadata only — no triage/bootstrap yet
            mapping = tcga.map_to_targets(sample["mutations"])
        except (KeyError, FileNotFoundError) as e:
            return {"error": str(e)}
        matched = mapping["matched_genotypes"]
        if not matched:
            return {"error": f"{sid} carries no in-scope mutation"}
        primary = matched[0]
        return dict(kind=kind, label=primary, sample_id=sid,
                    target=triage.MUTATIONS[primary]["target"], cached=True, modeled=False,
                    needs_compute=False,
                    tumor=dict(sample_id=sid, n_mutations=sample["n_mutations"],
                               in_scope_variants=mapping["in_scope_variants"],
                               matched_genotypes=matched, source=sample["source"]))
    if kind == "denovo":
        target = (req.get("target") or "").upper().strip()
        mutation = (req.get("mutation") or "").upper().strip()
        if target not in TARGET_WT:
            return {"error": f"unsupported target {target!r}; supported: {sorted(TARGET_WT)}"}
        if not POINT_MUT.match(mutation):
            return {"error": f"{mutation!r} is not a point mutation (expected like 'G719S'). "
                             f"Insertions/deletions/fusions need a real structure — out of on-demand scope."}
        known = _known_label_for(target, mutation)
        if known:
            return dict(kind="mutation", label=known, target=target, cached=True, modeled=False,
                        needs_compute=False, resolved_from="denovo")
        return dict(kind=kind, label=f"{target} {mutation}", target=target, cached=False,
                    modeled=True, needs_compute=True, wt=TARGET_WT[target], mutation=mutation)
    return {"error": f"unknown request kind {kind!r}"}


def result_for_computed(plan, mut_pdb, dry_run=False):
    """Build the result payload for a genotype computed on a GPU (or a dry-run placeholder).

    `mut_pdb` is the freshly-docked mutant structure id whose scores are now in the replicate CSV.
    For a dry run it's the wild-type used as a stand-in — the payload is flagged dry_run so the UI
    shows a loud 'not real docking' banner and it can never be mistaken for a genuine result.
    """
    label = plan["label"]
    data = triage.triage_structures(plan["wt"], mut_pdb, plan["target"], label,
                                    note="Structure modeled from the wild-type by side-chain "
                                         "substitution — lower confidence than a crystal structure.")
    return dict(
        label=label, target=data["target"], note=data.get("note"), drugs=data["drugs"],
        cached=False, modeled=True, dry_run=dry_run,
        source="dry run — pipeline test, NOT real docking" if dry_run else "computed on your GPU",
        tumor=None, claude_read=None, claude_model=_claude_model(), validation=None,
    )


def result_for_cached(plan):
    """Build the full result payload for a cached plan (instant — the physics ran earlier)."""
    label = plan["label"]
    data = triage.triage(label)
    key = plan.get("sample_id") or label
    modeled = bool(triage.MUTATIONS.get(label, {}).get("modeled"))  # e.g. C797S: side-chain-swap model
    return dict(
        label=label, target=data["target"], note=data.get("note"), drugs=data["drugs"],
        cached=True, modeled=modeled,
        source="precomputed (modeled structure)" if modeled else "precomputed (curated crystal structures)",
        tumor=plan.get("tumor"), claude_read=_claude_read(key) or _claude_read(label),
        claude_model=_claude_model(), validation=_VALIDATION.get(label),
    )


# reuse the same validation blurbs the static dashboard uses (single source would be nicer; kept
# short here to avoid a circular import with the builder)
_VALIDATION = {
    "EGFR L858R+T790M": "Recovers the acquired-resistance signature: erlotinib and gefitinib lose "
        "binding on the double mutant (credible intervals exclude zero) while osimertinib holds — the "
        "known clinical picture, reproduced from docking alone.",
    "KRAS G12C": "Non-covalent docking cannot capture the covalent Cys12 bond that defines the G12C "
        "drugs, so sotorasib / adagrasib / divarasib are unreliable in both directions — a caveat, "
        "not a finding.",
}
