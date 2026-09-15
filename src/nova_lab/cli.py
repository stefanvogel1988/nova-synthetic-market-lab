from pathlib import Path

import typer

from nova_lab.personas.factory import PersonaFactory
from nova_lab.providers.deterministic import DeterministicEngine
from nova_lab.settings import LabSettings
from nova_lab.storage.jsonl import append_jsonl

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """NOVA Synthetic Market Lab command-line interface."""


@app.command()
def validate() -> None:
    """Validate configuration and schemas."""
    typer.echo("configuration valid")


@app.command()
def generate(config: Path = Path("config/lab.yaml")) -> None:
    """Write deterministic, schema-valid synthetic populations to a new run."""
    settings = LabSettings.load(config)
    run_dir = settings.output_dir / settings.make_run_id()
    if run_dir.exists():
        raise typer.BadParameter(f"run directory already exists: {run_dir}")

    factory = PersonaFactory(settings.seed)
    payloads = {
        "parents": [
            persona.model_dump() for persona in factory.make_parents(settings.parent_count)
        ],
        "children": [
            persona.model_dump() for persona in factory.make_children(settings.child_count)
        ],
        "education": [
            persona.model_dump()
            for persona in factory.make_education(settings.education_count)
        ],
        "red_team": [persona.model_dump() for persona in factory.make_red_team()],
    }
    for name, records in payloads.items():
        append_jsonl(run_dir / f"{name}.jsonl", records)
    typer.echo(str(run_dir))


@app.command()
def run(
    config: Path = Path("config/lab.yaml"), provider: str = "deterministic"
) -> None:
    """Prepare a V1 experiment run with the local deterministic provider."""
    if provider != "deterministic":
        raise typer.BadParameter(
            "V1 zero-budget execution supports provider=deterministic only"
        )
    settings = LabSettings.load(config)
    DeterministicEngine(settings.seed)
    typer.echo("deterministic run ready")


@app.command()
def report(run_dir: Path = typer.Option(...)) -> None:
    """Select an existing run directory for report generation."""
    if not run_dir.is_dir():
        raise typer.BadParameter(f"run directory does not exist: {run_dir}")
    typer.echo(str(run_dir))
