# run_pipeline.py -- argparse-safe runner
import argparse
from pathlib import Path
import sys

def run_orchestrator(input_path: str):
    try:
        # lazy import to avoid import-time side-effects
        from agents.orchestrator import OrchestratorAgent
    except Exception as e:
        print(f"[run_pipeline] Error importing OrchestratorAgent: {e}", file=sys.stderr)
        raise

    orch = OrchestratorAgent()
    res = orch.run(input_path)
    print(f"Pipeline run complete. Artifacts: {res}")

def main(argv=None):
    parser = argparse.ArgumentParser(prog="run_pipeline", description="Kasparro agentic pipeline runner (argparse)")
    parser.add_argument("input", nargs="?", default="inputs/product_input.json", help="Path to product input JSON")
    args = parser.parse_args(argv)
    input_path = args.input
    p = Path(input_path)
    if not p.exists():
        print(f"[run_pipeline] Input file not found: {p}", file=sys.stderr)
        return 2
    try:
        run_orchestrator(input_path)
    except Exception as e:
        print(f"[run_pipeline] Orchestrator failed: {e}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
