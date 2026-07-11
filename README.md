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

### Point it at a real tumor (TCGA)

`src/tcga.py` runs the tool on genuine, de-identified patient tumors from TCGA Lung Adenocarcinoma
(cBioPortal, PanCancer Atlas 2018). It loads a tumor's real somatic mutations, maps them onto the
in-scope targets, and triages the primary genotype — a tumor carrying both L858R **and** T790M is
recognized as the resistant double mutant. A small cache (`data/tcga_luad_cache.json`) is committed
so it runs fully offline; `--refresh` re-pulls it from the public cBioPortal API. Open-access,
de-identified somatic calls only — never controlled-access data.

```bash
python src/tcga.py                     # list the cached real tumors
python src/tcga.py TCGA-L9-A50W-01     # map + triage a real L858R+T790M tumor
python src/tcga.py --refresh           # re-pull the cache from cBioPortal
```

The same capability is exposed to Claude as the `list_tcga_tumors` and `triage_tcga_profile` tools in
both the interpretation agent and the MCP server.

### Front door: pick a cancer type, then a mutation

If you don't already know the exact mutation label, start from the cancer type. `src/selector.py` is a
small terminal front door — pick "lung cancer", see the in-scope mutations, pick one, get the
leaderboard. It also runs non-interactively (handy for a scripted demo):

```bash
python src/selector.py                                   # interactive menus
python src/selector.py "lung cancer" "EGFR L858R+T790M"  # jump straight to the triage
```

For a visual version, `src/build_dashboard.py` bakes every triage result (and the real TCGA tumors)
into a single self-contained page, `dashboard/triage_dashboard.html` — it opens with why the problem
matters, leads with the verdict, shows the four-bucket leaderboard with each drug's wild-type→mutant
shift drawn as a 95%-credible-interval error bar, badges the calls that reproduce known biology, and
surfaces Claude's plain-English read. No server, no network: open the file in a browser. Rebuild it
with `python src/build_dashboard.py`. The Claude read is cached offline by `src/cache_claude_reads.py`
(run once with your API key; use `TRIAGE_MODEL=claude-opus-4-8` for the best phrasing).

### Bring your own tumor (and your own GPU)

The mutation registry lives in `config/mutations.json`, not in code, so you can triage a genotype the
tool has never seen — without editing Python. Add an entry mapping your label to a wild-type and
mutant structure, run the docking on your own GPU (the `cluster/` pipeline), append the scores, and
validate:

```bash
python src/check_registry.py "EGFR L747_P753delinsS"   # confirms structures + scores are present → READY
```

Then it's a first-class citizen in the CLI, selector, dashboard, agent, and MCP tools. Full
walkthrough: [`docs/bring_your_own_tumor.md`](docs/bring_your_own_tumor.md). The GPU-heavy docking
stays on your hardware; everything downstream is instant on a laptop. (If `config/mutations.json` is
absent, `triage.py` falls back to the built-in in-scope set, so the tool always works out of the box.)

## Repository layout

- `src/` — triage engine (`triage.py`), interpretation agent (`interpret.py`), MCP server
  (`mcp_server.py`), real-tumor loader (`tcga.py`), cancer-type front door (`selector.py`),
  dashboard builder (`build_dashboard.py`), Claude-read cache (`cache_claude_reads.py`), registry
  validator (`check_registry.py`), structure prep.
- `config/` — `mutations.json`, the editable tumor registry (add your own genotype here).
- `data/` — the drug pool, prepared receptors, docking/stats result tables, the cached TCGA slice,
  and the cached Claude reads.
- `dashboard/` — the self-contained visual product page (generated).
- `analysis/` — known-answer validation and the Bayesian-bootstrap credible intervals.
- `cluster/` — Berkeley-GPU docking pipeline (DiffDock + gnina), run separately.
- `docs/` — locked scope, structures, known-answer citations, and score-interpretation notes.

Prior art: RepoRx (Molecule McBob). This is a clean-room rebuild — no carried-over code.
