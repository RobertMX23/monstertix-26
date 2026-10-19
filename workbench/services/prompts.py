"""Step 2's prompt lab: swap a wording into PROACTIVE_INSTRUCTION, restart the
agent, and record what happened after it.

Writing the prompt is the edit the codelab asks a student to make by hand in
agent/concert/agent.py: the text replaces the body of PROACTIVE_INSTRUCTION,
and root_agent is pointed at it. Only that block and that one argument
change, and only in the file the step names.

Each try is kept in runs/prompt-tries.json with the time the agent restarted
on it. What happened in the window after it (how many runs there were, who
started them, what the venue sold) is read from the session store and the
venue, never from the page.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from workbench import config
from workbench.probe import events, venue_state
from workbench.services import procs

TRIES = config.RUNS / "prompt-tries.json"
BLOCK = re.compile(r'(PROACTIVE_INSTRUCTION = """\n)(.*?)(\n?""")', re.S)
USES = re.compile(r"(\binstruction=)\w+(,)")


class PromptError(Exception):
    pass


def _path(file: str):
    path = (config.ROOT / file).resolve()
    if config.ROOT not in path.parents or not path.is_file():
        raise PromptError(f"{file} is not in place. Load the step first.")
    return path


def current(file: str) -> dict[str, Any]:
    text = _path(file).read_text()
    block = BLOCK.search(text)
    uses = USES.search(text[text.find("root_agent"):]) if "root_agent" in text else None
    return {
        "text": block.group(2).strip("\n") if block else "",
        "using": bool(uses and "PROACTIVE_INSTRUCTION" in uses.group(0)),
    }


def _tries() -> list[dict[str, Any]]:
    try:
        return json.loads(TRIES.read_text())
    except (OSError, ValueError):
        return []


def swap(file: str, text: str, label: str) -> dict[str, Any]:
    text = text.strip("\n")
    if not text.strip():
        raise PromptError("The prompt is empty.")
    if len(text) > 4000:
        raise PromptError("Keep the prompt under 4,000 characters.")
    path = _path(file)
    source = path.read_text()
    if not BLOCK.search(source) or "root_agent" not in source:
        raise PromptError(f"{file} has no PROACTIVE_INSTRUCTION to replace. Load step 2 again.")
    safe = text.replace('"""', '\\"\\"\\"')
    source = BLOCK.sub(lambda m: f"{m.group(1)}{safe}\n{m.group(3).lstrip(chr(10))}", source, count=1)
    head, _, tail = source.partition("root_agent")
    tail = USES.sub(r"\1PROACTIVE_INSTRUCTION\2", tail, count=1)
    path.write_text(f"{head}root_agent{tail}")

    procs.restart("agent")
    tries = _tries()
    tries.append({"label": label.strip()[:80], "text": text, "started": time.time()})
    TRIES.write_text(json.dumps(tries, indent=1))
    return {"ok": True, "agent": procs.status("agent")["state"]}


def restore(file: str, original: str) -> dict[str, Any]:
    """Put the file back as the step shipped it, and forget the tries."""
    source = (config.ROOT / original).read_text()
    _path(file).write_text(source)
    TRIES.unlink(missing_ok=True)
    procs.restart("agent")
    return {"ok": True}


def results() -> list[dict[str, Any]]:
    tries = _tries()
    if not tries:
        return []
    seen = events()
    try:
        orders = venue_state().get("orders") or []
    except Exception:  # noqa: BLE001 - the venue being down is shown, not raised
        orders = None
    out = []
    for index, attempt in enumerate(tries):
        start = attempt["started"]
        end = tries[index + 1]["started"] if index + 1 < len(tries) else time.time() + 1
        window = [e for e in seen if start <= (e.get("timestamp") or 0) < end]
        runs: dict[str, str] = {}
        for event in window:
            runs.setdefault(event.get("invocation_id", ""), event.get("author", ""))
        typed = sum(1 for author in runs.values() if author == "user")
        tools = sorted({p["function_call"]["name"] for e in window
                        for p in ((e.get("content") or {}).get("parts") or []) if p.get("function_call")})
        sold = None if orders is None else [o for o in orders if start <= float(o.get("created_at") or 0) < end]
        out.append({
            "label": attempt["label"],
            "text": attempt["text"],
            "started": start,
            "runs": len(runs),
            "byYou": typed,
            "tools": tools,
            "orders": None if sold is None else len(sold),
        })
    return out
