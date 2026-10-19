"""Read-only questions about the world, for the workbench's checks.

    python -m workbench.probe tool join_queue
    python -m workbench.probe state user:prefs
    python -m workbench.probe orders --count 1 --section C

Each prints what it found and exits 0 when the answer is yes, 1 when it is no.
Nothing here writes: it reads the session stores, the memory file, the venue's
public state and the workbench's own logs. A student could run any of these in
a terminal and see the same thing the page shows.

The session stores it reads are the two the workshop uses: sessions.db at the
root (from step 4 on, and MonsterTix's from step 3), and the per-agent
agent/concert/.adk/session.db that `adk web` makes when it is given no
--session_service_uri (steps 2 and 3). The seeded `two-days-ago` conversation
is left out unless asked for, so a check only ever sees what the student did.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
SEEDED = "two-days-ago"


def _stores() -> list[Path]:
    found = [ROOT / "sessions.db"]
    found += sorted((ROOT / "agent").glob("*/.adk/session.db"))
    return [p for p in found if p.exists()]


def _rows(sql: str, args: tuple = ()) -> Iterable[tuple[Path, sqlite3.Row]]:
    for store in _stores():
        try:
            connection = sqlite3.connect(f"file:{store}?mode=ro", uri=True, timeout=2)
            connection.row_factory = sqlite3.Row
            for row in connection.execute(sql, args):
                yield store, row
            connection.close()
        except sqlite3.Error:
            continue


def events(include_seeded: bool = False, session: str = "") -> list[dict[str, Any]]:
    out = []
    for store, row in _rows("SELECT session_id, event_data FROM events"):
        if not include_seeded and row["session_id"] == SEEDED:
            continue
        if session and not row["session_id"].startswith(session):
            continue
        try:
            data = json.loads(row["event_data"])
        except (TypeError, ValueError):
            continue
        data["_session"] = row["session_id"]
        data["_store"] = store.name
        out.append(data)
    out.sort(key=lambda e: e.get("timestamp") or 0)
    return out


def _parts(event: dict[str, Any]) -> list[dict[str, Any]]:
    return ((event.get("content") or {}).get("parts")) or []


def calls(name: str, **kw) -> list[dict[str, Any]]:
    return [p["function_call"] | {"_session": e["_session"]} for e in events(**kw)
            for p in _parts(e) if (p.get("function_call") or {}).get("name") == name]


def responses(name: str, **kw) -> list[dict[str, Any]]:
    return [p["function_response"] | {"_session": e["_session"]} for e in events(**kw)
            for p in _parts(e) if (p.get("function_response") or {}).get("name") == name]


def _venue() -> str:
    url = os.environ.get("VENUE_URL", "")
    env = ROOT / ".env"
    if not url and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("VENUE_URL="):
                url = line.split("=", 1)[1].strip().strip('"')
    return (url or "http://127.0.0.1:8080").rstrip("/")


def venue_state() -> dict[str, Any]:
    with urllib.request.urlopen(_venue() + "/admin/state", timeout=8) as response:
        return json.loads(response.read())


def say(ok: bool, message: str) -> int:
    print(message)
    return 0 if ok else 1


def short(value: Any, limit: int = 300) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "…"


# ── the questions ────────────────────────────────────────────────────────────

def q_tool(args) -> int:
    found = calls(args.name, include_seeded=args.seeded)
    if not found:
        return say(False, f"no call to {args.name} yet")
    last = found[-1]
    ok = args.exactly is None or len(found) == args.exactly
    return say(ok, f"{len(found)} call(s) to {args.name}; last: {short(last.get('args'))}")


def q_response(args) -> int:
    found = responses(args.name)
    hits = [r for r in found if not args.contains or args.contains.lower() in json.dumps(r.get("response")).lower()]
    if not hits:
        return say(False, f"no {args.name} response" + (f" containing {args.contains!r}" if args.contains else "") + " yet")
    return say(True, f"{args.name} said: {short(hits[-1].get('response'))}")


def q_turns(args) -> int:
    """How many times the agent was run, and whether any run started without a person."""
    runs = {e["invocation_id"] for e in events() if e.get("invocation_id")}
    ok = len(runs) >= args.at_least
    return say(ok, f"{len(runs)} run(s) in the session store")


def q_session(args) -> int:
    ids = sorted({sid for _, row in _rows("SELECT id FROM sessions") for sid in [row["id"]]
                  if sid.startswith(args.prefix)})
    if not ids:
        return say(False, f"no session whose id starts with {args.prefix!r}")
    count = len([e for e in events(session=args.prefix) if e.get("author") != "user"])
    ok = count > 0
    return say(ok, f"{len(ids)} session(s): {', '.join(ids[:3])}; {count} agent event(s) in them")


def _state() -> tuple[dict[str, Any], dict[str, Any]]:
    """The newest session's state, and the user: state."""
    session_state: dict[str, Any] = {}
    newest = -1.0
    for _, row in _rows("SELECT id, state, update_time FROM sessions"):
        if row["id"] == SEEDED:
            continue
        stamp = row["update_time"]
        stamp = stamp if isinstance(stamp, (int, float)) else 0
        try:
            state = json.loads(row["state"] or "{}")
        except ValueError:
            continue
        if stamp >= newest:
            newest, session_state = stamp, state
    user: dict[str, Any] = {}
    for _, row in _rows("SELECT state FROM user_states"):
        try:
            user.update({f"user:{k}" if not k.startswith("user:") else k: v
                         for k, v in json.loads(row["state"] or "{}").items()})
        except ValueError:
            continue
    # Session state as events record it: the deltas, latest wins.
    for event in events():
        for key, value in ((event.get("actions") or {}).get("state_delta") or {}).items():
            if key.startswith("user:"):
                user[key] = value
            else:
                session_state[key] = value
    return session_state, user


