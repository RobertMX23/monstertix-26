"""The file explorer's view of the project: a tree, and one file at a time.

Read-only, confined to the repository, and blind to secrets: .env holds the
project id and, after step 10, a database password.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from workbench import config

ROOT = config.ROOT
HIDDEN = {".venv", "node_modules", "__pycache__", ".git", "dist", "runs", ".adk",
          ".pytest_cache", ".ruff_cache", ".claude", ".DS_Store"}
SECRETS = {".env"}
TEXT = {".py", ".js", ".ts", ".tsx", ".css", ".html", ".md", ".yaml", ".yml", ".json",
        ".sh", ".txt", ".toml", ".cfg", ".ini", ""}
MAX_READ = 300_000


class Outside(Exception):
    pass


def resolve(relative: str) -> Path:
    candidate = (ROOT / relative.strip().lstrip("/")).resolve()
    if candidate != ROOT and ROOT not in candidate.parents:
        raise Outside(relative)
    return candidate


def _hidden(path: Path) -> bool:
    return path.name in HIDDEN or path.name in SECRETS or path.suffix == ".pyc"


def tree(start: str = "", depth: int = 4) -> dict[str, Any]:
    def walk(directory: Path, left: int) -> list[dict[str, Any]]:
        entries = []
        for child in sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if _hidden(child):
                continue
            relative = str(child.relative_to(ROOT))
            if child.is_dir():
                entries.append({"name": child.name, "path": relative, "kind": "dir",
                                "children": walk(child, left - 1) if left > 1 else []})
            else:
                entries.append({"name": child.name, "path": relative, "kind": "file"})
        return entries

    base = resolve(start) if start else ROOT
    if not base.is_dir():
        return {"root": start, "entries": []}
    return {"root": "" if base == ROOT else str(base.relative_to(ROOT)), "entries": walk(base, depth)}


def read(relative: str) -> dict[str, Any]:
    path = resolve(relative)
    if path.name in SECRETS:
        return {"path": relative, "error": "holds your project settings, so it is not shown here"}
    if not path.is_file():
        return {"path": relative, "error": "not in place yet"}
    if path.suffix.lower() not in TEXT and path.name not in {"Dockerfile"}:
        return {"path": relative, "error": "not a text file"}
    raw = path.read_bytes()[:MAX_READ]
    try:
        text = raw.decode()
    except UnicodeDecodeError:
        return {"path": relative, "error": "not a text file"}
    return {"path": str(path.relative_to(ROOT)), "language": path.suffix.lstrip(".") or "text",
            "lines": text.split("\n")}


# ── a step's code, as the solution folder ships it ───────────────────────────
# The code shown in the reading is the step's own, whether or not that step is
# loaded in agent/ right now.

def stage_tree(number: int, start: str = "") -> dict[str, Any]:
    from workbench.services import stage

    files = sorted(p for p in stage.layout(number) if not start or p.startswith(start))
    root: dict[str, Any] = {}
    for path in files:
        node = root
        parts = path.split("/")
        for depth, name in enumerate(parts):
            key = "/".join(parts[: depth + 1])
            if depth == len(parts) - 1:
                node.setdefault("__files__", []).append({"name": name, "path": key, "kind": "file"})
            else:
                node = node.setdefault(name, {"__path__": key})

    def build(node: dict[str, Any]) -> list[dict[str, Any]]:
        dirs = [{"name": name, "path": child["__path__"], "kind": "dir", "children": build(child)}
                for name, child in sorted(node.items()) if not name.startswith("__")]
        return dirs + node.get("__files__", [])

    return {"root": "", "entries": build(root)}


def stage_read(number: int, relative: str) -> dict[str, Any]:
    from workbench.services import stage

    source = stage.layout(number).get(relative)
    if source is None:
        return {"path": relative, "error": f"not part of step {number}'s code"}
    return {"path": relative, "language": source.suffix.lstrip(".") or "text",
            "lines": source.read_text(errors="replace").split("\n")}
