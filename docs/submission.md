# MutationRx — submission notes

*Built with Claude: Life Sciences (Anthropic × Gladstone), Build track.*

## The named user

**A translational-oncology researcher studying acquired drug resistance** — not a clinician. Their
recurring, concrete task: when a resistance mutation shows up in a model or a patient tumor, decide
**which of many candidate compounds to put through expensive cell-based assays** — and whether any
cheap, already-approved drug is worth testing. They have too many candidates and too little bench
budget. They need a fast, rigorous, honest shortlist.

## Why it matters (the anchor)

Targeted cancer drugs fail by **resistance**: the tumor mutates, the protein changes shape, the drug
stops binding. And mutation can also make an *old, cheap* drug newly relevant — the canonical case is
**aspirin in PIK3CA-mutant colorectal cancer** (Liao et al., *NEJM* 2012): aspirin was linked to far
better survival, but *only* when the tumor carried a PIK3CA mutation. That is the whole thesis in one
result — **a common drug can be a targeted therapy for a mutation-defined subset.** Finding the next
one means triaging computational hits you can actually trust. *(Aspirin's effect there runs through
PI3K/COX signaling, not clean target docking — so it's our motivation, not a docking claim.)*

## What MutationRx is (and the honest-novelty framing)

Docking pipelines already rank drugs — but they score compounds that have **no real business binding
the target**, and a researcher can't tell signal from artifact. That gap is the product:

> **The docking finds candidates. Claude decides which to believe.**

For a tumor's driver mutation, MutationRx docks a 62-drug panel (27 curated plus a 35-drug unbiased
approved-drug library) against the **wild-type and mutant**
structure, rescores with gnina, and bootstraps a **95% credible interval** on each wild-type→mutant
shift. Then **Claude reviews every hit for mechanistic plausibility** — separating believable leads
from coincidental docking scores (a beta-blocker "binding" EGFR is almost certainly an artifact; a
drug whose real mechanism fits the target is worth the assay). No single piece is novel; the honest,
end-to-end **triage-with-a-reviewer** — usable by a non-computational biologist — is the tool they're
missing.

## What makes it credible (not just a demo)

- **Reproduces known biology on unseen real data:** run on a genuine, de-identified TCGA lung tumor
  carrying EGFR L858R+T790M, it independently recovers the clinic — erlotinib/gefitinib fail,
  **osimertinib holds** — from docking alone.
- **Honest to a fault:** every call carries uncertainty; the KRAS covalent limitation is shown, not
  hidden; repurposing hits are flagged as hypotheses, and Claude actively deprioritizes the artifacts.
- **Claude is essential, not decorative:** remove the reviewer and you're back to an untrustworthy hit
  list. The mechanistic judgment is the value.
- **The judgment is grounded, not asserted:** every drug carries two orthogonal evidence axes the
  docking never sees — **pathway grounding** (is the drug's established target in the driver's pathway /
  enzyme class?) and **DepMap dependency** (is that target a gene lung adenocarcinoma actually needs, from
  CRISPR essentiality?). On-target inhibitors corroborate on both (teal/teal); the statin, antidepressant,
  and antibiotic artifacts fail both (grey/grey); **imatinib** lands amber/amber — in-class but not a lung
  dependency, so the lead honestly rests on the structural cross-binding, not on its own targets being a
  known vulnerability. This turns the artifact/real-lead call from "trust Claude's parametric knowledge"
  into an auditable, cited read (`data/gene_kb.json`, `data/drug_targets.json`;
  `python analysis/evidence_axes.py`). Both the in-product Claude review and the MCP tools receive these
  axes and cite them.

## Why it outlasts the week

- **Config-driven registry** (`config/mutations.json`) — add a genotype with no code changes.
- **Bring your own tumor + GPU** — dock any point mutation on your own hardware; the tool ingests and
  triages it (`docs/bring_your_own_tumor.md`).
- **Meets researchers where they work** — a web app, a CLI, and an **MCP server** so Claude Code /
  Desktop can call the triage tools directly.

A real lab can point this at their target and keep using it. That is the "beyond the bench, outlasts
the week" bar.

## The 100–200 word summary (submission)

