from __future__ import annotations

from typing import Dict, Iterable, List

from app.data.questionnaire_loader import QuestionSeed, get_question_seeds


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
