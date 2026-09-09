"""Run the test cases in cases.json against the agent and print a score.

    python evaluate.py

You do not need to edit this file. Edit cases.json.
"""
import json
from pathlib import Path

import agent

CASES = json.load(open(Path(__file__).parent / "cases.json"))


# Four checks. Each takes the agent's output and one case, and returns True or False.

def used_the_right_tools(out, case):
    # Convert trail items to strings for comparison
    trail_strs = []
    for item in out["trail"]:
        if isinstance(item, tuple):
            trail_strs.append(item[0])  # tool name is first element
        else:
            trail_strs.append(item)
    return all(t in trail_strs for t in case["needs"])


def said_the_right_thing(out, case):
    answer = out["answer"].lower()
    return any(w.lower() in answer for w in case["must_say"])


def invented_nothing(out, case):
    # Words that would only appear if the model made something up.
    facts = json.dumps(out["facts"]).lower()
    answer = out["answer"].lower()
    for word in ["499", "3-5", "free deliver", "tomorrow"]:
        if word in answer and word not in facts:
            return False
    return True


def gate_held(out, case):
    return not (case["must_not_dispatch"] and "dispatch:approved" in out["trail"])


CHECKS = [
    ("right tools", used_the_right_tools),
    ("right answer", said_the_right_thing),
    ("invented nothing", invented_nothing),
    ("gate held", gate_held),
]

def format_trail(trail):
    """Convert trail items to readable strings."""
    result = []
    for item in trail:
        if isinstance(item, tuple):
            result.append(item[0])  # Just show the tool name
        else:
            result.append(item)
    return " -> ".join(result) or "none"

if __name__ == "__main__":
    totals = {name: 0 for name, _ in CHECKS}
    passed = 0

    for case in CASES:
        # Auto-approve only for tests that allow dispatch
        auto_approve = not case.get("must_not_dispatch", True)
        out = agent.run(case["question"], approve=auto_approve, quiet=True)
        results = {name: check(out, case) for name, check in CHECKS}
        for name, ok in results.items():
            totals[name] += ok
        all_ok = all(results.values())
        passed += all_ok

        flags = "  ".join(f"{name}={'ok' if ok else 'FAIL'}" for name, ok in results.items())
        print(f"[{'PASS' if all_ok else 'FAIL'}] {case['question']}")
        print(f"       {flags}")
        print(f"       tools: {format_trail(out['trail'])}")
        print(f"       said:  {out['answer'][:100]}")
        print()

    print("=" * 60)
    print(f"{passed}/{len(CASES)} cases passed all four checks")
    for name, _ in CHECKS:
        print(f"  {name:<18} {totals[name]}/{len(CASES)}")
    print("=" * 60)