# test_typer.py
import typer
from logging import getLogger

logger = getLogger(__name__)

app = typer.Typer()

@app.command("hello")
def hello(name: str = "world"):
    logger.info(f"hello {name}")

if __name__ == "__main__":
    app()
