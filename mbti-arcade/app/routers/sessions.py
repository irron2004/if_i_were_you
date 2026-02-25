from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import (
    compute_expiry,
    generate_invite_token,
    generate_owner_token,
    generate_session_id,
    sha256_hex,
)
from app.data.loader import seed_questions
from app.data.questions import questions_for_mode
from app.database import get_db
from app.models import Session as SessionModel, User
from app.schemas import InviteUpdate, QuestionSchema, SessionCreate, SessionResponse
from app.urling import build_owner_exchange_url
from app.utils.problem_details import ProblemDetailsException

router = APIRouter(prefix="/api", tags=["sessions"])


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    payload: SessionCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    seed_questions(db)

    owner = None
    if payload.owner_email:
        owner = db.query(User).filter(User.email == payload.owner_email).first()
        if owner is None:
            owner = User(email=payload.owner_email, nickname=payload.owner_nickname)
            db.add(owner)
            db.flush()
        elif payload.owner_nickname and not owner.nickname:
            owner.nickname = payload.owner_nickname

    session_id = generate_session_id()
    invite_token = generate_invite_token()
    owner_token = generate_owner_token()
    expires_at = compute_expiry(payload.expires_in_hours)

    session = SessionModel(
        id=session_id,
        owner_id=owner.id if owner else None,
        mode=payload.mode,
        invite_token=invite_token,
        owner_token_hash=sha256_hex(owner_token),
        is_anonymous=payload.anonymous,
        expires_at=expires_at,
        max_raters=payload.max_raters,
    )

    db.add(session)
    db.commit()

    owner_exchange_url = build_owner_exchange_url(request, owner_token=owner_token)

    return SessionResponse(
        session_id=session_id,
        invite_token=invite_token,
        owner_exchange_url=owner_exchange_url,
        expires_at=expires_at,
        mode=payload.mode,
        max_raters=payload.max_raters,
        anonymous=payload.anonymous,
    )


@router.post("/invite/create", response_model=SessionResponse)
async def update_invite(payload: InviteUpdate, db: Session = Depends(get_db)):
    session = db.get(SessionModel, payload.session_id)
    if session is None:
        raise ProblemDetailsException(
            status_code=404,
            title="Session Not Found",
            detail="해당 세션을 찾을 수 없습니다.",
            type_suffix="session-not-found",
        )

    if payload.expires_in_hours:
        session.expires_at = compute_expiry(payload.expires_in_hours)
    if payload.max_raters:
        session.max_raters = payload.max_raters
    if payload.anonymous is not None:
        session.is_anonymous = payload.anonymous

    db.commit()

    return SessionResponse(
        session_id=session.id,
        invite_token=session.invite_token,
        expires_at=session.expires_at,
        mode=session.mode,
        max_raters=session.max_raters,
        anonymous=session.is_anonymous,
    )


@router.get("/questions/{mode}", response_model=list[QuestionSchema])
async def fetch_questions(mode: str):
    data = questions_for_mode(mode)
    return [QuestionSchema(**item) for item in data]
