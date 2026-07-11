#!/usr/bin/env python3
"""
Pre-generate Claude's plain-English triage reads and cache them for the offline dashboard.

The dashboard's "Claude's read" panel shows Claude reasoning over the real numbers. To keep the demo
fully offline (and free of a live API call mid-recording), this script runs the same interpretation
agent as src/interpret.py once per demo case and saves the final answers to data/claude_reads.json.
The dashboard build (src/build_dashboard.py) embeds whatever is in that file.

Needs credentials (ANTHROPIC_API_KEY or an `ant auth login` profile), just like interpret.py. Use
TRIAGE_MODEL=claude-opus-4-8 for the recording-quality phrasing:
    TRIAGE_MODEL=claude-opus-4-8 python src/cache_claude_reads.py

Reads are keyed by mutation label (e.g. "EGFR L858R+T790M") and by TCGA sample id
(e.g. "TCGA-L9-A50W-01"); the dashboard prefers the sample-specific read when a tumor is loaded.
Existing reads are preserved unless --overwrite is passed, so you can regenerate one at a time.
"""
import json
import os
import sys

import anthropic

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import interpret  # noqa: E402  (reuse its SYSTEM prompt, tools, and model)
import tcga  # noqa: E402
import triage  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{HERE}/data/claude_reads.json"

TOOLS = [interpret.triage_tumor, interpret.list_available_mutations,
         interpret.mutations_for_cancer, interpret.list_tcga_tumors, interpret.triage_tcga_profile]


def _ask(client, question):
    """Run the interpretation agent to completion and return its final plain-English text."""
    runner = client.beta.messages.tool_runner(
        model=interpret.MODEL, max_tokens=16000, thinking={"type": "adaptive"},
        system=interpret.SYSTEM, tools=TOOLS,
        messages=[{"role": "user", "content": question}],
    )
    text = []
    for message in runner:
        for block in message.content:
            if block.type == "text" and block.text.strip():
                text.append(block.text.strip())
    return "\n\n".join(text)


def _cases():
    """The demo cases to pre-generate: every in-scope mutation, plus each real TCGA tumor."""
    for label in triage.list_mutations():
        yield label, (f"Give your triage verdict for a tumor with {label}: which drugs to avoid, "
                      f"which still bind, and any repurposing bets worth a wet-lab look. Be concise "
                      f"but keep the specific drugs, deltas, credible intervals, and caveats.")
    try:
        for s in tcga.list_samples():
            sid = s["sample_id"]
            yield sid, (f"Point at the real TCGA tumor {sid}. Tell me what this tumor is, which drugs "
                        f"to avoid, and any safe repurposing bets. Be concise but complete, and be "
                        f"honest about what's in scope.")
    except FileNotFoundError:
        pass


def main():
    overwrite = "--overwrite" in sys.argv
    blob = {"__model": None, "reads": {}}
    if os.path.exists(OUT):
        with open(OUT) as f:
            blob = json.load(f)
    blob.setdefault("reads", {})
    blob["__model"] = _model_label(interpret.MODEL)

    try:
        client = anthropic.Anthropic()
        for key, question in _cases():
            if key in blob["reads"] and not overwrite:
                print(f"  skip (cached): {key}")
                continue
            print(f"  generating: {key} …")
            blob["reads"][key] = _ask(client, question)
    except anthropic.AuthenticationError:
        sys.exit("\nNo Anthropic credentials. Set ANTHROPIC_API_KEY or run `ant auth login`, then "
                 "re-run. (Existing cached reads were left untouched.)")

    with open(OUT, "w") as f:
        json.dump(blob, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {OUT} — {len(blob['reads'])} reads (model: {blob['__model']}).")
    print("Now rebuild the dashboard: python src/build_dashboard.py")


def _model_label(model_id):
    return {"claude-opus-4-8": "Claude Opus 4.8", "claude-sonnet-5": "Claude Sonnet 5"}.get(
        model_id, model_id)


if __name__ == "__main__":
    main()
