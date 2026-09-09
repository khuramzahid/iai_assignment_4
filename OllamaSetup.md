# Assignment 4 — Ollama Installation Setup Guide

This guide explains how to set up and run the **tool-using AI agent** for Assignment 4 on **macOS and Windows**.

---

## 1. Requirements

Before running the assignment, make sure you have:

* Python 3.10 or later
* Ollama
* `granite4.1:3b` model
* The Assignment 4 files
* A terminal:

  * **macOS:** Terminal
  * **Windows:** PowerShell or Command Prompt

---

# 2. Install Python

## macOS

Check whether Python is installed:

```bash
python3 --version
```

If Python is not installed, download it from:

https://www.python.org/downloads/

## Windows

Open PowerShell and run:

```powershell
python --version
```

If Python is not installed, download it from:

https://www.python.org/downloads/

During installation, make sure to select:

**Add Python to PATH**

---

# 3. Install Ollama

Ollama runs the local AI model used by the agent.

## macOS

Download Ollama from:

https://ollama.com/download/mac

Install the application and open:

**Applications → Ollama**

Keep Ollama running in the background.

Then open a new Terminal window and verify:

```bash
ollama --version
```

You should see an Ollama version number.

---

## Windows

Download Ollama from:

https://ollama.com/download/windows

Install Ollama using the installer.

After installation, open PowerShell and verify:

```powershell
ollama --version
```

You should see an Ollama version number.

---

# 4. Download the Required AI Model

This assignment uses:

```text
granite4.1:3b
```

Download the model using:

```bash
ollama pull granite4.1:3b
```

This command is the same on macOS and Windows.

Check that the model was installed:

```bash
ollama list
```

You should see:

```text
granite4.1:3b
```

---

# 5. Test Ollama

Before running the Python agent, test that the model works.

Run:

```bash
ollama run granite4.1:3b
```

Then type:

```text
Hello
```

The model should respond.

To exit the model:

```text
/bye
```

---

# 6. Verify the Ollama Server

The Python agent communicates with Ollama through:

```text
http://localhost:11434
```

### macOS

Run:

```bash
curl http://localhost:11434
```

### Windows PowerShell

Run:

```powershell
curl http://localhost:11434
```

You should receive a response similar to:

```text
Ollama is running
```

If you receive a connection error, make sure the Ollama application is running.

---

# 7. Set Up the Python Virtual Environment

A virtual environment keeps the Python packages for this assignment separate from other projects.

## macOS

Navigate to the assignment folder:

```bash
cd "path/to/assignment 4"
```

Create the environment or using conda:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

You should see:

```text
(.venv)
```

in your terminal.

Install the required package:

```bash
pip install requests
```

---

## Windows

Navigate to the assignment folder:

```powershell
cd "path\to\assignment 4"
```

Create the environment or using conda:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

You should see:

```text
(.venv)
```

in your terminal.

Install the required package:

```powershell
pip install requests
```

---

# 8. Run the Agent

Make sure:

1. Ollama is running.
2. `granite4.1:3b` is installed.
3. The Python virtual environment is activated.

Then run:

```bash
python agent.py
```

The program will run the sample questions.

You should see something similar to:

```text
CUSTOMER: order A-1042 ka kya status hai?

[tool] get_order(...)
BOT: Order A-1042 is currently awaiting payment.

tools: get_order
```

---

# 9. Troubleshooting

## Error: `Cannot reach Ollama at localhost:11434`

This means the Ollama server is not running.

### macOS

Open:

**Applications → Ollama**

Then try:

```bash
curl http://localhost:11434
```

### Windows

Make sure Ollama is running.

Then try:

```powershell
curl http://localhost:11434
```

---

## Error: `ollama: command not found`

### macOS

Make sure Ollama has been installed and opened.

Download it from:

https://ollama.com/download/mac

Then close and reopen Terminal.

Try:

```bash
ollama --version
```

### Windows

Restart PowerShell after installing Ollama and run:

```powershell
ollama --version
```

---

## Error: Model not found

If you see an error indicating that:

```text
granite4.1:3b
```

cannot be found, run:

```bash
ollama pull granite4.1:3b
```

Then verify:

```bash
ollama list
```

---

## Error: `ModuleNotFoundError: No module named 'requests'`

Activate your virtual environment and install `requests`:

### macOS

```bash
source .venv/bin/activate
pip install requests
```

### Windows

```powershell
.venv\Scripts\Activate.ps1
pip install requests
```

---

# 10. Quick Setup Checklist

Before submitting/running the assignment, verify:

```text
[ ] Python installed
[ ] Ollama installed
[ ] Ollama application running
[ ] ollama --version works
[ ] granite4.1:3b downloaded
[ ] ollama list shows granite4.1:3b
[ ] Ollama responds on localhost:11434
[ ] Python virtual environment activated
[ ] requests installed
[ ] agent.py runs successfully
```

---
