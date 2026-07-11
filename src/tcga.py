#!/usr/bin/env python3
"""
TCGA bring-your-own-tumor loader (Level 2 — "point it at a real tumor").

Loads a de-identified slice of somatic mutation calls from real TCGA Lung Adenocarcinoma tumors
(cBioPortal, PanCancer Atlas 2018), maps each tumor's mutations onto the in-scope targets the
docking panel actually covers, and hands the match to the triage engine. This is the demo's
Act 2: the same tool that reproduces known EGFR biology, now run on an unseen real patient tumor.

A small cache (data/tcga_luad_cache.json) is COMMITTED so the demo runs fully offline. The cache
is rebuilt live from the public cBioPortal REST API with `python src/tcga.py --refresh`.

COMPLIANCE (non-negotiable, see docs/scope.md): open-access, de-identified somatic calls ONLY.
TCGA sample barcodes carry no patient identity; we store only gene / protein change / mutation
type / locus per variant — never controlled-access data, never anything patient-level.

CLI:
  python src/tcga.py                     # list the cached real tumors
  python src/tcga.py TCGA-L9-A50W-01     # map + triage one real tumor
  python src/tcga.py --refresh           # re-pull the cache from cBioPortal
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import triage  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = f"{HERE}/data/tcga_luad_cache.json"

# --- cBioPortal open-access source (TCGA Lung Adenocarcinoma, PanCancer Atlas) ---
API = "https://www.cbioportal.org/api"
STUDY_ID = "luad_tcga_pan_can_atlas_2018"
PROFILE_ID = f"{STUDY_ID}_mutations"

# Real de-identified samples cached for the offline demo. All map onto structures the panel has
# already docked, so adding more costs nothing — it just makes the tool feel populated and real:
#   - treatment-naive EGFR L858R tumors         -> "the real tumor" (drugs that should work)
#   - real L858R+T790M double-mutant tumors     -> the acquired-resistance payoff (5UGC showcase)
#   - KRAS G12C tumors                          -> the second in-scope target (+ covalent caveat)
DEMO_SAMPLES = [
    "TCGA-17-Z047-01", "TCGA-49-4490-01", "TCGA-50-5944-01", "TCGA-55-8096-01",  # EGFR L858R
    "TCGA-L9-A50W-01", "TCGA-49-4494-01",                                          # EGFR L858R+T790M
    "TCGA-05-4244-01", "TCGA-05-4249-01", "TCGA-05-4250-01",                       # KRAS G12C
]


# ---------------------------------------------------------------------------
# live fetch (only used by --refresh; the committed cache makes the demo offline)
# ---------------------------------------------------------------------------
def _fetch_sample(sample_id):
    """Pull one sample's full somatic mutation list from the public cBioPortal API."""
    url = f"{API}/molecular-profiles/{PROFILE_ID}/mutations/fetch?projection=DETAILED"
    body = json.dumps({"sampleIds": [sample_id]}).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        records = json.load(r)
    if not isinstance(records, list):
        raise RuntimeError(f"cBioPortal error for {sample_id}: {str(records)[:200]}")
    muts = [
        dict(
            gene=m["gene"]["hugoGeneSymbol"],
            protein_change=m.get("proteinChange", "?"),
            mutation_type=m.get("mutationType"),
            chromosome=m.get("chr"),
            position=m.get("startPosition"),
        )
        for m in records
    ]
    muts.sort(key=lambda x: (x["gene"], x["protein_change"]))
    return muts


def refresh(sample_ids=DEMO_SAMPLES, path=CACHE):
    """Re-pull the demo samples from cBioPortal and (re)write the offline cache."""
    samples = {}
    for sid in sample_ids:
        muts = _fetch_sample(sid)
        in_scope = sorted({f"{m['gene']} {m['protein_change']}" for m in muts} & _known_variants())
        samples[sid] = dict(
            descriptor=f"{len(muts)} somatic mutations; in-scope: {', '.join(in_scope) or 'none'}",
            n_mutations=len(muts),
            mutations=muts,
        )
    blob = dict(
        source="cBioPortal public API — TCGA Lung Adenocarcinoma (PanCancer Atlas 2018)",
        study_id=STUDY_ID,
        molecular_profile_id=PROFILE_ID,
        url="https://www.cbioportal.org/",
        access="open-access, de-identified somatic mutation calls (no controlled-access, no patient data)",
        samples=samples,
    )
    with open(path, "w") as f:
        json.dump(blob, f, indent=2)
    return blob


