"""Local task journal: one JSON line per task, grouped by local date."""
import json
import os
from datetime import date, datetime
from pathlib import Path


def journal_path() -> Path:
    base = Path(os.environ.get("HRMS_MCP_HOME", Path.home() / ".hrms-mcp"))
    base.mkdir(parents=True, exist_ok=True)
    return base / "tasks.jsonl"


def add_task(description: str, day: date | None = None) -> dict:
    entry = {
        "date": (day or date.today()).isoformat(),
        "logged_at": datetime.now().isoformat(timespec="seconds"),
        "task": description.strip(),
    }
    with journal_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def tasks_for(day: date | None = None) -> list[str]:
    path = journal_path()
    if not path.exists():
        return []
    key = (day or date.today()).isoformat()
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        if e["date"] == key and e["task"] not in out:
            out.append(e["task"])
    return out
