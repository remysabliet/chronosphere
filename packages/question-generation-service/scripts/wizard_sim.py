"""Live Quiz-Wizard simulation: drives ThemaService.extract/refine against the
real Mistral API with in-memory repos, and grades each edge case.

Not part of CI — live-model output is nondeterministic, so this is a manual
exploration tool. The deterministic guards live in tests/unit/test_thema_service.py
and tests/unit/test_thema_prompt.py.

Run from packages/question-generation-service:
    uv run python scripts/wizard_sim.py            # all scenarios
    uv run python scripts/wizard_sim.py additive_topic double_refine  # a subset
"""

import asyncio
import json
import sys
from collections.abc import Callable
from uuid import UUID, uuid4

from question_generation_service.schemas.thema import (
    AmbiguousThema,
    NonTopicInput,
    RefineRequest,
    ResolvedThema,
    ThemaExtractionResult,
    ThemaRequest,
)
from question_generation_service.services.thema_service import ThemaService


class FakeEntry:
    def __init__(self, notes: str, raw_user_input: str) -> None:
        self.id: UUID = uuid4()
        self.notes: str | None = notes
        self.raw_user_input: str = raw_user_input
        self.extracted_thema: str | None = None
        self.extracted_topic: str | None = None
        self.user_corrected: bool = False
        self.user_correction: str | None = None


class FakeRepo:
    def __init__(self) -> None:
        self.rows: dict[UUID, FakeEntry] = {}

    async def save(
        self,
        raw_user_input: str,
        extracted_thema: str,
        extracted_topic: str,
        extraction_model: str,
        extraction_confidence: float,
        notes: str,
    ) -> FakeEntry:
        entry = FakeEntry(notes, raw_user_input)
        self.rows[entry.id] = entry
        return entry

    async def get(self, extraction_id: UUID) -> FakeEntry | None:
        return self.rows.get(extraction_id)

    async def mark_superseded(self, entry: FakeEntry, notes: str) -> FakeEntry:
        entry.notes = notes
        return entry


class _Unused:
    def __getattr__(self, name: str) -> object:
        raise AssertionError(f"unexpected use of dependency: {name}")


def make_service() -> tuple[ThemaService, FakeRepo]:
    repo = FakeRepo()
    svc = ThemaService(repo, _Unused(), _Unused(), _Unused())  # type: ignore[arg-type]
    return svc, repo


def topics_of(result: ThemaExtractionResult) -> list[str]:
    if isinstance(result, ResolvedThema):
        return result.topics
    if isinstance(result, AmbiguousThema):
        return result.candidates[0].topics
    return []


def thema_of(result: ThemaExtractionResult) -> str:
    if isinstance(result, ResolvedThema):
        return result.thema
    if isinstance(result, AmbiguousThema):
        return result.candidates[0].thema
    return ""


def norm(topic: str) -> str:
    return topic.strip().lower()


def kept(prior_topic: str, new_topics: list[str]) -> bool:
    """A prior topic survives if some new topic contains it or it contains the
    new topic (tolerates cosmetic suffixes like 'of World War II')."""
    p = norm(prior_topic)
    return any(p in norm(t) or norm(t) in p for t in new_topics)


Check = Callable[
    [ThemaExtractionResult, ThemaExtractionResult | None, FakeRepo], list[str]
]


class Scenario:
    def __init__(
        self,
        name: str,
        initial: str,
        clarification: str | None,
        check: Check,
        second_clarification: str | None = None,
    ) -> None:
        self.name = name
        self.initial = initial
        self.clarification = clarification
        self.second_clarification = second_clarification
        self.check = check


def _require_topics(result: ThemaExtractionResult | None, errors: list[str]) -> list[str]:
    if result is None:
        errors.append("no refine result")
        return []
    t = topics_of(result)
    if not t:
        errors.append(f"refine did not produce topics: {type(result).__name__}")
    return t


