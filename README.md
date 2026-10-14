# hrms-mcp

Personal MCP server for the Falkenherz HRMS (ppl.falkenherz.net). Nothing runs on a schedule:
Claude punches in/out **only when you say "start day" / "end day"**, and submits the task list
you actually worked on that day.

## Tools
| Tool | What it does |
|---|---|
| `start_day(planned_tasks, is_wfh)` | Punch in (`POST /duty/start`), sends planned tasks as `start_task` |
| `log_task(description)` | Add a task to today's local journal (`~/.hrms-mcp/tasks.jsonl`) |
| `list_tasks` | Show today's tasks |
| `end_day(notes?, dry_run?)` | Punch out via `/duty/end/id/{open duty id}` (found from `timeline`); sends logged tasks as `end_task` |
| `timeline` | Raw `/duty/timeline` records for today |

## Setup
1. `python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
2. `cp .env.example .env` and fill it in. Set HRMS_TOKEN (Bearer token) or the login path+credentials.
   punch-out URL paths, and how login returns auth (token in JSON, or cookie). Alternatively set
   `HRMS_TOKEN` directly.
3. Register in Claude Code: `claude mcp add hrms -- /path/to/.venv/bin/python -m hrms_mcp.server`
   (run from the repo root), or add the same command to Claude Desktop's config.
4. Tests: `pip install pytest responses && pytest`.

`.env` is gitignored; never commit credentials.
