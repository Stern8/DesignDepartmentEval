"""Run a model-written renderer in a subprocess and record run metadata.

Contract: `python <submission>/main.py <task> <outdir>` where task in {furnace, prism, caustic}.
Outputs (in outdir): furnace -> furnace.npy (H,W,3 float) + mask.npy (H,W bool);
prism -> deviation.json {"wavelengths_nm": [...], "exit_deviation_deg": [...]};
caustic -> render.png (top-down orthographic, world x,z in [-4,4], sphere at origin).
The harness writes run.json {returncode, seconds, timed_out, stderr_tail}.
NOTE: subprocess is not a security sandbox; run untrusted submissions in a container/VM.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


def run_submission(submission_dir: str, task: str, outdir: str, timeout: float = 60.0) -> dict:
    submission_dir = str(Path(submission_dir).resolve())
    out = Path(outdir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, str(Path(submission_dir) / "main.py"), task, str(out)],
                           capture_output=True, text=True, timeout=timeout, cwd=submission_dir)
        meta = {"returncode": r.returncode, "timed_out": False, "stderr_tail": r.stderr[-2000:]}
    except subprocess.TimeoutExpired as e:
        meta = {"returncode": -1, "timed_out": True, "stderr_tail": str(e.stderr or "")[-2000:]}
    meta["seconds"] = round(time.time() - t0, 3)
    meta["timeout"] = timeout
    (out / "run.json").write_text(json.dumps(meta))
    return meta
