#!/usr/bin/env python3
"""
MCP server — exposes the triage engine as tools so Claude (inside Claude Code or Claude Desktop)
can call them live. This is the "Claude runs inside the product" surface: the user talks to Claude
in plain English, Claude calls these tools, and reasons over the real docking+stats results.

Same triage data as the standalone agent (src/interpret.py); different delivery — here the host
(Claude Code/Desktop) is the reasoning client, and this server just provides the grounded tools.

Requires Python 3.10+ and the `mcp` package (pip install "mcp[cli]"). Runs over stdio; register it
with a host via .mcp.json (Claude Code) or claude_desktop_config.json (Claude Desktop) — see README.
"""
import json
import os
import sys

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import triage  # noqa: E402

mcp = FastMCP("onco-triage")


@mcp.tool()
def triage_tumor(mutation: str) -> str:
    """Get the drug triage for a specific tumor mutation.

    Returns each drug classified into weakened / robust / improved / non-binder, with wild-type and
    mutant binding affinities (kcal/mol, more negative = stronger), the wild-type-vs-mutant delta,
    its 95% credible interval, and a confidence flag. May include a 'note' field carrying an important
    caveat for this mutation — always surface it.

    Interpretation guardrails (apply these when explaining the result to the user):
    - Affinity is a docking PROXY, not a measured Kd and not clinical efficacy.
    - A credible interval that excludes zero is a confident call; one that straddles zero is not.
    - 'robust' repurposing candidates are HYPOTHESES for wet-lab follow-up, never discoveries.
    - Heed the 'note': for KRAS G12C, non-covalent docking cannot capture the covalent mechanism, so
      results for the covalent G12C drugs (sotorasib/adagrasib/divarasib) are unreliable in either
      direction — say so rather than reading them as real signals.

    Args:
        mutation: exact mutation label, e.g. "EGFR L858R+T790M", "EGFR T790M", or "KRAS G12C".
                  Call list_available_mutations first if unsure of the exact spelling.
    """
    try:
        return json.dumps(triage.triage(mutation))
    except KeyError:
        return json.dumps({"error": "unknown mutation", "known_mutations": triage.list_mutations()})


@mcp.tool()
def list_available_mutations() -> str:
    """List every tumor mutation the tool has docking results for (exact labels for triage_tumor)."""
    return json.dumps(triage.list_mutations())


@mcp.tool()
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
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
