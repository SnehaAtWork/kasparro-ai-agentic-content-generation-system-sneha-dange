# config.py
from dotenv import load_dotenv
import os

load_dotenv(override=True)

# Optional LLM toggle
USE_OLLAMA = os.getenv("USE_OLLAMA", "0").lower() in ("1", "true", "yes")

# Ollama settings
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")
