# run_pipeline.py -- argparse-safe runner
import argparse
from pathlib import Path
import sys
import os
import logging
from dotenv import load_dotenv

# load environment from .env (only here)
load_dotenv()

# configure logging once at program start
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

def run_orchestrator(input_path: str):
    try:
        # lazy import to avoid import-time side-effects in modules
        from agents.orchestrator import OrchestratorAgent
    except Exception as e:
        logger.error("[run_pipeline] Error importing OrchestratorAgent: %s", e, exc_info=True)
        raise

    # Build explicit config dict from environment (and/or CLI args)
    config = {
        "ollama_base": os.getenv("OLLAMA_BASE"),         # None if not set
        "use_ollama": os.getenv("USE_OLLAMA", "1"),      # default to "1" unless overridden
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama3:8b"),
        # add more config entries here as needed
    }

    # Pass config into the orchestrator (dependency injection)
    orch = OrchestratorAgent(config=config)
    res = orch.run(input_path)
    logger.info("Pipeline run complete. Artifacts: %s", res)

def main(argv=None):
    parser = argparse.ArgumentParser(prog="run_pipeline", description="Kasparro agentic pipeline runner (argparse)")
    parser.add_argument("input", nargs="?", default="inputs/product_input.json", help="Path to product input JSON")
    args = parser.parse_args(argv)
    input_path = args.input
    p = Path(input_path)
    if not p.exists():
        logger.error("[run_pipeline] Input file not found: %s", p)
        return 2
    try:
        run_orchestrator(input_path)
    except Exception as e:
        logger.error("[run_pipeline] Orchestrator failed: %s", e, exc_info=True)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
