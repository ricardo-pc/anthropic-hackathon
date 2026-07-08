# PDB structural survey: EGFR kinase domain and KRAS

*Genotypes in both surveys were verified directly from each entry's deposited sequence via its SIFTS alignment to the reference UniProt (residues read at the oncogenic hotspots), not from entry titles — titles almost never state the mutation, and several high-resolution entries carry confounding mutations at other positions.*

---

# 1. Human EGFR kinase-domain structures by mutational state

Searched RCSB PDB for all human EGFR (UniProt **P00533**) experimental structures, kept the intracellular tyrosine-kinase-domain entries, and verified each genotype from sequence by reading the residues that the SIFTS alignment maps to UniProt positions 790 and 858. That gave a clean split across 140 kinase structures: WT = 63, L858R-only = 9, T790M-only = 23, L858R+T790M double = 45. Both requested T790M forms exist, so all four states are reported below, top-3 by resolution each.

All top candidates are **X-ray**; cryo-EM EGFR structures exist but are full-length/ectodomain receptor assemblies at much lower resolution, none competitive for kinase-domain comparison.

## (a) Wild-type (Thr790 / Leu858)
| PDB | Method | Res (Å) | Depositing group / year | Inhibitor | Chains (ASU) |
|---|---|---|---|---|---|
| **8A27** | X-ray | **1.07** | Obst-Sander *et al.*, Genentech — *J Med Chem* 2022 | isoindolinone–pyrroloimidazole inhibitor (medchem series) | 1 |
| **8A2A** | X-ray | 1.43 | Obst-Sander *et al.*, Genentech — 2022 | same series analog | 1 |
| **3POZ** | X-ray | 1.50 | Aertgeerts *et al.*, Takeda — *J Biol Chem* 2011 | **TAK-285** (reversible) | 1 |

## (b) L858R single mutant (Thr790 / **Arg858**)
| PDB | Method | Res (Å) | Depositing group / year | Inhibitor | Chains (ASU) |
|---|---|---|---|---|---|
| **8A2D** | X-ray | **1.11** | Obst-Sander *et al.*, Genentech — 2022 | indazole-spiro inhibitor | 1 |
| **8A2B** | X-ray | 1.69 | Obst-Sander *et al.*, Genentech — 2022 | isoindolinone–pyrroloimidazole inhibitor | 1 |
| **2ITV** | X-ray | 2.47 | Yun & Boggon *et al.*, Yale — *Cancer Cell* 2007 | apo (AMP-PNP nucleotide only, no drug) | 1 |

## (c) T790M single mutant (**Met790** / Leu858)
| PDB | Method | Res (Å) | Depositing group / year | Inhibitor | Chains (ASU) |
|---|---|---|---|---|---|
| **4I24** | X-ray | **1.80** | Gajiwala *et al.*, Pfizer — *Structure* 2013 | **Dacomitinib** (PF-00299804, irreversible) | 2 |
| **7JXQ** | X-ray | 1.83 | To & Beyett *et al.*, Dana-Farber — *Nat Cancer* 2022 | AMP-PNP + **JBJ-04-125-02** allosteric inhibitor | 4 |
| **7JXP** | X-ray | 2.16 | Beyett & To *et al.*, Dana-Farber — *Nat Commun* 2022 | AMP-PNP + **osimertinib** + JBJ allosteric inhibitor | 6 |

## (c′) L858R + T790M double mutant (**Met790 / Arg858**)
| PDB | Method | Res (Å) | Depositing group / year | Inhibitor | Chains (ASU) |
|---|---|---|---|---|---|
| **5UG9** | X-ray | **1.33** | Planken *et al.*, Pfizer — *J Med Chem* 2017 | aminopurine covalent inhibitor | 1 |
| **5UG8** | X-ray | 1.46 | Planken *et al.*, Pfizer — 2017 | aminopurine covalent inhibitor (analog) | 1 |
| **5UGC** | X-ray | 1.58 | Planken *et al.*, Pfizer — 2017 | aminopurine covalent inhibitor (analog) | 1 |

![Best X-ray resolution per EGFR kinase-domain genotype]({{artifact:art_e21941fe-32a3-409f-b304-0681c03adcfb}})

## Recommended matched WT / L858R / T790M set

