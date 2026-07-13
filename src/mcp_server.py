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
import tcga  # noqa: E402

mcp = FastMCP("onco-triage")


@mcp.tool()
def triage_tumor(mutation: str) -> str:
    """Get the drug triage for a specific tumor mutation.

    Returns each drug classified into weakened / robust / improved / non-binder, with wild-type and
    mutant binding affinities (kcal/mol, more negative = stronger), the wild-type-vs-mutant delta,
    its 95% credible interval, and a confidence flag. Each drug also carries an `evidence` object with
    two orthogonal axes computed from data the docking never sees: `evidence.pathway.status`
    (aligned / plausible / off-pathway — is the drug's real target in the driver's pathway?) and
    `evidence.depmap.status` (dependency / weak / none — is that target a lung-adenocarcinoma
    dependency in DepMap?). Cite them when judging plausibility. May include a 'note' field carrying an
    important caveat for this mutation — always surface it.

    Interpretation guardrails (apply these when explaining the result to the user):
    - Affinity is a docking PROXY, not a measured Kd and not clinical efficacy.
    - A credible interval that excludes zero is a confident call; one that straddles zero is not.
    - YOUR KEY JOB is to separate real signal from docking artifact. Docking will score drugs that have
      no business binding this target. For each notable 'robust'/repurposing hit, weigh mechanistic
      plausibility from what you know: is this drug's real mechanism related to this target, or is the
      score coincidental? Many old drugs (thalidomide, propranolol, statins, metformin) have genuine
      cancer-repurposing literature but via mechanisms UNRELATED to the docked target — that does not
      validate the docking hit. Use the per-drug `evidence` axes to ground this: off-pathway + no
      dependency on both axes is a strong artifact signal; aligned + a real dependency corroborates.
      Sort hits into "believe this / worth an assay" vs "likely artifact / skip", with a reason.
      Flagging an artifact is as useful as endorsing a hit.
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


@mcp.tool()
def list_tcga_tumors() -> str:
    """List the cached real, de-identified TCGA Lung Adenocarcinoma tumors available to triage.

    Each entry has a sample_id (a de-identified TCGA barcode), a one-line descriptor, and the somatic
    mutation count. Pass a sample_id to triage_tcga_profile to run the tool on that real tumor.
    """
    return json.dumps(tcga.list_samples())


@mcp.tool()
def triage_tcga_profile(sample_id: str) -> str:
    """Triage a REAL, de-identified TCGA tumor: map its somatic mutations onto the in-scope targets
    and triage its primary genotype.

    Returns the sample id and source, the total somatic-mutation count, which in-scope variants the
    tumor actually carries, the matched genotype(s) (a tumor carrying BOTH L858R and T790M is matched
    as the resistant DOUBLE mutant — a genuine acquired-resistance genotype), and the full triage
    table for the primary genotype.

    Interpretation guardrails (surface these to the user):
    - This is a real de-identified patient tumor, open-access from TCGA. It is pre-wet-lab triage,
      never treatment advice.
    - A real tumor carries many mutations; the panel only covers EGFR L858R/T790M (and their double)
      and KRAS G12C. Most of the tumor is out of scope — say so.
    - The same affinity/CI/covalent caveats as triage_tumor apply to the triage table returned here.

    Args:
        sample_id: a cached TCGA barcode, e.g. "TCGA-L9-A50W-01". Call list_tcga_tumors first.
    """
    try:
        return json.dumps(tcga.triage_sample(sample_id))
    except (KeyError, FileNotFoundError) as e:
        return json.dumps({"error": str(e),
                           "available_tumors": [s["sample_id"] for s in tcga.list_samples()]})


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