def check_exclusion(keyword: str) -> Check:
    def check(
        first: ThemaExtractionResult, second: ThemaExtractionResult | None, repo: FakeRepo
    ) -> list[str]:
        errors: list[str] = []
        prior = topics_of(first)
        if not prior:
            return [f"initial extract produced no topics: {type(first).__name__}"]
        new = _require_topics(second, errors)
        if not new:
            return errors
        excluded = {norm(t) for t in prior if keyword in norm(t)}
        kept_expected = [t for t in prior if norm(t) not in excluded]
        for t in new:
            if keyword in norm(t):
                errors.append(f"excluded keyword {keyword!r} still present: {t!r}")
        for t in kept_expected:
            if not kept(t, new):
                errors.append(f"prior topic dropped: {t!r} not in {new}")
        for t in new:
            if not kept(t, prior):
                errors.append(f"invented topic not in prior list: {t!r}")
        return errors

    return check


def check_multi_exclusion(keywords: list[str]) -> Check:
    def check(
        first: ThemaExtractionResult, second: ThemaExtractionResult | None, repo: FakeRepo
    ) -> list[str]:
        errors: list[str] = []
        prior = topics_of(first)
        if not prior:
            return [f"initial extract produced no topics: {type(first).__name__}"]
        new = _require_topics(second, errors)
        if not new:
            return errors
        for kw in keywords:
            for t in new:
                if kw in norm(t):
                    errors.append(f"excluded keyword {kw!r} still present: {t!r}")
        kept_expected = [t for t in prior if not any(kw in norm(t) for kw in keywords)]
        for t in kept_expected:
            if not kept(t, new):
                errors.append(f"prior topic dropped: {t!r} not in {new}")
        return errors

    return check


def check_addition(keyword: str) -> Check:
    def check(
        first: ThemaExtractionResult, second: ThemaExtractionResult | None, repo: FakeRepo
    ) -> list[str]:
        errors: list[str] = []
        prior = topics_of(first)
        if not prior:
            return [f"initial extract produced no topics: {type(first).__name__}"]
        new = _require_topics(second, errors)
        if not new:
            return errors
        missing = [t for t in prior if not kept(t, new)]
        # At the 7-topic schema ceiling the model must merge two prior topics
        # to make room — tolerate up to 2 verbatim losses there, none below it.
        allowed_losses = 2 if len(prior) >= 7 else 0
        if len(missing) > allowed_losses:
            errors.append(f"prior topics dropped/reworded on additive refine: {missing}")
        if not any(keyword in norm(t) for t in new):
            errors.append(f"requested addition {keyword!r} missing from {new}")
        return errors

    return check


def check_unchanged() -> Check:
    def check(
        first: ThemaExtractionResult, second: ThemaExtractionResult | None, repo: FakeRepo
    ) -> list[str]:
        errors: list[str] = []
        prior = topics_of(first)
        if not prior:
            return [f"initial extract produced no topics: {type(first).__name__}"]
        new = _require_topics(second, errors)
        if not new:
            return errors
        if [norm(t) for t in new] != [norm(t) for t in prior]:
            errors.append(f"topics changed although exclusion was irrelevant: {prior} -> {new}")
        return errors

    return check


def check_pivot(*thema_keywords: str) -> Check:
    def check(
        first: ThemaExtractionResult, second: ThemaExtractionResult | None, repo: FakeRepo
    ) -> list[str]:
        errors: list[str] = []
        if second is None:
            return ["no refine result"]
        new_thema = norm(thema_of(second))
        if not any(kw in new_thema for kw in thema_keywords):
            errors.append(f"pivot not honored, thema={new_thema!r}")
        return errors

    return check


