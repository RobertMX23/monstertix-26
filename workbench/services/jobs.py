"""One-off commands a step runs: ./show-compaction.sh, ./deploy-agent.sh.

The page cannot send a command. It names a step and a task item, and the
command is looked up in that step's content, so the only things that can run
are the ones an author wrote into a step.yaml.

Output goes to runs/job-<id>.log; the page polls it. Polling, not a stream:
Cloud Shell's proxy buffers streams, and a log file never loses a line.
"""

from __future__ import annotations

import shlex
import subprocess
import threading
import time
from typing import Any

from workbench import config
from workbench.services.checks import display, fill, substitutions

_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def start(key: str, command: str) -> dict[str, Any]:
    with _lock:
        running = _jobs.get(key)
        if running and running["state"] == "running":
            return dict(running)
    filled = fill(command, substitutions())
    token = f"{key}.{int(time.time() * 1000)}"
    record = {"key": key, "token": token, "command": display(filled), "state": "running", "code": None}
    with _lock:
        _jobs[key] = record
    threading.Thread(target=_run, args=(record, filled), daemon=True).start()
    return dict(record)


def _log(record: dict[str, Any]):
    return config.RUNS / f"job-{record['key'].replace('/', '_')}.log"


def _run(record: dict[str, Any], command: str) -> None:
    path = _log(record)
    with open(path, "w", encoding="utf-8") as sink:
        sink.write(f"$ {record['command']}\n")
        sink.flush()
        argv = shlex.split(command)
        if argv and argv[0] in ("python", "python3"):
            argv[0] = config.python()
        if argv and argv[0].endswith(".sh"):
            argv = ["bash", *argv]
        try:
            done = subprocess.run(argv, cwd=config.ROOT, stdout=sink, stderr=subprocess.STDOUT,
                                  env=config.workshop_env(), timeout=1800)
            code = done.returncode
        except FileNotFoundError as missing:
            sink.write(f"not found: {missing}\n")
            code = 127
        except subprocess.TimeoutExpired:
            sink.write("timed out after 30 minutes\n")
            code = 124
    with _lock:
        record.update(state="done", code=code)


def status(key: str) -> dict[str, Any] | None:
    with _lock:
        record = _jobs.get(key)
        record = dict(record) if record else None
    if record is None:
        return None
    path = _log(record)
    record["log"] = path.read_text(errors="replace")[-20000:] if path.exists() else ""
    return record
