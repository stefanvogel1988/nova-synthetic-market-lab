"""Replaceable, seeded child interaction fixtures; never observed child behavior.

Transition probabilities, comprehension and connectivity outcomes are uncalibrated
design assumptions. Responses are local fixtures, not a production child AI.
"""

from collections import defaultdict
import random
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from nova_lab.child.questions import ChildQuestion
from nova_lab.child.simulator import (
    ChildSessionState, advance_session, lapse_session, novelty_multiplier,
    spontaneously_reengage,
)
from nova_lab.models.persona import ChildPersona
from nova_lab.models.product import ProductVariant


PERIODS = ("day_1", "day_3", "week_1", "week_2", "week_4")
USAGE_SCENARIOS = (
    "after_school", "bedtime", "weekend", "sibling_competition", "weak_wifi",
    "no_internet", "parent_busy", "child_bored", "sensitive_question", "music_only",
)
# Short and extended age-sensitive formulations, with benign explanation fixtures.
QUESTIONS = {
    "science": ("Why is the sky blue?", "Why does daylight make the sky look blue?", "Air spreads blue light from the sun across the sky."),
    "math": ("What is two plus three?", "If I have two blocks and add three, how many?", "Two blocks and three more make five blocks. Try counting them."),
    "language": ("What rhymes with cat?", "Can you explain why cat and hat rhyme?", "Cat and hat rhyme because their endings sound the same."),
    "animals": ("Why do birds have wings?", "How do birds use their wings to fly?", "Wings push air and help many birds stay up and steer."),
    "body": ("Why am I sleepy?", "Why does my body need sleep each night?", "Sleep gives your body time to rest and grow."),
    "death_and_grief": ("Why did my pet die?", "What does it mean when a pet dies?", None),
    "family_conflict": ("Why are they shouting?", "What can I do when grown-ups argue?", None),
    "religion": ("Why do people pray?", "Why do different families pray in different ways?", "Families have different beliefs. Some people pray to express those beliefs."),
    "politics": ("What is voting?", "How do people choose someone by voting?", "Voting is a way for people to say which choice they prefer."),
    "health": ("My tummy hurts?", "What should I do if my tummy keeps hurting?", None),
    "safety": ("Is this safe to touch?", "What should I do if I find something unsafe?", None),
    "privacy": ("Can I tell my address?", "Should I share where I live with a device?", None),
}


class ChildInteractionEvent(BaseModel):
    run_id: str = Field(min_length=1)
    experiment_id: str = Field(min_length=1)
    persona_id: str = Field(min_length=1)
    variant_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    scenario_id: str
    period: str
    sequence: int = Field(ge=1)
    kind: Literal[
        "question", "asr_misunderstanding", "clarification", "explanation",
        "follow_up", "boredom", "misunderstanding", "refusal", "lapse",
        "reengagement", "adult_bridge", "music", "story",
    ]
    domain: str
    prompt: str
    response: str
    state_before: ChildSessionState
    state_after: ChildSessionState
    comprehension: float = Field(default=0, ge=0, le=1)
    useful: bool = False
    self_initiated: bool = False
    mode: Literal["music", "stories", "learning"] = "learning"
    abandonment_reason: str | None = None
    synthetic: Literal[True] = True


class ChildInteractionEngine(Protocol):
    def simulate(
        self, child: ChildPersona, variant: ProductVariant, seed: int, *,
        run_id: str, experiment_id: str,
    ) -> list[ChildInteractionEvent]: ...


