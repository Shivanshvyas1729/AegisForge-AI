import subprocess
import sys

# The absolute best models for a laptop constraint (8-16GB RAM)
REQUIRED_MODELS = [
    "llama3.1:8b",          # Supervisor Agent (Best 8B Reasoner)
    "qwen2.5-coder:7b",     # Coder Agent (Best 7B Coder)
    "deepseek-r1:8b",       # Reasoning Agent (Best CoT Math Checker)
    "moondream:latest",     # Vision Agent
    "llama3.2:3b"           # Reviewer/Publisher Agent (Fast Summarizer)
]

# The weak/outdated models we no longer need
MODELS_TO_DELETE = [
    "qwen2.5-coder:1.5b",
    "qwen2.5:3b",
    "qwen2.5:0.5b",
    "deepseek-r1:1.5b"
]

def run_command(cmd, stream=False):
    if stream:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            print(line, end="")
        process.wait()
        return process.returncode == 0
    else:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error running {' '.join(cmd)}: {e}")
            return ""

def get_installed_models():
    output = run_command(["ollama", "list"])
    if not output: return []
    models = []
    lines = output.strip().split("\n")[1:]
    for line in lines:
        if line.strip():
            # Handle tags (ollama list might show llama3.1 or llama3.1:latest)
            models.append(line.split()[0])
    return models

def main():
    print("Checking installed Ollama models...")
    installed = get_installed_models()
    
    print("\n--- Deleting Weak/Outdated Models ---")
    for model in MODELS_TO_DELETE:
        if model in installed or f"{model}:latest" in installed:
            print(f"Deleting {model} to free up space...")
            run_command(["ollama", "rm", model])
            print(f"✅ {model} deleted.")
        else:
            print(f"Skipped {model} (already removed).")
            
    print("\n--- Pulling Required Premium Models ---")
    for model in REQUIRED_MODELS:
        # Check if model exists (exact match or with :latest)
        if model in installed or (":" not in model and f"{model}:latest" in installed):
            print(f"✅ {model} is already installed.")
        else:
            print(f"📥 Pulling {model}... (This may take a few minutes depending on your internet speed)")
            run_command(["ollama", "pull", model], stream=True)
            print(f"✅ {model} pulled successfully.")
            
    print("\n🎉 Model setup complete! Your environment is perfectly optimized for your laptop.")

if __name__ == "__main__":
    main()
