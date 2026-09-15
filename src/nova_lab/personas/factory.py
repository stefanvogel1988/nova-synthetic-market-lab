from __future__ import annotations

import random

from nova_lab.models.persona import (
    ChildPersona,
    EducationPersona,
    ParentPersona,
    RedTeamPersona,
)


class PersonaFactory:
    def __init__(self, seed: int):
        self._rng = random.Random(seed)

    def _score(self) -> float:
        return round(self._rng.random(), 2)

    def make_parents(self, count: int) -> list[ParentPersona]:
        attitudes = ["enthusiastic", "pragmatic", "cautious", "opposed"]
        streams = ["spotify", "apple_music", "other", "none"]
        locales = ["urban", "suburban", "rural"]
        screens = ["strict", "limited", "pragmatic", "permissive"]
        devices = [[], ["toniebox"], ["wobie"], ["yoto"], ["tablet"], ["smart_speaker"]]
        budgets = [75, 125, 175, 250, 400]
        return [
            ParentPersona(
                persona_id=f"parent-{index:03d}",
                child_age=5 + (index % 5),
                child_count=1 + (index % 3),
                disposable_budget_eur=budgets[index % len(budgets)],
                price_sensitivity=self._score(),
                ai_attitude=attitudes[index % len(attitudes)],
                privacy_concern=self._score(),
                subscription_tolerance=self._score(),
                existing_devices=devices[index % len(devices)],
                streaming_service=streams[index % len(streams)],
                technical_confidence=self._score(),
                education_orientation=self._score(),
                convenience_orientation=self._score(),
                screen_time_philosophy=screens[index % len(screens)],
                locale_type=locales[index % len(locales)],
            )
            for index in range(count)
        ]

    def make_children(self, count: int) -> list[ChildPersona]:
        domains = [["animals"], ["space"], ["math"], ["stories"], ["sports"]]
        sibling_contexts = ["only_child", "younger_sibling", "older_sibling", "multiple"]
        return [
            ChildPersona(
                persona_id=f"child-{index:03d}",
                age=5 + (index % 5),
                curiosity_frequency=self._score(),
                language_ability=self._score(),
                reading_ability=self._score(),
                attention_span=self._score(),
                willingness_to_speak_to_devices=self._score(),
                frustration_tolerance=self._score(),
                novelty_seeking=self._score(),
                sibling_context=sibling_contexts[index % len(sibling_contexts)],
                preference_music=self._score(),
                preference_stories=self._score(),
                preference_learning=self._score(),
                preferred_domains=domains[index % len(domains)],
            )
            for index in range(count)
        ]

    def make_education(self, count: int) -> list[EducationPersona]:
        roles = [
            "kindergarten_teacher",
            "kindergarten_director",
            "primary_teacher",
            "school_principal",
            "media_educator",
            "special_education_teacher",
            "data_protection_officer",
            "it_administrator",
            "school_procurement",
            "parent_council",
        ]
        setup_times = [2, 5, 10, 15]
        return [
            EducationPersona(
                persona_id=f"edu-{index:03d}",
                role=roles[index % len(roles)],
                setup_time_tolerance_minutes=setup_times[index % len(setup_times)],
                privacy_concern=self._score(),
                device_management_burden=self._score(),
                pedagogical_openness=self._score(),
                procurement_complexity=self._score(),
                classroom_noise_sensitivity=self._score(),
            )
            for index in range(count)
        ]

    def make_red_team(self) -> list[RedTeamPersona]:
        roles = [
            "consumer_vc",
            "hardware_vc",
            "cfo",
            "child_development",
            "elementary_education",
            "media_safety",
            "privacy_lawyer",
            "cybersecurity",
            "audio_product",
            "competitive_strategy",
            "skeptical_parent",
            "school_procurement",
        ]
        return [
            RedTeamPersona(
                persona_id=f"red-{index:02d}",
                role=role,
                rejection_bias=round(0.55 + index * 0.03, 2),
            )
            for index, role in enumerate(roles)
        ]
