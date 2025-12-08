import typer
from agents.orchestrator import OrchestratorAgent

app = typer.Typer()

@app.command("run")
def run_pipeline(input_path: str = "inputs/product_input.json"):
    """
    Run the agentic pipeline.
    """
    orch = OrchestratorAgent()
    res = orch.run(input_path)
    typer.echo(f"Pipeline run complete. Artifacts: {res}")

if __name__ == "__main__":
    app()