def check_named_topics(*keywords: str) -> Check:
    def check(
        first: ThemaExtractionResult, second: ThemaExtractionResult | None, repo: FakeRepo
    ) -> list[str]:
        errors: list[str] = []
        new = _require_topics(second, errors)
        if not new:
            return errors
        for kw in keywords:
            if not any(kw in norm(t) for t in new):
                errors.append(f"named topic {kw!r} missing from {new}")
        if len(new) > len(keywords) + 1:
            errors.append(f"generic curriculum substituted for named topics: {new}")
        return errors

    return check


def check_chitchat_keeps_parent() -> Check:
    def check(
        first: ThemaExtractionResult, second: ThemaExtractionResult | None, repo: FakeRepo
    ) -> list[str]:
        errors: list[str] = []
        if not isinstance(second, NonTopicInput):
            errors.append(f"chit-chat clarification not detected: {type(second).__name__}")
        parent = repo.rows.get(getattr(first, "extraction_id", uuid4()))
        if parent is None or parent.notes is None:
            errors.append("parent entry missing")
        elif json.loads(parent.notes)["status"] == "superseded":
            errors.append("chit-chat clarification superseded the parent")
        return errors

    return check


def check_narrowing(keyword: str, sibling_keywords: list[str]) -> Check:
    """"only X" narrows the scope: accept keeping X from the prior list OR
    re-scoping the thema to X with subtopics of X — but no sibling topics."""

    def check(
        first: ThemaExtractionResult, second: ThemaExtractionResult | None, repo: FakeRepo
    ) -> list[str]:
        errors: list[str] = []
        prior = topics_of(first)
        if not prior:
            return [f"initial extract produced no topics: {type(first).__name__}"]
        new = _require_topics(second, errors)
        if not new:
            return errors
        scoped_ok = keyword in norm(thema_of(second)) if second else False
        kept_ok = any(keyword in norm(t) for t in new)
        if not (scoped_ok or kept_ok):
            errors.append(f"narrowed scope {keyword!r} missing: thema/topic {new}")
        for t in new:
            for sib in sibling_keywords:
                if sib in norm(t):
                    errors.append(f"sibling topic survived narrowing: {t!r}")
        return errors

    return check


def check_non_topic(expected_kind: str) -> Check:
    def check(
        first: ThemaExtractionResult, second: ThemaExtractionResult | None, repo: FakeRepo
    ) -> list[str]:
        errors: list[str] = []
        if not isinstance(first, NonTopicInput):
            return [f"expected NonTopicInput, got {type(first).__name__}: {first}"]
        if first.input_kind != expected_kind:
            errors.append(f"expected kind {expected_kind!r}, got {first.input_kind!r}")
        if not first.reply.strip():
            errors.append("empty reply for non-topic input")
        return errors

    return check


def check_ambiguity_surfaced() -> Check:
    def check(
        first: ThemaExtractionResult, second: ThemaExtractionResult | None, repo: FakeRepo
    ) -> list[str]:
        if isinstance(first, AmbiguousThema):
            return []
        if isinstance(first, ResolvedThema) and first.alternates:
            return []
        return [f"homonym ambiguity not surfaced: {type(first).__name__}: {first}"]

    return check


def check_resolved_thema(*keywords: str) -> Check:
    def check(
        first: ThemaExtractionResult, second: ThemaExtractionResult | None, repo: FakeRepo
    ) -> list[str]:
        target = second if second is not None else first
        t = norm(thema_of(target))
        if not any(kw in t for kw in keywords):
            return [f"expected thema matching {keywords}, got {t!r} ({type(target).__name__})"]
        return []

    return check


