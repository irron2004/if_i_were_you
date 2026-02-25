from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import sha256_hex
from app.database import get_db
from app.models import Participant, RelationAggregate, Session as SessionModel
from app.routers.responses import ensure_session_active
from app.urling import build_invite_url
from app.utils.problem_details import ProblemDetailsException
from app.utils.privacy import NOINDEX_VALUE, apply_noindex_headers
from app import settings

router = APIRouter(tags=["owner"])

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

OWNER_TOKEN_COOKIE = "owner_token"


def _apply_owner_page_headers(response) -> None:
    apply_noindex_headers(response)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"


def _get_owner_session(request: Request, db: Session) -> SessionModel:
    owner_token = request.cookies.get(OWNER_TOKEN_COOKIE)
    if not owner_token:
        raise ProblemDetailsException(
            status_code=401,
            title="Unauthorized",
            detail="소유자 인증 쿠키가 필요합니다.",
            type_suffix="unauthorized",
        )

    token_hash = sha256_hex(owner_token)
    session = (
        db.query(SessionModel)
        .filter(SessionModel.owner_token_hash == token_hash)
        .first()
    )
    if session is None:
        raise ProblemDetailsException(
            status_code=401,
            title="Unauthorized",
            detail="소유자 인증 정보가 올바르지 않습니다.",
            type_suffix="unauthorized",
        )

    ensure_session_active(session)
    return session


@router.get("/o/{owner_token}", response_class=HTMLResponse, name="owner_exchange")
def owner_exchange(
    owner_token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    token_hash = sha256_hex(owner_token)
    session = (
        db.query(SessionModel)
        .filter(SessionModel.owner_token_hash == token_hash)
        .first()
    )
    if session is None:
        raise ProblemDetailsException(
            status_code=404,
            title="Owner Link Not Found",
            detail="소유자 링크를 찾을 수 없습니다.",
            type_suffix="owner-link-not-found",
        )

    ensure_session_active(session)

    response = RedirectResponse(url="/me", status_code=303)
    response.set_cookie(
        key=OWNER_TOKEN_COOKIE,
        value=owner_token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/",
    )
    _apply_owner_page_headers(response)
    return response


@router.get("/me", response_class=HTMLResponse, name="owner_progress")
def owner_progress(
    request: Request,
    db: Session = Depends(get_db),
):
    session = _get_owner_session(request, db)

    invite_url = build_invite_url(request, token=session.invite_token)
    threshold = 3
    respondent_count = (
        db.query(func.count(Participant.id))
        .filter(
            Participant.session_id == session.id,
            Participant.answers_submitted_at.isnot(None),
        )
        .scalar()
        or 0
    )
    unlocked = respondent_count >= threshold
    progress_percent = (
        min(100, int((respondent_count / threshold) * 100)) if threshold else 0
    )
    status_url = f"/v1/invites/{session.invite_token}/status"

    response = templates.TemplateResponse(
        "mbti/owner_progress.html",
        {
            "request": request,
            "invite_url": invite_url,
            "invite_token": session.invite_token,
            "status_url": status_url,
            "respondent_count": respondent_count,
            "threshold": threshold,
            "unlocked": unlocked,
            "progress_percent": progress_percent,
            "owner_name": session.snapshot_owner_name or "",
            "kakao_js_key": settings.KAKAO_JAVASCRIPT_KEY,
            "robots_meta": NOINDEX_VALUE,
        },
    )
    _apply_owner_page_headers(response)
    return response


@router.get("/me/report", response_class=HTMLResponse, name="owner_report")
def owner_report(
    request: Request,
    db: Session = Depends(get_db),
):
    session = _get_owner_session(request, db)

    threshold = 3
    respondent_count = (
        db.query(func.count(Participant.id))
        .filter(
            Participant.session_id == session.id,
            Participant.answers_submitted_at.isnot(None),
        )
        .scalar()
        or 0
    )
    unlocked = respondent_count >= threshold

    relations = (
        db.query(RelationAggregate)
        .filter(RelationAggregate.session_id == session.id)
        .order_by(RelationAggregate.relation.asc())
        .all()
    )

    response = templates.TemplateResponse(
        "mbti/owner_report.html",
        {
            "request": request,
            "respondent_count": respondent_count,
            "threshold": threshold,
            "unlocked": unlocked,
            "relations": relations,
            "owner_name": session.snapshot_owner_name or "",
            "robots_meta": NOINDEX_VALUE,
        },
    )
    _apply_owner_page_headers(response)
    return response
