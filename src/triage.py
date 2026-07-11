#!/usr/bin/env python3
"""
Triage engine — the deterministic core the interpretation agent reasons over.

Given a tumor mutation, returns each drug classified into one of four buckets, with the
WT-vs-mutant affinity delta and its 95% credible interval (Bayesian bootstrap over the
docking replicates). Classification is DETERMINISTIC and reproducible; the Claude layer
explains it, it does not invent it.

Four buckets (affinity kcal/mol, more negative = stronger binding; delta = mutant - WT,
positive delta = binds worse on the mutant = resistance):
  - weakened   : binds WT but loses binding on the mutant (resistance predictor)
  - robust     : binds the mutant and does NOT significantly weaken (safe repurposing bet)
  - improved   : binds significantly BETTER on the mutant (rare)
  - non-binder : doesn't bind either state, or the pose is QC-unreliable

CLI:  python src/triage.py "EGFR L858R+T790M"
"""
import copy
import csv
import json
import os
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPL = f"{HERE}/data/gnina_scores_replicates.csv"
REGISTRY = f"{HERE}/config/mutations.json"
TRIAGE_CACHE = f"{HERE}/data/triage_cache.json"  # precomputed results for the static registry genotypes

# --- tunable thresholds (documented, not magic) ---
BIND_KCAL = -6.0      # affinity <= this counts as "binds"
DELTA_MEANINGFUL = 1.0  # kcal/mol; a shift smaller than this is practically negligible even if
                        # statistically significant (~5x affinity change; ~docking noise floor).
                        # Guards against calling a trivially-small-but-significant delta "resistance".
QC_RMSD_MAX = 5.0     # mean minimize RMSD above this => pose unreliable
B = 4000              # bootstrap iterations
RNG = np.random.default_rng(0)

# The tumor registry: mutation label -> mutant structure, WT reference, and an honesty note; plus
# the cancer-type -> mutations map for the UI selector. This lives in config/mutations.json so a user
# can add their OWN tumor without editing code (see docs/bring_your_own_tumor.md). The built-in
# defaults below are the canonical in-scope set (matches docs/scope.md) AND the fallback used if the
# config file is absent, so the tool always works out of the box.
_BUILTIN_MUTATIONS = {
    "EGFR L858R":        dict(mut="8A2B", wt="3POZ", target="EGFR"),
    "EGFR T790M":        dict(mut="4I24", wt="3POZ", target="EGFR",
                              note="single T790M; clinically T790M usually co-occurs with L858R "
                                   "-- see 'EGFR L858R+T790M', which is the resistant tumor and "
                                   "gives the reliable read."),
    "EGFR L858R+T790M":  dict(mut="5UGC", wt="3POZ", target="EGFR",
                              note="the clinically relevant acquired-resistance tumor."),
    "KRAS G12C":         dict(mut="4LDJ", wt="8FMI", target="KRAS",
                              note="apo (closed) pocket; non-covalent docking does not capture the "
                                   "covalent Cys12 selectivity that defines G12C drugs -- read with care."),
    "KRAS G12C (drug-bound pocket)": dict(mut="6OIM", wt="8FMI", target="KRAS",
                              note="switch-II pocket already opened by sotorasib; other drugs docked "
                                   "into this induced conformation are often unreliable."),
}
_BUILTIN_CANCER_TYPES = {
    "lung cancer": ["EGFR L858R", "EGFR T790M", "EGFR L858R+T790M", "KRAS G12C"],
    "colorectal cancer": ["KRAS G12C"],
}


def _load_registry():
    """Registry from config/mutations.json when present, else the built-in defaults."""
    if os.path.exists(REGISTRY):
        with open(REGISTRY) as f:
            data = json.load(f)
        muts = data.get("mutations") or _BUILTIN_MUTATIONS
        cancers = data.get("cancer_types") or _BUILTIN_CANCER_TYPES
        return muts, cancers
    return _BUILTIN_MUTATIONS, _BUILTIN_CANCER_TYPES


MUTATIONS, CANCER_TYPES = _load_registry()


def _load():
    aff, rmsd, conf, cat = defaultdict(list), defaultdict(list), defaultdict(list), {}
    with open(REPL) as f:
        for r in csv.DictReader(f):
            key = (r["drug"], r["pdb"])
            aff[key].append(float(r["gnina_affinity"]))
            rmsd[key].append(float(r["gnina_minimize_rmsd"]))
            conf[key].append(float(r["diffdock_confidence"]) if r["diffdock_confidence"] else np.nan)
            cat[r["drug"]] = r["category"]
    return aff, rmsd, conf, cat


