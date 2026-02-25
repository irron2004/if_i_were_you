from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.config import sha256_hex
from app.models import Participant, Question, Session as SessionModel
from app.schemas import (
    DIMENSIONS,
    ParticipantReportAxis,
    ParticipantReportResponse,
    SessionRelationReportItem,
    SessionReportResponse,
)
from app.services.aggregator import (
    build_question_lookup,
    load_self_norm,
    recalculate_relation_aggregates,
)
from app.services.scoring import norms_to_mbti
from app.utils.problem_details import ProblemDetailsException

UNLOCK_THRESHOLD = 3

OWNER_TOKEN_COOKIE = "owner_token"


def _ensure_owner_cookie(request: Request, session: SessionModel) -> None:
    owner_token = request.cookies.get(OWNER_TOKEN_COOKIE)
    if not owner_token:
        raise ProblemDetailsException(
            status_code=401,
            title="Unauthorized",
            detail="소유자 인증 쿠키가 필요합니다.",
            type_suffix="unauthorized",
        )

    if (
        not session.owner_token_hash
        or sha256_hex(owner_token) != session.owner_token_hash
    ):
        raise ProblemDetailsException(
            status_code=401,
            title="Unauthorized",
            detail="소유자 인증 정보가 올바르지 않습니다.",
            type_suffix="unauthorized",
        )


router = APIRouter(prefix="/v1/report", tags=["report"])


def _load_self_axes(db: Session, session: SessionModel) -> Dict[str, float]:
    questions = db.query(Question).all()
    lookup = build_question_lookup(questions)
    self_norm = load_self_norm(db, session, lookup)
    if self_norm is None:
        raise ProblemDetailsException(
            status_code=409,
            title="Self Answers Missing",
            detail="세션 소유자가 아직 자기 평가를 완료하지 않았습니다.",
            type_suffix="self-missing",
        )
    return {dim: round(value, 6) for dim, value in self_norm.items()}


@router.get("/participant/{participant_id}", response_model=ParticipantReportResponse)
def participant_report(
    participant_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> ParticipantReportResponse:
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise ProblemDetailsException(
            status_code=404,
            title="Participant Not Found",
            detail="참여자를 찾을 수 없습니다.",
            type_suffix="participant-not-found",
        )

    if not participant.axes_payload or not participant.perceived_type:
        raise ProblemDetailsException(
            status_code=409,
            title="Participant Answers Missing",
            detail="참여자가 아직 평가를 제출하지 않았습니다.",
            type_suffix="answers-missing",
        )

    session = participant.session
    if session is None:
        raise ProblemDetailsException(
            status_code=500,
            title="Session Missing",
            detail="연결된 세션 정보를 찾을 수 없습니다.",
            type_suffix="session-missing",
        )

    _ensure_owner_cookie(request, session)

    self_axes = _load_self_axes(db, session)

    if session.self_mbti:
        self_type = session.self_mbti
    else:
        self_type = norms_to_mbti(self_axes)

    participant_axes = {
        dim: round(participant.axes_payload.get(dim, 0.0), 6) for dim in DIMENSIONS
    }

    diff_axes = []
    for dim in DIMENSIONS:
        self_value = self_axes.get(dim, 0.0)
        participant_value = participant_axes.get(dim, 0.0)
        diff_axes.append(
            ParticipantReportAxis(
                dimension=dim,
                self_value=self_value,
                participant_value=participant_value,
                delta=round(participant_value - self_value, 6),
            )
        )

    summary = recalculate_relation_aggregates(session.id, db)

    return ParticipantReportResponse(
        participant_id=participant.id,
        session_id=session.id,
        self_type=self_type,
        participant_type=participant.perceived_type,
        self_axes=self_axes,
        participant_axes=participant_axes,
        diff_axes=diff_axes,
        respondent_count=summary.total_respondents,
    )


@router.get("/session/{session_id}", response_model=SessionReportResponse)
def session_report(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> SessionReportResponse:
    session = db.get(SessionModel, session_id)
    if session is None:
        raise ProblemDetailsException(
            status_code=404,
            title="Session Not Found",
            detail="해당 세션을 찾을 수 없습니다.",
            type_suffix="session-not-found",
        )

    _ensure_owner_cookie(request, session)

    self_axes: Dict[str, float] | None
    try:
        self_axes = _load_self_axes(db, session)
    except ProblemDetailsException:
        self_axes = None

    summary = recalculate_relation_aggregates(session.id, db)
    respondents = summary.total_respondents
    unlocked = respondents >= UNLOCK_THRESHOLD

    relations = []
    for item in summary.relations:
        payload = item.axes_payload if unlocked else None
        relations.append(
            SessionRelationReportItem(
                relation=item.relation,
                respondent_count=item.respondent_count,
                top_type=item.top_type if unlocked else None,
                top_fraction=item.top_fraction if unlocked else None,
                second_type=item.second_type if unlocked else None,
                second_fraction=item.second_fraction if unlocked else None,
                consensus=item.consensus if unlocked else None,
                pgi=item.pgi if unlocked else None,
                axes_payload=payload,
            )
        )

    if session.self_mbti:
        self_type = session.self_mbti
    elif self_axes is not None:
        self_type = norms_to_mbti(self_axes)
    else:
        self_type = None

    return SessionReportResponse(
        session_id=session.id,
        self_type=self_type,
        respondent_count=respondents,
        threshold=UNLOCK_THRESHOLD,
        unlocked=unlocked,
        relations=relations,
    )
