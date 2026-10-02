"""Conversational CLI for PM Copilot."""
from agent import build_agent

BANNER = """
╔══════════════════════════════════════════╗
║  PM COPILOT — Domain Expert Agent        ║
║  Planning • Tracking • RAID • Reporting  ║
║  Type 'help', 'demo', or 'quit'          ║
╚══════════════════════════════════════════╝
"""

HELP = """Commands:
  plan <goal>            e.g. plan launch company website in 6 weeks
  add task: <title>      e.g. add task: draft UAT test cases
  list tasks [filter]    filters: todo/in-progress/blocked/done/overdue
  mark T-001 done|blocked <reason>
  add risk: <desc>       log a risk
  list risks
  status / report        weekly RAG report
  quit
"""

def main():
    print(BANNER)
    bot = build_agent()
    print(bot.chat("hello"))
    while True:
        try:
            u = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not u:
            continue
        if u.lower() in ("quit", "exit"):
            print("PM Copilot: Good luck with delivery!")
            break
        if u.lower() == "help":
            print(HELP); continue
        if u.lower() == "demo":
            for d in ["plan launch company website in 6 weeks", "list tasks",
                      "add risk: key designer may leave, mitigation cross-train backup",
                      "status report"]:
                print(f"\n> {d}\n{bot.chat(d)}")
            continue
        # sugar: mark T-001 done
        import re
        mm = re.match(r"mark\s+(T-\d+)\s+(done|blocked|todo|in-progress)(.*)", u, re.I)
        if mm:
            tid, st, rest = mm.groups()
            print(bot.chat(f"update {tid} to {st} {rest}")); continue
        print(f"\nPM Copilot:\n{bot.chat(u)}")

if __name__ == "__main__":
    main()
