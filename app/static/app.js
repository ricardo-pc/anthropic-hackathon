/* MutationRx — research-assistant workspace. Talks to the FastAPI job API. */
const DMIN = -6, DMAX = 6, DMEAN = 1.0;                 // diverging axis + "matters" threshold
const ORDER = ["weakened", "robust", "improved", "non-binder"];
const BMETA = {
  "weakened":  {label:"Weakened",   desc:"avoid; loses binding on the mutant",       cvar:"--c-weakened"},
  "robust":    {label:"Robust",     desc:"safe bet; binding holds on the mutant",    cvar:"--c-robust"},
  "improved":  {label:"Improved",   desc:"binds better on the mutant (rare)",        cvar:"--c-improved"},
  "non-binder":{label:"Non-binder", desc:"no binding either state, or QC-flagged",   cvar:"--c-nonbinder"},
};
const CATNAME = {
  egfr_family:"EGFR family", kras_family:"KRAS family", known_answer:"known answer",
  multi_kinase:"multi-kinase", repurposing_candidate:"repurposing candidate",
  approved_library:"approved library", control:"control", tool_compound:"tool compound",
};
const catLabel = c => CATNAME[c] || String(c || "").replace(/_/g, " ");
const esc = s => String(s).replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const drugChips = arr => arr.length
  ? arr.slice(0, 3).map(d => `<span class="tchip">${esc(d.drug)}</span>`).join("")
      + (arr.length > 3 ? `<span class="tchip more">+${arr.length - 3}</span>` : "")
  : `<span class="tchip-none">none</span>`;
const xPct = v => (Math.max(DMIN, Math.min(DMAX, v)) - DMIN) / (DMAX - DMIN) * 100;
const $ = id => document.getElementById(id);

const CLIENT = (() => {
  let c = localStorage.getItem("mutationrx_client");
  if (!c) { c = "c_" + Math.random().toString(36).slice(2, 12); localStorage.setItem("mutationrx_client", c); }
  return c;
})();
const api = (path, opts = {}) => fetch(path, {
  ...opts, headers: {"Content-Type": "application/json", "X-Client-Id": CLIENT, ...(opts.headers || {})}
});

let BOOT = null;
let lastReq = null, lastDisplay = null;   // remembered so we can re-run after a GPU connects

// icon markup — defined up here so showHero() can use them the instant init() runs
const ATOM = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="1.6" fill="currentColor"/><ellipse cx="12" cy="12" rx="10" ry="4.3"/><ellipse cx="12" cy="12" rx="10" ry="4.3" transform="rotate(60 12 12)"/><ellipse cx="12" cy="12" rx="10" ry="4.3" transform="rotate(120 12 12)"/></svg>`;
const SPARK = `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l1.7 5.1a3 3 0 0 0 1.9 1.9L21 11l-5.4 1.9a3 3 0 0 0-1.9 1.9L12 21l-1.7-6.2a3 3 0 0 0-1.9-1.9L3 11l5.4-1.9a3 3 0 0 0 1.9-1.9z"/></svg>`;
const CHIP = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><rect x="6.5" y="6.5" width="11" height="11" rx="2"/><path d="M9.5 2v3M14.5 2v3M9.5 19v3M14.5 19v3M2 9.5h3M2 14.5h3M19 9.5h3M19 14.5h3"/></svg>`;
// verdict-tile glyphs: stop / keep / investigate — the three triage actions
const IC_BAN = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M5.6 5.6l12.8 12.8"/></svg>`;
const IC_HOLD = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12.5l5 5 11-11"/></svg>`;
const IC_FLASK = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3h6M10 3.5v6L5.2 17a2 2 0 0 0 1.7 3h10.2a2 2 0 0 0 1.7-3L14 9.5v-6"/><path d="M7.6 14h8.8"/></svg>`;
const IC_WARN = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 3.8 1.8 18a2 2 0 0 0 1.7 3h16.9a2 2 0 0 0 1.7-3L13.7 3.8a2 2 0 0 0-3.4 0zM12 9v4M12 17h.01"/></svg>`;

// ---------------- init ----------------
(async function init() {
  applyTheme(localStorage.getItem("mutationrx_theme"));
  $("themeBtn").onclick = () => {
    const cur = document.documentElement.getAttribute("data-theme");
    const next = cur === "dark" ? "light" : (cur === "light" ? "dark" : (matchMedia("(prefers-color-scheme: dark)").matches ? "light" : "dark"));
    applyTheme(next); localStorage.setItem("mutationrx_theme", next);
  };
  $("newBtn").onclick = showHero;
  $("whyBtn").onclick = showWhy;
  $("methodBtn").onclick = showMethodology;
  $("askForm").onsubmit = e => { e.preventDefault(); runQuery($("query").value.trim()); };
  $("query").oninput = onType;
  document.addEventListener("click", e => { if (!e.target.closest(".field")) hideSuggest(); });

  showHero();            // render immediately so the page is never blank while bootstrap loads
  loadBoot();
})();

async function loadBoot(attempt = 0) {
  try {
    const r = await api("/api/bootstrap");
    if (!r.ok) throw new Error("HTTP " + r.status);   // 502/503 while the host is waking
    BOOT = await r.json();
  } catch (e) {
    if (attempt < 20) return setTimeout(() => loadBoot(attempt + 1), 3000);  // covers a ~60s cold start
    $("askHint").textContent = "Still waking the server up… reload in a moment.";
    return;
  }
  renderSidebar();
  refreshUsage();
  if (document.querySelector(".hero")) showHero();   // fill the hero's tumor CTAs, if still on it
}

function applyTheme(t) { if (t) document.documentElement.setAttribute("data-theme", t); }

// ---------------- sidebar ----------------
function renderSidebar() {
  $("tumorChips").innerHTML = BOOT.tumors.map(t =>
    `<button class="chip" data-tumor="${esc(t.sample_id)}">
       <span class="t">${esc(t.sample_id)}</span>
       <span class="s">${esc(t.in_scope_variants.join(", "))} · ${t.n_mutations} mutations</span>
     </button>`).join("");
  $("geneChips").innerHTML = BOOT.mutations.filter(m => !m.includes("(")).map(m =>
    `<button class="chip gene" data-mut="${esc(m)}"><span class="t">${esc(m)}</span></button>`).join("");
  $("tumorChips").querySelectorAll("[data-tumor]").forEach(b =>
    b.onclick = () => submit({kind: "tumor", sample_id: b.dataset.tumor}, b.dataset.tumor));
  $("geneChips").querySelectorAll("[data-mut]").forEach(b =>
    b.onclick = () => { $("query").value = b.dataset.mut; runQuery(b.dataset.mut); });
}

function refreshUsage() {
  api("/api/usage").then(r => r.json()).then(u => {
    const bar = $("usageBar");
    if (!u.gpu_connected) {                 // nothing to meter until a GPU is connected
      $("usageText").textContent = "GPU not connected";
      bar.style.width = "0%"; bar.style.opacity = ".4";
      return;
    }
    const left = Math.max(0, u.limit - u.used);
    $("usageText").textContent = `${left} of ${u.limit} free runs`;
    bar.style.opacity = "1"; bar.style.width = `${(u.used / u.limit) * 100}%`;
  }).catch(() => {});
}

