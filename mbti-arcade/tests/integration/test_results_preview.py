from __future__ import annotations

from http import HTTPStatus

from testing_utils import build_fake_answers


def _create_session(client) -> dict:
    response = client.post("/api/sessions", json={"mode": "basic"})
    assert response.status_code == HTTPStatus.CREATED
    return response.json()


def _submit_self(client, session_id: str) -> None:
    answers = build_fake_answers()
    response = client.post(
        "/api/self/submit",
        json={"session_id": session_id, "answers": answers},
    )
    assert response.status_code == HTTPStatus.OK


def _register_and_submit_other(client, invite_token: str, idx: int) -> None:
    registration = client.post(
        f"/v1/participants/{invite_token}",
        json={
            "relation": "friend",
            "display_name": f"참여자-{idx}",
            "consent_display": False,
        },
    )
    assert registration.status_code == HTTPStatus.CREATED
    participant_id = registration.json()["participant_id"]

    answers = build_fake_answers()
    response = client.post(
        f"/v1/answers/{participant_id}",
        json={"answers": answers},
    )
    assert response.status_code == HTTPStatus.CREATED


def test_preview_returns_real_data_when_available(client):
    session_payload = _create_session(client)
    _submit_self(client, session_payload["session_id"])

    for idx in range(3):
        _register_and_submit_other(client, session_payload["invite_token"], idx)

    preview = client.get("/api/result/preview")
    assert preview.status_code == HTTPStatus.OK
    body = preview.json()

    assert body["session_id"] == session_payload["session_id"]
    assert body["n"] >= 3
    assert body["other_norm"] is not None
    assert body["radar_other"] is not None
    assert body["gap"] is not None
    assert body["unlocked"] is True


def test_preview_uses_sample_when_no_data(client):
    response = client.get("/api/result/preview")
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["session_id"] == "demo-session"
    assert body["mode"] == "preview"


def test_preview_remains_locked_with_two_responses(client):
    session_payload = _create_session(client)
    _submit_self(client, session_payload["session_id"])

    for idx in range(2):
        _register_and_submit_other(client, session_payload["invite_token"], idx)

    preview = client.get("/api/result/preview")
    assert preview.status_code == HTTPStatus.OK
    body = preview.json()
    assert body["session_id"] == "demo-session"
    assert body["mode"] == "preview"


def test_result_endpoint_respects_lock_threshold(client):
    session_payload = _create_session(client)
    invite_token = session_payload["invite_token"]
    _submit_self(client, session_payload["session_id"])

    for idx in range(2):
        _register_and_submit_other(client, invite_token, idx)

    locked = client.get(f"/api/result/{invite_token}")
    assert locked.status_code == HTTPStatus.OK
    locked_body = locked.json()
    assert locked_body["unlocked"] is False
    assert locked_body["other_norm"] is None
    assert locked_body["gap"] is None

    _register_and_submit_other(client, invite_token, 2)

    unlocked = client.get(f"/api/result/{invite_token}")
    assert unlocked.status_code == HTTPStatus.OK
    unlocked_body = unlocked.json()
    assert unlocked_body["unlocked"] is True
    assert unlocked_body["other_norm"] is not None
    assert unlocked_body["gap"] is not None
