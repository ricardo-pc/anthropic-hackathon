› Full Claude Science Specialist (Onco Repurposing Reviewer) response to the 4 structure-prep sanity-check questions. Independent audit: pulled all 7 locked PDB structures fresh via the PDB connector, read genotypes from deposited sequence, measured switch-region B-factors directly.

Mirrored from vault: `claude-second-brain/anthropic-hackathon/claude-science/4 sanity check questions.md`.

---

## 1. Pocket-local alignment — right fix, but tighten the landmark

Global backbone RMSD of 2.9–5.1 Å across EGFR mutation states is the two-lobe kinase hinge breathing, not the mutation — confirmed correct to fix via pocket-local superposition (0.68–1.45 Å once restricted to CA within 12 Å of pocket).

**Risk identified:** a radius-based selection can include residue 790 (the T790M gatekeeper) in the alignment set itself — partly aligning on the thing being measured. **Fix:** align on a fixed landmark instead of a radius — hinge backbone (~790–797), catalytic HRD/DFG motifs, K745(β3)–E762(αC) salt bridge. These are invariant across the mutations in scope. Treat the gatekeeper sidechain as *measured*, never *fitting*. Report backbone CA and all-atom pocket RMSD separately (covalent inhibitors reshape sidechain rotamers even when backbone is rigid).

## 2. T790M single vs. double — double is clinically correct; four-corner design gets more for free

L858R+T790M (5UGC) is the right model of "the resistant patient" — T790M arises as a second acquired mutation on top of an activating driver, not standalone. But the double mutant alone cannot isolate what T790M *by itself* does — L858R already perturbs the kinase equilibrium.

We already have all four states locked (WT/3POZ, L858R/8A2B, T790M-alone/4I24, double/5UGC) — a thermodynamic-cycle design: (double − L858R) isolates T790M on the resistant background; (T790M-alone − WT) isolates it on the WT background; comparing the two reveals whether the mutations interact non-additively. No new structures needed — an analysis-design note for the stats layer.

## 3. KRAS switch-II — GDP·Mg correct; switch-II open/closed state is the real per-structure variable

GDP·Mg retention confirmed necessary (switch-II pocket only exists GDP-bound/inactive). Measured switch-I and switch-II B-factors directly:

| PDB | State | Ligand | Switch-I ⟨B⟩ | Switch-II ⟨B⟩ | Overall ⟨B⟩ | All switch residues modeled? |
|---|---|---|---|---|---|---|
| 8FMI | WT | apo | 14.3 | 7.1 | 8.4 | yes |
| 4LDJ | G12C | apo | 12.6 | 9.6 | 9.7 | yes |
| 6OIM | G12C | sotorasib | 25.9 | 27.8 | 23.1 | yes |

Switch-II is low-B (rigid, collapsed) in both apo structures and high-B (mobile, propped open) only in drug-bound 6OIM — **the pocket is induced-fit, not pre-existing.** Docking a new candidate into apo 4LDJ risks scoring it artificially poorly since the pocket isn't open yet. Built-in check: Wednesday's known-answer validation already docks sotorasib against 4LDJ — if sotorasib itself scores poorly there, that confirms the problem and the pipeline should pivot to 6OIM's conformation as the G12C template. 4LDJ/8FMI remain valid for the apo-backbone WT-vs-mutant question.

## 4. General structure audit — engineered mutations beyond the driver, mostly outside the pocket

Every structure except 3POZ and 4LDJ carries an engineered mutation beyond the intended driver (see `structure_audit.csv`):
- **8A2B, 5UGC: V948R** (C-lobe dimer-interface crystallization aid). Far from ATP pocket. Since *both* L858R and double share it, it cancels in the L858R→double comparison; WT (3POZ, no V948R) → mutant comparisons carry a small uncontrolled variable at position 948 — likely inconsequential given its distance from the cleft, but worth a footnote.
- **6OIM: C51S+C80L+C118S** ("cysteine-light" construct so sotorasib's covalent warhead reacts only at Cys12). None in the switch-II pocket — fine for drug-binding readout, matters only for whole-protein comparisons.
- **8FMI ("WT"): C118S** — and C118 is actually **native** (part of the NKCD guanine-binding motif, near GDP). This means the "WT" structure is the more-engineered one at a nucleotide-proximal position; 4LDJ (G12C) is the cleaner one aside from the intended mutation. Backbone effect likely negligible; flag if computing anything nucleotide-proximal.
- **4I24: 2 protomers in the ASU** — already handled by extracting a single consistent protomer in `structure_prep.py`.
- The one fully clean pair in the set: **3POZ (EGFR WT)** and **4LDJ (KRAS G12C)** — zero engineered mutations beyond intent.

None are wrong structure choices — all standard crystallography practice. The actionable point: the WT-vs-mutant delta isn't measuring only the driver mutation unless these are accounted for. Pocket-local readout (the Q1 fix) protects against most of them since the extras sit outside the pocket in every case.

**Caveat underlying all four:** these are binding-pocket geometry checks, not efficacy predictions. A clean pocket RMSD and plausible pose confirm the structural story is coherent — they don't establish a specific ΔΔG. The known clinical facts (erlotinib/gefitinib lose to T790M, osimertinib holds, sotorasib exploits the G12C switch-II pocket) remain the ground truth to validate *against*, not something a docking score substitutes for.
