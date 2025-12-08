# test_typer.py
import typer

app = typer.Typer()

@app.command("hello")
def hello(name: str = "world"):
    print(f"hello {name}")

if __name__ == "__main__":
    app()
