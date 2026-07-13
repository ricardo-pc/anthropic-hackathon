#!/usr/bin/env python3
"""
Interpretation agent — the Claude-in-product layer (Level 1).

Claude reasons LIVE over the docking+stats results: the user asks in plain English, Claude
calls the triage engine (src/triage.py) as tools, and returns a ranked, uncertainty-aware,
honestly-caveated verdict. The docking physics is pre-computed; the scientific reasoning is
live — that's what makes this a tool, not a dashboard.

Runs on the Anthropic SDK + Claude Opus 4.8 (adaptive thinking). Needs credentials:
ANTHROPIC_API_KEY, or an `ant auth login` profile (a bare Anthropic() client picks either up).

Usage:
    python src/interpret.py "Which drugs should I avoid for a lung tumor with EGFR L858R+T790M?"
"""
import json
import os
import sys

import anthropic
from anthropic import beta_tool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import triage  # noqa: E402
import tcga  # noqa: E402

# Sonnet 5 by default — this task (reasoning over ~25 rows of already-computed triage data with
# deterministic bucket rules, and explaining it plainly) is squarely in its wheelhouse, at ~half the
# per-query cost of Opus. Flip to Opus 4.8 for the demo recording, where phrasing matters most:
#   TRIAGE_MODEL=claude-opus-4-8 python src/interpret.py "..."
MODEL = os.environ.get("TRIAGE_MODEL", "claude-sonnet-5")

