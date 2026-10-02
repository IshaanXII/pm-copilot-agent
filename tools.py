"""LangChain tools backed by local JSON storage. No external PM system needed."""
import json
import os
from datetime import date, datetime
from langchain_core.tools import tool

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")
RISKS_FILE = os.path.join(DATA_DIR, "risks.json")

os.makedirs(DATA_DIR, exist_ok=True)
for f, default in [(TASKS_FILE, []), (RISKS_FILE, [])]:
    if not os.path.exists(f):
        with open(f, "w") as fh:
            json.dump(default, fh, indent=2)

def _load(path):
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w") as fh:
            json.dump([], fh)
        return []
    with open(path) as fh:
        return json.load(fh)

def _save(path, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)

@tool
def add_task(title: str, owner: str = "unassigned", due_date: str = "", effort_days: float = 1.0, priority: str = "Medium") -> str:
    """Add a project task. Args: title, owner, due_date (YYYY-MM-DD), effort_days, priority (Low/Medium/High)."""
    tasks = _load(TASKS_FILE)
    tid = f"T-{len(tasks)+1:03d}"
    tasks.append({
        "id": tid, "title": title, "owner": owner, "due_date": due_date,
        "effort_days": effort_days, "priority": priority,
        "status": "todo", "blocker": "", "created": str(date.today())
    })
    _save(TASKS_FILE, tasks)
    return f"Added {tid}: {title} | owner={owner} | due={due_date or 'TBD'} | priority={priority}"

@tool
def list_tasks(status_filter: str = "all") -> str:
    """List tasks. status_filter: all/todo/in-progress/blocked/done/overdue."""
    tasks = _load(TASKS_FILE)
    if not tasks:
        return "No tasks yet. Use add_task or plan_project to create some."
    today = str(date.today())
    rows = []
    for t in tasks:
        if status_filter == "overdue":
            if not (t["due_date"] and t["due_date"] < today and t["status"] != "done"):
                continue
        elif status_filter != "all" and t["status"] != status_filter:
            continue
        rows.append(f"{t['id']} | {t['status']:11} | {t['priority']:6} | {t['owner']:12} | due:{t['due_date'] or 'TBD':10} | {t['title']}" + (f" [BLOCKER: {t['blocker']}]" if t["blocker"] else ""))
    return "\n".join(rows) if rows else f"No tasks matching '{status_filter}'."

@tool
def update_task_status(task_id: str, status: str, blocker: str = "") -> str:
    """Update task status. status must be todo/in-progress/blocked/done. Optionally set blocker reason."""
    tasks = _load(TASKS_FILE)
    for t in tasks:
        if t["id"].lower() == task_id.lower():
            t["status"] = status
            if blocker:
                t["blocker"] = blocker
            elif status != "blocked":
                t["blocker"] = ""
            t["updated"] = datetime.now().isoformat(timespec="seconds")
            _save(TASKS_FILE, tasks)
            return f"Updated {t['id']} -> {status}" + (f" | blocker: {blocker}" if blocker else "")
    return f"Task {task_id} not found."

@tool
def add_risk(description: str, likelihood: int = 3, impact: int = 3, mitigation: str = "", owner: str = "unassigned") -> str:
    """Log a RAID risk. likelihood 1-5, impact 1-5. Score = LxI. Auto-flags High if >=15."""
    risks = _load(RISKS_FILE)
    score = int(likelihood) * int(impact)
    level = "High" if score >= 15 else ("Medium" if score >= 8 else "Low")
    rid = f"R-{len(risks)+1:03d}"
    risks.append({
        "id": rid, "description": description, "likelihood": likelihood,
        "impact": impact, "score": score, "level": level,
        "mitigation": mitigation, "owner": owner, "date": str(date.today())
    })
    _save(RISKS_FILE, risks)
    return f"Logged {rid}: {description} | score={score} ({level}) | owner={owner}"

@tool
def list_risks() -> str:
    """List all risks in RAID log sorted by score desc."""
    risks = _load(RISKS_FILE)
    if not risks:
        return "RAID log empty."
    risks = sorted(risks, key=lambda r: r["score"], reverse=True)
    return "\n".join([f"{r['id']} | {r['level']:6}({r['score']:2}) | {r['owner']:12} | {r['description']} | Mitigation: {r['mitigation'] or 'TBD'}" for r in risks])

@tool
def generate_status_report() -> str:
    """Generate a weekly RAG status report from current tasks + risks."""
    tasks = _load(TASKS_FILE)
    risks = _load(RISKS_FILE)
    today = str(date.today())
    done = [t for t in tasks if t["status"] == "done"]
    prog = [t for t in tasks if t["status"] == "in-progress"]
    blocked = [t for t in tasks if t["status"] == "blocked"]
    overdue = [t for t in tasks if t["due_date"] and t["due_date"] < today and t["status"] != "done"]
    high_risks = [r for r in risks if r["level"] == "High"]

    if blocked or len(high_risks) > 0 or len(overdue) > 2:
        rag = "[RED]"
    elif blocked or overdue or high_risks or len(prog) > 5:
        rag = "[AMBER]"
    else:
        rag = "[GREEN]"

    completed_lines = [f"- {t['id']} {t['title']} ({t['owner']})" for t in done] or ["- none"]
    prog_lines = [f"- {t['id']} {t['title']} -- {t['owner']}, due {t['due_date'] or 'TBD'}" for t in prog] or ["- none"]
    blocked_lines = [f"- {t['id']} {t['title']} -- {t['blocker'] or 'overdue '+t['due_date']}" for t in blocked + overdue] or ["- none"]
    top_risks = sorted(risks, key=lambda x: x['score'], reverse=True)[:5]
    risk_lines = [f"- {r['id']} [{r['level']}] {r['description']} -> {r['mitigation'] or 'mitigation TBD'}" for r in top_risks] or ["- none"]

    lines = [f"# Weekly Status Report -- {today}", f"**RAG: {rag}**", "",
             f"Total: {len(tasks)} | Done: {len(done)} | In-progress: {len(prog)} | Blocked: {len(blocked)} | Overdue: {len(overdue)} | High risks: {len(high_risks)}", "",
             "## Completed"] + completed_lines + ["", "## In-Progress"] + prog_lines + ["", "## Blocked / Overdue"] + blocked_lines + ["", "## Top Risks"] + risk_lines + ["", "## Next 7 days: focus on unblocking + closing overdue items."]
    return "\n".join(lines)

ALL_TOOLS = [add_task, list_tasks, update_task_status, add_risk, list_risks, generate_status_report]
