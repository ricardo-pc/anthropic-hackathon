#!/usr/bin/env python3
"""
Job store + background runner. A triage request becomes a Job that moves through the pipeline STAGES
so the UI can show honest progress. Cached requests complete instantly (the physics ran earlier, so
every stage is already done); a de-novo point mutation runs a real GPU job stage by stage.

In-memory and single-process — fine for a demo / single researcher. Swap for a real queue (Redis/RQ)
to run it as a service.
"""
import threading
import time
import uuid

from engine import STAGES, resolve, result_for_cached, NeedsGpu


class Job:
    def __init__(self, req, client_id):
        self.id = uuid.uuid4().hex[:12]
        self.req = req
        self.client_id = client_id
        self.status = "queued"          # queued | running | done | error
        self.stages = [{"name": s, "status": "pending"} for s in STAGES]
        self.result = None
        self.error = None
        self.cached = None
        self.created = time.time()

    def as_dict(self):
        return dict(id=self.id, status=self.status, stages=self.stages, result=self.result,
                    error=self.error, cached=self.cached)

    # -- stage helpers --
    def _set(self, name, status):
        for s in self.stages:
            if s["name"] == name:
                s["status"] = status

    def _all_done(self):
        for s in self.stages:
            s["status"] = "done"


class JobStore:
    def __init__(self, gpu=None):
        self._jobs = {}
        self._lock = threading.Lock()
        self.gpu = gpu  # a GpuBackend, or None (real-compute requests then error cleanly)

    def get(self, job_id):
        with self._lock:
            j = self._jobs.get(job_id)
            return j.as_dict() if j else None

    def submit(self, req, client_id):
        job = Job(req, client_id)
        with self._lock:
            self._jobs[job.id] = job
        threading.Thread(target=self._run, args=(job,), daemon=True).start()
        return job.id

    # ------------------------------------------------------------------
    def _run(self, job):
        job.status = "running"
        try:
            plan = resolve(job.req)
            if "error" in plan:
                job.status, job.error = "error", plan["error"]
                return
            job._set("Resolving genotype", "done")

            if not plan["needs_compute"]:
                # cached: the pipeline already ran; reveal the remaining stages as done and return.
                job.cached = True
                job._all_done()
                job.result = result_for_cached(plan)
                job.status = "done"
                return

            # real compute: model the mutant, dock the panel on a GPU, rescore, bootstrap, classify.
            job.cached = False
            if self.gpu is None:
                raise NeedsGpu(
                    "This genotype isn't precomputed, so it needs a real docking run on a GPU. "
                    "No GPU backend is configured. Connect a RunPod key or your own GPU to compute it "
                    "(see docs/bring_your_own_tumor.md), or pick a precomputed example.")
            self._run_gpu(job, plan)
            job.status = "done"
        except NeedsGpu as e:
            job.status, job.error = "needs_gpu", str(e)
        except Exception as e:  # noqa: BLE001 - surface any pipeline failure to the UI
            job.status, job.error = "error", f"{type(e).__name__}: {e}"

    def _run_gpu(self, job, plan):
        """Drive a real docking run through the GPU backend, updating stage status as it goes."""
        g = self.gpu

        def stage(name, fn):
            job._set(name, "running")
            out = fn()
            job._set(name, "done")
            return out

        handle = stage("Modeling mutant structure", lambda: g.begin(plan))
        stage("Docking the panel (wild-type + mutant)", lambda: g.step(handle, "dock"))
        stage("Rescoring poses (gnina)", lambda: g.step(handle, "rescore"))
        mut_pdb = stage("Bootstrapping credible intervals", lambda: g.finalize(handle, plan))
        job.result = stage("Classifying & explaining", lambda: g.triage_result(plan, mut_pdb))