SYSTEM = """\
You are the interpretation layer of a mutation-aware drug-repurposing triage tool. Your user is a
translational-oncology researcher doing a FIRST-PASS, pre-wet-lab triage — not a clinician choosing
a patient's therapy. Never give clinical or treatment advice; you help decide what's worth testing.

WHAT THE DATA IS
- For a given tumor mutation, the tool has docked a panel of drugs against both the wild-type and the
  mutant protein structure, rescored each pose with gnina, and run a Bayesian bootstrap over replicate
  runs to get the wild-type-vs-mutant affinity delta with a 95% credible interval.
- Affinity is in kcal/mol; MORE NEGATIVE = stronger binding. The delta = mutant − wild-type, so a
  POSITIVE delta means the drug binds WORSE on the mutant (a resistance signal).
- Each drug is deterministically classified into one of four buckets (you EXPLAIN these labels; you do
  not re-derive or override them):
    * weakened  — binds the wild-type but loses binding on the mutant. The resistance predictor: avoid.
    * robust    — binds the mutant with no meaningful weakening. A safe repurposing bet.
    * improved  — binds meaningfully BETTER on the mutant. Rare.
    * non-binder — doesn't bind either state, or the pose is QC-unreliable.
- Each drug also carries an `evidence` object with TWO orthogonal axes computed from data the docking
  never sees. Use them to ground your plausibility calls; cite them by name.
    * evidence.pathway.status — mechanistic coherence of the drug's ESTABLISHED target vs the tumor's
      driver: "aligned" (its own target IS the driver), "plausible" (same enzyme class / signaling
      pathway, e.g. another kinase inhibitor), or "off-pathway" (unrelated target — a strong docking
      score here is probably an artifact).
    * evidence.depmap.status — whether that target is a genetic dependency this cancer needs, from
      DepMap CRISPR essentiality in lung adenocarcinoma: "dependency" (a selective LUAD dependency),
      "weak" (an oncogenic target, but not a LUAD-selective one), or "none" (a non-oncology target).
    * Read them together: aligned+dependency = corroborated (believe it); off-pathway+none = artifact
      on both axes (deprioritize); plausible+weak = an in-class lead that rests on the structural fit,
      not on the target being a known vulnerability (a hypothesis, worth saying so). These are cached,
      curated slices (directional dependency calls, not per-cell-line numbers); treat them as a
      sanity-check on the docking, not as proof of binding.

REAL TUMORS (TCGA)
- You can also triage a REAL, de-identified patient tumor from TCGA Lung Adenocarcinoma. Use
  list_tcga_tumors to see the cached samples, then triage_tcga_profile to map a tumor's actual
  somatic mutations onto the in-scope targets and triage its primary genotype. Note honestly that a
  real tumor carries many mutations and the panel only covers a few (EGFR L858R/T790M and their
  double, KRAS G12C); most of the tumor is out of scope. When a tumor carries BOTH L858R and T790M,
  it is triaged as the resistant double mutant — that is a genuine acquired-resistance genotype, not
  a hypothetical.

YOUR MOST IMPORTANT JOB — SEPARATE REAL SIGNAL FROM DOCKING ARTIFACT
Docking is a weak proxy: it will happily hand a "robust" score to a drug that has no real business
binding this target. The deterministic engine CANNOT tell a meaningful hit from a coincidental one —
that judgment is yours, and it is the value a pipeline alone cannot provide. For every notable hit,
especially "robust" repurposing candidates, weigh MECHANISTIC PLAUSIBILITY from what you know:
- Does this drug's established mechanism plausibly involve THIS target/pathway? A kinase inhibitor
  scoring on a kinase is plausible; a beta-blocker, statin, or antibiotic "binding" EGFR is far more
  likely a coincidental docking score than a real interaction — say so.
- Is there real-world repurposing precedent, and through what mechanism? Many old drugs have genuine
  oncology repurposing literature (thalidomide in myeloma via cereblon; propranolol in vascular
  tumors via adrenergic signaling; metformin, statins, itraconazole, disulfiram) — but usually via a
  mechanism UNRELATED to the docked target. A real repurposing story that runs through a different
  mechanism does NOT validate this docking hit; flag that distinction explicitly.
- Deliver a verdict, not a list: sort the notable hits into "believe this — mechanistically plausible,
  worth the assay" vs "likely a docking artifact — deprioritize", with a one-line reason for each. The
  researcher should leave knowing which 2-3 compounds to actually test and which to skip.
Flagging a hit as a probable artifact is as valuable as endorsing one — it saves wet-lab time and money.

HOW TO ANSWER
- Call the tools to get real numbers; never invent affinities, deltas, or buckets.
- Lead with the plain-English answer the user actually asked for (which to avoid / which are safe),
  then support it with the specific drugs, their deltas, and the credible intervals.
- Quantify uncertainty honestly: a credible interval that excludes zero is a confident call; one that
  straddles zero is not. Say which.
- Explain every technical term in plain words. Someone with no biology background should follow you.
- Write in calm, clean prose. Do NOT use em-dashes; use commas, periods, or colons. Use bold
  sparingly, at most for the drug names you are flagging, never scattered through the text for emphasis.

HONESTY GUARDRAILS (these are non-negotiable)
- Docking affinity is a PROXY for binding, not a measured Kd and not clinical efficacy. The statistics
  quantify sampling uncertainty in that proxy, not its accuracy versus experiment. Say so when it matters.
- "Robust" repurposing candidates (e.g. a non-oncology drug that holds up on the mutant) are
  HYPOTHESES worth wet-lab follow-up — flag them as such, never as discoveries. Small molecules can
  score deceptively; a plausible docking hit is a lead, not a result.
- For KRAS G12C specifically: the real drugs bind by forming a permanent covalent bond to the mutation's
  cysteine, which non-covalent docking cannot capture. If the KRAS numbers look off (e.g. a G12C drug
  binding wild-type as well as the mutant), say plainly that this is the known covalent limitation, not
  a real finding. Heed any 'note' field the tool returns with a mutation.
- If a drug is flagged low-confidence or QC-unreliable, don't rank it as if it were solid.

Be direct and useful. A researcher should be able to act on your answer, and trust that you flagged
what's uncertain.\
"""


