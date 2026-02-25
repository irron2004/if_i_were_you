from __future__ import annotations

from http import HTTPStatus
from urllib.parse import urlparse

from testing_utils import build_fake_answers


def _owner_headers(owner_exchange_url: str) -> dict[str, str]:
    owner_token = urlparse(owner_exchange_url).path.rstrip("/").split("/")[-1]
    return {"Cookie": f"owner_token={owner_token}"}


def test_status_endpoint_increments_and_unlocks(client):
    create = client.post("/api/sessions", json={"mode": "basic"})
    assert create.status_code == HTTPStatus.CREATED
    session = create.json()

    answers = build_fake_answers(mode="basic")
    submit_self = client.post(
        "/api/self/submit",
        json={"session_id": session["session_id"], "answers": answers},
    )
    assert submit_self.status_code == HTTPStatus.OK

    status0 = client.get(f"/v1/invites/{session['invite_token']}/status")
    assert status0.status_code == HTTPStatus.OK
    body0 = status0.json()
    assert body0["respondent_count"] == 0
    assert body0["unlocked"] is False
    assert body0["threshold"] == 3
    assert body0["updated_at"] is None

    reg = client.post(
        f"/v1/participants/{session['invite_token']}",
        json={"relation": "friend", "display_name": "A", "consent_display": False},
    )
    assert reg.status_code == HTTPStatus.CREATED
    participant_id = reg.json()["participant_id"]

    submit_other = client.post(
        f"/v1/answers/{participant_id}",
        json={"answers": answers},
    )
    assert submit_other.status_code == HTTPStatus.CREATED

    status1 = client.get(f"/v1/invites/{session['invite_token']}/status")
    assert status1.status_code == HTTPStatus.OK
    body1 = status1.json()
    assert body1["respondent_count"] == 1
    assert body1["unlocked"] is False
    assert body1["updated_at"] is not None

    for idx in range(2):
        reg = client.post(
            f"/v1/participants/{session['invite_token']}",
            json={
                "relation": "friend",
                "display_name": f"B{idx}",
                "consent_display": False,
            },
        )
        assert reg.status_code == HTTPStatus.CREATED
        participant_id = reg.json()["participant_id"]
        response = client.post(
            f"/v1/answers/{participant_id}",
            json={"answers": answers},
        )
        assert response.status_code == HTTPStatus.CREATED

    status3 = client.get(f"/v1/invites/{session['invite_token']}/status")
    assert status3.status_code == HTTPStatus.OK
    body3 = status3.json()
    assert body3["respondent_count"] == 3
    assert body3["unlocked"] is True


def test_owner_only_endpoints_reject_without_cookie(client):
    create = client.post("/api/sessions", json={"mode": "friend"})
    assert create.status_code == HTTPStatus.CREATED
    session = create.json()

    report = client.get(f"/v1/report/session/{session['session_id']}")
    assert report.status_code == HTTPStatus.UNAUTHORIZED

    preview = client.get(f"/v1/participants/{session['invite_token']}/preview")
    assert preview.status_code == HTTPStatus.UNAUTHORIZED


def test_owner_only_endpoints_allow_with_cookie(client):
    create = client.post("/api/sessions", json={"mode": "friend"})
    assert create.status_code == HTTPStatus.CREATED
    session = create.json()
    headers = _owner_headers(session["owner_exchange_url"])

    report = client.get(
        f"/v1/report/session/{session['session_id']}",
        headers=headers,
    )
    assert report.status_code == HTTPStatus.OK