def _boot_delta_ci(wt, mut):
    """95% credible interval + significance flags for mean(mut)-mean(WT)."""
    wt, mut = np.asarray(wt), np.asarray(mut)
    out = np.empty(B)
    for i in range(B):
        out[i] = mut @ RNG.dirichlet(np.ones(len(mut))) - wt @ RNG.dirichlet(np.ones(len(wt)))
    lo, hi = np.percentile(out, [2.5, 97.5])
    return float(lo), float(hi)


def _bucket(aff_wt, aff_mut, rmsd_mut, lo, hi):
    """Deterministic four-bucket classification. Returns (bucket, confidence, reason).
    A shift must be BOTH statistically significant (CI excludes 0) AND practically meaningful
    (|delta| >= DELTA_MEANINGFUL) to count as weakened/improved -- effect size, not just p."""
    if aff_mut > 0 or aff_wt > 0 or rmsd_mut > QC_RMSD_MAX:
        return "non-binder", "low", "QC-unreliable pose (positive affinity or large minimization move)"
    delta = aff_mut - aff_wt
    binds_wt = aff_wt <= BIND_KCAL
    binds_mut = aff_mut <= BIND_KCAL
    meaningful_worse = lo > 0 and delta >= DELTA_MEANINGFUL     # sig AND big enough to matter
    meaningful_better = hi < 0 and delta <= -DELTA_MEANINGFUL

    if not binds_wt and not binds_mut:
        return "non-binder", "high", "does not bind either the wild-type or the mutant"
    if meaningful_better and binds_mut:
        return "improved", "high", "binds meaningfully and significantly better on the mutant"
    if binds_wt and not binds_mut:
        return "weakened", ("high" if lo > 0 else "low"), "binds the wild-type but drops below the binding threshold on the mutant"
    if meaningful_worse:
        return "weakened", "high", "significantly and meaningfully weaker on the mutant, though still above threshold"
    if binds_mut:
        return "robust", "high" if binds_wt else "medium", "binds the mutant with no meaningful weakening vs wild-type"
    return "non-binder", "low", "weak/ambiguous binding"


def triage_structures(wt_pdb, mut_pdb, target, label, note=None, data=None):
    """Core triage over two structures' docking scores — the reusable engine under triage().

    Works for ANY wild-type/mutant structure pair that has scores in the replicate CSV, not just the
    curated registry: the bring-your-own-GPU path docks a new mutant, appends its rows, then calls
    this with the fresh mutant PDB id. `data` is an optional preloaded (aff, rmsd, conf, cat) tuple.
    """
    aff, rmsd, conf, cat = data if data is not None else _load()
    drugs = sorted({d for (d, p) in aff if p == mut_pdb})
    results = []
    for d in drugs:
        wt_vals, mut_vals = aff.get((d, wt_pdb)), aff.get((d, mut_pdb))
        if not wt_vals or not mut_vals:
            continue
        aff_wt, aff_mut = float(np.mean(wt_vals)), float(np.mean(mut_vals))
        rmsd_mut = float(np.mean(rmsd[(d, mut_pdb)]))
        lo, hi = _boot_delta_ci(wt_vals, mut_vals)
        bucket, confidence, reason = _bucket(aff_wt, aff_mut, rmsd_mut, lo, hi)
        results.append(dict(
            drug=d, category=cat[d], bucket=bucket, confidence=confidence, reason=reason,
            affinity_wt=round(aff_wt, 2), affinity_mut=round(aff_mut, 2),
            delta=round(aff_mut - aff_wt, 2), ci95=[round(lo, 2), round(hi, 2)],
        ))
    # rank: strongest binders to the actual mutant first (most negative affinity_mut)
    results.sort(key=lambda r: r["affinity_mut"])
    return dict(mutation=label, target=target, note=note, drugs=results)


_TCACHE = None


def _triage_cache():
    """Lazily load the precomputed triage results (empty dict if the cache file is absent)."""
    global _TCACHE
    if _TCACHE is None:
        try:
            with open(TRIAGE_CACHE) as f:
                _TCACHE = json.load(f)
        except (OSError, ValueError):
            _TCACHE = {}
    return _TCACHE


