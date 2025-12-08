import typer
from agents.orchestrator import OrchestratorAgent

app = typer.Typer()

@app.command()
def run(input_path: str = "inputs/product_input.json"):
    orch = OrchestratorAgent()
    res = orch.run(input_path)
    print("Pipeline run complete. Artifacts:", res)

if __name__ == "__main__":
    app()