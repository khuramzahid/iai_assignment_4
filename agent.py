"""A tool-using agent.

    python agent.py                 answer the two sample questions using tools
    python agent.py --naive         same questions, no tools
    python agent.py --ask "..."     ask your own question
    python agent.py --approve       auto-approve the irreversible action (for testing)

The model asks for a tool. This script decides whether to run it.
"""
import argparse
import json
import sqlite3

import requests

MODEL = "granite4.1:3b"
OLLAMA = "http://localhost:11434/v1/chat/completions"
MAX_STEPS = 4


# 1. Data. TODO: replace these tables and rows with your own business.
#    Invent the data. Do not use real customer names or numbers.

DB = sqlite3.connect(":memory:", check_same_thread=False)
DB.row_factory = sqlite3.Row
DB.executescript("""
CREATE TABLE orders(id TEXT, customer TEXT, item TEXT, amount INT, status TEXT);
CREATE TABLE payments(order_id TEXT, method TEXT, amount INT, received TEXT);
CREATE TABLE stock(item TEXT, size TEXT, on_hand INT);

INSERT INTO orders VALUES
 ('A-1041', 'Bilal', 'Lawn kurta',    3200, 'dispatched'),
 ('A-1042', 'Sana',  'Khaddar shawl', 4500, 'awaiting_payment'),
 ('A-1043', 'Hamza', 'Cotton shalwar',5600, 'packed');

INSERT INTO payments VALUES ('A-1041', 'easypaisa', 3200, '2026-08-21');

INSERT INTO stock VALUES ('Khaddar shawl', 'M', 7), ('Lawn kurta', 'M', 0);
""")


# 2. Tools. TODO: replace these with tools that read your tables.
#    Each tool takes simple arguments and returns a dict.

def get_order(order_id):
    row = DB.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    return dict(row) if row else {"error": f"no order {order_id}"}


def get_payment(order_id):
    row = DB.execute("SELECT * FROM payments WHERE order_id=?", (order_id,)).fetchone()
    return dict(row) if row else {"order_id": order_id, "payment": "NO RECORD FOUND"}


def get_stock(item):
    row = DB.execute("SELECT * FROM stock WHERE item LIKE ?", (f"%{item}%",)).fetchone()
    return dict(row) if row else {"item": item, "on_hand": "UNKNOWN"}


def dispatch(order_id):
    return {"dispatched": order_id}


# Tools the model may use freely.
TOOLS = {"get_order": get_order, "get_payment": get_payment, "get_stock": get_stock}

# Tools that cannot be undone. A person must approve these before they run.
NEEDS_HUMAN = {"dispatch": dispatch}


# 3. The model. TODO: if you rename or add tools, update the list in PLAN.

def ask(system, user):
    try:
        r = requests.post(OLLAMA, timeout=120, json={
            "model": MODEL, "temperature": 0, "max_tokens": 160,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}]})
    except requests.exceptions.ConnectionError:
        raise SystemExit("Cannot reach Ollama at localhost:11434. Start the Ollama app and try again.")
    return r.json()["choices"][0]["message"]["content"].strip()


PLAN = """Pick ONE tool, or say done. Reply with JSON only.
{"tool":"get_order","args":{"order_id":"A-1042"}}   order status
{"tool":"get_payment","args":{"order_id":"A-1042"}} did the money arrive
{"tool":"get_stock","args":{"item":"shawl"}}        is it in stock
{"tool":"dispatch","args":{"order_id":"A-1042"}}    send the order (cannot be undone)
{"tool":"done","args":{}}                           you have enough facts

Rules:
- Never pick a tool whose result is already in FACTS.
- Before dispatch you must have the order, the payment, and the stock in FACTS.
- Only say done when the question can be answered from FACTS."""

SPEAK = ("You are a shop assistant. Answer only from the FACTS below. "
         "If a fact is missing, say you do not have it. Never guess a price, "
         "a date, stock, or a payment. Two short sentences of plain English.")


def first_json(text):
    """Return the first JSON object in the model's reply, or {} if there is none."""
    i = text.find("{")
    if i < 0:
        return {}
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[i:])
        return obj if isinstance(obj, dict) else {}
    except ValueError:
        return {}


# 4. The agent loop. You do not need to change this.

def run(question, approve=None, quiet=False):
    facts, trail = [], []

    for _ in range(MAX_STEPS):
        raw = ask(PLAN, f"QUESTION: {question}\nFACTS SO FAR: {json.dumps(facts)}")
        want = first_json(raw)
        name, args = want.get("tool"), want.get("args", {})

        if name == "done" or not name:
            break

        if name in NEEDS_HUMAN:
            if approve is None:
                ok = input(f"  approve {name}({args})? [y/N] ").strip().lower() == "y"
            else:
                ok = approve
            trail.append(f"{name}:{'approved' if ok else 'REFUSED'}")
            if not quiet:
                print(f"  [gate] {name} {'approved' if ok else 'REFUSED, nothing sent'}")
            facts.append({name: NEEDS_HUMAN[name](**args) if ok else "refused by human"})
            continue

        if name not in TOOLS:
            if not quiet:
                print(f"  [blocked] {name} is not a tool")
            break

        if name in trail:
            break

        result = TOOLS[name](**args)
        trail.append(name)
        facts.append({name: result})
        if not quiet:
            print(f"  [tool] {name}({args}) -> {result}")

    answer = ask(SPEAK, f"FACTS: {json.dumps(facts)}\nCUSTOMER: {question}")
    return {"answer": answer, "trail": trail, "facts": facts}


def naive(question):
    return ask("You are a shop assistant. Reply in two short sentences.", question)


# 5. Run it.

SAMPLE_QUESTIONS = [
    "order A-1042 ka kya status hai?",
    "maine payment kar di hai, dispatch kar do",
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--naive", action="store_true")
    parser.add_argument("--ask")
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args()

    for q in ([args.ask] if args.ask else SAMPLE_QUESTIONS):
        print(f"\nCUSTOMER: {q}")
        if args.naive:
            print(f"     BOT: {naive(q)}")
        else:
            out = run(q, approve=args.approve or None)
            print(f"     BOT: {out['answer']}")
            print(f"   tools: {' -> '.join(out['trail']) or 'none'}")