SCENARIOS = [
    Scenario(
        "subtractive_exclusion",
        "Python advanced",
        "i dont care about advanced exception handlg",
        check_exclusion("exception"),
    ),
    Scenario(
        "additive_topic",
        "World War 2",
        "also cover the pacific war",
        check_addition("pacific"),
    ),
    Scenario(
        "exclusion_of_absent_topic",
        "Photosynthesis",
        "i dont care about quantum physics",
        check_unchanged(),
    ),
    Scenario(
        "full_pivot",
        "Python advanced",
        "actually forget that, I want to learn french cooking",
        check_pivot("cook", "cuisine", "culinary", "gastronomy"),
    ),
    Scenario(
        "named_topics_override",
        "American history",
        "just focus on slavery, the civil war, and reconstruction",
        check_named_topics("slavery", "civil war", "reconstruction"),
    ),
    Scenario(
        "chitchat_clarification",
        "Python advanced",
        "thanks!",
        check_chitchat_keeps_parent(),
    ),
    Scenario(
        "multi_exclusion",
        "Linear algebra",
        "skip determinants and eigenvalues please",
        check_multi_exclusion(["determinant", "eigen"]),
    ),
    Scenario(
        "keep_only_one",
        "Photosynthesis",
        "only the light reactions",
        check_narrowing("light", ["calvin", "stomata", "carbon cycle"]),
    ),
    Scenario("greeting", "hey", None, check_non_topic("greeting_or_chitchat")),
    Scenario("unintelligible", "asdkfj qpwoe zzz", None, check_non_topic("unintelligible")),
    Scenario("meta_question", "what can you do?", None, check_non_topic("meta_question")),
    Scenario("homonym_ambiguity", "spring", None, check_ambiguity_surfaced()),
    Scenario(
        "non_english_input",
        "la révolution française",
        None,
        check_resolved_thema("revolution", "révolution"),
    ),
    Scenario(
        "refine_after_greeting",
        "hey",
        "python basics",
        check_resolved_thema("python"),
    ),
    Scenario(
        "double_refine",
        "Python advanced",
        "i dont care about exception handling",
        check_multi_exclusion(["exception", "decorator", "metaclass"]),
        second_clarification="also drop decorators and metaclasses",
    ),
]


async def run_scenario(
    scenario: Scenario, sem: asyncio.Semaphore
) -> tuple[str, list[str], str]:
    svc, repo = make_service()
    try:
        async with sem:
            first = await svc.extract(ThemaRequest(raw_user_input=scenario.initial))
        second: ThemaExtractionResult | None = None
        if scenario.clarification is not None:
            parent_id = getattr(first, "extraction_id", None)
            if parent_id is None:
                return scenario.name, ["initial result has no extraction_id"], ""
            async with sem:
                second = await svc.refine(
                    parent_id, RefineRequest(clarification=scenario.clarification)
                )
        if scenario.second_clarification is not None and second is not None:
            next_id = getattr(second, "extraction_id", None)
            if next_id is not None:
                async with sem:
                    second = await svc.refine(
                        next_id, RefineRequest(clarification=scenario.second_clarification)
                    )
        detail = (
            f"first: {thema_of(first)!r} {topics_of(first)}"
            + (f"\n    second: {thema_of(second)!r} {topics_of(second)}" if second else "")
        )
        if scenario.second_clarification is None or scenario.clarification is None:
            errors = scenario.check(first, second, repo)
        else:
            errors = scenario.check(first, second, repo)
        return scenario.name, errors, detail
    except Exception as exc:  # noqa: BLE001 — report, don't crash the batch
        return scenario.name, [f"EXCEPTION {type(exc).__name__}: {exc}"], ""


async def main(only: list[str]) -> int:
    sem = asyncio.Semaphore(2)
    selected = [s for s in SCENARIOS if not only or s.name in only]
    results = await asyncio.gather(*(run_scenario(s, sem) for s in selected))
    failures = 0
    for name, errors, detail in results:
        status = "PASS" if not errors else "FAIL"
        if errors:
            failures += 1
        print(f"[{status}] {name}")
        if detail:
            print(f"    {detail}")
        for e in errors:
            print(f"    !! {e}")
    print(f"\n{len(selected) - failures}/{len(selected)} passed")
    return failures


if __name__ == "__main__":
    sys.exit(1 if asyncio.run(main(sys.argv[1:])) else 0)
