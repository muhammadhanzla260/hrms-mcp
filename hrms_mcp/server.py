"""MCP server: explicit start/end-day punches plus a task journal."""
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import journal
from .client import HRMSClient, HRMSError


def _load_dotenv() -> None:
    path = Path(os.environ.get("HRMS_ENV_FILE", Path(__file__).parent.parent / ".env"))
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()
mcp = FastMCP("hrms")
_client: HRMSClient | None = None


def _c() -> HRMSClient:
    global _client
    if _client is None:
        _client = HRMSClient()
    return _client


@mcp.tool()
def log_task(description: str) -> str:
    """Record a task you actually worked on today. Included when you end the day."""
    journal.add_task(description)
    return f"Logged. Today so far: {len(journal.tasks_for())} task(s)."


@mcp.tool()
def list_tasks() -> list[str]:
    """Tasks logged today (what end_day would submit)."""
    return journal.tasks_for()


@mcp.tool()
def start_day(planned_tasks: list[str], is_wfh: bool = True) -> str:
    """Punch in with today's planned tasks. Only call when the user explicitly
    says to start their day; ask for the planned tasks if not given."""
    for t in planned_tasks:
        journal.add_task(t)
    try:
        return f"Started: {_c().start_day(planned_tasks, is_wfh)}"
    except HRMSError as e:
        return f"Failed: {e}"


@mcp.tool()
def end_day(notes: str = "") -> str:
    """Punch out, submitting today's logged tasks. Only call when the user
    explicitly says to end their day. Show the task list to the user first."""
    tasks = journal.tasks_for()
    if not tasks:
        return "No tasks logged today; log tasks first or confirm with the user."
    try:
        return f"Ended with {len(tasks)} task(s): {_c().end_day(tasks, notes)}"
    except HRMSError as e:
        return f"Failed: {e}"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
