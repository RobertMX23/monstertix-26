"""Check the workbench's content after editing it.

    python -m workbench.check

For every step: it loads, each :::exercise in the reading has its tasks in
step.yaml, every figure exists, every probe is one the workbench will run,
every file explorer opens a file the step has, every `highlight` pattern
matches at least one line of that step's code, every :::code block names a
file of that step and highlights at least one of its lines, and no two tasks in
a step share an id (commands are looked up by it). Exits 1 on any problem.
"""

from __future__ import annotations

import re
import shlex
import sys

import yaml

from workbench import config
from workbench.services import checks, content, stage


def main() -> int:
    problems: list[str] = []
    for order, name, folder in content._folders():
        meta = yaml.safe_load((folder / "step.yaml").read_text()) or {}
        slug = meta.get("slug", name)
        try:
            loaded = content.step(slug, config.DEFAULT_LANG)
        except Exception as error:  # noqa: BLE001 - report every step, not the first
            problems.append(f"{slug}: does not load: {error}")
            continue
        task_ids = [task.get("id") for part in meta.get("parts") or []
                    for exercise in (part.get("exercises") or {}).values()
                    for task in exercise.get("tasks") or []]
        for duplicate in sorted({i for i in task_ids if task_ids.count(i) > 1}):
            # Commands and the prompt lab are looked up by task id: two tasks
            # with one id would run the wrong one's command.
            problems.append(f"{slug}: task id {duplicate!r} is used more than once")
        for part in meta.get("parts") or []:
            where = f"{slug}/{part.get('id', '')}"
            body = (folder / part["body"]).read_text() if part.get("body") else ""
            placed = set(re.findall(r':::exercise id="([^"]+)"', body))
            defined = set((part.get("exercises") or {}).keys())
            for missing in placed - defined:
                problems.append(f"{where}: :::exercise {missing} has no tasks in step.yaml")
            for unused in defined - placed:
                problems.append(f"{where}: exercise {unused} is never placed in the reading")
            for placed in re.findall(r':::task id="([^"]+)"', body):
                if placed not in task_ids:
                    problems.append(f"{where}: :::task {placed} is not a task of this step")
            for path, pattern in re.findall(r':::code path="([^"]+)" highlight="([^"]*)"', body):
                number = meta.get("stage")
                source = stage.layout(number).get(path) if number is not None else None
                if source is None:
                    problems.append(f"{where}: :::code {path} is not in step {number}'s code")
                elif not any(re.search(pattern, line) for line in source.read_text(errors="replace").splitlines()):
                    problems.append(f"{where}: :::code highlight matches no line of {path}")
            for image in re.findall(r'src="/docs-img/([^"]+)"', body):
                if not (config.ROOT / "docs" / "img" / image).exists():
                    problems.append(f"{where}: no docs/img/{image}")
            for check in part.get("checks") or []:
                try:
                    checks._vet(shlex.split(checks.fill(check["probe"], {})))
                except Exception as error:  # noqa: BLE001
                    problems.append(f"{where}: check {check.get('id')}: {error}")
            for exercise in (part.get("exercises") or {}).values():
                for task in exercise.get("tasks") or []:
                    if task.get("kind") != "files" or task.get("stage") is None:
                        continue
                    placed_files = stage.layout(task["stage"])
                    if task.get("open") and task["open"] not in placed_files:
                        problems.append(f"{where}: {task['open']} is not in step {task['stage']}")
                    if task.get("highlight"):
                        pattern = re.compile(task["highlight"])
                        only = task.get("only") or ["agent/", "monstertix/"]
                        files = [src for repo, src in placed_files.items()
                                 if any(repo == o or (o.endswith("/") and repo.startswith(o)) for o in only)]
                        if not any(pattern.search(line) for f in files
                                   for line in f.read_text(errors="replace").splitlines()):
                            problems.append(f"{where}: highlight matches no line of step {task['stage']}")
        checks_count = sum(len(p["checks"]) for p in loaded["parts"])
        print(f"  {order:02d} {slug:<14} {len(loaded['parts'])} parts, {checks_count} checks")
    for problem in problems:
        print(f"✗ {problem}")
    print("✓ content is consistent" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
