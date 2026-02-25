from __future__ import annotations

from http import HTTPStatus
from urllib.parse import urlparse

from testing_utils import build_fake_answers


def _create_session(client) -> dict:
    response = client.post("/api/sessions", json={"mode": "friend"})
    assert response.status_code == HTTPStatus.CREATED
    return response.json()


def _owner_headers(owner_exchange_url: str) -> dict[str, str]:
    owner_token = urlparse(owner_exchange_url).path.rstrip("/").split("/")[-1]
    return {"Cookie": f"owner_token={owner_token}"}


def _submit_self(client, session_id: str) -> None:
    answers = build_fake_answers(mode="friend")
    response = client.post(
        "/api/self/submit",
        json={"session_id": session_id, "answers": answers},
    )
    assert response.status_code == HTTPStatus.OK


def _register_participant(client, invite_token: str) -> dict:
    response = client.post(
        f"/v1/participants/{invite_token}",
        json={"relation": "friend", "display_name": "글로벌", "consent_display": True},
    )
    assert response.status_code == HTTPStatus.CREATED
    return response.json()


def _submit_answers(client, participant_id: int):
    answers = build_fake_answers(mode="friend")
    response = client.post(
        f"/v1/answers/{participant_id}",
        json={"answers": answers},
    )
    assert response.status_code == HTTPStatus.CREATED


def test_participant_report_success(client):
    session = _create_session(client)
    owner_headers = _owner_headers(session["owner_exchange_url"])
    _submit_self(client, session["session_id"])

    participant = _register_participant(client, session["invite_token"])
    _submit_answers(client, participant["participant_id"])

    response = client.get(
        f"/v1/report/participant/{participant['participant_id']}",
        headers=owner_headers,
    )
    assert response.status_code == HTTPStatus.OK

    body = response.json()
    assert body["participant_id"] == participant["participant_id"]
    assert body["session_id"] == session["session_id"]
    assert body["self_type"]
    assert body["participant_type"]
    assert body["respondent_count"] == 1
    assert len(body["diff_axes"]) == 4
    assert all(
        axis["dimension"] in ("EI", "SN", "TF", "JP") for axis in body["diff_axes"]
    ), "Unexpected dimension in diff axes"


def test_participant_report_requires_answers(client):
    session = _create_session(client)
    owner_headers = _owner_headers(session["owner_exchange_url"])
    _submit_self(client, session["session_id"])

    participant = _register_participant(client, session["invite_token"])

    response = client.get(
        f"/v1/report/participant/{participant['participant_id']}",
        headers=owner_headers,
    )
    assert response.status_code == HTTPStatus.CONFLICT
    body = response.json()
    assert body["type"].endswith("/answers-missing")


def test_session_report_lock_and_unlock(client):
    session = _create_session(client)
    owner_headers = _owner_headers(session["owner_exchange_url"])
    _submit_self(client, session["session_id"])

    participant_ids = []
    for idx in range(3):
        registration = _register_participant(client, session["invite_token"])
        participant_ids.append(registration["participant_id"])
        _submit_answers(client, registration["participant_id"])

        report = client.get(
            f"/v1/report/session/{session['session_id']}",
            headers=owner_headers,
        )
        assert report.status_code == HTTPStatus.OK
        payload = report.json()
        expected_count = idx + 1
        assert payload["respondent_count"] == expected_count
        assert payload["threshold"] == 3
        if expected_count < 3:
            assert payload["unlocked"] is False
            assert all(item["top_type"] is None for item in payload["relations"])
        else:
            assert payload["unlocked"] is True
            assert any(item["top_type"] for item in payload["relations"])
            assert any(item["axes_payload"] for item in payload["relations"])

    # sanity check participant report after unlock
    final_participant = participant_ids[-1]
    participant_report = client.get(
        f"/v1/report/participant/{final_participant}",
        headers=owner_headers,
    )
    assert participant_report.status_code == HTTPStatus.OK
    assert participant_report.json()["respondent_count"] == 3