// ---------------- query parsing ----------------
function parseQuery(str) {
  const s = str.trim();
  if (!s) return {error: "Enter a mutation, e.g. EGFR L858R+T790M or EGFR G719S."};
  const exact = BOOT.mutations.find(m => m.toLowerCase() === s.toLowerCase());
  if (exact) return {kind: "mutation", label: exact};
  const parts = s.split(/\s+/);
  if (parts.length >= 2) {
    const target = parts[0].toUpperCase();
    const mutation = parts.slice(1).join("").toUpperCase();
    return {kind: "denovo", target, mutation};
  }
  return {error: `Couldn't read “${esc(s)}”. Try a target and mutation, e.g. EGFR G719S.`};
}

function runQuery(str) {
  const req = parseQuery(str);
  if (req.error) { flashHint(req.error); return; }
  hideSuggest();
  // If it doesn't name a supported target, it's probably a cancer name — help instead of erroring.
  if (req.kind === "denovo" && BOOT && !BOOT.targets.includes(req.target)) return renderScopeHelp(str);
  submit(req, str);
}

function renderScopeHelp(input) {
  $("workspace").innerHTML = `
    <div class="notice">
      <h3>That looks like a cancer type, not a driver mutation</h3>
      <p>MutationRx triages from a specific <b>driver mutation</b>, a gene plus a variant, like
        <code>EGFR L858R</code>, not a cancer's name. Today it covers the targets
        <b>${BOOT.targets.join(" and ")}</b> (the drivers behind much of lung and colorectal cancer).
        To triage a tumor on a different target, you bring that protein's structure and dock it on your
        own GPU; the method is the same. See <code>docs/bring_your_own_tumor.md</code>.</p>
      <div class="startline" style="margin:6px 2px">Try one of these instead →</div>
      <div class="chips" id="scopeChips" style="display:grid;grid-template-columns:1fr 1fr;gap:8px;max-width:560px"></div>
    </div>`;
  $("scopeChips").innerHTML = BOOT.mutations.filter(m => !m.includes("(")).map(m =>
    `<button class="chip gene" data-mut="${esc(m)}"><span class="t">${esc(m)}</span></button>`).join("");
  $("scopeChips").querySelectorAll("[data-mut]").forEach(b =>
    b.onclick = () => { $("query").value = b.dataset.mut; runQuery(b.dataset.mut); });
}

// ---------------- suggestions ----------------
let hiIdx = -1;
function onType(e) {
  const v = e.target.value.trim().toLowerCase();
  if (!v) return hideSuggest();
  const matches = BOOT.mutations.filter(m => m.toLowerCase().includes(v)).slice(0, 6);
  const box = $("suggest");
  let html = matches.map((m, i) => `<button data-q="${esc(m)}">${esc(m)}</button>`).join("");
  if (/^[a-z]+\s+\S+/i.test(e.target.value) && !matches.some(m => m.toLowerCase() === v))
    html += `<button data-q="${esc(e.target.value)}" class="new">Compute <b>${esc(e.target.value.toUpperCase())}</b> (a new genotype)</button>`;
  if (!html) return hideSuggest();
  box.innerHTML = html; box.hidden = false; hiIdx = -1;
  box.querySelectorAll("button").forEach(b => b.onclick = () => { $("query").value = b.dataset.q; runQuery(b.dataset.q); });
}
function hideSuggest() { $("suggest").hidden = true; }
function flashHint(msg) { const h = $("askHint"); h.textContent = msg; h.style.color = "var(--c-weakened)"; setTimeout(() => h.style.color = "", 2600); }

// ---------------- hero / empty ----------------
function previewCard() {
  // a real result, in miniature: the double-mutant verdict + a few error-bar rows + Claude's line
  const rows = [
    {d: "erlotinib", delta: 1.87, b: "weakened"}, {d: "gefitinib", delta: 1.20, b: "weakened"},
    {d: "osimertinib", delta: 0.02, b: "robust"}, {d: "imatinib", delta: -2.29, b: "robust"},
  ];
  const px = v => (Math.max(-4, Math.min(4, v)) + 4) / 8 * 100;
  const bars = rows.map(r => {
    const c = `var(${BMETA[r.b].cvar})`;
    return `<div class="pv-row"><span class="pv-d">${r.d}</span>
      <span class="pv-track"><span class="pv-zero"></span><span class="pv-dot" style="left:${px(r.delta)}%;background:${c}"></span></span>
      <span class="pv-n" style="color:${c}">${r.delta >= 0 ? "+" : ""}${r.delta.toFixed(2)}</span></div>`;
  }).join("");
  return `<div class="preview" id="previewCard" role="button" tabindex="0" title="Open this result">
      <div class="pv-top"><span class="pv-dots"><i></i><i></i><i></i></span><span class="pv-t">MutationRx</span><span class="pv-live">live result</span></div>
      <div class="pv-body">
        <div class="pv-head"><span class="pv-gt">EGFR L858R+T790M</span><span class="pv-chip">resistant tumor</span></div>
        <div class="pv-tiles">
          <div class="pv-tile w"><b>12</b><span>avoid</span></div>
          <div class="pv-tile r"><b>7</b><span>holds</span></div>
          <div class="pv-tile h"><b>3</b><span>to review</span></div>
        </div>
        <div class="pv-rows">${bars}</div>
        <div class="pv-claude"><span class="pv-cd">${SPARK}</span><span><b>Claude</b> &nbsp;Avoid the first-gen inhibitors; osimertinib holds. The one non-obvious lead worth a bench test is imatinib.</span></div>
      </div>
    </div>`;
}

