# Usage — every way to run MutationRx

MutationRx meets you where you work: a hosted web app, a terminal CLI, a live Claude interpretation
agent, and an MCP server. The docking + statistics are pre-computed and committed, so everything below
runs instantly on a laptop; only adding a brand-new genotype needs a GPU (see
[bring_your_own_tumor.md](bring_your_own_tumor.md)).

## The hosted app (nothing to install)

**<https://mutationrx.onrender.com>** — pick a real patient tumor or type a driver mutation, watch the
staged pipeline, and get a verdict-first result with the four-bucket leaderboard, credible-interval
error bars, and Claude's plain-English read. It is fully cache-driven, so it never needs a GPU; a
never-seen point mutation surfaces the "Connect GPU" gate instead.

Run it locally:

```bash
pip install -r requirements-web.txt
python app/server.py                      # http://localhost:8800
```

`MUTATIONRX_DRYRUN=1 python app/server.py` walks the whole de-novo compute flow with no GPU (loudly
flagged "not real docking") to demonstrate the mechanics end-to-end.

## Local setup for the CLI + agent

The local pieces (triage, interpretation agent, stats, structure-prep) need only light Python deps.
The heavy docking (DiffDock + gnina, GPU) is a separate cluster setup — see
[`../cluster/README.md`](../cluster/README.md).

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

## Talk to it inside Claude Code / Claude Desktop (MCP)

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

## Point it at a real tumor (TCGA)

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

## Front door: pick a cancer type, then a mutation

If you don't already know the exact mutation label, start from the cancer type. `src/selector.py` is a
small terminal front door — pick "lung cancer", see the in-scope mutations, pick one, get the
leaderboard. It also runs non-interactively (handy for a scripted demo):

```bash
python src/selector.py                                   # interactive menus
python src/selector.py "lung cancer" "EGFR L858R+T790M"  # jump straight to the triage
```

## Orthogonal evidence axes (why to believe a hit)

Every triage result now carries two per-drug axes that are independent of the docking score, so a
coincidental hit can be caught: **pathway grounding** (is the drug's real target in the driver's
pathway / enzyme class?) and **DepMap dependency** (is that target a gene lung adenocarcinoma actually
needs?). They show as paired pills in the web app's evidence table and in an "Orthogonal evidence"
strip, and they are handed to the Claude review (and the MCP tools) to ground its plausibility call.
Reproduce the read for any genotype from the terminal:

```bash
python analysis/evidence_axes.py "EGFR L858R+T790M"   # on-target corroborated, imatinib in-between, artifacts flagged
```

Provenance and the honesty caveats (the DepMap slice is cached/curated, not a live query) live in
`data/gene_kb.json` and `data/drug_targets.json`.

## The self-contained dashboard

`src/build_dashboard.py` bakes every triage result (and the real TCGA tumors) into a single
self-contained page, `dashboard/triage_dashboard.html` — it opens with why the problem matters, leads
with the verdict, shows the four-bucket leaderboard with each drug's wild-type→mutant shift drawn as a
95%-credible-interval error bar, badges the calls that reproduce known biology, and surfaces Claude's
plain-English read. No server, no network: open the file in a browser. Rebuild it with `python
src/build_dashboard.py`. The Claude read is cached offline by `src/cache_claude_reads.py` (run once
with your API key; use `TRIAGE_MODEL=claude-opus-4-8` for the best phrasing).

## Bring your own tumor (and your own GPU)

The mutation registry lives in `config/mutations.json`, not in code, so you can triage a genotype the
tool has never seen without editing Python. Add the entry, dock on your own GPU (the `cluster/`
pipeline), append the scores, and validate with `python src/check_registry.py "<label>"`. Full
walkthrough: [bring_your_own_tumor.md](bring_your_own_tumor.md). If `config/mutations.json` is absent,
`triage.py` falls back to the built-in in-scope set, so the tool always works out of the box.
