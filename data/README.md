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
