#!/usr/bin/env python3
"""
RunPod serverless worker — the GPU side of "bring your own GPU".

This is the handler that runs INSIDE your RunPod endpoint's Docker image (which has DiffDock + gnina +
PyMOL installed). MutationRx's RunPodBackend (app/gpu.py) calls your endpoint with a genotype; this
handler models the mutant, docks the drug panel against the wild-type and mutant, gnina-rescores, and
returns the score rows MutationRx then triages.

It is a REFERENCE implementation: the DiffDock/gnina invocations below mirror cluster/ (the pipeline
that produced all the shipped data). Point DIFFDOCK_DIR / GNINA_BIN / STRUCT_DIR at your image's
layout. Not run here (no GPU); deploy it per docs/bring_your_own_tumor.md.

Input  (event["input"]): {target, wt_pdb, mutation, drugs:[{name,smiles,category}], replicates}
Output: {"scores": [ {rep,drug,category,pdb,target,state,diffdock_confidence,gnina_affinity,
                       gnina_minimize_rmsd,gnina_cnn_score,gnina_cnn_affinity}, ... ]}
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model_mutant import model_mutant  # noqa: E402

DIFFDOCK_DIR = os.environ.get("DIFFDOCK_DIR", "/opt/DiffDock")
GNINA_BIN = os.environ.get("GNINA_BIN", "/opt/bin/gnina")
STRUCT_DIR = os.environ.get("STRUCT_DIR", "/opt/structures/prepared")  # wild-type receptors, by pdb id
WORK = "/tmp/mutationrx_job"


def _dock_and_score(receptor_pdb, pdb_id, state, target, drugs, replicates):
    """Dock each drug into one receptor N times and gnina-rescore. Returns score rows.

    Mirrors cluster/replicate_and_rescore.py: DiffDock (blind) -> rank1 pose -> gnina --minimize
    (NOT --score_only; raw poses clash). Fill in the two subprocess blocks for your image.
    """
    rows = []
    for rep in range(1, replicates + 1):
        for d in drugs:
            # 1) DiffDock: dock d["smiles"] into receptor_pdb -> best pose sdf  (see cluster/full_sweep.sbatch)
            #    subprocess.run([sys.executable, f"{DIFFDOCK_DIR}/inference.py", ...], check=True)
            # 2) gnina --minimize the rank1 pose against the receptor -> affinity + cnn scores
            #    out = subprocess.run([GNINA_BIN, "--minimize", "-r", receptor_pdb, "-l", pose_sdf,
            #                          "--autobox_ligand", pose_sdf], capture_output=True, text=True)
            #    conf, aff, rmsd, cnn, cnn_aff = _parse(out.stdout)
            raise NotImplementedError(
                "Wire DiffDock + gnina here for your image (see cluster/README.md). This handler is the "
                "reference skeleton; the shipped data was produced by the cluster/ scripts it mirrors.")
            rows.append(dict(rep=rep, drug=d["name"], category=d["category"], pdb=pdb_id, target=target,
                             state=state, diffdock_confidence=conf, gnina_affinity=aff,  # noqa: F821
                             gnina_minimize_rmsd=rmsd, gnina_cnn_score=cnn, gnina_cnn_affinity=cnn_aff))  # noqa: F821
    return rows


def run(inp):
    os.makedirs(WORK, exist_ok=True)
    target, wt_pdb, mutation = inp["target"], inp["wt_pdb"], inp["mutation"]
    drugs, replicates = inp["drugs"], int(inp.get("replicates", 3))

    wt_receptor = f"{STRUCT_DIR}/{wt_pdb}_receptor.pdb"
    mut_pdb_id = f"{target}_{mutation}"
    mut_receptor = f"{WORK}/{mut_pdb_id}_receptor.pdb"
    model_mutant(wt_receptor, mutation, mut_receptor)  # side-chain swap -> mutant structure

    rows = []
    # wild-type is usually already cached in MutationRx, but docking it here keeps the run self-contained
    rows += _dock_and_score(mut_receptor, mut_pdb_id, mutation, target, drugs, replicates)
    return {"scores": rows, "mut_pdb": mut_pdb_id}


def handler(event):
    try:
        return run(event["input"])
    except Exception as e:  # RunPod surfaces this as the job error
        return {"error": f"{type(e).__name__}: {e}"}


if __name__ == "__main__":
    # Local entrypoint for the RunPod serverless runtime:
    #   import runpod; runpod.serverless.start({"handler": handler})
    import runpod
    runpod.serverless.start({"handler": handler})
