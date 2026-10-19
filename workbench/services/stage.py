"""Which step's code is in agent/, what a step changes, and loading one.

`use-solution.sh` stays the one place that knows how to load a step. The
workbench runs it exactly as the codelab tells a student to, with the agent
stopped first because it deletes sessions.db.

To know which step is loaded, the files in place are compared with every
solution folder. A student who edits a file (step 2 asks for one edit) still
sees the nearest step, marked as edited.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from workbench import config
from workbench.services import procs

RECORD = config.RUNS / "stage.json"
SKIP = {"__pycache__", "artifacts", ".adk"}
AGENT_EXTRAS = ("main.py", "Dockerfile", "requirements.txt")


def steps() -> dict[int, Path]:
    found = {}
    for folder in config.SOLUTIONS.glob("step*_*"):
        match = re.match(r"step(\d+)_", folder.name)
        if match and folder.is_dir():
            found[int(match.group(1))] = folder
    return dict(sorted(found.items()))


def _files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p.relative_to(folder) for p in folder.rglob("*")
                  if p.is_file() and not (set(p.relative_to(folder).parts) & SKIP)
                  and p.suffix != ".pyc")


def layout(number: int) -> dict[str, Path]:
    """Where each file is once step `number` is loaded: repo path -> source.

    Mirrors use-solution.sh: concert/ comes from the latest step that has one
    (step 3 has none and leaves step 2's in place), the root monstertix/ from
    the latest step that ships one, and agent/main.py and friends only from a
    step that has them."""
    known = steps()
    placed: dict[str, Path] = {}
    concert = max((n for n, f in known.items() if n <= number and (f / "concert").is_dir()), default=None)
    if concert is not None:
        base = known[concert] / "concert"
        for rel in _files(base):
            placed[f"agent/concert/{rel}"] = base / rel
    root_tix = max((n for n, f in known.items() if n <= number and (f / "monstertix").is_dir()), default=None)
    if root_tix is not None:
        base = known[root_tix] / "monstertix"
        for rel in _files(base):
            placed[f"monstertix/{rel}"] = base / rel
    folder = known.get(number)
    if folder is not None:
        for name in AGENT_EXTRAS:
            if (folder / name).is_file():
                placed[f"agent/{name}"] = folder / name
        if (folder / "monstertix").is_dir() and (folder / "concert").is_dir():
            for rel in _files(folder / "monstertix"):
                placed[f"agent/monstertix/{rel}"] = folder / "monstertix" / rel
    return placed


def _digest(path: Path) -> str:
    try:
        return hashlib.sha1(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _recorded() -> int | None:
    try:
        return int(json.loads(RECORD.read_text())["step"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _score(number: int) -> tuple[int, int]:
    """How many of step `number`'s agent files are in place unchanged, out of how many."""
    files = {k: v for k, v in layout(number).items() if k.startswith("agent/")}
    same = sum(1 for repo, source in files.items() if _digest(config.ROOT / repo) == _digest(source))
    return same, len(files)


def detect() -> dict[str, Any]:
    present = {str(p.relative_to(config.ROOT)) for p in (config.ROOT / "agent").rglob("*")
               if p.is_file() and not (set(p.parts) & SKIP) and p.suffix != ".pyc"}
    best: tuple[int, int, int] | None = None     # (exact files, -extra files, step)
    for number in steps():
        files = {k for k in layout(number) if k.startswith("agent/")}
        same, total = _score(number)
        extra = len((present - files) - {"agent/.dockerignore", "agent/.gcloudignore"})
        candidate = (same - extra - (total - same), -extra, number)
        if best is None or candidate > best:
            best = candidate
    if best is None:
        return {"step": None, "edited": False}
    number = best[2]
    same, total = _score(number)
    recorded = _recorded()
    # Steps 2 and 3 share an agent; so do 9 and 10 apart from the wrapper.
    # The workbench's own record decides between equals.
    if recorded is not None and recorded != number and _score(recorded) == (same, total):
        number = recorded
    return {"step": number, "edited": same < total}


def current() -> int | None:
    return detect()["step"]


def changes(since: int, to: int) -> dict[str, Any]:
    """What loading step `to` changes compared with step `since`: files added,
    and for each changed file, the line numbers (in the new file) that differ."""
    before, after = layout(since), layout(to)
    files = []
    for repo, source in sorted(after.items()):
        new = source.read_text(errors="replace").splitlines()
        if repo not in before:
            files.append({"path": repo, "status": "added", "lines": []})
            continue
        old = before[repo].read_text(errors="replace").splitlines()
        if old == new:
            continue
        lines: list[int] = []
        matcher = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
        for tag, _, _, j1, j2 in matcher.get_opcodes():
            if tag in ("replace", "insert"):
                lines.extend(range(j1 + 1, j2 + 1))
        files.append({"path": repo, "status": "changed", "lines": lines})
    removed = sorted(set(before) - set(after))
    return {"since": since, "to": to, "files": files, "removed": removed}


def load(number: int, reset_venue: bool = True) -> dict[str, Any]:
    """Load a step the way the codelab does: stop what holds sessions.db,
    RESET THE VENUE, `./use-solution.sh N --force`, start the agent again."""
    if number not in steps():
        return {"ok": False, "output": f"no solution for step {number}"}
    was_running = {name: procs.status(name)["state"] in ("running", "starting")
                   for name in ("monstertix",)}
    output: list[str] = []
    for name in ("clock", "monstertix", "agent"):
        if procs.status(name)["pid"] is not None:
            procs.stop(name)
            output.append(f"→ stopped {name}")
    if reset_venue:
        output.append(venue_reset())
    # A step that ships no agent (step 3) keeps whatever agent is in place.
    # Coming from a later step, that would be the wrong one, so load the step
    # whose agent it builds on first, as the README says to.
    known = steps()
    if not (known[number] / "concert").is_dir():
        base = max((n for n, f in known.items() if n < number and (f / "concert").is_dir()), default=None)
        if base is not None and _score(base)[0] < _score(base)[1]:
            first = subprocess.run(["bash", "./use-solution.sh", str(base), "--force"],
                                   cwd=config.ROOT, capture_output=True, text=True, timeout=120,
                                   env=config.workshop_env())
            output.append(f"$ ./use-solution.sh {base} --force")
            output.append((first.stdout + first.stderr).strip())
    done = subprocess.run(["bash", "./use-solution.sh", str(number), "--force"],
                          cwd=config.ROOT, capture_output=True, text=True, timeout=120,
                          env=config.workshop_env())
    output.append(f"$ ./use-solution.sh {number} --force")
    output.append((done.stdout + done.stderr).strip())
    if done.returncode == 0:
        RECORD.write_text(json.dumps({"step": number}))
        # A fresh step starts a fresh prompt lab (step 2).
        (config.RUNS / "prompt-tries.json").unlink(missing_ok=True)
        for name in ("agent", "monstertix"):
            if name == "agent" or was_running.get(name):
                result = procs.start(name)
                output.append(f"→ started {name}: {result['state']}")
    return {"ok": done.returncode == 0, "output": "\n".join(o for o in output if o),
            **detect()}


def venue_reset() -> str:
    import urllib.error
    import urllib.request

    request = urllib.request.Request(procs.origin("venue") + "/admin/reset", data=b"{}",
                                     method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10):
            return "→ RESET THE VENUE"
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return f"⚠ could not reset the venue: {error}"
