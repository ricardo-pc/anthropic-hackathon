#!/usr/bin/env python3
"""
Expand the docking panel from the curated 27 to a few-hundred approved-drug repurposing library.

The curated 27 (data/drugs.csv) each carry a hand-written target rationale. This script keeps all of
them untouched and APPENDS a broad library of FDA/EMA-approved small molecules pulled from ChEMBL
(max_phase = 4), so an overnight sweep can screen hundreds of approved drugs for a mutant-selective
hit instead of 27. The bigger the honest repurposing net, the better the "more shots on goal" story.

Every structure is validated the same way the original panel was — real SMILES from a public source,
desalted to the parent, RDKit-canonicalized, deduped by InChIKey — never hand-typed. Library rows are
tagged category `approved_library` (distinct from the 10 curated `repurposing_candidate` entries that
have published, target-specific rationales) so the two are never conflated.

Names are sanitized to [a-z0-9-] with no spaces and no '__' — the docking sweep builds and later parses
folders named '<drug>__<pdb>' (cluster/build_sweep_csv.py, replicate_and_rescore.py), so a stray space
or double underscore would corrupt the run.

Usage:
    python src/build_drug_panel.py                 # add up to 300 approved drugs to data/drugs.csv
    python src/build_drug_panel.py --target 150    # a smaller library
    python src/build_drug_panel.py --dry-run       # print what would be added; write nothing

After it runs, regenerate the sweep input and dock on your GPU (see docs/bring_your_own_tumor.md):
    python cluster/build_sweep_csv.py    # rebuilds full_sweep_input.csv from the expanded drugs.csv
"""
import argparse
import csv
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")  # quiet RDKit's per-molecule parse warnings

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRUGS = f"{HERE}/data/drugs.csv"
CHEMBL = "https://www.ebi.ac.uk/chembl/api/data/molecule.json"
FIELDS = ["name", "category", "target_rationale", "evidence_level", "pubchem_cid",
          "molecular_formula", "molecular_weight", "smiles_canonical_rdkit", "smiles_pubchem_raw"]

# Drug-likeness gate for the library rows (the curated 27 are exempt — kept as-is).
MW_MIN, MW_MAX = 150.0, 700.0


def _sanitize(name):
    """ChEMBL 'FOLIC ACID' -> 'folic-acid'; strip anything not [a-z0-9-]; collapse and trim hyphens.
    Guarantees no spaces and no '__' so the '<drug>__<pdb>' folder scheme stays parseable."""
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def _parent(smiles):
    """Parse SMILES, keep the largest organic fragment (desalt), return (mol, canonical_smiles).
    Returns (None, None) if it doesn't parse or isn't a reasonable small organic molecule."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None, None
    frags = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
    if not frags:
        return None, None
    mol = max(frags, key=lambda m: m.GetNumHeavyAtoms())  # parent = biggest fragment
    if not any(a.GetSymbol() == "C" for a in mol.GetAtoms()):
        return None, None                                 # must be organic
    return mol, Chem.MolToSmiles(mol)


def _load_existing():
    """Return (rows, header, seen_names, seen_inchikeys) for the current drugs.csv."""
    with open(DRUGS) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames
    names, keys = set(), set()
    for r in rows:
        names.add(r["name"].strip().lower())
        smi = r.get("smiles_canonical_rdkit") or ""
        mol, _ = _parent(smi)
        if mol is not None:
            keys.add(Chem.MolToInchiKey(mol))
    return rows, header, names, keys


def _fetch_page(offset, limit=1000):
    q = urllib.parse.urlencode({
        "max_phase": 4, "molecule_type": "Small molecule",
        "limit": limit, "offset": offset,
    })
    req = urllib.request.Request(f"{CHEMBL}?{q}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        import json
        return json.load(r)


def build(target, dry_run=False):
    rows, header, seen_names, seen_keys = _load_existing()
    if header != FIELDS:
        print(f"WARNING: drugs.csv header differs from expected; using the file's own header.\n"
              f"  file:     {header}\n  expected: {FIELDS}", file=sys.stderr)
    n_start = len(rows)
    added, offset = [], 0
    print(f"Curated panel: {n_start} drugs. Fetching approved small molecules from ChEMBL "
          f"(target +{target})…")

    while len(added) < target:
        page = _fetch_page(offset)
        mols = page.get("molecules", [])
        if not mols:
            break
        for m in mols:
            if len(added) >= target:
                break
            pref = (m.get("pref_name") or "").strip()
            struct = m.get("molecule_structures") or {}
            raw_smiles = (struct.get("canonical_smiles") or "").strip()
            if not pref or not raw_smiles:
                continue
            name = _sanitize(pref)
            if not name or name in seen_names:
                continue
            mol, canon = _parent(raw_smiles)
            if mol is None:
                continue
            mw = Descriptors.MolWt(mol)
            if not (MW_MIN <= mw <= MW_MAX):
                continue
            key = Chem.MolToInchiKey(mol)
            if key in seen_keys:                     # same molecule as a curated drug or an earlier row
                continue
            seen_names.add(name)
            seen_keys.add(key)
            added.append({
                "name": name,
                "category": "approved_library",
                "target_rationale": "FDA/EMA-approved small molecule (ChEMBL max_phase=4); "
                                    "unbiased repurposing-library screen, no target-specific rationale",
                "evidence_level": "approved (library screen)",
                "pubchem_cid": "",
                "molecular_formula": rdMolDescriptors.CalcMolFormula(mol),
                "molecular_weight": round(mw, 1),
                "smiles_canonical_rdkit": canon,     # docking input
                "smiles_pubchem_raw": raw_smiles,    # source (ChEMBL) SMILES, kept for cross-check
            })
        offset += len(mols)
        print(f"  scanned {offset} ChEMBL records -> {len(added)} new library drugs so far", flush=True)
        time.sleep(0.3)                              # be polite to the public API
        if page.get("page_meta", {}).get("next") is None:
            break

    added.sort(key=lambda r: r["name"])
    print(f"\nSelected {len(added)} new approved drugs (deduped, desalted, MW {MW_MIN:.0f}-{MW_MAX:.0f}).")
    print("  examples:", ", ".join(r["name"] for r in added[:12]) + (" …" if len(added) > 12 else ""))

    if dry_run:
        print("\n--dry-run: drugs.csv not modified.")
        return

    with open(DRUGS, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows + added)
    print(f"\nWrote {DRUGS}: {n_start} curated + {len(added)} library = {n_start + len(added)} drugs.")
    print("Next: python cluster/build_sweep_csv.py  (rebuild the DiffDock input), then dock on your GPU.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", type=int, default=300, help="how many approved drugs to add (default 300)")
    ap.add_argument("--dry-run", action="store_true", help="print the selection; write nothing")
    args = ap.parse_args()
    build(args.target, args.dry_run)


if __name__ == "__main__":
    main()
