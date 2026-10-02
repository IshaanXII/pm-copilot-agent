# PM Copilot — Domain Expert AI Agent (Project Management)

Single expert agent covering **Full PM lifecycle**: Planning → Tracking → RAID/Risks → Reporting.
Conversational assistant, **LangChain-based** (`langchain-core` `@tool` + `ChatOpenAI` when key present, offline-mock otherwise).

## Quickstart
```powershell
cd pm_copilot_agent
pip install -r requirements.txt
copy .env.example .env   # optional, for full LLM reasoning
python demo.py           # smoke test, no key needed
python app.py            # interactive chat
```

## How it works
- `config.py` — PM persona / system prompt (PMP + Agile)
- `tools.py` — 6 LangChain tools: `add_task`, `list_tasks`, `update_task_status`, `add_risk`, `list_risks`, `generate_status_report` (JSON-backed in `data/`)
- `agent.py` — `PMCopilot` class: intent routing + LLM polishing + auto WBS → tasks
- `app.py` — conversational CLI (`help`, `demo`)
- `demo.py` — automated verification

## Example
```
> plan launch company website in 6 weeks
> list tasks
> mark T-001 done
> add risk: key designer may leave
> status report   → RAG + Completed / Blocked / Top Risks
```

## Extend next
- Jira/Trello sync as new `@tool`
- Streamlit UI (`st.chat_message`)
- Vector memory for past standups (Chroma + embeddings)
