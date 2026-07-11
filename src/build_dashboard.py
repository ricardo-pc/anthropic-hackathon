#!/usr/bin/env python3
"""
Build the visual triage product page (Part B, Option 2) — a self-contained HTML file.

Runs the triage engine for every in-scope mutation (and resolves each cached TCGA tumor to its
primary genotype), bakes ALL of it into one static HTML file, and writes it to
dashboard/triage_dashboard.html. The page has no server and no network dependency — every number is
embedded — so it opens straight from disk and cannot break on camera. It is pure presentation over
the already-computed docking + bootstrap results; it invents nothing.

The page is built to be read as a *tool*, not a chart dump: it opens with why the problem matters,
leads with the verdict for the selected tumor, shows the evidence with validation badges (does it
reproduce known biology? is this a real patient tumor?), surfaces Claude's plain-English read, and
ends with how to run it on your own tumor + GPU.

Run:  python src/build_dashboard.py    (re-run whenever the triage data or Claude reads change)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import triage  # noqa: E402
import tcga  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{HERE}/dashboard/triage_dashboard.html"
CLAUDE_READS = f"{HERE}/data/claude_reads.json"

# What known biology each in-scope genotype reproduces — the credibility beat, shown as a badge.
# Honest and specific; nothing here is a claim beyond what the docking+stats actually recover.
VALIDATION = {
    "EGFR L858R+T790M":
        "Recovers the acquired-resistance signature: erlotinib and gefitinib lose binding on the "
        "double mutant (credible intervals exclude zero), while osimertinib — the third-generation "
        "drug designed to defeat T790M — holds. This is the known clinical picture, reproduced from "
        "docking alone.",
    "EGFR L858R":
        "The activating mutation that makes tumors sensitive to first-generation EGFR inhibitors. "
        "Used here as the treatment-naive baseline the resistance case is measured against.",
    "EGFR T790M":
        "Single-gatekeeper view. Clinically T790M co-occurs with L858R, so the double mutant gives "
        "the reliable resistance read — this single-variant structure is the muddier one.",
    "KRAS G12C":
        "Honest limitation on display: non-covalent docking cannot capture the covalent Cys12 bond "
        "that defines the G12C drugs, so sotorasib / adagrasib / divarasib numbers are unreliable in "
        "both directions. Shown as a caveat, never as a finding.",
}


def _load_claude_reads():
    """Cached plain-English interpretations from the Claude agent (offline-safe). Empty if not built
    yet — the page then shows a 'generate this' placeholder instead of a Claude panel. The returned
    dict is keyed by mutation label / sample id, plus a '__model' label the page shows as a tag."""
    if os.path.exists(CLAUDE_READS):
        with open(CLAUDE_READS) as f:
            blob = json.load(f)
        return {**blob.get("reads", {}), "__model": blob.get("__model", "Claude")}
    return {}


def build_data():
    mutations = {label: triage.triage(label) for label in triage.list_mutations()}
    tumors = []
    try:
        for s in tcga.list_samples():
            info = tcga.triage_sample(s["sample_id"])
            if info.get("primary_genotype"):
                tumors.append(dict(
                    sample_id=info["sample_id"],
                    n_mutations=info["n_mutations"],
                    in_scope_variants=info["in_scope_variants"],
                    matched_genotypes=info["matched_genotypes"],
                    primary_genotype=info["primary_genotype"],
                    source=info["source"],
                ))
    except FileNotFoundError:
        pass  # dashboard still works without the TCGA cache; the tumor row is just omitted
    return dict(
        generated=__import__("datetime").date.today().isoformat(),
        thresholds=dict(bind_kcal=triage.BIND_KCAL, delta_meaningful=triage.DELTA_MEANINGFUL),
        domain=[-6.0, 6.0],  # fixed diverging axis; rows beyond clamp with a chevron
        cancer_types=triage.CANCER_TYPES,
        mutations=mutations,
        validation=VALIDATION,
        tcga=tumors,
        claude_reads=_load_claude_reads(),
        n_drugs=len({d["drug"] for m in mutations.values() for d in m["drugs"]}),
    )


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mutation-aware drug-repurposing triage</title>
<style>
  :root{
    --surface:#fcfcfb; --plane:#f4f4f1; --card:#fff; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
    --grid:#e1e0d9; --axis:#c3c2b7; --border:rgba(11,11,11,0.10); --accent:#2a78d6;
    --c-weakened:#d03b3b; --c-robust:#0ca30c; --c-improved:#2a78d6; --c-nonbinder:#898781;
    --chip:#f0efec; --tint-w:rgba(208,59,59,.06); --tint-r:rgba(12,163,12,.06);
    --tint-i:rgba(42,120,214,.06); --tint-n:rgba(137,135,129,.06);
  }
  @media (prefers-color-scheme:dark){
    :root{
      --surface:#1a1a19; --plane:#0d0d0d; --card:#1f1f1d; --ink:#fff; --ink2:#c3c2b7; --muted:#8f8d86;
      --grid:#2c2c2a; --axis:#3a3a37; --border:rgba(255,255,255,0.10); --accent:#3987e5;
      --c-weakened:#e66767; --c-robust:#12b312; --c-improved:#3987e5; --c-nonbinder:#8f8d86;
      --chip:#26261f; --tint-w:rgba(230,103,103,.09); --tint-r:rgba(18,179,18,.08);
      --tint-i:rgba(57,135,229,.09); --tint-n:rgba(143,141,134,.08);
    }
  }
  :root[data-theme=light]{
    --surface:#fcfcfb; --plane:#f4f4f1; --card:#fff; --ink:#0b0b0b; --ink2:#52514e; --grid:#e1e0d9;
    --axis:#c3c2b7; --border:rgba(11,11,11,0.10); --accent:#2a78d6;
    --c-weakened:#d03b3b; --c-improved:#2a78d6; --c-nonbinder:#898781; --chip:#f0efec;
    --tint-w:rgba(208,59,59,.06); --tint-r:rgba(12,163,12,.06); --tint-i:rgba(42,120,214,.06); --tint-n:rgba(137,135,129,.06);
  }
  :root[data-theme=dark]{
    --surface:#1a1a19; --plane:#0d0d0d; --card:#1f1f1d; --ink:#fff; --ink2:#c3c2b7; --grid:#2c2c2a;
    --axis:#3a3a37; --border:rgba(255,255,255,0.10); --accent:#3987e5;
    --c-weakened:#e66767; --c-robust:#12b312; --c-improved:#3987e5; --c-nonbinder:#8f8d86; --chip:#26261f;
    --tint-w:rgba(230,103,103,.09); --tint-r:rgba(18,179,18,.08); --tint-i:rgba(57,135,229,.09); --tint-n:rgba(143,141,134,.08);
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--plane);color:var(--ink);
    font-family:system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.5;
    -webkit-font-smoothing:antialiased}
  .wrap{max-width:1080px;margin:0 auto;padding:0 20px 72px}
  a{color:var(--accent)}

  /* hero */
  .hero{padding:40px 0 20px}
  .eyebrow{font-size:12px;font-weight:700;letter-spacing:.10em;text-transform:uppercase;color:var(--accent);margin:0 0 10px}
  h1{font-size:32px;line-height:1.12;letter-spacing:-0.02em;margin:0 0 12px;max-width:20ch}
  .lede{font-size:17px;color:var(--ink2);margin:0 0 18px;max-width:64ch}
  .why{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0 4px}
  .why .c{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
  .why .c b{display:block;font-size:13px;margin-bottom:3px}
  .why .c span{font-size:12.5px;color:var(--ink2)}

  /* controls */
  .controls{position:sticky;top:0;z-index:10;background:var(--plane);
    display:flex;flex-wrap:wrap;gap:14px;align-items:flex-end;padding:14px 0;border-bottom:1px solid var(--border)}
  .ctl{display:flex;flex-direction:column;gap:5px}
  .ctl label{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
  select{font:inherit;font-size:14px;padding:8px 10px;border-radius:8px;border:1px solid var(--axis);
    background:var(--card);color:var(--ink);min-width:200px}
  .tcga{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-left:auto}
  .tcga .lbl{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);width:100%}
  .tumor-btn{font:inherit;font-size:12.5px;padding:8px 11px;border-radius:8px;cursor:pointer;
    border:1px solid var(--axis);background:var(--card);color:var(--ink)}
  .tumor-btn:hover{border-color:var(--accent)}
  .tumor-btn.active{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent);color:var(--accent)}

  section{margin-top:26px}
  .sec-h{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 12px}

  /* verdict */
  .genotype{font-size:20px;font-weight:700;letter-spacing:-0.01em;margin:0 0 2px}
  .genotype .tgt{color:var(--muted);font-weight:600;font-size:15px}
  .verdict-line{font-size:15px;color:var(--ink2);margin:0 0 16px;max-width:74ch}
  .verdict-line b{color:var(--ink)}
  .tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
  .tile{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px 18px;position:relative;overflow:hidden}
  .tile:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px}
  .tile.w:before{background:var(--c-weakened)} .tile.r:before{background:var(--c-robust)} .tile.h:before{background:var(--accent)}
  .tile .n{font-size:34px;font-weight:750;letter-spacing:-0.02em;line-height:1}
  .tile .k{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin:2px 0 6px}
  .tile.w .k{color:var(--c-weakened)} .tile.r .k{color:var(--c-robust)} .tile.h .k{color:var(--accent)}
  .tile .names{font-size:12.5px;color:var(--ink2);line-height:1.4}

  /* badges */
  .badges{display:flex;flex-direction:column;gap:10px}
  .badge{display:flex;gap:11px;align-items:flex-start;background:var(--card);border:1px solid var(--border);
    border-radius:12px;padding:12px 14px;font-size:13px}
  .badge .ic{flex:none;width:22px;height:22px;border-radius:50%;display:grid;place-items:center;
    font-size:13px;font-weight:800;color:#fff;margin-top:1px}
  .badge.valid .ic{background:var(--c-robust)} .badge.real .ic{background:var(--accent)}
  .badge.caveat .ic{background:var(--c-nonbinder)}
  .badge b{color:var(--ink)}
  .badge .bt{color:var(--ink2)}

  /* chart */
  .axis-ends{display:flex;justify-content:space-between;font-size:11.5px;color:var(--muted);padding:0 2px 6px}
  .legend{display:flex;flex-wrap:wrap;gap:16px;font-size:12.5px;color:var(--ink2);padding:2px 2px 10px}
  .legend .it{display:flex;align-items:center;gap:6px}
  .sw{width:11px;height:11px;border-radius:3px;display:inline-block}
  .axkey{color:var(--muted)}
  .bucket{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:6px 16px 10px;margin-bottom:14px;border-left-width:4px;border-left-style:solid}
  .bucket.b-weakened{border-left-color:var(--c-weakened);background:linear-gradient(var(--tint-w),var(--tint-w)),var(--card)}
  .bucket.b-robust{border-left-color:var(--c-robust);background:linear-gradient(var(--tint-r),var(--tint-r)),var(--card)}
  .bucket.b-improved{border-left-color:var(--c-improved);background:linear-gradient(var(--tint-i),var(--tint-i)),var(--card)}
  .bucket.b-non-binder{border-left-color:var(--c-nonbinder);background:linear-gradient(var(--tint-n),var(--tint-n)),var(--card)}
  .bhead{display:flex;align-items:center;gap:9px;font-size:15px;font-weight:700;padding:12px 0 6px}
  .bhead .desc{font-weight:400;color:var(--ink2);font-size:13px}
  .bhead .ct{margin-left:auto;color:var(--muted);font-size:12px;font-weight:600}
  table.rows{width:100%;border-collapse:collapse}
  .rows td{padding:9px 6px;border-top:1px solid var(--grid);vertical-align:middle}
  .rows tr:first-child td{border-top:none}
  .dname{font-weight:650;font-size:14px;white-space:nowrap}
  .bench{display:inline-block;font-size:9.5px;font-weight:800;letter-spacing:.03em;text-transform:uppercase;
    color:var(--c-robust);border:1px solid var(--c-robust);border-radius:5px;padding:0 4px;margin-left:6px;vertical-align:1px}
  .cat{display:block;color:var(--muted);font-size:11px;font-weight:400;margin-top:1px}
  .track{position:relative;height:30px;min-width:190px}
  .zero{position:absolute;top:4px;bottom:4px;width:1px;background:var(--axis);opacity:.6}
  .ci{position:absolute;top:12.5px;height:5px;border-radius:3px;opacity:.3}
  .dot{position:absolute;top:9px;width:10px;height:10px;border-radius:50%;margin-left:-5px;
    border:2px solid var(--card);box-shadow:0 1px 2px rgba(15,21,25,.2);z-index:1}
  .chev{position:absolute;top:6px;font-size:17px;line-height:1;font-weight:800}
  .num{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap;font-size:13.5px;font-weight:600}
  .ci-txt{font-variant-numeric:tabular-nums;color:var(--ink2);font-size:12px;white-space:nowrap}
  .conf{font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;font-weight:700}
  .conf.low{color:var(--c-weakened)} .conf.medium{color:var(--muted)} .conf.high{color:var(--ink2)}

  /* claude */
  .claude{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden}
  .claude .ch{display:flex;align-items:center;gap:9px;padding:13px 16px;border-bottom:1px solid var(--border)}
  .claude .ch .dot2{width:9px;height:9px;border-radius:50%;background:var(--accent)}
  .claude .ch b{font-size:14px}
  .claude .ch .tag{margin-left:auto;font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;
    color:var(--muted);border:1px solid var(--border);border-radius:6px;padding:2px 7px}
  .claude .body{padding:8px 18px 16px;font-size:14px;color:var(--ink2)}
  .claude .body h4{color:var(--accent);font-size:14px;font-weight:650;letter-spacing:-0.01em;margin:16px 0 5px}
  .claude .body strong{color:var(--ink)}
  .claude .body ul{margin:6px 0;padding-left:20px}
  .claude .empty{padding:20px 18px;color:var(--muted);font-size:13.5px}
  .claude .empty code{background:var(--chip);padding:2px 6px;border-radius:5px;font-size:12.5px;color:var(--ink)}

  /* byo */
  .byo{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px}
  .byo h3{margin:0 0 6px;font-size:17px}
  .byo p{color:var(--ink2);font-size:14px;margin:0 0 14px;max-width:72ch}
  .steps{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
  .step{font-size:12.5px}
  .step .sn{display:grid;place-items:center;width:24px;height:24px;border-radius:50%;background:var(--accent);
    color:#fff;font-weight:800;font-size:12px;margin-bottom:7px}
  .step b{display:block;margin-bottom:2px}
  .step span{color:var(--ink2)}
  pre{background:var(--chip);border:1px solid var(--border);border-radius:10px;padding:13px 15px;overflow-x:auto;
    font-size:12.5px;line-height:1.5;margin:0}
  code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}

  .foot{margin-top:26px;color:var(--muted);font-size:11.5px;max-width:88ch;line-height:1.55}
  .tip{position:fixed;pointer-events:none;z-index:30;background:var(--ink);color:var(--surface);
    font-size:12px;padding:8px 10px;border-radius:8px;max-width:300px;opacity:0;transition:opacity .08s;
    box-shadow:0 6px 20px rgba(0,0,0,.28);line-height:1.4}
  @media (max-width:720px){
    .why,.tiles,.steps{grid-template-columns:1fr} h1{font-size:26px} .tcga{margin-left:0}
    .cat{display:inline;margin-left:6px} .ci-txt{display:none}
  }
</style>
</head>
<body>
<div class="wrap">

  <div class="hero">
    <p class="eyebrow">Mutation-aware drug-repurposing triage</p>
    <h1>When a tumor mutates, the drug that worked stops working. Which one do you try next?</h1>
    <p class="lede">Targeted cancer drugs fail by resistance — the tumor changes shape and the drug no
      longer binds. Deciding what to test next, or whether an already-approved drug could be
      repurposed, means expensive, slow wet-lab screening. This tool is the fast first pass: for a
      tumor's driver mutation it scores a panel of approved drugs against the wild-type and mutant
      protein and sorts them into <b>what to stop</b>, <b>what still binds</b>, and <b>what's worth
      testing</b> — with the uncertainty stated, before you spend a day at the bench.</p>
    <div class="why">
      <div class="c"><b>Grounded in physics</b><span>Each drug is docked against the real mutant
        structure and rescored for binding affinity — not a guess from a text model.</span></div>
      <div class="c"><b>Honest about uncertainty</b><span>Every call carries a 95% credible interval
        from replicate runs. Affinity is a proxy, not a K<sub>d</sub>; repurposing hits are
        hypotheses, never discoveries.</span></div>
      <div class="c"><b>Reviewed by Claude</b><span>Docking scores drugs that don't really bind. Claude
        weighs each hit by mechanism and flags the likely artifacts — so you test signal, not noise.</span></div>
    </div>
  </div>

  <div class="controls">
    <div class="ctl"><label for="cancer">Cancer type</label><select id="cancer"></select></div>
    <div class="ctl"><label for="mutation">Mutation</label><select id="mutation"></select></div>
    <div class="tcga" id="tcga"><span class="lbl">&hellip; or load a real, de-identified TCGA patient tumor</span></div>
  </div>

  <section id="verdictSec">
    <p class="sec-h">The verdict</p>
    <div class="genotype" id="genotype"></div>
    <p class="verdict-line" id="verdictLine"></p>
    <div class="tiles" id="tiles"></div>
  </section>

  <section id="badgeSec">
    <p class="sec-h">Does it hold up?</p>
    <div class="badges" id="badges"></div>
  </section>

  <section>
    <p class="sec-h">The evidence &mdash; wild-type &rarr; mutant binding shift</p>
    <div class="legend">
      <span class="it"><span class="sw" style="background:var(--c-weakened)"></span>Weakened</span>
      <span class="it"><span class="sw" style="background:var(--c-robust)"></span>Robust</span>
      <span class="it"><span class="sw" style="background:var(--c-improved)"></span>Improved</span>
      <span class="it"><span class="sw" style="background:var(--c-nonbinder)"></span>Non-binder / unreliable</span>
      <span class="it axkey">&#9679; = &Delta; (mutant&minus;WT) &nbsp; &#124;&mdash;&#124; = 95% CI &nbsp; dashed = &plusmn;1 kcal/mol "matters" line</span>
    </div>
    <div class="axis-ends"><span>&larr; binds better on the mutant</span>
      <span>0 = no change</span><span>binds worse (resistance) &rarr;</span></div>
    <div id="chart"></div>
  </section>

  <section id="claudeSec">
    <p class="sec-h">Claude's read</p>
    <div class="claude" id="claude"></div>
  </section>

  <section>
    <p class="sec-h">Run it on your own tumor</p>
    <div class="byo">
      <h3>Bring your own tumor &mdash; and your own GPU</h3>
      <p>You are not limited to these examples. The docking is the only GPU-heavy step, and it runs on
        <i>your</i> hardware (a lab cluster, or a rented cloud GPU). Give the tool your tumor's
        wild-type and mutant structures, run the documented pipeline, add one config entry, and the
        same triage and this page work on your genotype.</p>
      <div class="steps">
        <div class="step"><div class="sn">1</div><b>Structures</b><span>Get the wild-type and mutant PDB structures for your target.</span></div>
        <div class="step"><div class="sn">2</div><b>Dock on your GPU</b><span>Run DiffDock + gnina from <code>cluster/</code> against the drug panel.</span></div>
        <div class="step"><div class="sn">3</div><b>Register it</b><span>Add one entry to <code>config/mutations.json</code> mapping the label to the structures.</span></div>
        <div class="step"><div class="sn">4</div><b>Triage</b><span>Rebuild — your genotype now appears here with full credible intervals.</span></div>
      </div>
<pre><code>// config/mutations.json — add your genotype, no code changes
"EGFR L747_P753delinsS": {
  "target": "EGFR", "wt": "3POZ", "mut": "YOUR_PDB",
  "note": "exon-19 deletion; sensitizing"
}</code></pre>
      <p style="margin:14px 0 0;font-size:13px">Full walkthrough: <code>docs/bring_your_own_tumor.md</code>. The GPU run stays on your side — the tool ingests the scores it produces.</p>
    </div>
  </section>

  <div class="foot" id="foot"></div>
</div>
<div class="tip" id="tip"></div>

<script>
const DATA = __DATA__;
const [DMIN, DMAX] = DATA.domain;
const ORDER = ["weakened","robust","improved","non-binder"];
const BMETA = {
  "weakened":  {label:"Weakened — avoid",         desc:"loses binding on the mutant",            cvar:"--c-weakened"},
  "robust":    {label:"Robust — safe bet",        desc:"binding holds on the mutant",            cvar:"--c-robust"},
  "improved":  {label:"Improved",                 desc:"binds better on the mutant (rare)",      cvar:"--c-improved"},
  "non-binder":{label:"Non-binder / unreliable",  desc:"no binding either state, or QC-flagged", cvar:"--c-nonbinder"},
};
const xPct = v => (Math.max(DMIN,Math.min(DMAX,v)) - DMIN)/(DMAX-DMIN)*100;
const esc = s => String(s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));

const $ = id => document.getElementById(id);
const $cancer=$("cancer"), $mut=$("mutation"), $tcga=$("tcga"), $chart=$("chart"),
      $tip=$("tip"), $foot=$("foot");
let curTumor=null;

for(const c of Object.keys(DATA.cancer_types)){
  const o=document.createElement("option"); o.value=c; o.textContent=c; $cancer.appendChild(o);
}
for(const t of DATA.tcga){
  const b=document.createElement("button"); b.className="tumor-btn"; b.dataset.id=t.sample_id;
  b.textContent=t.sample_id+"  ("+t.in_scope_variants.join(", ")+")";
  b.onclick=()=>loadTumor(t);
  $tcga.appendChild(b);
}
function fillMutations(cancer){
  $mut.innerHTML="";
  for(const m of DATA.cancer_types[cancer]){
    const o=document.createElement("option"); o.value=m; o.textContent=m; $mut.appendChild(o);
  }
}
$cancer.onchange=()=>{ curTumor=null; fillMutations($cancer.value); render($mut.value); };
$mut.onchange=()=>{ curTumor=null; render($mut.value); };

function loadTumor(t){
  curTumor=t;
  const label=t.primary_genotype;
  for(const c of Object.keys(DATA.cancer_types)){
    if(DATA.cancer_types[c].includes(label)){ $cancer.value=c; fillMutations(c); $mut.value=label; break; }
  }
  render(label);
}

// ---- verdict ----
function renderVerdict(T){
  const by=b=>T.drugs.filter(d=>d.bucket===b);
  const weak=by("weakened"), rob=by("robust"), imp=by("improved");
  const leads=rob.filter(d=>d.category==="repurposing_candidate");
  $("genotype").innerHTML = esc(T.mutation)+' <span class="tgt">· target '+esc(T.target)+'</span>';
  const nm = arr => arr.slice(0,3).map(d=>esc(d.drug)).join(", ")+(arr.length>3?", …":"");
  const tiles=[
    {c:"w",n:weak.length,k:"Avoid",names: weak.length?nm(weak):"none"},
    {c:"r",n:rob.length, k:"Still binds",names: rob.length?nm(rob):"none"},
    {c:"h",n:leads.length,k:"To review",names: leads.length?nm(leads):"none"},
  ];
  $("tiles").innerHTML = tiles.map(t=>
    `<div class="tile ${t.c}"><div class="n">${t.n}</div><div class="k">${t.k}</div>`+
    `<div class="names">${t.names}</div></div>`).join("");
  let line=`Docking flags <b>${weak.length}</b> drug${weak.length!=1?"s":""} that lose grip on this mutation `+
    `and <b>${rob.length}</b> that hold — but a robust docking score isn't automatically a real hit. `;
  if(leads.length) line+=`<b>${leads.length}</b> are approved non-oncology drugs `+
    `(${nm(leads)}); the mechanistic review below weighs which are believable and which are likely artifacts.`;
  $("verdictLine").innerHTML=line;
}

// ---- badges ----
function renderBadges(T){
  const out=[];
  if(curTumor){
    out.push(`<div class="badge real"><span class="ic">&#9679;</span><span class="bt">`+
      `<b>Real patient tumor.</b> ${esc(curTumor.sample_id)} — a de-identified TCGA lung-adenocarcinoma sample `+
      `with ${curTumor.n_mutations} somatic mutations, never seen by the tool. In-scope: <b>${esc(curTumor.in_scope_variants.join(", "))}</b>; `+
      `most of the tumor is outside the panel. Source: cBioPortal, TCGA PanCancer Atlas 2018.</span></div>`);
  }
  const v=DATA.validation[T.mutation];
  if(v){
    const isCaveat = T.mutation.startsWith("KRAS");
    out.push(`<div class="badge ${isCaveat?"caveat":"valid"}"><span class="ic">${isCaveat?"!":"&#10003;"}</span>`+
      `<span class="bt"><b>${isCaveat?"Known limitation.":"Reproduces known biology."}</b> ${esc(v)}</span></div>`);
  }
  $("badges").innerHTML=out.join("");
  $("badgeSec").style.display = out.length?"":"none";
}

// ---- chart ----
function ciBar(r){
  const c=`var(${BMETA[r.bucket].cvar})`;
  const lo=xPct(r.ci95[0]), hi=xPct(r.ci95[1]), d=xPct(r.delta), z=xPct(0);
  const t1=xPct(-DATA.thresholds.delta_meaningful), t2=xPct(DATA.thresholds.delta_meaningful);
  let over="";
  if(r.delta>DMAX) over=`<span class="chev" style="left:calc(100% - 11px);color:${c}">&rsaquo;</span>`;
  if(r.delta<DMIN) over=`<span class="chev" style="left:2px;color:${c}">&lsaquo;</span>`;
  return `<div class="track">
    <span class="zero" style="left:${z}%"></span>
    <span class="ci" style="left:${lo}%;width:${Math.max(hi-lo,0.7)}%;background:${c}"></span>
    <span class="dot" style="left:${d}%;background:${c}"></span>${over}</div>`;
}
function renderChart(T){
  let html="";
  for(const bucket of ORDER){
    const rows=T.drugs.filter(d=>d.bucket===bucket);
    if(!rows.length) continue;
    const m=BMETA[bucket];
    html+=`<div class="bucket b-${bucket}"><div class="bhead"><span class="sw" style="background:var(${m.cvar})"></span>`+
      `${m.label}<span class="desc">&mdash; ${m.desc}</span><span class="ct">${rows.length} drug${rows.length>1?"s":""}</span></div>`+
      `<table class="rows"><tbody>`;
    for(const r of rows){
      const dsign=(r.delta>=0?"+":"")+r.delta.toFixed(2);
      const bench = r.category==="known_answer" ? '<span class="bench" title="clinical benchmark drug">benchmark</span>' : "";
      html+=`<tr data-tip="<b>${esc(r.drug)}</b>: ${esc(r.reason)}.<br>WT ${r.affinity_wt}, mutant ${r.affinity_mut} kcal/mol · &Delta; ${dsign} [95% CI ${r.ci95[0].toFixed(2)}, ${r.ci95[1].toFixed(2)}] · ${r.confidence} confidence.">`+
        `<td style="width:150px"><span class="dname">${esc(r.drug)}${bench}</span><span class="cat">${esc(r.category)}</span></td>`+
        `<td>${ciBar(r)}</td>`+
        `<td class="num" style="width:56px">${dsign}</td>`+
        `<td class="ci-txt" style="width:98px">[${r.ci95[0].toFixed(2)}, ${r.ci95[1].toFixed(2)}]</td>`+
        `<td class="conf ${r.confidence} num" style="width:58px">${r.confidence}</td></tr>`;
    }
    html+=`</tbody></table></div>`;
  }
  $chart.innerHTML=html;
  attachTips();
}

// ---- claude read ----
function mdToHtml(md){
  const lines=md.split("\n"); let html="", inList=false;
  const inline=s=>esc(s).replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>");
  for(let ln of lines){
    ln=ln.replace(/\r$/,"");
    if(/^#{1,6}\s/.test(ln)){ if(inList){html+="</ul>";inList=false;} html+="<h4>"+inline(ln.replace(/^#+\s/,""))+"</h4>"; }
    else if(/^\s*[-*]\s/.test(ln)){ if(!inList){html+="<ul>";inList=true;} html+="<li>"+inline(ln.replace(/^\s*[-*]\s/,""))+"</li>"; }
    else if(ln.trim()===""){ if(inList){html+="</ul>";inList=false;} }
    else { if(inList){html+="</ul>";inList=false;} html+="<p style='margin:8px 0'>"+inline(ln)+"</p>"; }
  }
  if(inList)html+="</ul>";
  return html;
}
function renderClaude(T){
  const key = curTumor ? (DATA.claude_reads[curTumor.sample_id] ? curTumor.sample_id : T.mutation) : T.mutation;
  const read = DATA.claude_reads[key];
  const model = DATA.claude_reads.__model || "Claude";
  if(read){
    $("claude").innerHTML =
      `<div class="ch"><span class="dot2"></span><b>Claude's interpretation</b>`+
      `<span class="tag">${esc(model)} · cached</span></div>`+
      `<div class="body">${mdToHtml(read)}</div>`;
  } else {
    $("claude").innerHTML =
      `<div class="ch"><span class="dot2"></span><b>Claude's interpretation</b><span class="tag">not cached</span></div>`+
      `<div class="empty">Claude reads these same numbers live and returns a plain-English verdict. `+
      `Generate the cached reads for the demo with <code>python src/cache_claude_reads.py</code> `+
      `(uses your API key once), or ask it live via <code>python src/interpret.py</code> or the MCP server.</div>`;
  }
}

// ---- hover tooltips ----
function attachTips(){
  for(const tr of $chart.querySelectorAll("tr[data-tip]")){
    tr.onmousemove=e=>{ $tip.innerHTML=tr.dataset.tip; $tip.style.opacity="1";
      let x=e.clientX+14, y=e.clientY+16;
      if(x+312>innerWidth) x=e.clientX-300;
      if(y+90>innerHeight) y=e.clientY-90;
      $tip.style.left=x+"px"; $tip.style.top=y+"px"; };
    tr.onmouseleave=()=>{ $tip.style.opacity="0"; };
  }
}

function render(label){
  const T=DATA.mutations[label];
  if(!T) return;
  document.querySelectorAll(".tumor-btn").forEach(b=>b.classList.toggle("active", !!curTumor && b.dataset.id===curTumor.sample_id));
  renderVerdict(T); renderBadges(T); renderChart(T); renderClaude(T);
  $foot.textContent="Target "+T.target+" · Δ = mutant − wild-type affinity (kcal/mol); more negative binds stronger. "+
    "A credible interval that excludes zero is a confident call; one that straddles zero is not. "+
    "Docking affinity is a proxy, not a measured Kd or clinical efficacy — this is pre-wet-lab triage, "+
    "not treatment advice. Robust repurposing hits are hypotheses for wet-lab follow-up, never discoveries. "+
    "Data generated "+DATA.generated+" over "+DATA.n_drugs+" approved drugs.";
}

const first=Object.keys(DATA.cancer_types)[0];
$cancer.value=first; fillMutations(first); render($mut.value);
</script>
</body>
</html>
"""


def main():
    data = build_data()
    html = TEMPLATE.replace("__DATA__", json.dumps(data))
    # write the standalone report, and a copy the app serves as its "static report" link
    for out in (OUT, f"{HERE}/app/static/dashboard.html"):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as f:
            f.write(html)
    n_reads = len([k for k in data["claude_reads"] if not k.startswith("__")])
    print(f"Wrote {OUT}")
    print(f"  {len(data['mutations'])} mutations · {len(data['tcga'])} real TCGA tumors · "
          f"{data['n_drugs']} drugs · Claude reads cached: {n_reads}")


if __name__ == "__main__":
    main()
