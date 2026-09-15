"""Normalize evidence claims into safe-to-label report sections."""

from collections.abc import Iterable
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


def build_report_context(
    claims: Iterable[EvidenceClaim] = (), **sections: Any
) -> dict[str, list[str]]:
    """Build a display-ready context without presenting synthetic claims as proven.

    ``PROVEN`` claims are listed only when the evidence register has already
    assigned that status. Synthetic support and contested claims retain their
    own buckets, and every unproven claim's real-world test is surfaced.
    Additional named report sections may be supplied as iterables of strings.
    """
    context: dict[str, list[str]] = {
        "proven": [],
        "synthetic": [],
        "contested": [],
        "human_tests": [],
        "evidence_register": [],
        **{name: [] for name in REPORT_SECTION_NAMES},
    }

    for claim in claims:
        context["evidence_register"].append(
            f"[{claim.current_status.value}] {claim.claim_text}"
        )
        if claim.current_status is EvidenceStatus.PROVEN:
            context["proven"].append(claim.claim_text)
            continue
        if claim.current_status is EvidenceStatus.CONTESTED:
            context["contested"].append(claim.claim_text)
        elif claim.synthetic_experiments or claim.current_status is EvidenceStatus.SUPPORTED:
            context["synthetic"].append(claim.claim_text)
        if claim.required_real_world_test:
            context["human_tests"].append(claim.required_real_world_test)

    for name, items in sections.items():
        if name not in context:
            raise ValueError(f"Unknown report section: {name}")
        context[name] = list(items)
    return context
