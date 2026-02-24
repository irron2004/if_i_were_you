from urllib.parse import parse_qs, urlparse


def test_allowed_host_passes(client):
    response = client.get(
        "http://webservice-production-c039.up.railway.app/mbti/friend"
    )
    assert response.status_code == 200


def test_unallowed_host_blocked(client):
    response = client.get("http://evil.example.com/mbti/friend")
    assert response.status_code in (400, 421)


def test_share_link_canonicalizes_to_https(client):
    payload = {
        "display_name": "테스트",
        "mbti_value": "INTJ",
    }

    response = client.post(
        "http://webservice-production-c039.up.railway.app/share",
        data=payload,
        headers={
            "x-forwarded-proto": "http",
            "x-forwarded-for": "203.0.113.10",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    location = response.headers.get("location", "")
    assert location

    parsed = urlparse(location)
    share_url = parse_qs(parsed.query).get("url", [""])[0]
    assert share_url.startswith("https://webservice-production-c039.up.railway.app")
