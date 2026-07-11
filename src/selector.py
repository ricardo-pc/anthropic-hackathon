#!/usr/bin/env python3
"""
Cancer-type -> mutation selector (Part B) — the friendly front door.

Instead of having to know the exact mutation label, start from the cancer type: pick "lung cancer",
see the in-scope mutations for it, pick one, and get the triage leaderboard. This is pure navigation
over the existing engine (triage.CANCER_TYPES + triage.triage) — no new science.

Three ways to run it:
  python src/selector.py                                   # interactive menus
  python src/selector.py "lung cancer"                     # list that cancer's mutations, then prompt
  python src/selector.py "lung cancer" "EGFR L858R+T790M"  # jump straight to the triage (scriptable)

The scriptable form matters for the demo: the exact path can be typed once and replayed on camera
with zero menu fumbling.

(Named selector.py, not select.py, on purpose: a module named 'select' would shadow the standard
library's `select` module for anything else importing it while src/ is on sys.path.)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import triage  # noqa: E402


def _choose(title, options):
    """Print a numbered menu and return the chosen option, or None for quit/back.

    Accepts a number, or the option's name typed directly (case-insensitive). 'q'/empty backs out.
    """
    print(f"\n{title}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}) {opt}")
    while True:
        try:
            raw = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if raw.lower() in ("", "q", "quit", "exit", "b", "back"):
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        match = next((o for o in options if raw.lower() == o.lower()), None)
        if match:
            return match
        print(f"  (enter 1-{len(options)}, an option name, or 'q' to go back)")


def _resolve(value, options, kind):
    """Match a passed-in string against the valid options (case-insensitive). None if no match."""
    match = next((o for o in options if value.lower() == o.lower()), None)
    if not match:
        print(f"  {value!r} is not a known {kind}. Options: {options}")
    return match


def interactive():
    """Loop: pick a cancer type, pick one of its mutations, show the triage, repeat."""
    cancers = list(triage.CANCER_TYPES)
    print("Mutation-aware drug-repurposing triage — pick a cancer type, then a mutation.")
    while True:
        cancer = _choose("Cancer types (q to quit):", cancers)
        if cancer is None:
            return
        mutation = _choose(f"Mutations in scope for {cancer} (q to go back):",
                           triage.mutations_for_cancer(cancer))
        if mutation is None:
            continue
        triage._print(mutation)


def one_shot(cancer, mutation):
    """Non-interactive path used when a cancer type (and optionally a mutation) is passed as args."""
    cancer = _resolve(cancer, list(triage.CANCER_TYPES), "cancer type")
    if not cancer:
        return
    muts = triage.mutations_for_cancer(cancer)
    if mutation is None:
        mutation = _choose(f"Mutations in scope for {cancer} (q to quit):", muts)
        if mutation is None:
            return
    else:
        mutation = _resolve(mutation, muts, f"mutation for {cancer}")
        if not mutation:
            return
    triage._print(mutation)


def main():
    args = sys.argv[1:]
    if not args:
        interactive()
    else:
        one_shot(args[0], " ".join(args[1:]) or None)


if __name__ == "__main__":
    main()
