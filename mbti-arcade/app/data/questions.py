from __future__ import annotations

from typing import Dict, Iterable, List

from .questionnaire_loader import QuestionSeed, get_question_seeds


QUESTION_SEEDS: tuple[QuestionSeed, ...] = tuple(get_question_seeds())
CONTEXT_TO_SEEDS: Dict[str, List[QuestionSeed]] = {
    context: [seed for seed in QUESTION_SEEDS if seed.context == context]
    for context in {"common", "couple", "friend", "work", "partner", "family"}
}
MODE_TO_CONTEXTS: Dict[str, set[str]] = {
    "basic": {"common"},
    "friend": {"friend"},
    "couple": {"common", "couple"},
    "work": {"work"},
    "partner": {"partner"},
    "family": {"family"},
}
INVITE_MODE_PREFIX: Dict[str, str] = {
    "friend": "F",
    "work": "W",
    "partner": "P",
    "family": "G",
}
INVITE_DIMS: tuple[str, ...] = ("EI", "SN", "TF", "JP")
INVITE_ORDINALS: range = range(1, 6)


def iter_questions() -> Iterable[QuestionSeed]:
    return iter(QUESTION_SEEDS)


def question_payload(seed: QuestionSeed) -> Dict[str, object]:
    return {
        "id": seed.id,
        "code": seed.code,
        "dim": seed.dim,
        "sign": seed.sign,
        "context": seed.context,
        "prompt_self": seed.prompt_self,
        "prompt_other": seed.prompt_other,
        "theme": seed.theme,
        "scenario": seed.scenario,
    }


def questions_for_mode(mode: str) -> List[Dict[str, object]]:
    normalized = mode.lower()
    if normalized not in MODE_TO_CONTEXTS:
        raise ValueError(f"Unsupported mode: {mode}")
    contexts = MODE_TO_CONTEXTS[normalized]
    seeds: list[QuestionSeed] = [
        seed for context in contexts for seed in CONTEXT_TO_SEEDS.get(context, [])
    ]
    seeds.sort(key=lambda seed: seed.id)
    return [question_payload(seed) for seed in seeds]


def select_invite_other_questions(
    mode: str,
    question_payloads: Iterable[Dict[str, object]],
) -> List[Dict[str, object]]:
    normalized = mode.lower()
    prefix = INVITE_MODE_PREFIX.get(normalized)
    payloads = list(question_payloads)
    if not prefix:
        return payloads

    allowlist = {
        f"{prefix}-{dim}-{ordinal:02d}"
        for dim in INVITE_DIMS
        for ordinal in INVITE_ORDINALS
    }
    selected = [payload for payload in payloads if payload.get("code") in allowlist]
    selected_codes = {
        code
        for payload in selected
        for code in [payload.get("code")]
        if isinstance(code, str)
    }
    missing = allowlist - selected_codes

    if len(selected) != 20 or missing:
        raise ValueError(
            f"Invite questionnaire selection failed for mode '{mode}': "
            f"expected 20 questions, got {len(selected)}; "
            f"missing codes={sorted(missing)}"
        )
    return selected
