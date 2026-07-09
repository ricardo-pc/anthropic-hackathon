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

### Talk to it inside Claude Code / Claude Desktop (MCP)

`src/mcp_server.py` exposes the triage engine as MCP tools, so you can ask Claude Code or Claude
Desktop about a tumor in plain English and it calls the tools live — no API key of your own needed
(the host provides Claude). Needs Python 3.10+ and `mcp` (in `requirements.txt`).

- **Claude Code:** the project ships a `.mcp.json` — open Claude Code in this repo (with the venv
  created) and approve the `onco-triage` server. Then ask e.g. *"which drugs should I avoid for KRAS G12C?"*
- **Claude Desktop:** add to `~/Library/Application Support/Claude/claude_desktop_config.json`
  (use absolute paths):
  ```json
  {"mcpServers": {"onco-triage": {
    "command": "/ABSOLUTE/PATH/anthropic-hackathon/.venv/bin/python",
    "args": ["/ABSOLUTE/PATH/anthropic-hackathon/src/mcp_server.py"]}}}
  ```
  Restart Claude Desktop; the `onco-triage` tools appear.

The reasoning guardrails (docking is a proxy, repurposing hits are hypotheses, the KRAS covalent
caveat) travel with the tool descriptions and the `note` field the tools return.

## Repository layout

- `src/` — triage engine (`triage.py`), interpretation agent (`interpret.py`), structure prep.
- `data/` — the drug pool, prepared receptors, and docking/stats result tables.
- `analysis/` — known-answer validation and the Bayesian-bootstrap credible intervals.
- `cluster/` — Berkeley-GPU docking pipeline (DiffDock + gnina), run separately.
- `docs/` — locked scope, structures, known-answer citations, and score-interpretation notes.

Prior art: RepoRx (Molecule McBob). This is a clean-room rebuild — no carried-over code.
