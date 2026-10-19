"""Loading the course from content/, in any language it has been translated to.

A step is a folder under content/steps/ named NN-slug; the number is the order.

    step.yaml        meta, parts, exercises and checks, in English
    a-something.md   one part's reading, in English
    step.es.yaml     optional: only the strings that differ in Spanish
    a-something.es.md

A translation never has to be complete. Each file falls back to English on its
own, and a step.<lang>.yaml overlay only needs the keys it translates: maps are
merged key by key, and lists of maps are matched by `id` (or by position when
the entries have none). Commands, probes and file paths are never translated,
so an overlay that leaves them out keeps the English ones.

Content is re-read on every request, so an author sees an edit on reload.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from workbench import config

LANG = re.compile(r"^[a-z]{2}(-[A-Za-z]{2})?$")


def clean(lang: str | None) -> str:
    return lang if lang and LANG.match(lang) else config.DEFAULT_LANG


def merge(base: Any, over: Any) -> Any:
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for key, value in over.items():
            out[key] = merge(base[key], value) if key in base else value
        return out
    if isinstance(base, list) and isinstance(over, list):
        if all(isinstance(x, dict) and "id" in x for x in base + over):
            index = {x["id"]: x for x in over}
            return [merge(x, index[x["id"]]) if x["id"] in index else x for x in base]
        return [merge(b, o) for b, o in zip(base, over)] + base[len(over):]
    return over if over not in (None, "") else base


def _yaml(path: Path, lang: str) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text()) if path.exists() else {}
    data = data or {}
    if lang != config.DEFAULT_LANG:
        overlay = path.with_name(f"{path.stem}.{lang}{path.suffix}")
        if overlay.exists():
            data = merge(data, yaml.safe_load(overlay.read_text()) or {})
    return data


def _text(path: Path, lang: str) -> str:
    if lang != config.DEFAULT_LANG:
        translated = path.with_name(f"{path.stem}.{lang}{path.suffix}")
        if translated.exists():
            return translated.read_text()
    return path.read_text() if path.exists() else ""


def languages() -> list[str]:
    """English, and every language at least one file has been translated to."""
    found = {config.DEFAULT_LANG}
    for path in config.CONTENT.rglob("*.*.*"):
        code = path.suffixes[-2].lstrip(".") if len(path.suffixes) >= 2 else ""
        if LANG.match(code):
            found.add(code)
    return sorted(found, key=lambda c: (c != config.DEFAULT_LANG, c))


def course(lang: str) -> dict[str, Any]:
    return _yaml(config.CONTENT / "course.yaml", lang)


def _folders() -> list[tuple[int, str, Path]]:
    out = []
    if not config.STEPS.exists():
        return out
    for folder in sorted(config.STEPS.iterdir()):
        prefix, _, slug = folder.name.partition("-")
        if folder.is_dir() and prefix.isdigit() and (folder / "step.yaml").exists():
            out.append((int(prefix), slug, folder))
    return out


def _step(order: int, slug: str, folder: Path, lang: str, full: bool) -> dict[str, Any]:
    meta = _yaml(folder / "step.yaml", lang)
    parts = []
    for index, part in enumerate(meta.get("parts") or [{"body": "step.md"}]):
        entry = {"id": str(part.get("id", "")), "label": part.get("label", ""),
                 "headline": part.get("headline", ""),
                 # The live venue panel in a left column, for this part only.
                 "venue": bool(part.get("venue"))}
        if full:
            entry |= {
                "body": _text(folder / part["body"], lang) if part.get("body") else "",
                "exercises": part.get("exercises") or {},
                "checks": [_public(c) for c in part.get("checks") or []],
                # What the ADK web UI and the venue should show: the top of the verify card.
                "expect": part.get("expect") or [],
                "checksTitle": part.get("checksTitle", ""),
            }
        else:
            entry["checkCount"] = len(part.get("checks") or [])
        parts.append(entry)
    return {
        "slug": meta.get("slug", slug),
        "order": order,
        "title": meta.get("title", slug),
        "kicker": meta.get("kicker", f"Step {order}"),
        "minutes": int(meta.get("minutes", 10)),
        "color": meta.get("color", "cyan"),
        "summary": meta.get("summary", ""),
        "venue": bool(meta.get("venue")),
        "stage": meta.get("stage"),
        "parts": parts,
    }


def _public(check: dict[str, Any]) -> dict[str, Any]:
    """A check as the page sees it: the probe stays on the server."""
    return {"id": check["id"], "label": check.get("label", ""), "hint": check.get("hint", ""),
            "expected": check.get("expect") == "fail", "note": check.get("note", "")}


def all_steps(lang: str) -> list[dict[str, Any]]:
    return [_step(o, s, f, lang, full=False) for o, s, f in _folders()]


def step(slug: str, lang: str) -> dict[str, Any] | None:
    for order, name, folder in _folders():
        meta = yaml.safe_load((folder / "step.yaml").read_text()) or {}
        if meta.get("slug", name) == slug:
            return _step(order, name, folder, lang, full=True)
    return None


def _raw(slug: str) -> dict[str, Any] | None:
    """The English step.yaml: where commands and probes are looked up."""
    for _, name, folder in _folders():
        meta = yaml.safe_load((folder / "step.yaml").read_text()) or {}
        if meta.get("slug", name) == slug:
            return meta
    return None


def checks(slug: str, part: str | None) -> list[dict[str, Any]]:
    meta = _raw(slug) or {}
    found = []
    for entry in meta.get("parts") or []:
        if part is None or str(entry.get("id", "")) == part:
            found += entry.get("checks") or []
    return found


def task(slug: str, task_id: str) -> dict[str, Any] | None:
    meta = _raw(slug) or {}
    for part in meta.get("parts") or []:
        for exercise in (part.get("exercises") or {}).values():
            for item in exercise.get("tasks") or []:
                if item.get("id") == task_id:
                    return item
    return None
