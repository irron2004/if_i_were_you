from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import (
    compute_expiry,
    generate_invite_token,
    generate_owner_token,
    generate_session_id,
    sha256_hex,
)
from app.database import get_db
from app.models import OwnerProfile, Session as SessionModel
from app.schemas import InviteCreateRequest, InviteCreateResponse
from app.urling import build_invite_url, build_owner_exchange_url
from app.utils.auth import extract_owner_key
from app.utils.problem_details import ProblemDetailsException

router = APIRouter(prefix="/v1", tags=["invites"])


def _hours_from_days(days: int) -> int:
    return max(1, days * 24)


@router.post("/invites", response_model=InviteCreateResponse, status_code=201)
def create_invite(
    payload: InviteCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    owner_key = extract_owner_key(request)

    profile = (
        db.query(OwnerProfile).filter(OwnerProfile.owner_key == owner_key).one_or_none()
    )
    if profile is None:
        raise ProblemDetailsException(
            status_code=412,
            title="Profile Required",
            detail="초대를 만들기 전에 소유자 프로필을 먼저 저장해 주세요.",
            type_suffix="profile-required",
        )

    session_id = generate_session_id()
    invite_token = generate_invite_token()
    owner_token = generate_owner_token()
    expires_at = compute_expiry(_hours_from_days(payload.expires_in_days))

    session = SessionModel(
        id=session_id,
        owner_id=None,
        mode="friend",
        invite_token=invite_token,
        owner_token_hash=sha256_hex(owner_token),
        is_anonymous=not profile.show_public,
        expires_at=expires_at,
        max_raters=payload.max_raters,
        self_mbti=profile.mbti_value,
        snapshot_owner_name=profile.display_name,
        snapshot_owner_avatar=profile.avatar_url,
    )

    db.add(session)
    db.commit()

    invite_url = build_invite_url(request, token=session.invite_token)
    owner_exchange_url = build_owner_exchange_url(request, owner_token=owner_token)

    return InviteCreateResponse(
        session_id=session.id,
        invite_token=session.invite_token,
        invite_url=invite_url,
        owner_exchange_url=owner_exchange_url,
        expires_at=session.expires_at,
        max_raters=session.max_raters,
        show_public=profile.show_public,
        owner_display_name=profile.display_name,
        owner_avatar_url=profile.avatar_url,
    )
