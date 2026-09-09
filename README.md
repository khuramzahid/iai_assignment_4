# Week 4 Assignment: a shop assistant that does not invent facts

Due: before next week's session. Submit on Discord.

## What is in this folder

| File | What it is |
|---|---|
| `agent.py` | The agent. About 100 lines. You will edit this. |
| `evaluate.py` | Runs your test cases against the agent and prints a score. You do not need to edit this. |
| `cases.json` | Six example test cases. You will replace these with your own ten. |
| `requirements.txt` | One package. |


## Setup (5 minutes)

1. `conda activate iai-week4`
2. `pip install -r requirements.txt`
3. Make sure Ollama is running. Follow `OllamaSetup.md` file.
4. Run `python agent.py`. You should see two questions answered, with the tools it used.
5. Run `python agent.py --naive`. Same questions, no tools. Compare the answers.
6. Run `python evaluate.py`. You should see a score out of 6.

If step 4 fails with a connection error, Ollama is not running. Start it and try again.

## Part 1: point the agent at a business you know

Pick a business you know well. Your own shop, a family business, a tuition centre, your employer's support desk. It must be a real kind of business, because you need to know when the agent's answer is wrong.

In `agent.py`, edit the parts marked `TODO`:

1. Replace the sample tables and rows with tables for your business. Invent the data. Do not use real customer names, phone numbers, or amounts.
2. Replace the three lookup tools with tools that read your tables.
3. Keep at least one action that cannot be undone (for example: confirm an order, cancel a booking). Leave it in `NEEDS_HUMAN` so the agent must ask before doing it.
4. Update the tool list in `PLAN` so the model knows what your tools are called.

When you are done, `python agent.py --ask "your question"` should answer from your data.

## Part 2: write ten test cases

Do this before you finish Part 1. Write the cases first, then make the agent pass them.

Put ten cases in `cases.json`, in the same format as the six examples. Each case has:

- `question`: what a customer would type
- `needs`: which tools the agent should call
- `must_say`: words that should appear in a correct answer (any one of them is enough)
- `must_not_dispatch`: `true` if the agent should not perform the irreversible action

At least four of the ten must be questions your data cannot answer. For those, `must_say` should contain phrases like `"not have"`, `"no record"`, `"cannot"`.

Then run `python evaluate.py`.

## Part 3: write up the result

Create `results.txt` with:

1. The full output of `python evaluate.py`.
2. For each case that failed: one or two sentences on why.
3. One case where the agent invented a fact, and what you changed to stop it. If this never happened, say so and explain why you think your cases did not catch it.

## What to submit

1. `agent.py`
2. `cases.json`
3. `results.txt`

Put them in a folder with your name and post it on Discord.

## What good work looks like

1. The agent answers from tools and refuses when the data has no answer.
2. Ten cases, at least four refusals, written before the agent passed them.
3. `results.txt` explains the failures clearly.

A run of 6/10 with a clear explanation of the four failures is better work than 10/10 with no explanation.

## Two rules

1. Do not connect this to a real WhatsApp number. Not yours, not your employer's.
2. Do not use real customer data. Invent every row.

## Bonus

Two directions if you want to go further. Pointers only.

### Bonus 1: turn it into a real app

The agent in `agent.py` reads from an in-memory database that is rebuilt every run. To make it a real, queryable application:

1. Store the data in a file. Change `sqlite3.connect(":memory:")` to `sqlite3.connect("shop.db")`. The data now persists between runs. If your business data is in a spreadsheet, load it with `pandas.read_csv` and write it to the database once.
2. Give it a chat interface. In Week 3 you used Gradio. `pip install gradio`, then `gr.ChatInterface(lambda msg, history: run(msg)["answer"]).launch()`. That gives you a web page where a customer types and the agent answers.
3. Add tools. One function per kind of question your business gets. Add each one to `TOOLS` and to the list in `PLAN`. Keep anything that cannot be undone in `NEEDS_HUMAN`.
4. Keep the approval gate. As you add actions, the gate is the part that protects the business.

### Bonus 2: see the agent's steps as a trace in LangSmith

LangSmith shows each run as a tree: the model asking for a tool, the tool running, the model answering. A free account is enough.

1. Create an account at smith.langchain.com and make an API key (Settings, API Keys).
2. `pip install langsmith`
3. In your terminal:
   ```
   export LANGSMITH_API_KEY=your_key
   export LANGSMITH_TRACING=true
   export LANGSMITH_PROJECT=week4-agent
   ```
4. In `agent.py`, add `from langsmith import traceable` at the top, and put `@traceable` on the line above `def run`, `def ask`, and each tool function.
5. Run `python agent.py`, then open smith.langchain.com. Each question is one trace. Click it to see every step.

To run your ten cases as a LangSmith experiment (one row per case, with the scores), use `client.evaluate`. A worked example is in the course repo at `week4-agents/week4/_old/eval_langsmith.py`. The LangSmith evaluation quickstart covers the same steps: docs.langchain.com/langsmith/evaluation-quickstart

## If you get stuck

- The agent calls the same tool twice and stops: the model ignored the instruction not to repeat. This is expected sometimes. The step limit stops it.
- The agent answers without calling any tool: look at `PLAN`. The tool description may not match the question.
- The agent invents a fact: that is what Part 3 asks you to find and report.

Post questions in the Discord channel. The TAs answer within a day.
