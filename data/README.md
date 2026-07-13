# Data

## drugs.csv
Curated drug pool (27 compounds) for docking against the locked EGFR/KRAS structures in [`../docs/scope.md`](../docs/scope.md). SMILES pulled live from PubChem (PUG REST API, by drug name → CID), then canonicalized with RDKit — no hand-typed or memorized SMILES.

Columns:
- `category` — `known_answer` (5, the validation-panel drugs), `egfr_family`/`kras_family` (6, other approved TKIs against the same targets), `multi_kinase` (6, approved oncology drugs for other cancers — negative-control cross-reactivity check, kept at full size deliberately, see note below), `repurposing_candidate` (10, non-oncology drugs with a published binding rationale — the "long shot" bucket)
- `evidence_level` — honest flag on how strong the rationale is, from `clinical (landmark)` down to `speculative`
- `smiles_canonical_rdkit` — use this for docking input
- `smiles_pubchem_raw` — PubChem's own canonical form, kept for cross-check

**Negative controls (`multi_kinase`) are kept at full size (6), not trimmed.** An initial pass cut this bucket to make room for more long-shot candidates, but a hackathon scored partly on scientific rigor needs a real negative-control group to show the tool discriminates rather than just saying yes to everything — cutting it to fund more speculative entries was the wrong trade. If compute becomes tight later, trim the `repurposing_candidate` bucket instead, not this one.

**The `repurposing_candidate` bucket is deliberately the largest non-anchor category.** 7 of its 10 entries (aspirin, itraconazole, cimetidine, doxycycline, propranolol, thalidomide, verapamil) are hypotheses RepoRx itself proposed via literature/pharmacovigilance screening but never rigorously tested — they docked against unmutated KRAS or ERK2 (out of our scope) with a single raw confidence score, no rescoring, no WT-vs-mutant comparison, no uncertainty quantification. Re-running these through our matched WT/mutant structures + rescoring + bootstrap is a genuine, previously-undone test — a real finding either way (confirms a lead, or correctly debunks a speculative claim with actual rigor behind the "no").

Regenerate via the script that produced this file if the pool changes (PubChem lookup + RDKit canonicalization).

### Expanded approved-drug library (`approved_library`)
Beyond the curated 27, `data/drugs.csv` can carry a broad repurposing library of FDA/EMA-approved
small molecules, tagged `category = approved_library`. These are pulled from **ChEMBL** (`max_phase = 4`,
`molecule_type = Small molecule`), desalted to the parent fragment, RDKit-canonicalized, and deduped by
InChIKey against the curated set — same "no hand-typed SMILES" discipline as the original panel. They are
kept deliberately distinct from the 10 curated `repurposing_candidate` entries (which each have a
published, target-specific rationale); a library row's rationale is honestly just "approved; unbiased
screen". `smiles_canonical_rdkit` is the docking input; `smiles_pubchem_raw` holds the ChEMBL source SMILES
for library rows.

Build/refresh it with:
```
python src/build_drug_panel.py --target 300     # append ~300 approved drugs (curated 27 untouched)
python cluster/build_sweep_csv.py               # rebuild the DiffDock input from the expanded panel
```
Library drugs contribute **no** scores until they are actually docked, so adding them does not change any
cached result; they become triage-able only after an overnight sweep appends their rows to
`gnina_scores_replicates.csv`. Docking cost scales with drugs × structures × replicates — see
`cluster/README.md` for a feasible staged plan (coarse 1-replicate screen first, then replicate the hits).

## gene_kb.json + drug_targets.json — the orthogonal evidence axes
Two knowledge bases that power the pathway-grounding + DepMap-dependency axes shown beside every drug
(computed in [`../src/evidence.py`](../src/evidence.py), attached to every triage result):

- **`drug_targets.json`** — each panel drug → its canonical human molecular target gene(s) and drug
  class (from DrugBank / ChEMBL mechanism of action). These are the drug's *established* targets, not
  the docked protein: the axes ask whether a drug's real biology has any business at the driver.
- **`gene_kb.json`** — each target gene → its signaling pathway / enzyme class (KEGG + UniProt) and its
  DepMap CRISPR dependency in lung adenocarcinoma. **The DepMap slice is cached and curated** — a
  directional lineage-level dependency call grounded in the public DepMap gene-effect distributions
  (depmap.org), not a live per-cell-line query; it is labeled as such in the UI and in the file's
  `_provenance`. The axis is orthogonal to docking on purpose: a drug can dock well yet hit a protein
  the cancer does not depend on.

Reproduce the read for any genotype with `python analysis/evidence_axes.py "EGFR L858R+T790M"`
(output cached in `../analysis/results/evidence_axes.txt`).
