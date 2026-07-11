# New genotypes to dock (overnight cluster run)

Each new genotype only needs its **mutant** structure docked against the 27-drug panel — the wild-type
references (`3POZ` for EGFR, `8FMI` for KRAS) are already docked and cached, so you reuse them. Model
each point mutant from its wild-type with `cluster/model_mutant.py`, then run the existing sweep +
replicate pipeline (`cluster/README.md`). Ordered by demo value.

## Priority list

| # | Genotype | Model from | Why it's worth a night on the GPU |
|---|----------|-----------|------------------------------------|
| 1 | **EGFR C797S** | `3POZ` | The *next* resistance frontier — the mutation that defeats **osimertinib** itself. Lets the tool answer "what when even the third-gen drug fails?" Tests whether the imatinib cross-kinase signal survives here. |
| 2 | **EGFR L858R+T790M+C797S** | `5UGC` | The full triple-mutant resistance cascade. Model C797S *onto* the existing double-mutant structure. The strongest "resistance keeps evolving" story. |
| 3 | **EGFR G719S** | `3POZ` | A second sensitizing mutation (exon 18). Tests whether imatinib/ponatinib gain binding here too — consistency is what turns the hit from noise into a real hypothesis. |
| 4 | **KRAS G12D** *(stretch)* | `8FMI` | The most common KRAS mutation (pancreatic/colorectal), and — unlike G12C — its lead drug (MRTX1133) is **non-covalent**, so docking is *more* meaningful here. Add MRTX1133 to `data/drugs.csv` first for a known-answer. |

## Run it (per genotype, on the cluster)

```bash
# 1. model the mutant structure from the wild-type (needs PyMOL in the docking env)
python cluster/model_mutant.py data/structures/prepared/3POZ_receptor.pdb C797S \
       data/structures/prepared/EGFR_C797S_receptor.pdb
# (triple mutant: model from 5UGC instead of 3POZ)

# 2. dock the 27-drug panel against the new mutant, N replicates, gnina --minimize rescore
#    — add the new pdb id to the sweep CSV and run the existing overnight pipeline
sbatch cluster/overnight.sbatch        # see cluster/README.md; harvest gnina_scores_replicates rows

# 3. append the new rows to data/gnina_scores_replicates.csv (rsync back), then locally:
python src/check_registry.py "EGFR C797S"     # confirms structure + scores are present -> READY
```

## Register each (after scores land)

Add to `config/mutations.json` — no code changes:

```json
"EGFR C797S": { "target": "EGFR", "wt": "3POZ", "mut": "EGFR_C797S",
                "note": "acquired resistance to osimertinib (3rd-gen); modeled structure." },
"EGFR L858R+T790M+C797S": { "target": "EGFR", "wt": "3POZ", "mut": "EGFR_TRIPLE",
                "note": "full resistance cascade; osimertinib-resistant." },
"EGFR G719S": { "target": "EGFR", "wt": "3POZ", "mut": "EGFR_G719S",
                "note": "exon-18 sensitizing mutation; modeled structure." }
```

Then add the labels to `"cancer_types"` (lung cancer), run `python src/build_dashboard.py`, and they
appear across the app, CLI, dashboard, and MCP tools. Modeled structures are labeled lower-confidence
automatically.

## Note on the imatinib hypothesis

Genotypes 1–3 are also the honest test of the demo's headline lead: **imatinib (a CML kinase
inhibitor) gains binding across EGFR mutants.** If it holds up on C797S and G719S too, the
cross-kinase signal is real and consistent — a genuinely testable repurposing hypothesis. If it
doesn't, the tool said so honestly. Either way it's a stronger story than a single-structure fluke.
