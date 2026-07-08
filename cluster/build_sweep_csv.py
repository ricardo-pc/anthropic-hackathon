#!/usr/bin/env python3
"""
Build the single batch-input CSV for DiffDock's --protein_ligand_csv mode:
every drug in data/drugs.csv x every prepared receptor, as one row each.

Run ON gandalf/roo (just needs the csv module, no GPU/conda env required).
Columns DiffDock expects: complex_name, protein_path, ligand_description,
protein_sequence (left empty -- we always supply protein_path, never fold
from sequence).
"""
import csv
import os

HOME = os.path.expanduser("~")
DRUGS_CSV = f"{HOME}/hackathon/data/drugs.csv"
RECEPTOR_DIR = f"{HOME}/hackathon/data/structures/prepared"
OUT_CSV = f"{HOME}/hackathon/data/full_sweep_input.csv"


def main():
    with open(DRUGS_CSV) as f:
        drugs = list(csv.DictReader(f))

    receptors = sorted(fn for fn in os.listdir(RECEPTOR_DIR) if fn.endswith("_receptor.pdb"))

    rows = []
    for drug in drugs:
        name = drug["name"]
        smiles = drug["smiles_canonical_rdkit"]
        for receptor_fn in receptors:
            pdb = receptor_fn.replace("_receptor.pdb", "")
            rows.append({
                "complex_name": f"{name}__{pdb}",
                "protein_path": f"{RECEPTOR_DIR}/{receptor_fn}",
                "ligand_description": smiles,
                "protein_sequence": "",
            })

    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["complex_name", "protein_path", "ligand_description", "protein_sequence"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows ({len(drugs)} drugs x {len(receptors)} receptors) to {OUT_CSV}")


if __name__ == "__main__":
    main()
