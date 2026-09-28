# Testing Guide: Langfuse Telemetry & Laya 421M Router

This guide explains how to test the two major architectural optimizations recently added to the AegisForge-AI workbench:
1. **Langfuse Telemetry:** Deep observability for LLM chain-of-thought, tool invocation, and token tracking.
2. **Laya 421M Router:** Ultra-low latency intent classification using a sub-500M parameter model.

---

## 🛠️ Part 1: Testing Langfuse Telemetry

### Step 1: Start Langfuse Locally (Air-Gapped via Docker)
Since this project is air-gapped, we run Langfuse on a local Docker container instead of the cloud.
1. Make sure Docker Desktop is running on your system.
2. Run the following commands in your terminal:
```bash
git clone https://github.com/langfuse/langfuse.git
cd langfuse
docker compose up -d
```
3. Open your browser and go to `http://localhost:3000`.
4. Create a local admin account and create a new project (e.g., "AegisForge-AI").
5. Go to **Settings > API Keys** and generate a new Public and Secret Key.

### Step 2: Configure Environment Variables
In the terminal where you plan to run the AegisForge-AI backend, set the variables you just generated:

**For Windows (PowerShell):**
```powershell
$env:LANGFUSE_SECRET_KEY="sk-lf-..."
$env:LANGFUSE_PUBLIC_KEY="pk-lf-..."
$env:LANGFUSE_HOST="http://localhost:3000"
```

**For Linux/Mac (Bash):**
```bash
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_HOST="http://localhost:3000"
```

### Step 3: Run the Pipeline and View Traces
1. Start the main backend in the same terminal: `uv run main.py` or `python main.py`.
2. Submit a complex query to the assistant, such as: *"Calculate the ASME UG-27 wall thickness for 11-V-102 at 14.5 MPa."*
3. Return to the Langfuse Dashboard (`http://localhost:3000`), click on **Traces**, and you will see a detailed visual tree of the agent's thought process, latency metrics, and exact tool invocations.

*(Failsafe Note: If you do not set these environment variables, the system will log a warning and run normally without crashing.)*

---

## ⚡ Part 2: Testing Laya 421M Ultra-Low Latency Router

The `laya:421m` model was integrated to replace heavy 8B models for the initial intent classification, dramatically reducing latency and saving VRAM.

### Step 1: Pull the Laya Model
Ensure the Laya model is available in your local Ollama instance. Run this in your terminal:
```bash
ollama run laya:421m
# Press Ctrl+D to exit after it finishes downloading
```

### Step 2: Test the Triage Latency (Terminal Test)
1. Start the backend: `uv run main.py` or `python main.py`
2. First, test a **basic conversational greeting**: 
   - Prompt: *"Hello, how are you?"*
   - Watch the console logs. You should see a log immediately triggering: `Router LLM (Laya) classified 'Hello, how are you?...' -> direct_answer`.
   - Notice how much faster the response is compared to before (often under 100ms!).
3. Next, test a **complex engineering task**:
   - Prompt: *"Write a python script in the sandbox to calculate primes."*
   - Watch the console logs. Laya will instantly trigger: `Router LLM (Laya) classified 'Write a python script...' -> supervisor`.
   - The heavy 7B/8B models (like `qwen2.5-coder` or `llama3.1:8b`) will now take over in the background to do the hard work.

### Expected Behavior
- **VRAM Usage:** You should notice less memory swapping when the application starts routing.
- **Fallback Safety:** Even if Laya outputs improperly formatted JSON, the custom regex fallback inside `pipeline.py` guarantees it will securely default to the `supervisor` route without throwing any exceptions.
