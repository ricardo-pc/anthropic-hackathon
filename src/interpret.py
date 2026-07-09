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

MODEL = "claude-opus-4-8"

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

HOW TO ANSWER
- Call the tools to get real numbers; never invent affinities, deltas, or buckets.
- Lead with the plain-English answer the user actually asked for (which to avoid / which are safe),
  then support it with the specific drugs, their deltas, and the credible intervals.
- Quantify uncertainty honestly: a credible interval that excludes zero is a confident call; one that
  straddles zero is not. Say which.
- Explain every technical term in plain words. Someone with no biology background should follow you.

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
    interval, and a confidence flag. May include a 'note' with an important caveat for this mutation.

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


def main():
    question = " ".join(sys.argv[1:]).strip() or (
        "I have a lung tumor with EGFR L858R+T790M. Which drugs should I avoid, "
        "and are there any safe repurposing bets worth a look?"
    )
    print(f"\n\033[1mQ:\033[0m {question}\n" + "-" * 72)

    client = anthropic.Anthropic()
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=SYSTEM,
        tools=[triage_tumor, list_available_mutations, mutations_for_cancer],
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
