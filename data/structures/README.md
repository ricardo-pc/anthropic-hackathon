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
5. **Pocket-local superposition** onto the target's WT reference frame (EGFR→3POZ, KRAS→8FMI), so one shared pocket box is valid across all states.

## Alignment quality (pocket CA RMSD vs. WT reference)
| Structure | Pocket RMSD | Global RMSD | note |
|---|---|---|---|
| 8A2B EGFR L858R | 0.88 Å | 3.15 Å | |
| 4I24 EGFR T790M | 0.68 Å | 5.05 Å | |
| 5UGC EGFR double | 1.45 Å | 2.85 Å | highest — flag for spot-check |
| 4LDJ KRAS G12C | 0.12 Å | 0.21 Å | |
| 6OIM KRAS+soto | 0.36 Å | 1.33 Å | |

The large EGFR *global* RMSD is real inter-lobe hinge motion (different inhibitors freeze different conformations); the **pockets** still overlay <1.5 Å, so the shared box measures the mutation, not global pose. Aligning globally instead of pocket-locally would have silently misplaced the box by up to ~5 Å.

## Protonation — deferred to dock time (deliberate)
Receptors are **heavy-atom only**. Polar hydrogens are added consistently for all 7 by the rescoring engine's receptor prep (Block E docking step). OpenBabel was rejected here — it rewrites PDB residue names/numbers and would destroy the mutation identity and cofactor labels; pdb2pqr drops the KRAS cofactors. Consistency (the actual requirement) is preserved by running the same dock-time prep on every receptor.

## Verified
Every prepared receptor was checked to carry the correct residue at its hotspot (EGFR 790/858, KRAS 12) and, for KRAS, to retain GDP+Mg and have sotorasib removed. Regenerate + re-verify by running `src/structure_prep.py`.