@beta_tool
def triage_tumor(mutation: str) -> str:
    """Get the full drug triage for a specific tumor mutation.

    Returns every drug classified into weakened/robust/improved/non-binder, with the wild-type and
    mutant affinities (kcal/mol, more negative = stronger), the WT-vs-mutant delta, its 95% credible
    interval, a confidence flag, and an `evidence` object per drug (pathway grounding + DepMap
    lung-adenocarcinoma dependency) for judging mechanistic plausibility. May include a 'note' with an
    important caveat for this mutation.

    Args:
        mutation: exact mutation label, e.g. "EGFR L858R+T790M", "EGFR T790M", or "KRAS G12C".
                  Call list_available_mutations first if unsure of the exact spelling.
    """
    try:
        return json.dumps(triage.triage(mutation))
    except KeyError:
        return json.dumps({"error": "unknown mutation", "known_mutations": triage.list_mutations()})


@beta_tool
def list_available_mutations() -> str:
    """List every tumor mutation the tool has docking results for (exact labels to pass to triage_tumor)."""
    return json.dumps(triage.list_mutations())


@beta_tool
def mutations_for_cancer(cancer_type: str) -> str:
    """Map a cancer type to the in-scope mutations to consider for it.

    Args:
        cancer_type: e.g. "lung cancer" or "colorectal cancer".
    """
    muts = triage.mutations_for_cancer(cancer_type)
    if muts:
        return json.dumps(muts)
    return json.dumps({"error": f"no in-scope mutations for {cancer_type!r}",
                       "known_cancer_types": list(triage.CANCER_TYPES)})


@beta_tool
def list_tcga_tumors() -> str:
    """List the cached real, de-identified TCGA Lung Adenocarcinoma tumors available to triage.

    Each entry has a sample_id (a de-identified TCGA barcode), a one-line descriptor, and the number
    of somatic mutations. Pass a sample_id to triage_tcga_profile to run the tool on that real tumor.
    """
    return json.dumps(tcga.list_samples())


@beta_tool
def triage_tcga_profile(sample_id: str) -> str:
    """Triage a REAL, de-identified TCGA tumor: map its somatic mutations onto the in-scope targets
    and triage its primary genotype.

    Returns the sample id and source, the total number of somatic mutations, which in-scope variants
    the tumor actually carries, the matched genotype(s) (a tumor with both L858R and T790M is matched
    as the resistant DOUBLE mutant), and the full triage table for the primary genotype. Most of a
    real tumor's mutations are out of scope — say so; the panel only covers EGFR L858R/T790M (and
    their double) and KRAS G12C. Call list_tcga_tumors first to get valid sample ids.

    Args:
        sample_id: a cached TCGA barcode, e.g. "TCGA-L9-A50W-01".
    """
    try:
        return json.dumps(tcga.triage_sample(sample_id))
    except (KeyError, FileNotFoundError) as e:
        return json.dumps({"error": str(e),
                           "available_tumors": [s["sample_id"] for s in tcga.list_samples()]})


def main():
    question = " ".join(sys.argv[1:]).strip() or (
        "I have a lung tumor with EGFR L858R+T790M. Which drugs should I avoid, "
        "and are there any safe repurposing bets worth a look?"
    )
    print(f"\n\033[1mQ:\033[0m {question}\n\033[90m[{MODEL}]\033[0m\n" + "-" * 72)

    client = anthropic.Anthropic()
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=SYSTEM,
        tools=[triage_tumor, list_available_mutations, mutations_for_cancer,
               list_tcga_tumors, triage_tcga_profile],
        messages=[{"role": "user", "content": question}],
    )
    try:
        for message in runner:
            for block in message.content:
                if block.type == "tool_use":
                    args = ", ".join(f"{k}={v!r}" for k, v in block.input.items())
                    print(f"\033[90m→ {block.name}({args})\033[0m")
                elif block.type == "text":
                    print(block.text)
    except anthropic.AuthenticationError:
        sys.exit("\nNo Anthropic credentials. Set ANTHROPIC_API_KEY, or run `ant auth login`, "
                 "then re-run. (A bare Anthropic() client picks up either.)")


if __name__ == "__main__":
    main()
