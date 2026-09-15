"""Local-only Jinja rendering for Markdown report templates."""

from pathlib import Path

from jinja2 import Template

from nova_lab.reporting.context import ExecutiveFinding, REPORT_SECTION_NAMES


EXECUTIVE_FINDING_SECTIONS = (
    "proven",
    "synthetic",
    "contested",
    "evidence_register",
    *REPORT_SECTION_NAMES,
)


def render_markdown(template_path: Path, context: dict) -> str:
    """Render a local template path; this function makes no network calls."""
    if template_path.name == "executive_report.md.j2":
        for section in EXECUTIVE_FINDING_SECTIONS:
            if not all(
                isinstance(finding, ExecutiveFinding)
                for finding in context.get(section, [])
            ):
                raise TypeError(f"{section} entries must be ExecutiveFinding values")
    return Template(template_path.read_text(encoding="utf-8")).render(**context)
