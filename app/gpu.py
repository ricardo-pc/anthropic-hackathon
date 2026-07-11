#!/usr/bin/env python3
"""
GPU backends — how a de-novo genotype actually gets docked.

Two implementations behind one interface:
  - DryRunBackend : runs the pipeline stages locally with NO GPU, returning a clearly-flagged
                    placeholder result (uses the wild-type as a stand-in mutant). It exists to prove
                    the whole submit -> compute -> result flow end-to-end and to demo the mechanics;
                    the payload is flagged dry_run so the UI shows a loud "not real docking" banner.
  - RunPodBackend : the real thing. Dispatches a docking job to a RunPod serverless endpoint (that
                    you deploy with the docking image — see docs/bring_your_own_tumor.md), waits for
                    it, appends the returned mutant scores to the replicate CSV, and triages them.

Selection (make_backend):
  RUNPOD_API_KEY + RUNPOD_ENDPOINT_ID set  -> RunPodBackend (real docking)
  MUTATIONRX_DRYRUN=1                          -> DryRunBackend (flow test, no GPU)
  neither                                   -> None (the app shows the bring-your-own-GPU gate)

Credentials come only from the environment or the /api/gpu/connect call the user makes to THEIR own
server; they are never committed, logged, or written to disk.
"""
import csv
import json
import os
import time
import urllib.request

import engine  # noqa: E402  (result_for_computed)
import triage  # noqa: E402

FAST_DRUGS = 8   # "fast mode": dock a reduced panel for a quick real run (a few minutes on an A100)


class GpuBackend:
    client_owned = False          # True once a user connects their own GPU (then it isn't metered)
    label = "gpu"

    def begin(self, plan):        # start the job; return a handle
        raise NotImplementedError

    def step(self, handle, phase):  # advance / wait for a phase ("dock", "rescore")
        return None

    def finalize(self, handle, plan):  # ensure scores are available; return the mutant pdb id
        raise NotImplementedError

    def triage_result(self, plan, mut_pdb):
        raise NotImplementedError


class DryRunBackend(GpuBackend):
    """No GPU. Walks the stages with brief pauses and returns a flagged placeholder result."""
    client_owned = True
    label = "dry-run"

    def begin(self, plan):
        time.sleep(0.8)
        return {"t": time.time()}

    def step(self, handle, phase):
        time.sleep(0.9)

    def finalize(self, handle, plan):
        time.sleep(0.6)
        return plan["wt"]         # stand-in: the wild-type structure poses as the "mutant"

    def triage_result(self, plan, mut_pdb):
        return engine.result_for_computed(plan, mut_pdb, dry_run=True)


class RunPodBackend(GpuBackend):
    """Real docking on a RunPod serverless endpoint you deploy. Submits one job that models the
    mutant, docks the panel, and gnina-rescores; then we append the scores and triage them."""
    client_owned = True
    label = "runpod"
    BASE = "https://api.runpod.ai/v2"

    def __init__(self, api_key, endpoint_id, fast=True):
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.fast = fast

    # -- RunPod REST helpers --
    def _post(self, path, body):
        req = urllib.request.Request(
            f"{self.BASE}/{self.endpoint_id}/{path}", data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)

    def _get(self, path):
        req = urllib.request.Request(f"{self.BASE}/{self.endpoint_id}/{path}",
                                     headers={"Authorization": f"Bearer {self.api_key}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)

    def healthy(self):
        """Cheap validity check for the connect step — is the key+endpoint reachable?"""
        try:
            self._get("health")
            return True
        except Exception:
            return False

    def begin(self, plan):
        drugs = _panel(self.fast)
        job = self._post("run", {"input": {
            "target": plan["target"], "wt_pdb": plan["wt"], "mutation": plan["mutation"],
            "drugs": drugs, "replicates": 3 if self.fast else 10}})
        return {"id": job["id"]}

    def step(self, handle, phase):
        # RunPod runs the whole job on the worker; here we just wait for it to be in/through-progress.
        self._await(handle, terminal=False)

    def finalize(self, handle, plan):
        out = self._await(handle, terminal=True)
        rows = out["scores"]                       # [{drug,category,pdb,state,rep,gnina_affinity,...}]
        mut_pdb = rows[0]["pdb"]
        _append_scores(rows)                       # persist so triage (and future loads) can see them
        return mut_pdb

    def triage_result(self, plan, mut_pdb):
        return engine.result_for_computed(plan, mut_pdb, dry_run=False)

    def _await(self, handle, terminal):
        for _ in range(600):                       # up to ~10 min at 1s
            st = self._get(f"status/{handle['id']}")
            status = st.get("status")
            if status == "COMPLETED":
                return st.get("output")
            if status == "FAILED":
                raise RuntimeError(f"RunPod job failed: {st.get('error','unknown')}")
            if not terminal and status == "IN_PROGRESS":
                return None
            time.sleep(1)
        raise RuntimeError("RunPod job timed out")


def _panel(fast):
    """The drug list to dock. Fast mode uses a representative subset for a quick real run."""
    drugs = []
    with open(f"{triage.HERE}/data/drugs.csv") as f:
        for r in csv.DictReader(f):
            drugs.append({"name": r["name"], "smiles": r.get("smiles", ""), "category": r.get("category", "")})
    return drugs[:FAST_DRUGS] if fast else drugs


def _append_scores(rows):
    """Append freshly-docked rows to the replicate CSV so the new genotype becomes triage-able."""
    path = triage.REPL
    with open(path) as f:
        header = f.readline().strip().split(",")
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        for row in rows:
            w.writerow(row)


def make_backend():
    key, endpoint = os.environ.get("RUNPOD_API_KEY"), os.environ.get("RUNPOD_ENDPOINT_ID")
    if key and endpoint:
        return RunPodBackend(key, endpoint, fast=os.environ.get("MUTATIONRX_FAST", "1") != "0")
    if os.environ.get("MUTATIONRX_DRYRUN"):
        return DryRunBackend()
    return None


def backend_from_credentials(key, endpoint):
    """Build a backend from a user-supplied key at /api/gpu/connect. RunPod if it validates; else the
    dry-run flow if the server was started in dry-run mode; else None (with a reason)."""
    if key and endpoint:
        b = RunPodBackend(key, endpoint)
        if b.healthy():
            return b, None
        return None, "Couldn't reach that RunPod endpoint with that key. Check the endpoint id and key."
    if os.environ.get("MUTATIONRX_DRYRUN"):
        return DryRunBackend(), None
    return None, ("No RunPod endpoint configured. Deploy the docking endpoint (docs/bring_your_own_tumor.md) "
                  "and provide its endpoint id + key, or start the server with MUTATIONRX_DRYRUN=1 to test the flow.")
