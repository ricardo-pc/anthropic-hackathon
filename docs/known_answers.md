# Known-answer validation panel — the three facts + their sources

*The tool must reproduce these three established oncology facts, blind, before it touches real data. Each is sourced to its landmark primary literature (via Claude Science, `claude-science/02/oncology_facts_citations.md`). This turns the validation panel from "we assert it" into "here is the paper."*

---

## Fact 1 — Erlotinib & gefitinib FAIL on EGFR T790M
First-generation reversible EGFR inhibitors lose efficacy against the T790M "gatekeeper" resistance mutation in NSCLC — on-target resistance, not a bypass pathway.

- **Kobayashi et al., NEJM 2005** — first identified T790M in a gefitinib-relapsed patient; cell confirmation that T790M restores kinase activity under drug. PMID 15728811 · doi:10.1056/NEJMoa044238
- **Pao et al., PLoS Med 2005** — independently found T790M in erlotinib/gefitinib-resistant lung adenocarcinomas. PMID 15737014 · doi:10.1371/journal.pmed.0020073

## Fact 2 — Osimertinib HOLDS on T790M
Third-gen osimertinib (AZD9291) was engineered to retain potency against T790M — irreversible, mutant-selective, covalent at Cys797, spares wild-type.

- **Cross et al., Cancer Discovery 2014** — preclinical characterization; potent on T790M lines/xenografts while sparing WT. PMID 24893891 · doi:10.1158/2159-8290.CD-14-0337
- **Jänne et al., NEJM 2015 (AURA)** — first-in-human; high durable responses concentrated in T790M-positive resistant NSCLC. PMID 25923549 · doi:10.1056/NEJMoa1411817

## Fact 3 — Sotorasib & adagrasib EXPLOIT KRAS G12C (covalent at Cys12)
The therapeutic strategy rests on the mutant cysteine itself; the switch-II pocket only exists in the inactive GDP-bound state.

- **Ostrem et al., Nature 2013** — original proof-of-concept: covalent bond to Cys12; co-crystals defined the switch-II pocket. PMID 24256730 · doi:10.1038/nature12796
- **Canon et al., Nature 2019** — AMG 510 (sotorasib), covalent Cys12 inhibitor, structural + in vivo. PMID 31666701 · doi:10.1038/s41586-019-1694-1
- **Hallin et al., Cancer Discovery 2020** — MRTX849 (adagrasib), selective covalent Cys12. PMID 31658955 · doi:10.1158/2159-8290.CD-19-1167
- **Fell et al., J Med Chem 2020** — adagrasib discovery + crystallographic covalent Cys12 binding mode. PMID 32250617 · doi:10.1021/acs.jmedchem.9b02052

---

## Two things these sources reinforce for our build

1. **Osimertinib's design is WT-sparing, mutant-selective** (Cross 2014). Our demo verdict for osimertinib should read as "holds up on the mutant" — consistent with the paper, not overclaimed.
2. **The G12C pocket (switch-II) only exists in the GDP-bound/inactive state** (Ostrem 2013) — our chosen KRAS structures (8FMI/4LDJ/6OIM) are GDP-bound, so this is correct. But it re-underscores the [covalent-docking risk](scope.md#3-known-risk--covalent-binders): the whole G12C effect is a covalent weld onto Cys12, which non-covalent docking may not reproduce.

## Honest-novelty note
All eight are pre-existing landmark papers (NEJM, Nature, Cancer Discovery). The science is not new — pharma established it by hand. Our contribution is tooling + uncertainty quantification that generalizes it. Reproducing these blind is a *validation* of our tool, not a scientific claim of discovery.
