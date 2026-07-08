# Scope — targets, mutations, and locked PDB structures

*Locked Tue Jul 7 (Day 0). Structures selected via Claude Science survey of the RCSB PDB, with genotype verified from each entry's deposited sequence (SIFTS alignment at the oncogenic hotspots) — not from entry titles, which are frequently wrong or silent about the mutation.*

Source survey: `claude-science/01 step/egfr_kras_structural_survey.md` (+ `egfr_kinase_structures.csv`, `kras_structures.csv`).

---

## 1. Targets and mutation states in scope

| Target | Gene / UniProt | States |
|---|---|---|
| EGFR (lung cancer) | EGFR / P00533, kinase domain only | wild-type, L858R, T790M (single), **L858R+T790M (double)** |
| KRAS (lung + colorectal) | KRAS / P01116 | wild-type, G12C |

Out of scope (narrative only, do not build): other EGFR/KRAS variants (e.g. KRAS G12D → pancreatic), BRAF, mutation panels beyond the above, AlphaFold-predicted mutants.

---

## 2. Locked structures

### EGFR — matched comparison set
All X-ray, single-chain, 1.5–1.8 Å, each with an inhibitor occupying the ATP pocket (so the active-site conformation is comparably constrained across states). This controls the WT-vs-mutant delta on **method and resolution**, so the measured difference reflects the mutation, not a data-quality gap.

| State | PDB | Res (Å) | Notes |
|---|---|---|---|
| Wild-type | **3POZ** | 1.50 | reversible inhibitor (TAK-285) in ATP pocket |
| L858R (sensitizing driver) | **8A2B** | 1.69 | reversible inhibitor |
| T790M single (resistance) | **4I24** | 1.80 | dacomitinib bound; **2 chains in ASU — extract one protomer before superposition** |
| L858R+T790M double (resistant tumor) | **5UGC** | 1.58 | covalent aminopurine inhibitor |

**Decision — resistance beat uses the L858R+T790M DOUBLE mutant (5UGC).** Clinically, T790M resistance almost always arises *on top of* L858R, so the double is the honest representation of a resistant tumor. T790M-single (4I24) is retained as a secondary/bonus structure.

Higher-resolution alternates on record if needed: 8A27 (WT, 1.07), 8A2D (L858R, 1.11), 5UG9 (double, 1.33) — but T790M caps the achievable match at ~1.8 Å, so the matched set above is preferred for the primary comparison.

### KRAS — clean shape pair + drug-bound pair
Two uses, two structure sets:

| Purpose | State | PDB | Res (Å) | Notes |
|---|---|---|---|---|
| Clean shape comparison | Wild-type | **8FMI** | 1.12 | GDP·Mg apo, single-chain |
| Clean shape comparison | G12C | **4LDJ** | 1.15 | GDP·Mg apo, single-chain |
| Drug-bound (the "flip" demo) | G12C + sotorasib | **6OIM** | 1.65 | sotorasib (AMG 510) covalent at Cys12 |
| Drug-bound (optional) | G12C + adagrasib | **6USZ** | 2.03 | adagrasib (MRTX849) covalent at Cys12 |

**Decision — use BOTH:** 8FMI + 4LDJ (apo, within 0.03 Å) for the least-confounded structural delta; 6OIM to define/validate the switch-II pocket and show how sotorasib engages the mutant.

Genotype-verification caught traps: apparent top WT hits 8ONV and 8B00 are actually G13D mutants (not WT) and were correctly excluded; 9IAY confirmed genuinely WT.

---

## 3. Known risk — covalent binders (affects the docking approach, Block E / Wed)

Several headline drugs bind **covalently** (form a permanent chemical bond), which vanilla non-covalent docking (DiffDock, default Vina/gnina) does not natively model:

| Drug | Binding | Demo beat | Robustness with normal docking |
|---|---|---|---|
| Erlotinib, gefitinib | reversible | fail on T790M | ✅ Safe — resistance is largely steric bulk + ATP-affinity, which docking can capture |
| Osimertinib | covalent (Cys797, conserved) | holds on T790M | 🟡 Medium |
| Sotorasib, adagrasib | covalent (Cys12, mutation-created) | flip on KRAS G12C | ⚠️ Risky — the entire G12C selectivity is the covalent weld; non-covalent docking may not reproduce it |

**Implications:**
- **Lead the demo on the EGFR T790M resistance beat** — most bulletproof.
- **KRAS flip is the ambitious beat** — may require a covalent-docking mode (gnina/smina support this) rather than assuming vanilla DiffDock shows it. Validate early Wednesday; don't discover it failing late.

---

## 4. Structure-prep requirements (identical across all states — the friend's spot-check job)

- Extract single protomer where ASU has multiple chains (4I24 has 2).
- Strip co-crystallized ligands before docking.
- Identical protonation across WT and mutant.
- Align all states to a common frame; define **one shared pocket box** used identically for WT and mutant.
- Watch conformational state: different bound inhibitors can stabilize different active/inactive (αC-helix, DFG) conformations — verify the compared states are in the same conformation, or the delta partly measures conformation, not mutation.

---

## 5. Open items
- [x] Source clinical-resistance citations for the three known-answer facts — done, see `known_answers.md` (Claude Science `02/`).
- [ ] Confirm covalent-docking plan for KRAS G12C (Block E).
- [ ] PhD-friend spot-check of structure-prep + conformational-state matching.
