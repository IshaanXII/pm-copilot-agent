"""PM Copilot single expert agent — LangChain tools + OpenAI (with offline fallback)."""
import os
import re
from dotenv import load_dotenv
from config import PM_COPILOT_SYSTEM_PROMPT
from tools import ALL_TOOLS, add_task, list_tasks, update_task_status, add_risk, list_risks, generate_status_report

load_dotenv()
TOOL_MAP = {t.name: t for t in ALL_TOOLS}

def _get_secret(name: str, default: str = "") -> str:
    # 1. env / .env, 2. Streamlit Cloud secrets
    v = os.getenv(name, "")
    if v:
        return v
    try:
        import streamlit as st
        if hasattr(st, "secrets") and name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return default

DEFAULT_WBS = [
    ("Define scope & success criteria", 2), ("Stakeholder kickoff", 1),
    ("Design / prototype", 5), ("Build MVP", 10), ("QA & UAT", 4),
    ("Launch & rollout", 2), ("Retrospective & handover", 1),
]

def _get_llm():
    # Priority: free options first (Groq/Gemini/Ollama), then OpenAI paid
    # Works locally via .env and on Streamlit Cloud via st.secrets
    # 1. Groq free tier
    if _get_secret("GROQ_API_KEY", ""):
        try:
            from langchain_groq import ChatGroq
            print("[PM Copilot] using Groq (free tier)")
            return ChatGroq(model=_get_secret("GROQ_MODEL", "openai/gpt-oss-20b"), temperature=0.3)
        except Exception as e:
            print(f"[warn] Groq init failed: {e}")
    # 2. Gemini free tier
    if os.getenv("GOOGLE_API_KEY", ""):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            print("[PM Copilot] using Gemini (free tier)")
            return ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"), temperature=0.3)
        except Exception as e:
            print(f"[warn] Gemini init failed: {e}")
    # 3. Ollama local (fully free, offline)
    if os.getenv("USE_OLLAMA", "").lower() in ("1", "true", "yes"):
        try:
            from langchain_ollama import ChatOllama
            print("[PM Copilot] using Ollama local")
            return ChatOllama(model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"))
        except Exception as e:
            print(f"[warn] Ollama init failed (is 'ollama serve' running?): {e}")
    # 4. OpenAI paid
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and not api_key.startswith("sk-your"):
        try:
            from langchain_openai import ChatOpenAI
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            return ChatOpenAI(model=model, temperature=0.3)
        except Exception as e:
            print(f"[warn] OpenAI init failed, using offline mode: {e}")
    return None

class PMCopilot:
    """Single domain-expert agent. Conversational, tool-calling."""

    def __init__(self):
        self.llm = _get_llm()
        if self.llm:
            name = type(self.llm).__name__
            self.mode = {"ChatGroq": "groq-free", "ChatGoogleGenerativeAI": "gemini-free", "ChatOllama": "ollama-local"}.get(name, "openai")
        else:
            self.mode = "offline-mock"
        print(f"[PM Copilot] mode={self.mode}")

    # ---- planning helper ----
    def plan_project(self, goal: str, owner: str = "unassigned") -> str:
        if self.llm:
            from langchain_core.messages import SystemMessage, HumanMessage
            resp = self.llm.invoke([
                SystemMessage(content=PM_COPILOT_SYSTEM_PROMPT),
                HumanMessage(content=f"Create a concise WBS for goal: {goal}. Output table: Task | Owner role | Effort(days) | Dependency. Max 10 tasks.")
            ])
            wbs_text = resp.content
        else:
            wbs_text = f"WBS for: {goal}\n" + "\n".join([f"- {t} ({d}d)" for t, d in DEFAULT_WBS])
        # auto-add as tasks
        added = []
        items = DEFAULT_WBS if not self.llm else DEFAULT_WBS  # keep deterministic task creation
        # if LLM mode, try to parse lines, else fallback
        for title, eff in items:
            added.append(add_task.invoke({"title": f"{goal[:40]}: {title}", "owner": owner, "effort_days": float(eff)}))
        return wbs_text + "\n\n[I auto-added these as tasks:]\n" + "\n".join(added)

    def chat(self, user_msg: str) -> str:
        m = user_msg.lower().strip()

        if "status" in m or "report" in m or "rag" in m or "weekly" in m:
            return generate_status_report.invoke({})

        if "risk" in m and ("add" in m or "log" in m or "new" in m or ":" in user_msg):
            desc = user_msg.split(":", 1)[1].strip() if ":" in user_msg else user_msg
            return add_risk.invoke({"description": desc})

        # intent routing (works in both modes; LLM polishes final text if available)
        if re.search(r"\b(plan|wbs|kick ?off|new project|launch)\b", m) and len(m) > 10:
            goal = user_msg
            out = self.plan_project(goal)
            return self._polish(f"Here's your project plan for: '{user_msg}'\n\n{out}\n\nWant owners/dates assigned?") if self.llm else out

        if m.startswith("add task") or "add a task" in m or m.startswith("create task"):
            title = re.sub(r"^(add|create)(\s+a)?\s+task\s*:?\s*", "", user_msg, flags=re.I)
            return add_task.invoke({"title": title or user_msg})

        if "block" in m:
            # try to find T-00x
            tid = re.search(r"T-\d+", user_msg, re.I)
            if tid:
                return update_task_status.invoke({"task_id": tid.group(0).upper(), "status": "blocked", "blocker": user_msg})
            return "Which task ID is blocked? (e.g. T-001). Use 'list tasks' to see IDs."

        if "done" in m or "complete" in m:
            tid = re.search(r"T-\d+", user_msg, re.I)
            if tid:
                return update_task_status.invoke({"task_id": tid.group(0).upper(), "status": "done"})
        
        if "list" in m and "task" in m:
            f = "all"
            for s in ["todo", "in-progress", "blocked", "done", "overdue"]:
                if s in m: f = s
            return list_tasks.invoke({"status_filter": f})

        if "list" in m and "risk" in m:
            return list_risks.invoke({})

        # default: LLM answer or offline help
        if self.llm:
            from langchain_core.messages import SystemMessage, HumanMessage
            ctx = list_tasks.invoke({"status_filter": "all"})[:2000] + "\n" + list_risks.invoke({})[:2000]
            resp = self.llm.invoke([
                SystemMessage(content=PM_COPILOT_SYSTEM_PROMPT + f"\n\nCurrent tasks:\n{ctx}"),
                HumanMessage(content=user_msg)
            ])
            return resp.content
        return ("I'm your PM Copilot (offline mode — set OPENAI_API_KEY for full reasoning).\n"
                "Try: 'plan website launch in 6 weeks' | 'list tasks' | 'add task: write UAT cases' | "
                "'mark T-001 done' | 'status report' | 'list risks'")

    def _polish(self, draft: str) -> str:
        return draft  # hook for future formatting

def build_agent() -> PMCopilot:
    return PMCopilot()