def _known_variants():
    """Every single-variant label that appears in an in-scope genotype (for the in-scope summary)."""
    variants = set()
    for label in triage.list_mutations():
        variants |= triage._components(label)
    return variants


# ---------------------------------------------------------------------------
# offline path (default): read cache, map onto in-scope genotypes, triage
# ---------------------------------------------------------------------------
def _load_cache(path=CACHE):
    if not os.path.exists(path):
        raise FileNotFoundError(f"no TCGA cache at {path}; run `python src/tcga.py --refresh` first")
    with open(path) as f:
        return json.load(f)


def list_samples():
    """The cached real tumors, each with a one-line descriptor."""
    blob = _load_cache()
    return [dict(sample_id=sid, **{k: s[k] for k in ("descriptor", "n_mutations")})
            for sid, s in blob["samples"].items()]


def load_sample(sample_id):
    """The cached de-identified mutation record for one real tumor (raises KeyError if not cached)."""
    blob = _load_cache()
    if sample_id not in blob["samples"]:
        raise KeyError(f"{sample_id!r} not cached; known: {list(blob['samples'])}")
    return dict(sample_id=sample_id, source=blob["source"], study_id=blob["study_id"],
                **blob["samples"][sample_id])


def map_to_targets(mutations):
    """Map a raw somatic mutation list onto the in-scope genotypes the panel covers.

    Returns the matched MUTATIONS keys (compound genotypes first), the in-scope single variants
    actually present, and how much of the tumor we can't act on (honesty: most passengers don't map).
    """
    present = {f"{m['gene']} {m['protein_change']}" for m in mutations}
    matched = triage.match_genotype(present)
    in_scope_present = sorted(present & _known_variants())
    return dict(matched_genotypes=matched, in_scope_variants=in_scope_present,
                n_mutations=len(mutations), n_mapped_variants=len(in_scope_present))


def triage_sample(sample_id):
    """Load a real tumor, map it onto in-scope targets, and triage its primary genotype.

    The 'primary' genotype is the most specific match — a real tumor carrying BOTH L858R and T790M
    is triaged as the resistant double mutant (its component singletons are also listed, and can be
    drilled into with the existing triage_tumor tool). Returns everything the interpreter needs to
    give a grounded, honest, plain-English read on a genuine patient tumor.
    """
    sample = load_sample(sample_id)
    mapping = map_to_targets(sample["mutations"])
    matched = mapping["matched_genotypes"]

    result = dict(
        sample_id=sample_id,
        source=sample["source"],
        study_id=sample["study_id"],
        n_mutations=sample["n_mutations"],
        in_scope_variants=mapping["in_scope_variants"],
        matched_genotypes=matched,
        disclaimer="Real de-identified TCGA tumor. Docking affinity is a proxy, not clinical "
                   "efficacy; this is pre-wet-lab triage, not treatment advice.",
    )
    if not matched:
        result["primary_genotype"] = None
        result["note"] = ("This tumor carries no mutation the panel covers — nothing to triage. "
                          "In scope: EGFR L858R / T790M (and their double) and KRAS G12C.")
        result["triage"] = None
        return result

    primary = matched[0]  # match_genotype already sorts most-specific (compound) first
    result["primary_genotype"] = primary
    result["also_applicable"] = matched[1:]
    result["triage"] = triage.triage(primary)
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _print_sample(sample_id):
    out = triage_sample(sample_id)
    print(f"\nREAL TUMOR: {out['sample_id']}   ({out['source']})")
    print(f"  {out['n_mutations']} somatic mutations; in-scope variants: "
          f"{', '.join(out['in_scope_variants']) or 'none'}")
    if not out["matched_genotypes"]:
        print(f"  {out['note']}")
        return
    print(f"  matched in-scope genotype(s): {', '.join(out['matched_genotypes'])}")
    print(f"  -> triaging PRIMARY genotype: {out['primary_genotype']}")
    triage._print(out["primary_genotype"])


def main():
    args = sys.argv[1:]
    if args and args[0] == "--refresh":
        print(f"Refreshing TCGA cache from cBioPortal ({', '.join(DEMO_SAMPLES)}) ...")
        blob = refresh()
        for sid, s in blob["samples"].items():
            print(f"  {sid}: {s['descriptor']}")
        print(f"Wrote {CACHE}")
        return
    if args:
        _print_sample(args[0])
        return
    print("Cached real TCGA-LUAD tumors (pass a sample id to triage it):")
    for s in list_samples():
        print(f"  {s['sample_id']:18} {s['descriptor']}")


if __name__ == "__main__":
    main()
