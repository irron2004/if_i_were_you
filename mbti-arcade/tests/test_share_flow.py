from urllib.parse import parse_qs, urlparse


def test_share_flow(client):
    """공유 링크 생성 → 퀴즈 → 결과 플로우 테스트"""

    # 1. 공유 링크 생성
    share_data = {
        "display_name": "테스트 사용자",
        "mbti_value": "INTJ",
    }

    response = client.post("/share", data=share_data, follow_redirects=False)
    assert response.status_code == 303  # Redirect

    # 2. 퀴즈 페이지 접근 (리다이렉트 URL에서 토큰 추출)
    # 리다이렉트 URL에서 토큰을 추출
    redirect_url = response.headers.get("location")
    assert redirect_url is not None
    assert "/mbti/share_success?url=" in redirect_url

    # URL에서 토큰 추출
    parsed_url = urlparse(redirect_url)
    query_params = parse_qs(parsed_url.query)
    share_url = query_params.get("url", [None])[0]
    owner_exchange_url = query_params.get("owner_exchange_url", [None])[0]
    assert share_url is not None
    assert owner_exchange_url is not None
    assert "/o/" in owner_exchange_url
    assert "/i/" in share_url
    test_token = share_url.split("/i/")[1]

    response = client.get(f"/i/{test_token}")
    assert response.status_code == 200

    # 3. 참여자 등록 + 제출
    reg = client.post(
        f"/v1/participants/{test_token}",
        json={
            "relation": "friend",
            "display_name": "참여자-A",
            "consent_display": False,
        },
    )
    assert reg.status_code == 201
    participant_id = reg.json()["participant_id"]

    quiz_data = {
        "friend_name": "테스트 사용자",
        "friend_mbti": "INTJ",
        "relationship": "friend",
        "relation_label": "친구",
        "responder_name": "참여자-A",
        "invite_token": test_token,
        "participant_id": str(participant_id),
    }

    question_ids = [
        1,
        2,
        101,
        102,
        201,
        202,
        3,
        4,
        103,
        104,
        203,
        204,
        5,
        6,
        105,
        106,
        205,
        206,
        301,
        302,
        401,
        402,
        501,
        502,
    ]
    for qid in question_ids:
        quiz_data[f"q{qid}"] = "3"

    submit = client.post("/mbti/result", data=quiz_data)
    assert submit.status_code == 200

    status = client.get(f"/v1/invites/{test_token}/status")
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["respondent_count"] == 1
    assert status_body["threshold"] == 3


def test_expired_token(client):
    """만료된 토큰 테스트"""

    # 잘못된 토큰으로 접근
    response = client.get("/i/invalid_token")
    assert response.status_code == 403
    body = response.json()
    assert body["type"].endswith("/http-403")
    assert body["title"] == "Forbidden"


def test_rate_limit_redirects_to_share_with_friendly_error(client):
    share_data = {
        "display_name": "테스트 사용자",
        "mbti_value": "INTJ",
    }

    first = client.post("/share", data=share_data, follow_redirects=False)
    assert first.status_code == 303

    limited = client.post("/share", data=share_data, follow_redirects=False)
    assert limited.status_code == 303

    location = limited.headers.get("location")
    assert location is not None
    assert location.startswith("/mbti/share?")
    parsed = urlparse(location)
    params = parse_qs(parsed.query)
    error = params.get("error", [""])[0]
    assert "잠시" in error
    assert "다시 시도" in error
    assert "Retry-After" in limited.headers


def test_missing_display_name_redirects_with_friendly_error(client):
    response = client.post(
        "/share",
        data={"mbti_source": "input", "mbti_value": "INTJ"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers.get("location")
    assert location is not None
    assert location.startswith("/mbti/share?")

    parsed = urlparse(location)
    params = parse_qs(parsed.query)
    error = params.get("error", [""])[0]
    assert "표시명" in error
