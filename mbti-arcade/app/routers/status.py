from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Participant, Session as SessionModel
from app.routers.participants import UNLOCK_THRESHOLD
from app.routers.responses import ensure_session_active
from app.schemas import InviteStatusResponse
from app.utils.problem_details import ProblemDetailsException

router = APIRouter(prefix="/v1", tags=["status"])


@router.get("/invites/{invite_token}/status", response_model=InviteStatusResponse)
def get_invite_status(
    invite_token: str,
    response: Response,
    db: Session = Depends(get_db),
):
    session = (
        db.query(SessionModel).filter(SessionModel.invite_token == invite_token).first()
    )
    if session is None:
        raise ProblemDetailsException(
            status_code=404,
            title="Invite Not Found",
            detail="초대 정보를 찾을 수 없습니다.",
            type_suffix="invite-not-found",
        )

    ensure_session_active(session)

    respondent_count = (
        db.query(func.count(Participant.id))
        .filter(
            Participant.session_id == session.id,
            Participant.answers_submitted_at.isnot(None),
        )
        .scalar()
        or 0
    )

    last_submitted_at: datetime | None = (
        db.query(func.max(Participant.answers_submitted_at))
        .filter(
            Participant.session_id == session.id,
            Participant.answers_submitted_at.isnot(None),
        )
        .scalar()
    )

    threshold = UNLOCK_THRESHOLD
    unlocked = respondent_count >= threshold

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return InviteStatusResponse(
        respondent_count=respondent_count,
        threshold=threshold,
        unlocked=unlocked,
        expires_at=session.expires_at,
        max_raters=session.max_raters,
        updated_at=last_submitted_at,
    )
