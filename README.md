# MutationRx

**Which existing drugs still fit a tumor's mutated target — triaged before anyone spends months at the bench.**

🔬 **Live app: <https://mutationrx.onrender.com>** · Built with Claude for the Anthropic × Gladstone *Claude: Life Sciences* hackathon.

---

When a targeted cancer drug stops working, it is usually because the tumor mutated and the protein
changed shape so the drug no longer binds. MutationRx docks a panel of approved drugs against the
**wild-type and mutant** structure, quantifies each wild-type→mutant binding shift with a 95%
credible interval, and sorts every drug into *weakened* (resistance), *robust* (safe bet), *improved*,
or *non-binder*. Then **Claude reviews each hit for mechanistic plausibility**, separating believable
leads from coincidental docking scores.

> **The docking finds candidates. Claude decides which to believe.**

## Why it's credible

- **Reproduces known biology on unseen real data.** Run on a real, de-identified TCGA lung tumor
  carrying EGFR L858R+T790M, it recovers the clinic from docking alone: erlotinib and gefitinib fail,
  **osimertinib holds**.
- **Statistics alone aren't enough, and it shows why.** Screening 300 approved drugs against the
  resistant mutant, docking + bootstrap flagged 10 as significantly *improved* binders (tight credible
  intervals, high confidence) — and every one is a mechanistic artifact (antidepressants,
  antipsychotics, antibiotics). Only mechanism separates them, which is exactly the judgment Claude
  adds. Reproduce it: `python analysis/library_screen_triage.py`.
- **Honest by construction.** Docking affinity is a proxy, repurposing hits are hypotheses, and
  covalent mechanisms (KRAS G12C, osimertinib on C797S) are flagged as blind spots, not hidden.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate    # Python 3.10+
pip install -r requirements.txt
python src/triage.py "EGFR L858R+T790M"               # deterministic triage, no API key needed
```

Add Claude's plain-English review, talk to it from Claude Code / Desktop over MCP, or point it at a
real TCGA tumor — all in **[docs/usage.md](docs/usage.md)**. Or just open the
**[live app](https://mutationrx.onrender.com)**.

## Documentation

| Doc | What's in it |
|---|---|
| **[docs/usage.md](docs/usage.md)** | Every way to run it: hosted app, CLI, interpretation agent, MCP, real TCGA tumors, the dashboard |
| [docs/bring_your_own_tumor.md](docs/bring_your_own_tumor.md) | Triage a genotype the tool has never seen and dock it on your own GPU |
| [docs/scope.md](docs/scope.md) | Locked targets, structures, and the structural-rigor decisions behind them |
| [docs/submission.md](docs/submission.md) | The full thesis, methodology, and the imatinib cross-kinase lead |
| [docs/docking_score_notes.md](docs/docking_score_notes.md) | How to read DiffDock / gnina scores and the WT-vs-mutant delta caveats |
| [cluster/README.md](cluster/README.md) | The GPU docking pipeline (DiffDock + gnina) |

## Repository layout

- `app/` — the hosted web app (FastAPI backend + single-page workspace in `app/static/`).
- `src/` — triage engine (`triage.py`), interpretation agent (`interpret.py`), MCP server
  (`mcp_server.py`), real-tumor loader (`tcga.py`), cancer-type selector (`selector.py`), dashboard
  builder, drug-panel builder, registry validator, structure prep.
- `config/` — `mutations.json`, the editable tumor registry (add your own genotype here).
- `data/` — the drug panel, prepared receptors, docking/stats result tables, the cached TCGA slice,
  and the cached Claude reads.
- `analysis/` — known-answer validation, the Bayesian-bootstrap credible intervals, and the pooled
  imatinib + library-screen analyses.
- `cluster/` — the GPU docking pipeline (DiffDock + gnina), run separately.
- `dashboard/` — the self-contained visual report (generated).
- `docs/` — usage, scope, bring-your-own-tumor, submission notes, and score-interpretation notes.

## Notes

- **License:** MIT.
- **Data sources:** TCGA Lung Adenocarcinoma via the open-access cBioPortal API (PanCancer Atlas 2018),
  de-identified somatic calls only — never controlled-access data. Structures: RCSB PDB. Drug
  chemistry: PubChem / ChEMBL + RDKit.
- **Prior art:** RepoRx (Molecule McBob). This is a clean-room rebuild — no carried-over code.
