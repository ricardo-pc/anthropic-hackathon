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

Implemented in `src/structure_prep.py`, verified by `src/verify_prep.py`. Prepared receptors in `data/structures/prepared/`, pocket boxes in `data/structures/pockets.json`. See `data/structures/README.md`.

- [x] Extract single protomer where ASU has multiple chains (4I24 has 2) — done (chain A).
- [x] Strip co-crystallized ligands before docking — done. **Kept KRAS GDP+Mg** (cofactor defining the switch-II pocket); stripped inhibitors + waters + additives.
- [x] Align all states to a common frame; define **one shared pocket box** — done via **pocket-local** superposition (see conformational note below).
- [x] Verified each prepared receptor carries the correct hotspot residue (EGFR 790/858, KRAS 12) + cofactors — all pass.
- [~] Identical protonation: receptors are heavy-atom-only with a uniform baseline (pre-deposited H stripped); polar-H added consistently at dock time by the rescoring engine. Deferred deliberately — OpenBabel mangles residue/cofactor identity, pdb2pqr drops cofactors.
- [!] **Conformational state — confirmed real and handled.** EGFR global all-CA RMSD is 2.9–5.1 Å (inter-lobe hinge motion; different inhibitors freeze different αC/DFG states), but **pocket-local RMSD is 0.68–1.45 Å** — the pockets are comparable. Global alignment would have misplaced the box by up to ~5 Å. 5UGC (double) is the loosest pocket fit (1.45 Å) → prioritize in the friend spot-check.

---

## 5. Open items
- [x] Source clinical-resistance citations for the three known-answer facts — done, see `known_answers.md` (Claude Science `02/`).
- [ ] Confirm covalent-docking plan for KRAS G12C (Block E).
- [ ] PhD-friend spot-check of structure-prep + conformational-state matching.
- [ ] **Fix alignment landmark (§6.1) before the full sweep** — pending exact residue numbers from Claude Science follow-up.
- [ ] Watch sotorasib-vs-4LDJ score in Wed known-answer validation — built-in test of the KRAS induced-fit risk (§6.3).
- [ ] Thursday stats: compute the T790M four-corner decomposition (§6.2), not just the headline WT-vs-double delta.

---

## 6. Independent structure audit (Claude Science Specialist, Jul 8)

Full response: `claude-science/03/structure_audit_and_4_questions.md` + `structure_audit.csv`. Independently pulled all 7 structures via the PDB connector and read genotypes from deposited sequence (not titles) — a second, connector-verified check on top of §2's survey.

### 6.1 — Alignment circularity risk (fix before the full sweep)
The pocket-local fix (§4) is confirmed correct in principle, but a **radius-based** residue selection (CA within 12 Å of pocket center) risks including residue 790 — the T790M gatekeeper itself — in the set used to *align* the structures. That's circular: partly using the mutation to measure the mutation. **Fix:** align on a fixed landmark instead of a radius — hinge backbone (~790–797), catalytic HRD/DFG motifs, K745(β3)–E762(αC) salt bridge (kinase-biology invariants, unaffected by the mutations in scope). Treat position 790's sidechain as *measured*, never *fitting*. Exact residue numbers for these landmarks, verified against our specific PDB entries, are a pending Claude Science follow-up before `structure_prep.py` is updated and the receptors regenerated.

### 6.2 — T790M four-corner design (Thursday stats note, not a blocker)
5UGC (double mutant) remains the correct "resistant tumor" representation. Since all four EGFR states are already locked (WT/3POZ, L858R/8A2B, T790M-alone/4I24, double/5UGC), the stats layer should compute **both** (double − WT) *and* (double − L858R) *and* (T790M-alone − WT) — the latter two decompose how much of the resistant-tumor delta is T790M acting alone vs. T790M's effect on an already-L858R-active kinase. No new structures needed.

### 6.3 — KRAS switch-II is induced-fit, not pre-existing (watch, don't fix yet)
Measured switch-I/switch-II B-factors directly: switch-II is rigid/collapsed in both apo structures (8FMI, 4LDJ) and only opens in drug-bound 6OIM. **The G12C pocket doesn't pre-exist in apo 4LDJ — sotorasib itself props it open.** Risk: docking a new candidate into apo 4LDJ may score it artificially poorly even if it would work, since the pocket isn't there yet. **Built-in test, no extra work required:** Wed's known-answer validation already docks sotorasib against 4LDJ — if sotorasib itself scores poorly there, that confirms the risk is real and the pipeline should pivot to using 6OIM's conformation as the G12C docking template instead. Watch this result closely before trusting any other KRAS G12C number.

### 6.4 — Engineered mutations beyond the driver (mostly outside the pocket; §4's pocket-local approach already mitigates)
Every structure except 3POZ and 4LDJ carries an engineered mutation beyond the intended driver:
- **8A2B, 5UGC:** V948R (C-lobe dimer-interface crystallization aid, far from ATP pocket). Cancels in the L858R→double comparison (both carry it); WT(3POZ, no V948R)→mutant comparisons carry a small uncontrolled variable at position 948, likely inconsequential given distance from the cleft.
- **6OIM:** C51S+C80L+C118S ("cysteine-light" construct so sotorasib's covalent warhead reacts only at Cys12). None in the switch-II pocket.
- **8FMI ("WT"):** carries C118S — and **C118 is native** (NKCD guanine-binding motif, near GDP). The "WT" structure is actually the more-engineered one at a nucleotide-proximal position; 4LDJ (G12C) is the cleaner structure aside from the intended mutation. Flag if computing anything nucleotide-proximal.
- The one fully clean pair in the whole set: **3POZ (EGFR WT)** and **4LDJ (KRAS G12C)** — zero engineered mutations beyond intent.

None are wrong structure choices (standard crystallography practice) — but the WT-vs-mutant delta isn't measuring *only* the driver mutation unless these are accounted for. Pocket-local readout (§4) already protects against most of this since every extra mutation sits outside the pocket.
