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
    return all(t in out["trail"] for t in case["needs"])


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

if __name__ == "__main__":
    totals = {name: 0 for name, _ in CHECKS}
    passed = 0

    for case in CASES:
        out = agent.run(case["question"], approve=False, quiet=True)
        results = {name: check(out, case) for name, check in CHECKS}
        for name, ok in results.items():
            totals[name] += ok
        all_ok = all(results.values())
        passed += all_ok

        flags = "  ".join(f"{name}={'ok' if ok else 'FAIL'}" for name, ok in results.items())
        print(f"[{'PASS' if all_ok else 'FAIL'}] {case['question']}")
        print(f"       {flags}")
        print(f"       tools: {' -> '.join(out['trail']) or 'none'}")
        print(f"       said:  {out['answer'][:100]}")
        print()

    print("=" * 60)
    print(f"{passed}/{len(CASES)} cases passed all four checks")
    for name, _ in CHECKS:
        print(f"  {name:<18} {totals[name]}/{len(CASES)}")
    print("=" * 60)