def q_state(args) -> int:
    session_state, user = _state()
    merged = {**session_state, **user}
    if args.absent:
        if args.after_tool and not calls(args.after_tool):
            return say(False, f"{args.after_tool} has not run yet, so there is nothing to have lost")
        present = args.key in merged
        return say(not present, f"{args.key} is {'still there: ' + short(merged[args.key]) if present else 'not in state'}")
    if args.key not in merged:
        return say(False, f"{args.key} is not in state yet")
    value = merged[args.key]
    if args.contains and args.contains.lower() not in json.dumps(value).lower():
        return say(False, f"{args.key} = {short(value)}  (no {args.contains!r} in it)")
    return say(True, f"{args.key} = {short(value)}")


def q_memory(args) -> int:
    path = ROOT / "memory" / "userx.md"
    if not path.exists():
        return say(False, "memory/userx.md does not exist")
    text = path.read_text()
    if args.contains and args.contains.lower() not in text.lower():
        return say(False, f"memory/userx.md has no {args.contains!r} in it yet")
    return say(True, text.strip()[-600:])


def q_artifacts(args) -> int:
    folder = ROOT / "artifacts"
    files = [p for p in folder.rglob("*") if p.is_file()] if folder.exists() else []
    if not files:
        return say(False, "artifacts/ is empty")
    return say(True, "\n".join(str(p.relative_to(ROOT)) for p in files[:12]))


def q_compaction(args) -> int:
    found = [e for e in events() if (e.get("actions") or {}).get("compaction")]
    if not found:
        return say(False, "no compaction has run in your session yet")
    summary = found[-1]["actions"]["compaction"].get("compacted_content") or {}
    text = " ".join(p.get("text", "") for p in summary.get("parts", []))
    return say(True, f"{len(found)} compaction(s). The latest summary:\n{text.strip()}")


def q_orders(args) -> int:
    try:
        state = venue_state()
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        return say(False, f"the venue did not answer: {error}")
    orders = state.get("orders") or []
    if args.since_start:
        try:
            started = float((ROOT / "runs" / f"{args.since_start}.started").read_text())
        except (OSError, ValueError):
            return say(False, f"{args.since_start} has not been started from the workbench")
        orders = [o for o in orders if float(o.get("created_at") or 0) >= started]
    lines = [f"{o.get('seats', '?')} × section {o.get('section', '?')} · "
             f"{o.get('event_id', '')} · ${o.get('total', '?'):g}" if isinstance(o.get('total'), (int, float))
             else f"{o.get('seats', '?')} × section {o.get('section', '?')} · {o.get('event_id', '')}" for o in orders]
    ok = len(orders) == args.count if args.count is not None else len(orders) >= args.at_least
    if ok and args.section:
        ok = any(str(o.get("section")) == args.section for o in orders)
    if ok and args.qty:
        ok = any(int(o.get("seats") or 0) == args.qty for o in orders)
    return say(ok, f"{len(orders)} order(s)" + (":\n" + "\n".join(lines) if lines else ""))