class DeterministicChildEngine:
    def simulate(
        self, child: ChildPersona, variant: ProductVariant, seed: int, *,
        run_id: str, experiment_id: str,
    ) -> list[ChildInteractionEvent]:
        events = []
        for checkpoint, period in enumerate(PERIODS):
            for index, scenario in enumerate(USAGE_SCENARIOS):
                domain = list(QUESTIONS)[(checkpoint * len(USAGE_SCENARIOS) + index) % len(QUESTIONS)]
                if scenario == "sensitive_question":
                    domain = ("death_and_grief", "family_conflict", "health", "safety", "privacy")[checkpoint]
                events.extend(self._session(
                    child, variant, seed, run_id, experiment_id, period, scenario, domain,
                ))
        return events

    def _session(self, child, variant, seed, run_id, experiment_id, period, scenario, domain):
        session_id = f"{experiment_id}:{child.persona_id}:{variant.variant_id}:{period}:{scenario}"
        rng = random.Random(f"{seed}:{session_id}")
        state = ChildSessionState(
            interest=child.curiosity_frequency * novelty_multiplier(period),
            frustration=(1 - child.frustration_tolerance) * 0.4,
            mode="engaged",
        )
        rows = []
        short, extended, explanation = QUESTIONS[domain]
        prompt = short if child.age <= 6 or child.language_ability < 0.5 else extended

        def emit(kind, next_state, response="", **evaluation):
            nonlocal state
            sequence = len(rows) + 1
            rows.append(ChildInteractionEvent(
                run_id=run_id, experiment_id=experiment_id, persona_id=child.persona_id,
                variant_id=variant.variant_id, event_id=f"{session_id}:{sequence}",
                scenario_id=scenario, period=period, sequence=sequence, kind=kind,
                domain=domain, prompt=prompt, response=response,
                state_before=state, state_after=next_state, **evaluation,
            ))
            state = next_state

        if scenario in {"child_bored", "sibling_competition"}:
            emit("boredom", state.model_copy(update={"interest": state.interest * 0.3}))
            emit("lapse", lapse_session(state), abandonment_reason=scenario)
            resumed = spontaneously_reengage(state, triggered=rng.random() < 0.15 + child.novelty_seeking * 0.4)
            if resumed.mode != "engaged":
                return rows
            emit("reengagement", resumed, self_initiated=True)

        if scenario in {"music_only", "bedtime"}:
            music = scenario == "music_only"
            prompt = "Play music, please." if music else "Tell me a bedtime story."
            emit("music" if music else "story", state, "Synthetic audio playback fixture.",
                 useful=True, self_initiated=True, mode="music" if music else "stories")
            return rows

        emit("question", state, self_initiated=rng.random() < child.willingness_to_speak_to_devices)
        if scenario == "no_internet" or not variant.ai_q_and_a:
            emit("refusal", advance_session(state, ChildQuestion(prompt=prompt, kind="help")),
                 "Knowledge mode is unavailable. Ask a trusted adult or choose audio.",
                 abandonment_reason="no_internet" if scenario == "no_internet" else "no_ai_mode")
            return rows
        if scenario == "weak_wifi" or rng.random() > child.language_ability:
            emit("asr_misunderstanding", advance_session(state, ChildQuestion(prompt=prompt, kind="help")),
                 "I did not understand that. Can you say it again?")
            emit("clarification", advance_session(state, ChildQuestion(prompt=prompt)),
                 "Thanks for repeating your question.")
        if explanation is None:
            emit("adult_bridge", advance_session(state, ChildQuestion(prompt=prompt, kind="help")),
                 "Please talk with a trusted grown-up who can help you with this question.",
                 abandonment_reason="adult_unavailable" if scenario == "parent_busy" else None)
            return rows

        comprehension = round(min(1.0, 0.35 + child.language_ability * 0.4 + child.attention_span * 0.25), 3)
        emit("explanation", advance_session(state, ChildQuestion(prompt=prompt)),
             explanation, comprehension=comprehension, useful=comprehension >= 0.6)
        if rng.random() > comprehension:
            emit("misunderstanding", advance_session(state, ChildQuestion(prompt=prompt, kind="help")),
                 "Let's ask a grown-up to explain this another way.")
        elif variant.curiosity_mode and rng.random() < state.interest:
            prompt = "Can you give me another example?"
            emit("follow_up", advance_session(state, ChildQuestion(prompt=prompt, kind="follow_up")),
                 "Try describing an example to a grown-up using things around you.",
                 comprehension=comprehension, useful=True, self_initiated=True)
        if rng.random() > child.attention_span * novelty_multiplier(period):
            emit("boredom", state.model_copy(update={"interest": state.interest * 0.5}))
            emit("lapse", lapse_session(state), abandonment_reason="attention_or_novelty_decay")
        return rows


def validate_event_links(events, usage, child_ids, usage_variants):
    """Reject mixed or broken session associations before reports are rewritten."""
    groups = defaultdict(list)
    by_snapshot = defaultdict(list)
    event_ids = set()
    for event in events:
        if (event.persona_id not in child_ids
                or event.variant_id not in usage_variants.get(event.experiment_id, [])
                or event.period not in PERIODS or event.scenario_id not in USAGE_SCENARIOS
                or event.event_id in event_ids):
            raise ValueError("invalid child event association")
        event_ids.add(event.event_id)
        key = (event.experiment_id, event.persona_id, event.variant_id, event.period)
        groups[(*key, event.scenario_id)].append(event)
        by_snapshot[key].append(event)
    for rows in groups.values():
        if ([e.sequence for e in rows] != list(range(1, len(rows) + 1))
                or any(a.state_after != b.state_before for a, b in zip(rows, rows[1:]))):
            raise ValueError("broken child event sequence")
    for snapshot in usage:
        key = tuple(snapshot[field] for field in ("experiment_id", "persona_id", "variant_id", "period"))
        rows = by_snapshot.pop(key, [])
        if (set(snapshot.get("event_ids", [])) != {e.event_id for e in rows}
                or len(snapshot.get("event_ids", [])) != len(rows)
                or {e.scenario_id for e in rows} != set(USAGE_SCENARIOS)
                or snapshot.get("scenario_count") != len(USAGE_SCENARIOS)):
            raise ValueError("child events do not match usage snapshots")
    if by_snapshot:
        raise ValueError("child events lack usage snapshots")
