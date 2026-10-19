"""Running a check.

A check never asks the student whether they did something. It runs a read-only
command and reads the answer, and the page shows that command next to the
result, so a student also learns how to find it out without a workbench.

Probes are vetted before they run: only `python3 -m workbench.probe …` and a
reading `curl`, never through a shell.
"""

from __future__ import annotations

import re
import shlex
import subprocess
from typing import Any

from workbench import config

TIMEOUT = 30


class ProbeRefused(Exception):
    pass


def substitutions() -> dict[str, str]:
    env = config.workshop_env()
    from workbench.services import procs

    return {
        "WORKSHOP": str(config.ROOT),
        "VENUE_URL": procs.origin("venue"),
        "AGENT_URL": env.get("AGENT_URL", "http://127.0.0.1:8000"),
        "PROJECT": env.get("GOOGLE_CLOUD_PROJECT", ""),
        "REGION": env.get("GOOGLE_CLOUD_REGION", "us-central1"),
    }


def fill(command: str, env: dict[str, str]) -> str:
    return re.sub(r"\$\{(\w+)\}|\$(\w+)",
                  lambda m: env.get(m.group(1) or m.group(2), m.group(0)), command)


def _vet(argv: list[str]) -> None:
    if not argv:
        raise ProbeRefused("empty probe")
    if argv[0] == "python3":
        if argv[1:3] != ["-m", "workbench.probe"]:
            raise ProbeRefused("python3 probes may only run workbench.probe")
        return
    if argv[0] == "curl":
        if any(flag in argv for flag in ("-d", "--data", "-T", "--upload-file", "-X", "-o")):
            raise ProbeRefused("curl probes may only read")
        return
    raise ProbeRefused(f"{argv[0]} is not an allowed probe")


def evaluate(spec: dict[str, Any]) -> dict[str, Any]:
    filled = fill(spec["probe"], substitutions())
    base = {"id": spec["id"], "label": spec.get("label", ""), "command": filled,
            "expected": spec.get("expect") == "fail"}
    try:
        argv = shlex.split(filled)
        _vet(argv)
    except (ProbeRefused, ValueError) as refusal:
        return {**base, "passed": False, "detail": f"probe refused: {refusal}"}
    if argv[0] == "python3":
        argv[0] = config.python()
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=TIMEOUT,
                              cwd=config.ROOT, env=config.workshop_env())
    except subprocess.TimeoutExpired:
        return {**base, "passed": False, "detail": "timed out"}
    except FileNotFoundError:
        return {**base, "passed": False, "detail": f"{argv[0]} is not installed"}
    out = (done.stdout or done.stderr).strip()
    passed = done.returncode == 0
    if passed and spec.get("contains"):
        passed = spec["contains"].lower() in out.lower()
    return {**base, "passed": passed, "detail": out[:2000]}


def display(command: str) -> str:
    """What a student would type: `python`, not the venv's absolute path."""
    return command.replace(config.python(), "python").replace(str(config.ROOT), "$WORKSHOP")

