# Structures

Prepared receptors for mutation-aware docking. Produced by [`../../src/structure_prep.py`](../../src/structure_prep.py) from the raw PDB entries locked in [`../../docs/scope.md`](../../docs/scope.md).

## Layout
- `raw/<PDB>.pdb` — unmodified RCSB downloads (7 entries).
- `prepared/<PDB>_receptor.pdb` — docking-ready receptors.
- `pockets.json` — one pocket box per target + alignment metadata.

## What prep does (identically to every structure)
1. **Single protomer** — keep chain A only (4I24 ships with two copies).
2. **Strip** the co-crystallized inhibitor, waters, and crystallization additives (SO4, GOL, EDO…).
3. **Keep** functional cofactors: KRAS **GDP + Mg** (they hold KRAS in the inactive state whose switch-II pocket the G12C drugs need — removing them would collapse the pocket). EGFR keeps protein only.
4. **Strip pre-deposited hydrogens** so all 7 begin from an identical heavy-atom baseline.
5. **Landmark superposition** onto the target's WT reference frame (EGFR→3POZ, KRAS→8FMI), fitting on **mutation-independent anchors** so one shared pocket box is valid across all states without fitting on the mutation itself. EGFR anchors: K745, E762, hinge 791–797 (**gatekeeper 790 excluded** — it's the T790M site and 5UGC models it in two altLocs), HRD 835–837, DFG 855–857. KRAS: rigid G-domain core, excluding residue 12 and the switch regions (30–38, 60–76).

## Alignment quality
`rmsd_landmark` = fit RMSD on the mutation-independent anchors (the transform). `rmsd_pocket_readout` = CA RMSD over pocket-lining residues *after* that fit — i.e. given a mutation-independent alignment, how well does the pocket line up (the number that decides box validity). Full data in `pockets.json`.

| Structure | Landmark fit | Pocket readout | Global (all-CA) | note |
|---|---|---|---|---|
| 8A2B EGFR L858R | 0.59 Å | 1.10 Å | 3.15 Å | |
| 4I24 EGFR T790M | 0.56 Å | 0.76 Å | 5.05 Å | |
| 5UGC EGFR double | 2.01 Å | 1.55 Å | 2.85 Å | highest — covalent inhibitor shifts the catalytic spine; flag for spot-check |
| 4LDJ KRAS G12C | 0.21 Å | 0.15 Å | 0.21 Å | |
| 6OIM KRAS+soto | 0.83 Å | 1.74 Å | 1.33 Å | switch-II opened by sotorasib (induced-fit; see scope §6.3) |

Why landmarks not a radius: a radius-based pocket selection would sweep in residue 790 (the T790M gatekeeper), partly aligning on the very mutation being measured — circular. Fitting on fixed invariant anchors removes that. The large EGFR *global* RMSD is real inter-lobe hinge motion; the pocket readout confirms the shared box still sits correctly on every state (all ≤1.75 Å, comfortably inside the box's 5 Å padding). Tested dropping HRD/DFG from the anchor set — it lowered the *fit* number but did not improve the pocket readout, so the fuller anchor set is kept.

## Protonation — deferred to dock time (deliberate)
Receptors are **heavy-atom only**. Polar hydrogens are added consistently for all 7 by the rescoring engine's receptor prep (Block E docking step). OpenBabel was rejected here — it rewrites PDB residue names/numbers and would destroy the mutation identity and cofactor labels; pdb2pqr drops the KRAS cofactors. Consistency (the actual requirement) is preserved by running the same dock-time prep on every receptor.

## Verified
Every prepared receptor was checked to carry the correct residue at its hotspot (EGFR 790/858, KRAS 12) and, for KRAS, to retain GDP+Mg and have sotorasib removed. Regenerate + re-verify by running `src/structure_prep.py`.
