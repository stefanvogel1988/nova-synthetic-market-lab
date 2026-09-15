"""Normalize evidence claims into safe-to-label report sections."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from nova_lab.models.common import EvidenceStatus
from nova_lab.models.evidence import EvidenceClaim


REPORT_SECTION_NAMES = (
    "product_ranking",
    "segment_map",
    "usage_risks",
    "education_opportunities",
    "price_sensitivity",
    "red_team",
    "investment_committee",
    "safety",
    "human_validation_priorities",
)


@dataclass(frozen=True)
class ExecutiveFinding:
    """A report conclusion with the evidence status visible to readers."""

    status: EvidenceStatus
    text: str

    @property
    def label(self) -> str:
        return f"[{self.status.value}] {self.text}"


def build_report_context(
    claims: Iterable[EvidenceClaim] = (), **sections: Any
) -> dict[str, list[str | ExecutiveFinding]]:
    """Build a display-ready context without presenting synthetic claims as proven.

    ``PROVEN`` claims are listed only when the evidence register has already
    assigned that status. Synthetic support and contested claims retain their
    own buckets, and every unproven claim's real-world test is surfaced.
    Additional executive sections accept ``ExecutiveFinding`` values only, so
    no executive conclusion can render without an evidence-status label.
    """
    context: dict[str, list[str | ExecutiveFinding]] = {
        "proven": [],
        "synthetic": [],
        "contested": [],
        "human_tests": [],
        "evidence_register": [],
        **{name: [] for name in REPORT_SECTION_NAMES},
    }

    for claim in claims:
        finding = ExecutiveFinding(claim.current_status, claim.claim_text)
        context["evidence_register"].append(finding)
        if claim.current_status is EvidenceStatus.PROVEN:
            context["proven"].append(finding)
            continue
        if claim.current_status is EvidenceStatus.CONTESTED:
            context["contested"].append(finding)
        elif claim.synthetic_experiments or claim.current_status is EvidenceStatus.SUPPORTED:
            context["synthetic"].append(finding)
        if claim.required_real_world_test:
            context["human_tests"].append(claim.required_real_world_test)

    for name, items in sections.items():
        if name not in context:
            raise ValueError(f"Unknown report section: {name}")
        findings = list(items)
        if name in REPORT_SECTION_NAMES and not all(
            isinstance(finding, ExecutiveFinding) for finding in findings
        ):
            raise TypeError(f"{name} entries must be ExecutiveFinding values")
        context[name] = findings
    return context
