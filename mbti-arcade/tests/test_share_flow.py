from urllib.parse import parse_qs, urlparse

from app import settings


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
    assert share_url is not None
    assert "/i/" in share_url
    test_token = share_url.split("/i/")[1]

    response = client.get(f"/i/{test_token}")
    assert response.status_code == 200

    # 3. 퀴즈 제출
    quiz_data = {"token": test_token, "relation": "friend"}

    # 24개 질문에 대한 답변 추가 (실제 데이터베이스 질문 ID 사용)
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
        quiz_data[f"q{qid}"] = "3"  # 보통이다

    response = client.post(f"/mbti/result/{test_token}", data=quiz_data)
    assert response.status_code == 200

    html = response.text
    expected_prefix = f"{settings.CANONICAL_BASE_URL}/i/"
    assert expected_prefix in html
    assert "testserver" not in html


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
