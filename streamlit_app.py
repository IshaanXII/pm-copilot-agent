"""PM Copilot Web UI — Streamlit chat interface."""
import streamlit as st
from agent import build_agent
from tools import list_tasks, list_risks

st.set_page_config(page_title="PM Copilot", page_icon="📋", layout="wide")

@st.cache_resource
def get_bot():
    return build_agent()

bot = get_bot()

st.title("📋 PM Copilot — Project Management Expert")
st.caption(f"Mode: `{bot.mode}` | Planning • Tracking • RAID • Reporting | Groq free tier, no paid key needed")

# Sidebar
with st.sidebar:
    st.header("Quick actions")
    if st.button("✨ Demo plan: website 6 weeks"):
        st.session_state["pending"] = "plan launch company website in 6 weeks"
    if st.button("📝 List tasks"):
        st.session_state["pending"] = "list tasks"
    if st.button("⚠️ List risks"):
        st.session_state["pending"] = "list risks"
    if st.button("📊 Status report"):
        st.session_state["pending"] = "status report"
    st.divider()
    st.subheader("Live data")
    try:
        st.code(list_tasks.invoke({"status_filter": "all"})[:1500] or "No tasks", language="text")
        st.code(list_risks.invoke({})[:1000] or "No risks", language="text")
    except Exception as e:
        st.error(str(e))
    if st.button("🗑️ Clear chat"):
        st.session_state["messages"] = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Hi! I'm your PM Copilot. Try:\n- `plan launch website in 6 weeks`\n- `add task: draft UAT cases`\n- `mark T-001 done`\n- `add risk: vendor delay`\n- `status report`"}
    ]

# Pending quick action
if st.session_state.get("pending"):
    st.session_state["messages"].append({"role": "user", "content": st.session_state.pop("pending")})

# Render history
for m in st.session_state["messages"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Chat input
if prompt := st.chat_input("Ask PM Copilot... (e.g. plan, status, risk)"):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                reply = bot.chat(prompt)
            except Exception as e:
                reply = f"Error: {e}"
            st.markdown(reply)
    st.session_state["messages"].append({"role": "assistant", "content": reply})
    st.rerun()
