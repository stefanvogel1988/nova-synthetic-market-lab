import typer

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """NOVA Synthetic Market Lab command-line interface."""


@app.command()
def validate() -> None:
    """Validate configuration and schemas."""
    typer.echo("configuration valid")