def q_tickets(args) -> int:
    """How many places in line the venue has handed out."""
    try:
        queue = venue_state().get("queue") or []
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        return say(False, f"the venue did not answer: {error}")
    lines = [f"{q.get('ticket', '?')} · position {q.get('position', '?')}" for q in queue]
    ok = len(queue) == args.count if args.count is not None else bool(queue)
    return say(ok, f"{len(queue)} queue ticket(s)" + (":\n" + "\n".join(lines) if lines else ""))


def q_queue(args) -> int:
    """Queue positions the agent was told, in order. Passes when the newest is
    lower than the first: the line moved while the agent was not there."""
    positions = []
    for response in responses("join_queue") + responses("check_queue"):
        body = response.get("response") or {}
        if isinstance(body, dict) and "result" in body and isinstance(body["result"], dict):
            body = body["result"]
        if isinstance(body, dict) and isinstance(body.get("position"), (int, float)):
            positions.append(int(body["position"]))
    if len(positions) < 2:
        return say(False, f"positions seen: {positions or 'none'}; ask where you are in line")
    return say(positions[-1] < positions[0], f"positions seen, in order: {positions}")


def q_killed(args) -> int:
    log = ROOT / "runs" / f"{args.service}.log"
    text = log.read_text(errors="replace") if log.exists() else ""
    marker = "[workbench] kill -9"
    if marker not in text:
        return say(False, f"{args.service} has not been killed")
    after = text.rsplit(marker, 1)[1]
    restarted = "\n$ " in after
    if args.restarted and not restarted:
        return say(False, f"{args.service} was killed and has not been started again")
    return say(True, f"{args.service} was killed" + (", then started again" if restarted else ""))


def q_wake(args) -> int:
    if args.clock:
        log = ROOT / "runs" / "clock.log"
        text = log.read_text(errors="replace") if log.exists() else ""
        hits = [line for line in text.splitlines() if "the agent ran" in line]
        if not hits:
            return say(False, "the clock has not woken the agent yet")
        return say(True, "\n".join(hits[-3:]))
    log = ROOT / "runs" / "monstertix.log"
    text = log.read_text(errors="replace") if log.exists() else ""
    hits = [line for line in text.splitlines() if "POST /wake" in line or "woken" in line.lower()]
    if not hits:
        return say(False, "MonsterTix has not been woken")
    return say(True, "\n".join(hits[-4:]))


def q_setting(args) -> int:
    """One setting from .env, set or not. Credentials inside a value (a
    database URI's user:password@) are blanked, since the page shows this."""
    env = ROOT / ".env"
    values = {}
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip().strip('"')
    value = values.get(args.key, "")
    if not value:
        return say(False, f"{args.key} is not set in .env yet")
    shown = re.sub(r"//[^/@\s]+@", "//…@", value)
    if any(word in args.key.upper() for word in ("PASSWORD", "SECRET", "TOKEN", "KEY")):
        shown = "(set)"
    return say(True, f"{args.key}={shown}")


def q_prompts(args) -> int:
    """Step 2's prompt lab: how many wordings were tried, and what each did."""
    try:
        tries = json.loads((ROOT / "runs" / "prompt-tries.json").read_text())
    except (OSError, ValueError):
        tries = []
    if len(tries) < args.at_least:
        return say(False, f"{len(tries)} prompt(s) tried; try {args.at_least}")
    return say(True, "\n".join(f"{i + 1}. {t.get('label') or t['text'].splitlines()[0][:60]}"
                                for i, t in enumerate(tries)))


def q_file(args) -> int:
    path = (ROOT / args.path).resolve()
    if path.name == ".env":
        return say(False, "use `setting KEY` for .env: it holds credentials")
    if ROOT not in path.parents or not path.is_file():
        return say(False, f"{args.path} not found")
    text = path.read_text(errors="replace")
    lines = [line.strip() for line in text.splitlines() if args.contains in line]
    if args.absent:
        return say(not lines, "\n".join(lines) or f"no {args.contains!r} in {args.path}")
    return say(bool(lines), "\n".join(lines[:4]) or f"no {args.contains!r} in {args.path}")


