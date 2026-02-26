from __future__ import annotations

from copy import deepcopy
from http import HTTPStatus
from urllib.parse import urlparse

from sqlalchemy import text

from app.database import engine as orm_engine
from testing_utils import FAKE_PARTICIPANT_PREVIEW, build_fake_answers


def _create_session(client) -> dict:
    response = client.post("/api/sessions", json={"mode": "basic"})
    assert response.status_code == HTTPStatus.CREATED
    return response.json()


def _owner_headers(owner_exchange_url: str) -> dict[str, str]:
    owner_token = urlparse(owner_exchange_url).path.rstrip("/").split("/")[-1]
    return {"Cookie": f"owner_token={owner_token}"}


def _submit_self(client, session_id: str, answers: list[dict[str, int]]) -> None:
    response = client.post(
        "/api/self/submit",
        json={"session_id": session_id, "answers": answers},
    )
    assert response.status_code == HTTPStatus.OK


def _register_participant(client, invite_token: str, idx: int) -> dict:
    response = client.post(
        f"/v1/participants/{invite_token}",
        json={
            "relation": "friend",
            "display_name": f"참여자-{idx}",
            "consent_display": idx == 0,
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    return response.json()


def _submit_answers(
    client,
    participant_id: int,
    answers: list[dict[str, int]],
    expected_status: int = HTTPStatus.CREATED,
):
    response = client.post(
        f"/v1/answers/{participant_id}",
        json={"answers": answers},
    )
    assert response.status_code == expected_status
    return response.json()


def _preview(client, invite_token: str, headers: dict[str, str]) -> dict:
    response = client.get(f"/v1/participants/{invite_token}/preview", headers=headers)
    assert response.status_code == HTTPStatus.OK
    return response.json()


def test_participant_registration_and_submission(client):
    session = _create_session(client)
    answers = build_fake_answers()
    _submit_self(client, session["session_id"], answers)

    participant = _register_participant(client, session["invite_token"], 0)
    body = _submit_answers(client, participant["participant_id"], answers)

    assert body["respondent_count"] == 1
    assert body["unlocked"] is False
    assert body["relation"] == "friend"
    assert body["threshold"] == 3


def test_participant_duplicate_submission_is_idempotent(client):
    session = _create_session(client)
    answers = build_fake_answers()
    _submit_self(client, session["session_id"], answers)

    participant = _register_participant(client, session["invite_token"], 0)

    first = _submit_answers(client, participant["participant_id"], answers)
    assert first["respondent_count"] == 1

    modified = deepcopy(answers)
    modified[0] = {"question_id": modified[0]["question_id"], "value": 5}
    second = _submit_answers(
        client,
        participant["participant_id"],
        modified,
        expected_status=HTTPStatus.OK,
    )

    assert second["respondent_count"] == 1
    assert second["axes_payload"] == first["axes_payload"]
    assert second["perceived_type"] == first["perceived_type"]


def test_preview_locks_until_threshold_and_matches_fixture(client):
    session = _create_session(client)
    owner_headers = _owner_headers(session["owner_exchange_url"])
    answers = build_fake_answers()
    _submit_self(client, session["session_id"], answers)

    participant_ids: list[int] = []
    for idx in range(3):
        registration = _register_participant(client, session["invite_token"], idx)
        participant_ids.append(registration["participant_id"])
        _submit_answers(client, registration["participant_id"], answers)

        preview = _preview(client, session["invite_token"], owner_headers)
        expected_count = idx + 1
        assert preview["respondent_count"] == expected_count
        if expected_count < 3:
            assert preview["unlocked"] is False
            assert all(entry["axes_payload"] is None for entry in preview["relations"])
        else:
            assert preview["unlocked"] is True

    final_preview = _preview(client, session["invite_token"], owner_headers)
    assert final_preview["respondent_count"] == 3
    assert final_preview["unlocked"] is True

    relation = final_preview["relations"][0]
    expected_relation = deepcopy(FAKE_PARTICIPANT_PREVIEW["relations"][0])
    expected_relation["respondent_count"] = relation["respondent_count"]
    assert relation == expected_relation

    participant_payload = final_preview["participants"][0]
    expected_participant = deepcopy(FAKE_PARTICIPANT_PREVIEW["participants"][0])
    expected_participant.update(
        {
            "participant_id": participant_ids[0],
            "display_name": f"참여자-0",
            "answers_submitted_at": participant_payload["answers_submitted_at"],
            "axes_payload": relation["axes_payload"],
        }
    )
    assert participant_payload == expected_participant


def test_problem_details_for_missing_invite(client):
    response = client.post(
        "/v1/participants/does-not-exist",
        json={"relation": "friend"},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    body = response.json()
    assert body["type"].endswith("/invite-not-found")
    assert body["title"] == "Invite Not Found"
    assert body["status"] == HTTPStatus.NOT_FOUND


def test_participant_registration_defaults_to_anonymous_name(client):
    session = _create_session(client)
    response = client.post(
        f"/v1/participants/{session['invite_token']}",
        json={"relation": "friend", "display_name": None, "consent_display": False},
    )
    assert response.status_code == HTTPStatus.CREATED
    body = response.json()
    assert body["display_name"] == "익명"


def test_two_respondents_counted_even_with_participant_token_uniqueness(client):
    session = _create_session(client)
    answers = build_fake_answers()
    _submit_self(client, session["session_id"], answers)

    with orm_engine.begin() as conn:
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_participant_token "
                "ON participants(session_id, invite_token)"
            )
        )

    first = _register_participant(client, session["invite_token"], 0)
    second = _register_participant(client, session["invite_token"], 1)

    _submit_answers(client, first["participant_id"], answers)
    _submit_answers(client, second["participant_id"], answers)

    status = client.get(f"/v1/invites/{session['invite_token']}/status")
    assert status.status_code == HTTPStatus.OK
    payload = status.json()
    assert payload["respondent_count"] == 2
    assert payload["unlocked"] is False
