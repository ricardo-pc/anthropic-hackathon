# anthropic-hackathon

Tells you which existing drugs will actually fit a specific tumor's broken protein — before anyone spends months in a lab.

License: MIT

Data sources: TCGA via open-access GDC somatic mutation calls (MAF) only — never controlled-access.

---

## What this is

A mutation-aware drug-repurposing triage tool. Given a tumor's driver mutation, it compares how a
panel of FDA-approved drugs bind the **wild-type** vs. the **mutant** protein, and classifies each
into four buckets — *weakened* (resistance predictor), *robust* (safe repurposing bet), *improved*,
or *non-binder* — with credible intervals, then explains the result in plain English via Claude.

The docking + stats are pre-computed; the scientific reasoning runs live. See `docs/scope.md` for the
locked targets/structures and `analysis/results/` for the validated known-answer panel.

## Running locally

The local pieces (triage, interpretation agent, stats, structure-prep) need only light Python deps.
The heavy docking (DiffDock + gnina, GPU) is a separate cluster setup — see `cluster/README.md`.

```bash
# 1. Create and activate a virtual environment (Python 3.10+)
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. See the deterministic triage for a mutation (no API key needed)
python src/triage.py "EGFR L858R+T790M"

# 4. Ask the interpretation agent in plain English (needs an Anthropic API key)
export ANTHROPIC_API_KEY=sk-ant-...      # your key; never commit it
python src/interpret.py "which drugs should I avoid for EGFR L858R+T790M, and any safe repurposing bets?"
```

The interpretation agent defaults to Claude Sonnet 5; set `TRIAGE_MODEL=claude-opus-4-8` for the
highest-quality phrasing.

## Repository layout

- `src/` — triage engine (`triage.py`), interpretation agent (`interpret.py`), structure prep.
- `data/` — the drug pool, prepared receptors, and docking/stats result tables.
- `analysis/` — known-answer validation and the Bayesian-bootstrap credible intervals.
- `cluster/` — Berkeley-GPU docking pipeline (DiffDock + gnina), run separately.
- `docs/` — locked scope, structures, known-answer citations, and score-interpretation notes.

Prior art: RepoRx (Molecule McBob). This is a clean-room rebuild — no carried-over code.
