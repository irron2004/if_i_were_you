from urllib.parse import parse_qs, urlparse


def test_share_redirect_is_valid_url(client):
    response = client.post(
        "/share",
        data={"display_name": "테스트", "mbti_value": "INTJ"},
        follow_redirects=False,
    )
    assert response.status_code in {200, 302, 303}

    location = response.headers.get("location", "")
    assert location
    assert "://" not in location or location.startswith("https://")

    parsed = urlparse(location)
    params = parse_qs(parsed.query)
    share_url = params.get("url", [""])[0]
    assert share_url
    assert "/i/" in share_url

    parsed_share = urlparse(share_url)
    if parsed_share.scheme:
        assert parsed_share.scheme in {"http", "https"}
        assert parsed_share.netloc
    assert parsed_share.path.startswith("/i/")
