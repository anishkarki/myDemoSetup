import os
import json
from transformers import pipeline

# Choose your model: local (Ollama/LM Studio) or HuggingFace Hub
# For local: set pipeline(model="path/to/your/model")
# For HuggingFace: set pipeline(model="mistralai/Mistral-7B-Instruct-v0.2")
# You can also use Llama 2, Falcon, etc.

# Example: Use HuggingFace Hub (requires internet and HF token)
classifier = pipeline("text-classification", model="mistralai/Mistral-7B-Instruct-v0.2")

# Load log lines (replace with your log file or OpenSearch export)
with open("postgres_logs.jsonl") as f:
    logs = [json.loads(line) for line in f]

# Analyze each log line
results = []
for entry in logs:
    log_line = entry.get("_raw") or str(entry)
    prompt = f"Is this log line an anomaly or indicative of a problem? Explain why.\nLog: {log_line}"
    result = classifier(prompt)
    results.append({"log": log_line, "analysis": result})

# Save results for review or re-indexing
with open("log_llm_analysis.jsonl", "w") as out:
    for r in results:
        out.write(json.dumps(r) + "\n")

print("LLM log analysis complete. Results saved to log_llm_analysis.jsonl")