function showHero() {
  $("query").value = ""; hideSuggest();
  $("workspace").innerHTML = `
    <div class="hero">
      <div class="hero-split">
        <div class="hero-left">
          <span class="eyebrow">Mutation-aware drug-repurposing triage</span>
          <h1>When a tumor mutates, its drugs stop working. Which one do you try next?</h1>
          <p class="lede">MutationRx docks 62 approved drugs against the mutant protein, then has Claude separate
            the real leads from docking noise. First-pass triage, before the bench.</p>
          <div class="hero-cta">
            <div class="cta-label">Start with a real patient tumor</div>
            <div class="cta-chips" id="heroTumors"></div>
          </div>
        </div>
        <div class="hero-right">
          <div class="hero-mol" id="heroMol" role="button" tabindex="0" title="Explore the 3D structure">
            <div class="hm-stage"><iframe id="heroFrame" tabindex="-1" title="3D structure of EGFR L858R+T790M" scrolling="no"></iframe>
              <span class="hm-badge">3D structure</span><span class="hm-x">Explore in 3D &rsaquo;</span></div>
            <div class="hm-cap"><span class="hm-gt">EGFR L858R+T790M</span><span class="hm-sub">The resistant double mutant it docks against</span></div>
          </div>
          ${previewCard()}
          <div class="pv-hint">Real mutant structure &amp; pre-computed result &middot; click either to explore live</div>
        </div>
      </div>
      <div class="featurestrip">
        <div class="fs"><span class="fs-ic">${ATOM}</span><div><b>Grounded in physics</b><span>Real docking, gnina rescore, and credible intervals. Not a text-model guess.</span></div></div>
        <div class="fs"><span class="fs-ic">${SPARK}</span><div><b>Reviewed by Claude</b><span>Separates real leads from coincidental docking hits, so you test signal.</span></div></div>
        <div class="fs"><span class="fs-ic">${CHIP}</span><div><b>Runs on your GPU</b><span>Any point mutation, modeled and docked on demand.</span></div></div>
      </div>
    </div>`;
  const hm = $("heroMol");
  if (hm) {
    const openDbl = () => openStructure("EGFR L858R+T790M");
    hm.onclick = openDbl;
    hm.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openDbl(); } };
    // lazy-mount the spinning molecule a beat after the hero paints, so it never delays the hero text or bootstrap
    setTimeout(() => { const f = $("heroFrame");
      if (f && !f.getAttribute("src")) f.src = "/static/structure.html?v=7&bare=1&genotype=" + encodeURIComponent("EGFR L858R+T790M"); }, 350);
  }
  if (BOOT) {
    const seen = new Set(), featured = [];   // one tumor per genotype keeps the CTA tight
    for (const t of BOOT.tumors) { if (!seen.has(t.primary_genotype)) { seen.add(t.primary_genotype); featured.push(t); } }
    $("heroTumors").innerHTML = featured.map(t =>
      `<button class="ctachip" data-tumor="${esc(t.sample_id)}">
         <span class="cc-t">${esc(t.primary_genotype)}</span>
         <span class="cc-s">${esc(t.sample_id)}</span>
         <span class="cc-arr">&rsaquo;</span></button>`).join("");
    $("heroTumors").querySelectorAll("[data-tumor]").forEach(b =>
      b.onclick = () => submit({kind: "tumor", sample_id: b.dataset.tumor}, b.dataset.tumor));
    const pv = $("previewCard");
    if (pv) pv.onclick = () => submit({kind: "tumor", sample_id: "TCGA-L9-A50W-01"}, "TCGA-L9-A50W-01");
  }
}

// ---------------- why it matters ----------------
function showWhy() {
  $("query").value = ""; hideSuggest();
  $("workspace").innerHTML = `
    <div class="method why">
      <span class="eyebrow">Why it matters</span>
      <h1 class="mh1">The drug works. Then the tumor learns to survive it.</h1>
      <p class="mlede">Targeted therapy is one of modern medicine's great victories, and its most predictable
        failure. Shrinking the distance between those two is the reason MutationRx exists.</p>

      <div class="wsec"><h3>The problem</h3>
        <p>Precision cancer drugs are remarkable at first. Match the right drug to the right mutation and
        tumors can shrink dramatically. But cancer adapts. Under the pressure of treatment it acquires new
        mutations that change the shape of the very protein the drug was built to fit, and the drug stops
        binding. For most targeted therapies this is not a rare complication. It is the expected endpoint.</p></div>

      <div class="wsec"><h3>The bottleneck that costs the most</h3>
        <p>When resistance appears, the question is brutally practical: what do we try next? Answering it
        properly means testing candidate drugs against the new, resistant form of the target. That is slow,
        expensive laboratory work, measured in months and in real budget. Computational shortcuts exist, but
        they hand back lists of "hits" no one can act on with confidence, because the underlying methods score
        plenty of drugs that would never truly bind. So the shortcut gets ignored, and the slow search grinds on.</p></div>

      <div class="wsec"><h3>What MutationRx changes</h3>
        <p>MutationRx compresses that first decision from weeks at the bench to minutes at a laptop. For a
        tumor's driver mutation it ranks a panel of approved drugs by how their binding shifts on the actual
        mutant, states the uncertainty honestly, and then does the step software has never managed on its own:
        it has Claude judge which of those computational hits are mechanistically believable and which are simply
        noise. The result is a short, trustworthy shortlist. Test these. Skip those. Here is why. And the "why" is
        open to inspection, not a black box: each call is backed by whether the drug's target sits in the tumor's
        pathway and whether the cancer actually depends on it, and you can question any result in plain language.</p></div>

      <div class="wsec"><h3>Why this is the hard part, and the whole point</h3>
        <p>Anyone can generate a docking score. The scarce skill is knowing which scores to believe, a judgment
        that is contextual and mechanistic. That is precisely what a frontier model provides and a script cannot.
        MutationRx turns an unreliable method into a decision a researcher can act on. That is the entire value.</p></div>

      <div class="wsec"><h3>The benefit</h3>
        <div class="pillars">
          <div class="pillar"><div class="pl-h">For researchers</div><p>Fewer wasted experiments, faster hypotheses, and more shots on goal for every dollar of bench budget.</p></div>
          <div class="pillar"><div class="pl-h">For the field</div><p>Precision-oncology reach that is not locked behind a pharma budget. Any lab, any point mutation, on its own GPU.</p></div>
          <div class="pillar"><div class="pl-h">For patients, ultimately</div><p>A faster, cheaper path from "the drug stopped working" to "here is the next thing to try."</p></div>
        </div></div>

      <div class="wsec"><h3>The human reality</h3>
        <div class="wnote">None of this is abstract. Behind every resistance mutation is a person whose working
        treatment quietly stopped working, and a family that felt it happen. Mutations like EGFR T790M are a lived
        reality for a great many people every year. Cutting the time and cost between "it stopped working" and
        "try this next" is a problem worth real effort.</div></div>
    </div>`;
}

