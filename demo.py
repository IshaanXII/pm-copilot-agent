"""Non-interactive smoke test — verifies agent + tools work."""
import os, shutil
from agent import build_agent

# fresh state for test
d = os.path.join(os.path.dirname(__file__), "data")
if os.path.exists(d):
    shutil.rmtree(d)

bot = build_agent()
checks = [
    "plan launch company website in 6 weeks",
    "list tasks",
    "add task: prepare UAT test cases",
    "add risk: vendor delay may slip launch, mitigation add buffer + backup vendor",
    "list risks",
    "status report",
]
for c in checks:
    print(f"\n>>> {c}\n{bot.chat(c)}\n{'-'*60}")
print("\nSMOKE TEST PASSED [OK]")