The absolute-best structures per state span a wide range (1.07–2.47 Å) and mix single-chain vs multi-chain ASUs with different bound-ligand classes — comparing 8A27 (1.07 Å) against 2ITV (2.47 Å) would confound genuine conformational differences with a ~1.4 Å data-quality gap. For a comparison controlled on **method and resolution**, use this combination, all single-chain X-ray within a 0.3 Å window:

| State | PDB | Res (Å) | Chains | Ligand context |
|---|---|---|---|---|
| WT | **3POZ** | 1.50 | 1 | reversible inhibitor (TAK-285), ATP pocket |
| L858R | **8A2B** | 1.69 | 1 | reversible inhibitor, ATP pocket |
| T790M | **4I24** | 1.80 | 1 chain of the biological pair (2 in ASU) | ATP-competitive inhibitor (dacomitinib) |
| L858R+T790M | **5UGC** | 1.58 | 1 | ATP-pocket inhibitor |

All four are X-ray, 1.5–1.8 Å, each with an inhibitor occupying the ATP cleft (so the active-site conformation is comparably constrained across the set). The only wrinkle: **4I24 has two chains in the ASU** (all others are single-chain) — extract one protomer before superposition. If you specifically need the *bare* T790M kinase at this quality it doesn't exist as a single-chain apo structure; 4I24 is the closest resolution match.

Two alternative framings depending on your goal:

- **Maximum resolution, accept a chain-count mismatch:** 8A27 (WT, 1.07) / 8A2D (L858R, 1.11) / 4I24 (T790M, 1.80) / 5UG9 (double, 1.33) — but the T790M state caps the achievable match at ~1.8 Å regardless.
- **Same lab / same crystal system:** the Genentech 2022 series (8A27 WT, 8A2D/8A2B L858R) is internally very consistent, but has no T790M member, so cross-state comparison still requires importing 4I24 or 5UGC from other groups.

**Verification note:** genotypes were assigned from the residue at UniProt positions 790/858 in each entry's deposited sequence via its SIFTS alignment, not from entry titles. One double-mutant entry (5U8L, not in the reported top-3) carries M790/R858 in sequence but a missing SIFTS mutation flag — a database annotation gap, not a genotype ambiguity.

**Files:** `egfr_kinase_structures.csv` — the 12 ranked candidates with method, resolution, depositing author, year, journal, inhibitor, and ASU chain count. `egfr_resolution_by_state.png` — resolution of every candidate by state, with the recommended 1.5–1.8 Å matching band.

---

# 2. Human KRAS structures: wild-type vs G12C

Searched RCSB PDB for all human KRAS (UniProt **P01116**) structures — 475 X-ray, 29 cryo-EM, 18 NMR — and verified genotype from sequence by reading the residue the SIFTS alignment maps to KRAS position 12, then screening the other oncogenic hotspots (13, 61, 117, 146) to reject look-alikes. This mattered: several of the highest-resolution "Gly12" entries (e.g. **8ONV, 8B00**, from the BI-2493/BI-2865 series) are actually **G13D** mutants that happen to keep Gly12, so they are *not* wild-type. The hotspot screen (positions 12/13/61/117/146) kept only genuinely canonical entries as WT — **9IAY (0.95 Å) is correctly wild-type** and stands as the #1 WT structure. The tables below use only entries where every hotspot is canonical (WT) or where position 12 is the sole change (G12C). All top candidates are **X-ray**; cryo-EM KRAS entries are lower-resolution complexes (SOS/RAF/membrane assemblies), none competitive here.

One thing to flag up front: **the sotorasib- and adagrasib-bound G12C structures are not the highest-resolution G12C entries.** The best G12C crystals are apo (GDP-only) or bound to newer/tool inhibitors at ~1.04 Å; the clinical-drug complexes sit at 1.65 Å (sotorasib) and 2.03 Å (adagrasib). Both are reported — top-3 by resolution and the two drug complexes.

## (a) Wild-type (Gly12, all hotspots canonical)
| PDB | Method | Res (Å) | Group / year | Ligand | Chains (ASU) |
|---|---|---|---|---|---|
| **9IAY** | X-ray | **0.95** | Bröker *et al.* — *J Med Chem* 2025 | GDP·Mg + aminobenzothiophene fragment (non-covalent tool cmpd) | 1 |
| **9IAW** | X-ray | 1.00 | Bröker *et al.* — *J Med Chem* 2025 | GDP·Mg + aminobenzothiophene fragment | 1 |
| **6P0Z** | X-ray | 1.01 | Dharmaiah *et al.*, NCI — *Sci Rep* 2019 | GDP·Mg only, N-acetylated KRAS(2-169) — **apo** | 2 |