// ---------------- methodology ----------------
function showMethodology() {
  $("query").value = ""; hideSuggest();
  const flow = ["Structures", "Dock (DiffDock)", "Rescore (gnina)", "Bootstrap CI", "Classify", "Evidence axes", "Claude review"];
  $("workspace").innerHTML = `
    <div class="method">
      <span class="eyebrow">Methodology</span>
      <h1 class="mh1">How MutationRx decides, and why to trust it</h1>
      <p class="mlede">For a tumor's driver mutation, MutationRx asks one question of every drug: does it still bind the
        <i>mutant</i> protein as well as it binds the <i>wild-type</i>? Everything below is how that question is
        answered rigorously, with the uncertainty quantified and the limits stated plainly.</p>

      <div class="mflow">${flow.map((s, i) =>
        `<span class="mstep">${esc(s)}</span>${i < flow.length - 1 ? '<span class="marr">&rsaquo;</span>' : ''}`).join("")}</div>

      <div class="msec"><h3><span class="mn">1</span> Structures, aligned for a fair comparison</h3>
        <p>Each genotype pairs a wild-type reference structure with a mutant structure, both real crystal
        structures from the RCSB PDB (EGFR wild-type <code>3POZ</code>; L858R <code>8A2B</code>; T790M
        <code>4I24</code>; L858R+T790M <code>5UGC</code>; KRAS wild-type <code>8FMI</code>, G12C <code>4LDJ</code>).
        They are superposed on mutation-independent landmarks so that a change in binding reflects the mutation,
        not an arbitrary alignment. A point mutant with no crystal structure (e.g. EGFR C797S) is <b>modeled</b>
        by side-chain substitution and labeled as lower-confidence.</p></div>

      <div class="msec"><h3><span class="mn">2</span> A panel of 62 approved drugs</h3>
        <p>27 are curated with a rationale: targeted EGFR/KRAS inhibitors, multi-kinase inhibitors, and
        non-oncology drugs as repurposing candidates. The other 35 come from an unbiased approved-drug library,
        a deliberate negative control that lets the tool show it discriminates rather than saying yes to
        everything. Canonical SMILES from PubChem / ChEMBL, prepared with RDKit. The same panel is docked against
        every structure, so results are directly comparable across genotypes.</p></div>

      <div class="msec"><h3><span class="mn">3</span> Docking, then an honest rescore</h3>
        <p>DiffDock (a diffusion model for blind docking) generates a binding pose for each drug against each
        structure. gnina then rescores that pose into a predicted binding affinity (kcal/mol, more negative =
        stronger). We use <code>gnina --minimize</code>, a local in-pocket relaxation, not <code>--score_only</code>:
        raw diffusion poses carry small clashes that score falsely positive, and the minimization removes them.</p></div>

      <div class="msec"><h3><span class="mn">4</span> Uncertainty, quantified</h3>
        <p>DiffDock is stochastic, so every drug&times;structure pair is docked <b>many independent times</b>. A
        Bayesian bootstrap (Dirichlet-weighted resampling over the replicates) yields the wild-type&rarr;mutant
        affinity shift <b>&Delta;</b> with a <b>95% credible interval</b>; Benjamini&ndash;Hochberg FDR controls
        the many comparisons across the panel. A credible interval that excludes zero is a confident call; one
        that straddles zero is not. This is the difference between a real shift and run-to-run noise.</p></div>

      <div class="msec"><h3><span class="mn">5</span> Deterministic four-bucket classification</h3>
        <p>Each drug is sorted into <b class="mk-w">weakened</b>, <b class="mk-r">robust</b>, <b class="mk-i">improved</b>,
        or <b class="mk-n">non-binder</b> by fixed rules, not by the model's whim. A shift counts as resistance or
        improvement only if it is <b>both statistically significant</b> (interval excludes zero) <b>and practically
        meaningful</b> (|&Delta;| &ge; 1 kcal/mol). Effect size, not just a p-value. Poses that move too far during
        minimization are QC-flagged as unreliable.</p></div>

      <div class="msec"><h3><span class="mn">6</span> Two orthogonal evidence axes, grounded in data</h3>
        <p>Before Claude judges a hit, each drug is scored on two axes the docking never sees, so the judgment is
        auditable rather than taken on faith. <b>Pathway grounding</b> asks whether the drug's established molecular
        target sits in the same signaling pathway or enzyme class as the tumor's driver (a kinase inhibitor on a
        kinase driver is coherent; a statin on EGFR is not). <b>DepMap dependency</b> asks whether that target is a
        gene this cancer actually needs, from CRISPR essentiality in lung-adenocarcinoma cell lines. A statin is
        off-pathway and hits no dependency (both grey); an on-target inhibitor is aligned and a real dependency
        (both teal); imatinib lands in between, in-class but not a lung dependency, so its lead rests on the
        structural fit. These are cached, curated slices (see <code>data/gene_kb.json</code>), reported beside every
        drug and to Claude.</p></div>

      <div class="msec"><h3><span class="mn">7</span> Claude reviews for mechanistic plausibility</h3>
        <p>Docking will happily give a strong score to a drug that has no business binding the target. The
        deterministic layer cannot tell a real hit from a coincidence; that judgment needs biology. Claude weighs
        each hit by mechanism and by the two evidence axes above, separating believable leads from likely artifacts.
        A statin scoring on EGFR is flagged as coincidental; a kinase inhibitor is taken seriously. This is where the
        tool earns trust rather than generating noise. And the judgment is not a dead end: every result carries a
        live chat that answers follow-up questions, grounded in the same numbers, buckets, and evidence axes, so you
        can ask why a drug is a lead or whether a hit is worth the bench and get a cited answer.</p></div>

      <div class="msec valid"><h3><span class="mn">&#10003;</span> Validation: it reproduces known biology</h3>
        <p>Told nothing but the structures, the tool independently recovers the clinic: on the T790M resistance
        mutant, erlotinib and gefitinib lose binding while osimertinib holds. Run on a real, de-identified TCGA
        patient tumor it had never seen, it gives the same answer. Reproducing what is known is the license to be
        believed on what is not.</p></div>

      <div class="msec limits"><h3><span class="mn">!</span> Limitations, stated plainly</h3>
        <ul>
          <li>Docking affinity is a <b>proxy</b> for binding, not a measured K<sub>d</sub> and not clinical efficacy. The statistics quantify sampling noise in that proxy, not its accuracy versus experiment.</li>
          <li><b>Non-covalent docking cannot capture covalent mechanisms.</b> KRAS G12C drugs and osimertinib (on C797S) bind covalently; the tool flags these rather than misreading them.</li>
          <li><b>Modeled mutant structures</b> (side-chain swap) are lower-confidence than crystal structures and are labeled as such.</li>
          <li>Only in-panel <b>driver</b> mutations are covered; a real tumor's other mutations are out of scope.</li>
          <li>Robust and improved hits are <b>hypotheses for wet-lab follow-up</b>, never discoveries. This is pre-wet-lab triage, not treatment advice.</li>
        </ul></div>

      <div class="msec"><h3><span class="mn">&#9673;</span> Data &amp; reproducibility</h3>
        <p>Tumors: TCGA Lung Adenocarcinoma via the cBioPortal public API (PanCancer Atlas 2018), open-access and
        de-identified. Structures: RCSB PDB. Drug chemistry: PubChem + RDKit. The classification is deterministic
        and reproducible; the pipeline is open-source; and any point mutation can be added by docking it on your
        own GPU (bring-your-own-tumor). The docking finds candidates. Claude decides which to believe.</p></div>
    </div>`;
}

// ---------------- submit + run ----------------
async function submit(req, display) {
  lastReq = req; lastDisplay = display;
  const stages = ["Resolving genotype", "Modeling mutant structure", "Docking the panel (wild-type + mutant)",
                  "Rescoring poses (gnina)", "Bootstrapping credible intervals", "Classifying & explaining"];
  renderRun(display, stages);
  let res;
  try { res = await (await api("/api/triage", {method: "POST", body: JSON.stringify(req)})).json(); }
  catch (e) { return renderError("Couldn't reach the compute service. Is the server running?"); }
  if (res.error === "free_runs_exhausted") return renderGpuGate(res);
  if (res.error) return renderError(res.error, res.known);

  if (res.cached) { await revealCached(stages); }        // replay the precomputed pipeline quickly
  await pollJob(res.job_id, res.cached);
}