def q_pending(args) -> int:
    """Is a run waiting on a person? An adk_request_input call with no answer."""
    asked = calls("adk_request_input")
    answered = {r.get("id") for r in responses("adk_request_input")}
    waiting = [c for c in asked if c.get("id") not in answered]
    if args.answered:
        ok = bool(asked) and len(waiting) < len(asked)
        return say(ok, f"{len(asked)} question(s) asked, {len(asked) - len(waiting)} answered")
    if not waiting:
        return say(False, "nothing is waiting on you" if not asked else "every question has been answered")
    return say(True, f"waiting for an answer: {short((waiting[-1].get('args') or {}).get('message') or waiting[-1].get('args'))}")


def q_nodes(args) -> int:
    seen = []
    for event in events():
        path = ((event.get("node_info") or {}).get("path")) or ""
        # A path is segments like "concert_nightly@1/pick_show@1": compare names exactly.
        names = {segment.split("@")[0] for segment in path.split("/") if segment}
        for node in args.names:
            if node in names and node not in seen:
                seen.append(node)
    missing = [n for n in args.names if n not in seen]
    return say(not missing, f"nodes that ran: {seen or 'none'}" + (f"; not yet: {missing}" if missing else ""))


def q_url(args) -> int:
    try:
        with urllib.request.urlopen(args.url, timeout=8) as response:
            body = response.read(400).decode(errors="replace")
            return say(response.status == 200, f"{response.status} {body}")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        return say(False, f"no answer from {args.url}: {error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m workbench.probe")
    sub = parser.add_subparsers(dest="question", required=True)

    p = sub.add_parser("tool"); p.add_argument("name"); p.add_argument("--seeded", action="store_true")
    p.add_argument("--exactly", type=int); p.set_defaults(fn=q_tool)
    p = sub.add_parser("response"); p.add_argument("name"); p.add_argument("--contains", default=""); p.set_defaults(fn=q_response)
    p = sub.add_parser("turns"); p.add_argument("--at-least", type=int, default=1); p.set_defaults(fn=q_turns)
    p = sub.add_parser("session"); p.add_argument("prefix"); p.set_defaults(fn=q_session)
    p = sub.add_parser("state"); p.add_argument("key"); p.add_argument("--contains", default=""); p.add_argument("--absent", action="store_true")
    p.add_argument("--after-tool", default="", help="with --absent: only once this tool has been called"); p.set_defaults(fn=q_state)
    p = sub.add_parser("memory"); p.add_argument("--contains", default=""); p.set_defaults(fn=q_memory)
    p = sub.add_parser("artifacts"); p.set_defaults(fn=q_artifacts)
    p = sub.add_parser("compaction"); p.set_defaults(fn=q_compaction)
    p = sub.add_parser("orders"); p.add_argument("--count", type=int); p.add_argument("--at-least", type=int, default=1)
    p.add_argument("--section", default=""); p.add_argument("--qty", type=int, default=0)
    p.add_argument("--since-start", default="", help="only orders made since this service last started")
    p.set_defaults(fn=q_orders)
    p = sub.add_parser("queue"); p.set_defaults(fn=q_queue)
    p = sub.add_parser("tickets"); p.add_argument("--count", type=int); p.set_defaults(fn=q_tickets)
    p = sub.add_parser("killed"); p.add_argument("service"); p.add_argument("--restarted", action="store_true"); p.set_defaults(fn=q_killed)
    p = sub.add_parser("wake"); p.add_argument("--clock", action="store_true", help="woken by the clock, not the page"); p.set_defaults(fn=q_wake)
    p = sub.add_parser("file"); p.add_argument("path"); p.add_argument("contains"); p.add_argument("--absent", action="store_true"); p.set_defaults(fn=q_file)
    p = sub.add_parser("pending"); p.add_argument("--answered", action="store_true"); p.set_defaults(fn=q_pending)
    p = sub.add_parser("nodes"); p.add_argument("names", nargs="+"); p.set_defaults(fn=q_nodes)
    p = sub.add_parser("url"); p.add_argument("url"); p.set_defaults(fn=q_url)
    p = sub.add_parser("prompts"); p.add_argument("--at-least", type=int, default=1); p.set_defaults(fn=q_prompts)
    p = sub.add_parser("setting"); p.add_argument("key"); p.set_defaults(fn=q_setting)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
