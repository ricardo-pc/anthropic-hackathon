#!/usr/bin/env python3
"""
Result chat — a grounded, per-result conversation layer on top of Claude's read.

Reuses the SAME interpretation agent as src/interpret.py (its SYSTEM prompt, its triage tools, its
honesty guardrails), but as a multi-turn conversation scoped to the result the user is looking at.
The user can go beyond the one-shot "Claude's read": ask why a drug is a lead, what a credible
interval means, whether an artifact is worth testing, and Claude answers over the REAL numbers by
calling the triage tools — never inventing affinities.

Stateless: the client resends the short conversation each turn. Non-streaming (a spinner in the UI);
each answer is a full tool-using turn. Needs credentials (ANTHROPIC_API_KEY or an `ant auth login`
profile) at RUNTIME, exactly like interpret.py — the server degrades gracefully to a clear message
when none is configured, and the cached triage results stay fully usable without it.
"""
import os
import sys

import anthropic

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
import interpret  # noqa: E402 — reuse SYSTEM prompt + triage tools

# Chat defaults to Sonnet 5 (an interactive back-and-forth makes many calls; Sonnet is fast, cheap,
# and squarely capable here). Override with CHAT_MODEL, or TRIAGE_MODEL to match the read.
CHAT_MODEL = os.environ.get("CHAT_MODEL") or os.environ.get("TRIAGE_MODEL") or "claude-sonnet-5"

CHAT_TOOLS = [interpret.triage_tumor, interpret.list_available_mutations,
              interpret.mutations_for_cancer, interpret.list_tcga_tumors, interpret.triage_tcga_profile]

MAX_TURNS = 16          # user+assistant messages kept per conversation (older ones are dropped)
MAX_CHARS = 2000        # per user message


def _scoped_system(label, sample_id):
    ctx = [interpret.SYSTEM,
           "\n\nCURRENT VIEW",
           f"The user is looking at the triage result for {label}."]
    if sample_id:
        ctx.append(f"This is the real, de-identified TCGA tumor {sample_id}; use triage_tcga_profile "
                   f"for its context.")
    ctx.append(
        "Answer their questions about THIS result. Call triage_tumor (or triage_tcga_profile) to "
        "ground every specific claim in the real affinities, deltas, credible intervals, and the "
        "per-drug evidence axes (pathway grounding + DepMap dependency) — never invent a number. "
        "This is a conversation, not a report: reply in a few clear sentences, lead with the direct "
        "answer, and only go long when they ask for depth. All the honesty guardrails above still apply "
        "(docking is a proxy, repurposing hits are hypotheses, covalent mechanisms are a blind spot).")
    return "\n".join(ctx)


def sanitize(messages):
    """Keep only well-formed user/assistant text turns, trim length, cap history."""
    clean = []
    for m in messages or []:
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            clean.append({"role": role, "content": content.strip()[:MAX_CHARS]})
    clean = clean[-MAX_TURNS:]
    # a valid exchange must end with a user turn
    if not clean or clean[-1]["role"] != "user":
        raise ValueError("the conversation must end with a user message")
    return clean


def answer(label, sample_id, messages):
    """Run one grounded chat turn; returns the assistant's plain-English reply text.

    Raises anthropic.AuthenticationError when no credentials are configured (the caller surfaces a
    friendly 'set an API key' message), and ValueError for a malformed conversation.
    """
    msgs = sanitize(messages)
    client = anthropic.Anthropic()
    runner = client.beta.messages.tool_runner(
        model=CHAT_MODEL, max_tokens=8000, thinking={"type": "adaptive"},
        system=_scoped_system(label, sample_id), tools=CHAT_TOOLS, messages=msgs,
    )
    out = []
    for message in runner:
        for block in message.content:
            if block.type == "text" and block.text.strip():
                out.append(block.text.strip())
    return "\n\n".join(out) or "…"
