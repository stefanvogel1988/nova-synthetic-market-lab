"""Local-only Jinja rendering for Markdown report templates."""

from pathlib import Path

from jinja2 import Template


def render_markdown(template_path: Path, context: dict) -> str:
    """Render a local template path; this function makes no network calls."""
    return Template(template_path.read_text(encoding="utf-8")).render(**context)
