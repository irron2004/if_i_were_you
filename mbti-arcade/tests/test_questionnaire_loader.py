from collections import Counter

import pytest

from app.main import _build_questions
from app.data.questionnaire_loader import get_question_seeds
from app.data.questions import questions_for_mode, select_invite_other_questions


def test_question_seed_counts():
    seeds = list(get_question_seeds())
    assert len(seeds) == 224

    contexts = Counter(seed.context for seed in seeds)
    assert contexts["common"] == 24
    assert contexts["couple"] == 8
    assert contexts["friend"] == 48
    assert contexts["work"] == 48
    assert contexts["partner"] == 48
    assert contexts["family"] == 48

    ids = [seed.id for seed in seeds]
    assert len(ids) == len(set(ids)), "question IDs must be unique"

    codes = [seed.code for seed in seeds]
    assert len(codes) == len(set(codes)), "question codes must be unique"


def test_questions_for_mode_counts():
    basic = questions_for_mode("basic")
    assert len(basic) == 24
    assert {item["context"] for item in basic} == {"common"}

    couple = questions_for_mode("couple")
    assert len(couple) == 32
    assert {item["context"] for item in couple} == {"common", "couple"}

    friend = questions_for_mode("friend")
    assert len(friend) == 48
    assert {item["context"] for item in friend} == {"friend"}

    work = questions_for_mode("work")
    assert len(work) == 48
    assert {item["context"] for item in work} == {"work"}

    partner = questions_for_mode("partner")
    assert len(partner) == 48
    assert {item["context"] for item in partner} == {"partner"}

    family = questions_for_mode("family")
    assert len(family) == 48
    assert {item["context"] for item in family} == {"family"}


@pytest.mark.parametrize(
    ("mode", "prefix"),
    [
        ("friend", "F"),
        ("work", "W"),
        ("partner", "P"),
        ("family", "G"),
    ],
)
def test_invite_other_selection_uses_first_five_ordinals_per_dimension(
    mode: str,
    prefix: str,
):
    mode_questions = questions_for_mode(mode)
    selected = select_invite_other_questions(mode, mode_questions)

    assert len(selected) == 20
    assert Counter(str(item["dim"]) for item in selected) == {
        "EI": 5,
        "SN": 5,
        "TF": 5,
        "JP": 5,
    }

    expected_codes = {
        f"{prefix}-{dim}-{ordinal:02d}"
        for dim in ("EI", "SN", "TF", "JP")
        for ordinal in range(1, 6)
    }
    selected_codes = {str(item["code"]) for item in selected}

    assert selected_codes == expected_codes
    assert selected_codes.issubset({str(item["code"]) for item in mode_questions})


def test_invite_other_selection_does_not_change_non_relationship_modes():
    basic = questions_for_mode("basic")
    couple = questions_for_mode("couple")

    assert select_invite_other_questions("basic", basic) == basic
    assert select_invite_other_questions("couple", couple) == couple


def test_build_questions_keeps_self_test_count_unchanged():
    assert len(_build_questions("basic", perspective="self")) == 24


@pytest.mark.parametrize("mode", ["friend", "work", "partner", "family"])
def test_build_questions_invite_other_count_is_twenty(mode: str):
    assert len(_build_questions(mode, perspective="other")) == 20