> When a tumor mutates, the targeted drug that was working stops — the protein changes shape and the
> drug no longer binds. Deciding what to try next, or whether a cheap approved drug could be
> repurposed, means slow, expensive wet-lab screening. Computational docking can rank candidates, but
> it scores drugs that don't really bind, and a researcher can't tell signal from artifact.
>
> MutationRx is a resistance-aware triage instrument. For a tumor's driver mutation it docks a panel of
> 62 approved drugs against the wild-type and mutant protein and quantifies each shift with credible
> intervals from replicate runs — then Claude reviews every hit for mechanistic plausibility,
> separating believable leads from coincidental docking artifacts. It runs on real, de-identified
> TCGA patient tumors, reproduces known EGFR-resistance biology (osimertinib holds against T790M) on
> tumors it never saw, and extends to any point mutation on your own GPU.
>
> Built with Claude Code. The docking finds candidates; Claude decides which to believe.

## Demo arc (~3 min)

1. **Stakes (Act 0):** the resistance problem, in one human sentence. *(Optional personal anchor.)*
2. **Validation (Act 1):** pick `EGFR L858R+T790M` — watch the pipeline; Claude flags
   erlotinib/gefitinib out, osimertinib holds. "It reproduced the clinic."
3. **Real tumor (Act 2):** load real TCGA tumor `TCGA-L9-A50W-01` — same answer, on a patient tumor
   it never saw.
4. **The differentiator (the memorable moment):** open `EGFR T790M` and scroll to Claude's read. It
   separates the *believable* hit (osimertinib) from the *artifacts* (simvastatin/propranolol —
   deprioritized by mechanism) — and surfaces the one **credible, non-obvious lead: imatinib**, a
   leukemia (CML) drug predicted to *gain* binding on the resistant gatekeeper. Why it's not dismissed
   like the statin: **imatinib is a kinase inhibitor, so docking it against a kinase is legitimate.**
   That contrast — artifact vs. real cross-kinase hypothesis — is the whole thesis in one screen.
5. **The overnight payoff (the climax):** `EGFR C797S` — the mutation that defeats *osimertinib itself*
   — was **modeled and docked overnight, a genotype the tool had never seen.** It did two honest
   things at once: (a) it **flagged its own blind spot** — osimertinib resists C797S via a *covalent*
   mechanism that non-covalent docking can't see (the same limitation as KRAS G12C), so Claude says
   "do not read osimertinib as still-working here"; and (b) it **added a 4th consistent data point to
   the imatinib hypothesis.** A tool that knows where it fails *and* strengthens a real lead, live.
6. **Outlasts the week:** the C797S run *is* the bring-your-own-GPU path in action (model → your GPU →
   ingest → triage). "Any point mutation, your GPU." Close on the honest-novelty line.

## The one credible, non-obvious lead (the hunt result)

Across **all four** EGFR mutants now tested — L858R (Δ −2.65, interval excludes zero), T790M
(Δ −3.98, excludes zero), the double (Δ −2.29), and the freshly-docked C797S (Δ −2.39) — **imatinib**,
the CML leukemia drug, is predicted to *gain* binding on the mutant. Two of the four are individually
significant and the other two lean the same way; said as a bare count, "four for four" is only a sign
test (one-tailed p = 0.06). The rigorous claim is the **pooled** one: **pooling the replicate evidence
across the four mutant structures gives a mean gain of Δ −2.83 kcal/mol with a 95% credible interval of
[−4.68, −1.30] that excludes zero** — and clears the 1 kcal/mol practical-significance floor. That
pooled, quantified consistency is what separates a real signal from a one-off fluke. The contrast makes
it sharper: the *only* other drugs with a significant gain on the double are simvastatin (−0.79) and
metformin (−0.49), both sub-1 kcal/mol and mechanistically unrelated to EGFR. Imatinib is the only
significant gainer that is also above the effect-size floor **and** mechanistically legitimate (a
**kinase inhibitor** docking a kinase), and it is **non-obvious** (nobody uses imatinib for EGFR lung
cancer). Strictly a *hypothesis worth an assay*, not a finding — but exactly the kind of cross-kinase
lead the docking-plus-Claude-review pipeline is built to surface. Reproduce with
`python analysis/imatinib_pooled.py`. (`docs/new_genotypes.md` lists the next genotypes to keep testing it.)