*Also notable:* **8FMI** (1.12 Å, Brenner *et al.*, *Biochemistry* 2023) is a clean **apo** single-chain WT if you want no bound small molecule at all.

## (b) G12C (Cys12, only position 12 altered)
| PDB | Method | Res (Å) | Group / year | Ligand | Chains (ASU) |
|---|---|---|---|---|---|
| **8AZX** | X-ray | **1.04** | Kim *et al.*, Boehringer Ingelheim — *Nature* 2023 | GDP·Mg + **BI-2865** (non-covalent pan-KRAS) | 1 |
| **8TVK** | X-ray | 1.04 | Deck *et al.* — *bioRxiv* 2025 | GDP·Mg only — **apo** | 1 |
| **4LDJ** | X-ray | 1.15 | Hunter *et al.* — *PNAS* 2014 | GDP·Mg only — **apo** | 1 |

### G12C bound to the clinical covalent drugs flagged
| PDB | Method | Res (Å) | Group / year | Ligand | Chains |
|---|---|---|---|---|---|
| **6OIM** ★ | X-ray | 1.65 | Canon *et al.*, Amgen — *Nature* 2019 | GDP·Mg + **sotorasib (AMG 510)**, covalent at Cys12 | 1 |
| **6USZ** ★ | X-ray | 2.03 | Fell *et al.*, Mirati — *J Med Chem* 2020 | GDP·Mg + **adagrasib (MRTX849)**, covalent at Cys12 | 1 |

![KRAS WT vs G12C resolution]({{artifact:art_d7ac036f-7401-4653-abb9-6afb7a583ede}})

## Recommended matched WT / G12C pair

The choice depends on whether you need the drug bound:

**If you want maximum resolution and don't require sotorasib/adagrasib** — pair **6P0Z (WT, 1.01 Å)** with **4LDJ (G12C, 1.15 Å)**. Both are single-domain, **GDP·Mg apo** (no inhibitor in either), X-ray within 0.14 Å — so a WT-vs-G12C comparison reflects the mutation and nucleotide state, not a drug perturbation or a data-quality gap. (6P0Z has 2 chains in the ASU vs 1 for 4LDJ; extract one protomer.) For strictly single-chain apo on both sides, substitute **8FMI (WT, 1.12 Å)** for 6P0Z — then both are 1 chain, apo, and within 0.03 Å of each other, the cleanest match available.

**If the point is the drug-bound active site** — the resolution floor is set by the G12C·drug complex, so pair a WT structure to it rather than chasing sub-Å WT:

- **sotorasib:** WT **8FMI** (1.12 Å apo) vs G12C **6OIM** (1.65 Å + AMG 510). A 0.5 Å gap is unavoidable — no WT KRAS·sotorasib exists because the covalent warhead requires Cys12.
- **adagrasib:** WT vs G12C **6USZ** (2.03 Å); match with a ~2 Å WT if you want method/resolution parity, though the sub-1.1 Å WT structures superpose so well that the resolution mismatch has little practical effect on backbone comparison.

Default recommendation: **8FMI (WT) + 4LDJ (G12C)** — both apo, single-chain, X-ray, 1.12/1.15 Å — as the least-confounded structural comparison, with **6OIM** added when you specifically need to see how sotorasib engages the mutant.

**Verification note:** genotypes were assigned from the deposited sequence at KRAS positions 12/13/61/117/146 via each entry's SIFTS alignment, not from titles — which is why apparent top WT hits that are really G13D mutants (8ONV, 8B00) were correctly excluded, while 9IAY was confirmed genuinely wild-type.

**Files:** `kras_structures.csv` — 12 candidates (WT + G12C, incl. both drug complexes) with method, resolution, group, year, journal, ligand, and ASU chain count. `kras_resolution_by_state.png` — WT vs G12C resolution, with the 1.0–1.15 Å matching band and the sotorasib/adagrasib complexes marked (◆).
