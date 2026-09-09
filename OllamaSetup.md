## Assignment 4 — Ollama Installation Setup Guide (Ubuntu)
This section explains how to set up and run the tool-using AI agent for Assignment 4 on Ubuntu.
------------------------------
## 1. Requirements
Before running the assignment, make sure you have:

* Python 3.10 or later
* Ollama
* granite4.1:3b model
* The Assignment 4 files
* Standard Terminal

------------------------------
## 2. Install Python & Venv Tools
Ubuntu comes with Python pre-installed, but you need to install the virtual environment coordinator package to avoid system package blocks:

# Update package list
sudo apt update
# Install python3 and the venv manager
sudo apt install python3 python3-venv curl -y

To verify your installation:

python3 --version

------------------------------
## 3. Install Ollama
On Ubuntu, Ollama is installed and managed via a single terminal command:

curl -fsSL https://ollama.com | sh

Ollama will automatically start as a system service in the background. Verify it works by checking the version:

ollama --version

------------------------------
## 4. Download the Required AI Model
Pull the specific assignment model into Ollama:

ollama pull granite4.1:3b

Check that the model was successfully downloaded:

ollama list

------------------------------
## 5. Test Ollama
Test that the local model runs properly in your terminal:

ollama run granite4.1:3b

Type Hello to confirm a response. To exit, type:

/bye

------------------------------
## 6. Verify the Ollama Server
Confirm the background engine is accessible on your local network port:

curl http://localhost:11434

You should see: Ollama is running.
------------------------------
## 7. Set Up the Python Virtual Environment
To fix the externally-managed-environment error permanently, create a local isolated virtual environment directly inside your project folder using native tools instead of a broken global alias:

# 1. Navigate to your assignment folder
cd ~/Documents/ITU_SeedProgramming/IAI_assignment_4
# 2. Create a fresh virtual environment named .venv
python3 -m venv .venv
# 3. Activate the new environment
source .venv/bin/activate

(Your prompt will change to show (.venv) at the beginning).
Now install your exact assignment specifications safely:

pip install -r requirements.txt

------------------------------
## 8. Run the Agent
With your native .venv environment active, execute the agent script:

python3 agent.py