def triage(mutation):
    """Return the ranked, bucketed drug list for a registry mutation.

    Serves a PRECOMPUTED result from data/triage_cache.json when present -- instant, and it avoids
    re-running the 4000-iteration bootstrap on every request (which is slow on a small hosted CPU).
    Falls back to live computation for genotypes not in the cache (e.g. a bring-your-own-GPU mutation).
    Rebuild the cache with build_triage_cache() whenever the docking data changes.
    """
    if mutation not in MUTATIONS:
        raise KeyError(f"unknown mutation {mutation!r}; known: {list(MUTATIONS)}")
    cached = _triage_cache().get(mutation)
    if cached is not None:
        return copy.deepcopy(cached)
    spec = MUTATIONS[mutation]
    return triage_structures(spec["wt"], spec["mut"], spec["target"], mutation, spec.get("note"))


def build_triage_cache(path=TRIAGE_CACHE):
    """Precompute triage for every registry genotype and write the cache JSON (run at build time)."""
    data = _load()  # load the docking scores once and reuse across all genotypes
    out = {}
    for label, spec in MUTATIONS.items():
        out[label] = triage_structures(spec["wt"], spec["mut"], spec["target"], label,
                                       spec.get("note"), data=data)
    with open(path, "w") as f:
        json.dump(out, f)
    return out


def list_mutations():
    return list(MUTATIONS)


def mutations_for_cancer(cancer_type):
    return CANCER_TYPES.get(cancer_type.lower(), [])


def _components(label):
    """The single-variant labels a MUTATIONS key is made of.
    'EGFR L858R+T790M' -> {'EGFR L858R', 'EGFR T790M'}; 'EGFR L858R' -> {'EGFR L858R'}.
    Returns an empty set for keys that describe a STRUCTURAL condition rather than a tumor
    genotype (e.g. 'KRAS G12C (drug-bound pocket)'), so those never match a raw tumor profile."""
    if "(" in label:
        return set()
    gene, changes = label.split(None, 1)
    return {f"{gene} {c}" for c in changes.split("+")}


def match_genotype(present_variants):
    """Map a real tumor's variants onto the in-scope MUTATIONS keys it satisfies.

    `present_variants` is an iterable of single-variant labels like {'EGFR L858R', 'EGFR T790M'}.
    Returns the matching keys, compound genotypes first (a compound like 'EGFR L858R+T790M' matches
    only when ALL its component variants are present in the tumor). This is what lets a raw somatic
    profile that happens to carry both L858R and T790M be recognized as the resistant double mutant.
    """
    present = set(present_variants)
    matched = [k for k in MUTATIONS if _components(k) and _components(k) <= present]
    # most-specific first: the double mutant leads its component singletons
    matched.sort(key=lambda k: len(_components(k)), reverse=True)
    return matched


# ---- CLI: human-readable triage (lets us SEE the tool's core output) ----
BUCKET_ORDER = ["weakened", "robust", "improved", "non-binder"]
BUCKET_LABEL = {
    "weakened": "WEAKENED — avoid (loses binding on this mutation)",
    "robust": "ROBUST — safe bets (binding holds on this mutation)",
    "improved": "IMPROVED — binds better on this mutation",
    "non-binder": "NON-BINDERS / unreliable",
}


def _print(mutation):
    out = triage(mutation)
    print(f"\nTUMOR MUTATION: {out['mutation']}  (target {out['target']})")
    if out["note"]:
        print(f"  note: {out['note']}")
    print(f"  {'drug':13}{'cat':16}{'WT':>7}{'mut':>7}{'delta':>7}{'95% CI':>16}  conf")
    for b in BUCKET_ORDER:
        group = [r for r in out["drugs"] if r["bucket"] == b]
        if not group:
            continue
        print(f"\n  [{BUCKET_LABEL[b]}]")
        for r in group:
            ci = f"[{r['ci95'][0]:+.2f},{r['ci95'][1]:+.2f}]"
            print(f"  {r['drug']:13}{r['category'][:15]:16}{r['affinity_wt']:>7.2f}"
                  f"{r['affinity_mut']:>7.2f}{r['delta']:>+7.2f}{ci:>16}  {r['confidence']}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _print(sys.argv[1])
    else:
        print("Known mutations:", list_mutations())
        print("Cancer types:", dict(CANCER_TYPES))
        for mut in ["EGFR L858R+T790M", "KRAS G12C"]:
            _print(mut)