function renderRun(display, stages) {
  hideSuggest();
  $("workspace").innerHTML = `
    <div class="run">
      <div class="rt"><b>${esc(display || "Triaging")}</b><span class="badge tag" id="runTag" style="margin-left:auto">working…</span></div>
      <div class="rsub" id="runSub">Running the triage pipeline.</div>
      <div class="pipeline" id="pipeline">
        ${stages.map(s => `<div class="pstage" data-s="${esc(s)}"><span class="pd">${stages.indexOf(s)+1}</span><span class="pn">${esc(s)}</span></div>`).join("")}
      </div>
    </div>`;
}
function setStage(name, status) {
  const el = document.querySelector(`.pstage[data-s="${cssq(name)}"]`);
  if (!el) return;
  el.className = "pstage " + status;
  if (status === "done") el.querySelector(".pd").innerHTML = "✓";
}
const cssq = s => s.replace(/"/g, '\\"');
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function revealCached(stages) {
  $("runTag").textContent = "precomputed";
  $("runSub").textContent = "Retrieving the precomputed result, replaying the pipeline that produced it.";
  // deliberately unhurried (~2s) so the stages are readable — this is a cached replay, not real timing
  for (const s of stages) { setStage(s, "running"); await sleep(230); setStage(s, "done"); await sleep(110); }
  await sleep(300);
}

async function pollJob(jobId, cached) {
  for (let i = 0; i < 900; i++) {
    let j;
    try { j = await (await api(`/api/job/${jobId}`)).json(); } catch { await sleep(700); continue; }
    if (!cached) j.stages.forEach(s => setStage(s.name, s.status));
    if (j.status === "done") { refreshUsage(); return renderResult(j.result); }
    if (j.status === "needs_gpu") { refreshUsage(); return renderGpuGate({message: j.error}); }
    if (j.status === "error") return renderError(j.error);
    await sleep(cached ? 120 : 700);
  }
  renderError("The compute job timed out.");
}

// ---------------- result ----------------
function renderResult(r) {
  const tags = [];
  if (r.dry_run) tags.push(`<span class="tag modeled">dry run</span>`);
  else if (r.cached) tags.push(`<span class="tag cache">precomputed</span>`);
  else tags.push(`<span class="tag computed">computed on GPU</span>`);
  if (r.modeled && !r.dry_run) tags.push(`<span class="tag modeled" title="mutant structure modeled from the wild-type by side-chain swap; lower confidence than a crystal structure">modeled structure</span>`);
  const dryBanner = r.dry_run ? `<div class="notice err" style="margin-top:0"><h3>⚠ Dry run: not real docking</h3><p style="margin:0">This walked the full pipeline with the wild-type standing in for the mutant, to demonstrate the mechanics end-to-end. The numbers below are <b>not</b> a real result for ${esc(r.label)}. Connect a real GPU (RunPod) for genuine docking.</p></div>` : "";

  const by = b => r.drugs.filter(d => d.bucket === b);
  const weak = by("weakened"), rob = by("robust"), imp = by("improved");
  const leads = rob.filter(d => d.category === "repurposing_candidate" || d.category === "approved_library");
  // orthogonal-evidence strip: the robust/improved hits worth a belief check — everything that binds
  // the mutant but isn't an obvious on-target inhibitor (the cross-kinase leads AND the artifacts).
  // Rank the believable in-class leads first, then the strongest-scoring artifacts, so the real lead
  // (e.g. imatinib) heads the strip instead of being buried under big-magnitude coincidences.
  const oeRank = d => d.evidence.pathway.status === "plausible" ? 0 : 1;
  const oeLeads = rob.concat(imp)
    .filter(d => d.evidence && d.evidence.pathway && d.evidence.pathway.status !== "aligned")
    .sort((a, b) => oeRank(a) - oeRank(b) || a.delta - b.delta).slice(0, 5);
  // fresh conversation scoped to this result
  CHAT = {label: r.label, sample_id: r.tumor ? r.tumor.sample_id : null, messages: [], busy: false, error: null};
  const nm = a => a.slice(0, 3).map(d => esc(d.drug)).join(", ") + (a.length > 3 ? ", …" : "");
  let line = `Docking flags <b>${weak.length}</b> drug${weak.length!=1?"s":""} that lose grip on ${esc(r.label)} and <b>${rob.length}</b> that hold, but a robust docking score isn't automatically a real hit.`;
  if (leads.length) line += ` <b>${leads.length}</b> are approved repurposing candidates (${nm(leads)}); Claude's review below weighs which are mechanistically believable and which are likely artifacts.`;

  const badges = [];
  if (r.tumor) badges.push(`<div class="badge real"><span class="ic">●</span><span class="bt"><b>Real patient tumor.</b> ${esc(r.tumor.sample_id)}, a de-identified TCGA lung-adenocarcinoma sample with ${r.tumor.n_mutations} somatic mutations, never seen by the tool. In scope: <b>${esc(r.tumor.in_scope_variants.join(", "))}</b>; most of the tumor is out of scope. Source: cBioPortal, TCGA PanCancer Atlas 2018.</span></div>`);
  if (r.validation) { const cav = r.label.startsWith("KRAS"); badges.push(`<div class="badge ${cav?"caveat":"valid"}"><span class="ic">${cav?"!":"✓"}</span><span class="bt"><b>${cav?"Known limitation.":"Reproduces known biology."}</b> ${esc(r.validation)}</span></div>`); }
  if (r.modeled) badges.push(`<div class="badge caveat"><span class="ic">i</span><span class="bt"><b>Modeled structure.</b> No crystal structure for this mutant, so it was modeled from the wild-type by side-chain substitution. Treat the affinities as lower-confidence than the curated crystal cases.</span></div>`);

  $("workspace").innerHTML = `
    <div class="result">
      ${dryBanner}
      <div class="rhead"><div class="gt">${esc(r.label)} <span class="tgt">· target ${esc(r.target)}</span></div>
        <div class="rhead-right">${hasStructure(r.label)?structBtn(r.label):""}<div class="tags">${tags.join("")}</div></div></div>
      <div class="card pad">
        <div class="verdict-line">${line}</div>
        <div class="tiles">
          <button type="button" class="tile w" data-focus="weakened">
            <div class="th"><span class="tic">${IC_BAN}</span><span class="k">Avoid</span></div>
            <div class="tn"><span class="n">${weak.length}</span><span class="unit">drug${weak.length!=1?"s":""}</span></div>
            <div class="tsub">lose their grip on the mutant</div>
            <div class="tchips">${drugChips(weak)}</div>
          </button>
          <button type="button" class="tile r" data-focus="robust">
            <div class="th"><span class="tic">${IC_HOLD}</span><span class="k">Still binds</span></div>
            <div class="tn"><span class="n">${rob.length}</span><span class="unit">drug${rob.length!=1?"s":""}</span></div>
            <div class="tsub">hold their affinity on the mutant</div>
            <div class="tchips">${drugChips(rob)}</div>
          </button>
          <button type="button" class="tile h" data-focus="robust">
            <div class="th"><span class="tic">${IC_FLASK}</span><span class="k">To review</span><span class="hbadge">${SPARK}Claude</span></div>
            <div class="tn"><span class="n">${leads.length}</span><span class="unit">lead${leads.length!=1?"s":""}</span></div>
            <div class="tsub">worth a bench test, not the bin</div>
            <div class="tchips">${drugChips(leads)}</div>
          </button>
        </div>
      </div>
      ${badges.length?`<div class="card">${badges.join("")}</div>`:""}
      ${r.claude_read?claudePanel(r):""}
      ${oeStrip(oeLeads)}
      ${r.dry_run?"":chatPanel(r)}
      <details class="card disclose" ${r.claude_read?"":"open"}>
        <summary>Full evidence <span class="sh">all ${r.drugs.length} drugs, wild-type to mutant shift with 95% CI</span><span class="chev">▸</span></summary>
        <div class="evidence">${evidence(r)}</div>
      </details>
      <div class="foot-note">Δ = mutant minus wild-type affinity (kcal/mol); more negative binds stronger. A credible interval that excludes zero is a confident call; one that straddles zero is not. Docking affinity is a proxy, not a measured K<sub>d</sub> or clinical efficacy. This is pre-wet-lab triage, not treatment advice.</div>
    </div>`;
  attachTips();
  wireChat();
  document.querySelectorAll(".tile[data-focus]").forEach(t => t.onclick = () => focusBucket(t.dataset.focus));
  const sb = $("structBtn");
  if (sb) sb.onclick = () => openStructure(sb.dataset.label);
}

// clicking a verdict tile opens Full evidence and pulls the matching bucket into view
function focusBucket(key) {
  const det = document.querySelector("details.disclose");
  if (det && !det.open) det.open = true;
  const el = document.querySelector(".bucket.b-" + key);
  if (!el) return;
  el.scrollIntoView({behavior: "smooth", block: "center"});
  el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash");
}

// ---------------- 3D structure viewer (non-blocking modal) ----------------
// We have a real crystal (or, for C797S, a modeled) structure for these genotypes. A de-novo genotype
// computed on a GPU has no bundled structure, so the button simply doesn't appear.
function hasStructure(label) {
  const L = (label || "").toLowerCase();
  return /c797s/.test(L) || /t790m/.test(L) || /l858r/.test(L) || /g12c/.test(L);
}
const STRUCT_IC = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l8 4.5v9L12 20 4 15.5v-9z"/><path d="M12 2v18M4 6.5l8 4.5 8-4.5"/></svg>`;
function structBtn(label) {
  return `<button class="struct-btn" id="structBtn" data-label="${esc(label)}">${STRUCT_IC} View 3D structure</button>`;
}
function openStructure(label) {
  let m = $("structModal");
  if (!m) {
    m = document.createElement("div");
    m.id = "structModal"; m.className = "struct-modal";
    m.innerHTML = `
      <div class="sm-backdrop" data-close></div>
      <div class="sm-panel">
        <div class="sm-bar">
          <span class="sm-title">3D structure</span><span class="sm-sub" id="smSub"></span>
          <button class="sm-close" data-close aria-label="Close viewer">✕</button>
        </div>
        <iframe class="sm-frame" id="smFrame" title="3D molecular structure viewer" allow="fullscreen"></iframe>
      </div>`;
    document.body.appendChild(m);
    m.addEventListener("click", e => { if (e.target.hasAttribute("data-close")) closeStructure(); });
  }
  $("smSub").textContent = label;
  $("smFrame").src = "/static/structure.html?v=7&genotype=" + encodeURIComponent(label);
  m.classList.add("open");
  document.addEventListener("keydown", escClose);
}
function escClose(e) { if (e.key === "Escape") closeStructure(); }
function closeStructure() {
  const m = $("structModal");
  if (m) { m.classList.remove("open"); $("smFrame").src = "about:blank"; }  // release the WebGL context
  document.removeEventListener("keydown", escClose);
}

function claudePanel(r) {
  return `<div class="card claude">
    <div class="ch"><span class="dot2"></span><b>Claude's read</b><span class="mtag">${esc(r.claude_model||"Claude")} · ${r.cached?"cached":"live"}</span></div>
    <div class="body">${mdToHtml(r.claude_read)}</div></div>`;
}

// ---------------- result chat (grounded conversation about THIS result) ----------------
// A multi-turn conversation on top of Claude's read: the same interpretation agent, but interactive
// and scoped to the result on screen. Answers are grounded in the real numbers via the triage tools.
let CHAT = {label: null, sample_id: null, messages: [], busy: false, error: null};

function chatSuggestions(r) {
  const q = [];
  const lead = r.drugs.find(d => (d.bucket === "robust" || d.bucket === "improved") &&
                                 d.evidence && d.evidence.pathway && d.evidence.pathway.status === "plausible");
  q.push("Which drugs should I avoid here, and why?");
  q.push(lead ? `Is ${lead.drug} actually worth testing?` : "Which robust hits are likely just docking artifacts?");
  q.push("What does a 95% credible interval mean for these calls?");
  return q;
}

function chatPanel(r) {
  const sugg = chatSuggestions(r).map(s =>
    `<button class="chat-sugg" data-q="${esc(s)}">${esc(s)}</button>`).join("");
  return `<div class="card chat" id="chatCard">
    <div class="ch"><span class="dot2"></span><b>Ask about this result</b>
      <span class="mtag">Claude · live</span></div>
    <div class="chat-scroll" id="chatMsgs">
      <div class="chat-empty">
        <p>Go beyond the read: ask why a drug is a lead, what a number means, or whether a hit is worth the bench.</p>
        <div class="chat-suggs">${sugg}</div>
      </div>
    </div>
    <form class="chat-inrow" id="chatForm" autocomplete="off">
      <input id="chatInput" placeholder="Ask about ${esc(r.label)}…" aria-label="Ask about this result">
      <button class="chat-send" id="chatSend" type="submit" aria-label="Send">${chatSendIcon}</button>
    </form>
    <div class="chat-foot">Grounded in the numbers above via the triage tools. A first-pass research aid, not treatment advice.</div>
  </div>`;
}

const chatSendIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4z"/></svg>`;

function renderChat() {
  const box = $("chatMsgs"); if (!box) return;
  if (!CHAT.messages.length && !CHAT.busy && !CHAT.error) return;  // keep the empty/suggestions state
  let html = "";
  for (const m of CHAT.messages) {
    html += m.role === "user"
      ? `<div class="cm user"><div class="cm-b">${esc(m.content)}</div></div>`
      : `<div class="cm bot"><span class="cm-ic">${SPARK}</span><div class="cm-b">${mdToHtml(m.content)}</div></div>`;
  }
  if (CHAT.busy) html += `<div class="cm bot"><span class="cm-ic">${SPARK}</span><div class="cm-b"><span class="cm-typing"><i></i><i></i><i></i></span></div></div>`;
  if (CHAT.error) html += `<div class="cm bot"><span class="cm-ic err">${IC_WARN}</span><div class="cm-b cm-err">${esc(CHAT.error)}</div></div>`;
  box.innerHTML = html;
  box.scrollTop = box.scrollHeight;
}

async function sendChat(text) {
  text = (text || "").trim();
  if (!text || CHAT.busy) return;
  CHAT.error = null;
  CHAT.messages.push({role: "user", content: text});
  CHAT.busy = true;
  const inp = $("chatInput"); if (inp) inp.value = "";
  renderChat();
  try {
    const res = await (await api("/api/chat", {method: "POST",
      body: JSON.stringify({label: CHAT.label, sample_id: CHAT.sample_id, messages: CHAT.messages})})).json();
    if (res.error) { CHAT.messages.pop(); CHAT.error = res.message || "Chat is unavailable right now."; }
    else { CHAT.messages.push({role: "assistant", content: res.reply}); }
  } catch (e) {
    CHAT.messages.pop();
    CHAT.error = "Couldn't reach the chat service. Is the server running?";
  }
  CHAT.busy = false;
  renderChat();
}

function wireChat() {
  const form = $("chatForm"); if (!form) return;
  form.onsubmit = e => { e.preventDefault(); sendChat($("chatInput").value); };
  document.querySelectorAll(".chat-sugg").forEach(b => b.onclick = () => sendChat(b.dataset.q));
}

// ---------- orthogonal evidence axes (pathway grounding + DepMap dependency) ----------
// A shared teal->amber->grey "belief" ramp answers "should we believe this docking hit?" using
// data the docking never sees. Triple-encoded: color + dot shape + a distinct word per state.
const OE = {
  pathway: {
    aligned:      {cls:"lvl-hi",  lab:"on-path",  full:"Pathway grounding: aligned — the drug's own target is the tumor's driver gene"},
    plausible:    {cls:"lvl-mid", lab:"in-class", full:"Pathway grounding: plausible — same enzyme class / signaling pathway as the driver, not the drug's designed target"},
    "off-pathway":{cls:"lvl-lo",  lab:"off-path", full:"Pathway grounding: off-pathway — target unrelated to the driver's biology, so a strong docking score is likely an artifact"},
  },
  depmap: {
    dependency:{cls:"lvl-hi",  lab:"lung dep", full:"DepMap dependency: the target is a selective lung-adenocarcinoma dependency — the cancer needs it (CRISPR essentiality)"},
    weak:      {cls:"lvl-mid", lab:"weak dep", full:"DepMap dependency: an oncogenic target, but not a lung-adenocarcinoma-selective dependency"},
    none:      {cls:"lvl-lo",  lab:"no dep",   full:"DepMap dependency: a non-oncology target the cancer does not depend on"},
  },
};
const oePill = o => `<span class="oe ${o.cls}" aria-label="${esc(o.full)}"><span class="oe-dot"></span>${o.lab}</span>`;
function oeParts(d) {
  const e = d.evidence; if (!e) return null;
  const p = OE.pathway[e.pathway && e.pathway.status], k = OE.depmap[e.depmap && e.depmap.status];
  return (p && k) ? {p, k, e} : null;
}
function oeCell(d) {
  const o = oeParts(d);
  return o ? `<td class="oe-cell">${oePill(o.p)}${oePill(o.k)}</td>` : `<td class="oe-cell"></td>`;
}
function oeTip(d) {
  const e = d.evidence; if (!e || !e.pathway || !e.depmap) return "";
  const tgt = (e.targets_display && e.targets_display.length) ? e.targets_display.join(", ") : "no annotated human target";
  return `<br><b>Target:</b> ${esc(tgt)}${e.target_class ? ` (${esc(e.target_class)})` : ""}.`
       + `<br><b>Pathway:</b> ${esc(e.pathway.status)} &mdash; ${esc(e.pathway.detail)}.`
       + `<br><b>DepMap:</b> ${esc(e.depmap.status)} &mdash; ${esc(e.depmap.detail)}.`;
}
const OE_NOTE = {
  "aligned|dependency":  "On-target and a validated lung dependency: the docking gain is corroborated by the biology.",
  "plausible|weak":      "In-class kinase cross-binding is plausible, but its own targets aren't lung dependencies: this lead rests on the structural fit, not its target biology.",
  "plausible|dependency":"Same pathway and a real lung dependency: a serious lead.",
  "plausible|none":      "Same enzyme class as the driver, but no dependency signal: a weak structural lead.",
  "off-pathway|none":    "Off the driver's pathway and not a dependency: most likely a docking artifact.",
  "off-pathway|weak":    "Off the driver's pathway; the target isn't a lung dependency: likely a docking artifact.",
};
function oeNote(d) {
  const e = d.evidence; if (!e || !e.pathway || !e.depmap) return "";
  return OE_NOTE[`${e.pathway.status}|${e.depmap.status}`] || `Pathway ${e.pathway.status}; DepMap dependency ${e.depmap.status}.`;
}
function oeStrip(rows) {
  if (!rows.length) return "";
  const body = rows.map(d => {
    const o = oeParts(d); if (!o) return "";
    return `<div class="oe-lead"><span class="oe-lead-d">${esc(d.drug)}</span>${oePill(o.p)}${oePill(o.k)}<span class="oe-lead-note">${esc(oeNote(d))}</span></div>`;
  }).join("");
  return `<div class="card oe-strip"><div class="oe-strip-h"><span class="oe-strip-t">Orthogonal evidence</span><span class="oe-strip-s">does the biology corroborate the docking score? &mdash; two axes the docking never sees</span></div>${body}</div>`;
}

function evidence(r) {
  const legend = `<div class="legend">
    <span class="it"><span class="sw" style="background:var(--c-weakened)"></span>Weakened</span>
    <span class="it"><span class="sw" style="background:var(--c-robust)"></span>Robust</span>
    <span class="it"><span class="sw" style="background:var(--c-improved)"></span>Improved</span>
    <span class="it"><span class="sw" style="background:var(--c-nonbinder)"></span>Non-binder</span>
    <span class="it"><span class="sw sw-band"></span>within &plusmn;1 kcal/mol &mdash; negligible</span>
    <span class="leg-sep"></span>
    <span class="it"><span class="oe-dot" style="color:var(--brand-ink);background:currentColor"></span>corroborates</span>
    <span class="it"><span class="oe-dot" style="color:var(--amber);background:linear-gradient(90deg,currentColor 50%,transparent 50%)"></span>partial</span>
    <span class="it"><span class="oe-dot" style="color:var(--muted)"></span>off-mechanism</span>
    <span class="it" style="color:var(--muted)">(top: pathway &middot; bottom: DepMap)</span>
    <span class="ev-axis">&larr; binds better&nbsp;&middot;&nbsp;0 = no change&nbsp;&middot;&nbsp;worse (resistance) &rarr;</span></div>`;
  let html = legend;
  for (const bucket of ORDER) {
    const rows = r.drugs.filter(d => d.bucket === bucket);
    if (!rows.length) continue;
    const m = BMETA[bucket];
    html += `<div class="bucket b-${bucket}"><div class="bhead"><span class="sw" style="background:var(${m.cvar})"></span>${m.label} <span class="desc">${m.desc}</span><span class="ct">${rows.length} drug${rows.length>1?"s":""}</span></div><table class="rows"><tbody>`;
    for (const d of rows) {
      const ds = (d.delta>=0?"+":"") + d.delta.toFixed(2);
      const bench = d.category === "known_answer" ? `<span class="bench">benchmark</span>` : "";
      html += `<tr data-tip="<b>${esc(d.drug)}</b>: ${esc(d.reason)}.<br>WT ${d.affinity_wt}, mutant ${d.affinity_mut} kcal/mol · Δ ${ds} [95% CI ${d.ci95[0].toFixed(2)}, ${d.ci95[1].toFixed(2)}] · ${d.confidence} confidence.${oeTip(d)}"><td style="width:150px"><span class="dname">${esc(d.drug)}${bench}</span><span class="cat">${esc(catLabel(d.category))}</span></td>${oeCell(d)}<td>${ciBar(d)}</td><td class="num" style="width:54px;color:var(${BMETA[d.bucket].cvar})">${ds}</td><td class="ci-txt" style="width:96px">[${d.ci95[0].toFixed(2)}, ${d.ci95[1].toFixed(2)}]</td>${confCell(d)}</tr>`;
    }
    html += `</tbody></table></div>`;
  }
  return html;
}
function ciBar(d) {
  const c = `var(${BMETA[d.bucket].cvar})`;
  const lo = xPct(d.ci95[0]), hi = xPct(d.ci95[1]), dd = xPct(d.delta), z = xPct(0);
  const nlo = xPct(-DMEAN), nhi = xPct(DMEAN);   // ±1 kcal/mol "negligible" band, shared across every row
  let over = "";
  if (d.delta > DMAX) over = `<span class="chev-o" style="left:calc(100% - 11px);color:${c}">›</span>`;
  if (d.delta < DMIN) over = `<span class="chev-o" style="left:2px;color:${c}">‹</span>`;
  return `<div class="track"><span class="band" style="left:${nlo}%;width:${nhi - nlo}%"></span>`
    + `<span class="zero" style="left:${z}%"></span>`
    + `<span class="ci" style="left:${lo}%;width:${Math.max(hi - lo, 0.7)}%;background:${c}"></span>`
    + `<span class="dot" style="left:${dd}%;background:${c}"></span>${over}</div>`;
}
// confidence, inverted: high is the quiet default (a small neutral dot); only medium/low earns a visible flag
function confCell(d) {
  if (d.confidence === "high") return `<td class="conf-cell"><span class="conf-ok" aria-label="high confidence"></span></td>`;
  return `<td class="conf-cell"><span class="conf-flag ${esc(d.confidence)}">${IC_WARN}${esc(d.confidence)}</span></td>`;
}

// ---------------- gpu gate / errors ----------------
function renderGpuGate(res) {
  $("workspace").innerHTML = `
    <div class="notice gpu">
      <h3>This genotype needs a real docking run</h3>
      <p>${esc(res.message || "It isn't precomputed, so it has to be docked on a GPU.")} The docking is the only GPU-heavy step, so bring your own GPU and MutationRx runs the pipeline on it, then triages the result here.</p>
      <div class="row">
        <input id="gpuEndpoint" placeholder="RunPod endpoint id" aria-label="RunPod endpoint id" style="max-width:200px">
        <input id="gpuKey" placeholder="RunPod API key" aria-label="RunPod API key">
        <button class="connect" id="gpuConnect">Connect GPU</button>
      </div>
      <div class="secure" id="gpuMsg">Your key is sent to <b>your</b> MutationRx server only, used to dispatch the job, and never stored in the page or committed. Deploy the docking endpoint per <code>docs/bring_your_own_tumor.md</code>.</div>
    </div>`;
  $("gpuConnect").onclick = connectGpu;
}

async function connectGpu() {
  const key = $("gpuKey").value.trim(), endpoint = $("gpuEndpoint").value.trim();
  const msg = $("gpuMsg"), btn = $("gpuConnect");
  btn.disabled = true; btn.textContent = "Connecting…";
  try {
    const res = await (await api("/api/gpu/connect", {method: "POST", body: JSON.stringify({key, endpoint})})).json();
    if (res.error) { msg.innerHTML = esc(res.error); btn.disabled = false; btn.textContent = "Connect GPU"; return; }
    refreshUsage();
    msg.innerHTML = `GPU connected (<b>${esc(res.mode)}</b>). Re-running your genotype…`;
    if (lastReq) submit(lastReq, lastDisplay);
  } catch (e) {
    msg.innerHTML = "Couldn't reach the server to connect the GPU."; btn.disabled = false; btn.textContent = "Connect GPU";
  }
}
function renderError(msg, known) {
  $("workspace").innerHTML = `<div class="notice err"><h3>Couldn't triage that</h3><p>${esc(msg)}</p>${known?`<p>Known genotypes: ${known.map(esc).join(", ")}</p>`:""}</div>`;
}

// ---------------- markdown + tooltips ----------------
function mdToHtml(md) {
  const lines = md.split("\n"); let html = "", inList = false;
  const inline = s => esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  for (let ln of lines) {
    ln = ln.replace(/\r$/, "");
    if (/^#{1,6}\s/.test(ln)) { if (inList) {html += "</ul>"; inList = false;} html += "<h4>" + inline(ln.replace(/^#+\s/, "")) + "</h4>"; }
    else if (/^\s*[-*]\s/.test(ln)) { if (!inList) {html += "<ul>"; inList = true;} html += "<li>" + inline(ln.replace(/^\s*[-*]\s/, "")) + "</li>"; }
    else if (ln.trim() === "") { if (inList) {html += "</ul>"; inList = false;} }
    else { if (inList) {html += "</ul>"; inList = false;} html += "<p>" + inline(ln) + "</p>"; }
  }
  if (inList) html += "</ul>";
  return html;
}
function attachTips() {
  const tip = $("tip");
  document.querySelectorAll("tr[data-tip]").forEach(tr => {
    tr.onmousemove = e => { tip.innerHTML = tr.dataset.tip; tip.style.opacity = "1";
      let x = e.clientX + 14, y = e.clientY + 16;
      if (x + 312 > innerWidth) x = e.clientX - 300;
      if (y + 90 > innerHeight) y = e.clientY - 90;
      tip.style.left = x + "px"; tip.style.top = y + "px"; };
    tr.onmouseleave = () => tip.style.opacity = "0";
  });
}
