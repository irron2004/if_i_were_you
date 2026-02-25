from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.db import get_session
from app.core.services.mbti_service import MBTIService
from app.core.token import issue_token
from app.urling import build_invite_url

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Share"])
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


@router.post("/share", response_class=HTMLResponse)
@limiter.limit("1/minute")
def make_share_link(
    request: Request,
    display_name: str = Form(...),
    avatar_url: str | None = Form(None),
    mbti_source: str = Form("input"),
    mbti_value: str = Form(""),
    show_public: str | None = Form(None),
    session=Depends(get_session),
):
    name = (display_name or "").strip()
    if len(name) < 2 or len(name) > 20:
        query_params = {"error": "표시명은 2~20자로 입력해 주세요.", "name": name}
        return RedirectResponse(
            url=f"/mbti/share?{urlencode(query_params)}",
            status_code=303,
        )

    source = (mbti_source or "input").strip()
    if source not in {"input", "self_test"}:
        source = "input"

    avatar = (avatar_url or "").strip() or None
    mbti_clean = (mbti_value or "").strip().upper()
    if source != "input":
        mbti_clean = ""

    svc = MBTIService(session)
    pair_id = svc.create_pair(
        "friend",
        None,
        my_name=name,
        my_mbti=mbti_clean or None,
        my_avatar=avatar,
        my_mbti_source=source,
        show_public=bool(show_public),
    )

    token = issue_token(pair_id, mbti_clean)
    share_url = build_invite_url(request, token=token)
    query_params = {"url": share_url, "name": name}
    if mbti_clean:
        query_params["mbti"] = mbti_clean

    return RedirectResponse(
        url=f"/mbti/share_success?{urlencode(query_params)}",
        status_code=303,
    )
