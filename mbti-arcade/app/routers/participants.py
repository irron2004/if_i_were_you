from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.data.loader import seed_questions
from app.core.config import sha256_hex
from app.database import get_db
from app.models import (
    OtherResponse,
    Participant,
    ParticipantAnswer,
    ParticipantRelation,
    Question,
    Session as SessionModel,
)
from app.routers.responses import ensure_session_active, validate_answers
from app.schemas import (
    ParticipantAnswerSubmitRequest,
    ParticipantAnswerSubmitResponse,
    ParticipantPreviewParticipant,
    ParticipantPreviewRelation,
    ParticipantPreviewResponse,
    ParticipantRegistrationRequest,
    ParticipantRegistrationResponse,
)
from app.services.aggregator import (
    build_question_lookup,
    recalculate_aggregate,
    recalculate_relation_aggregates,
)
from app.services.scoring import ScoringError, compute_norms, norms_to_mbti
from app.utils.problem_details import ProblemDetailsException

router = APIRouter(prefix="/v1", tags=["participants"])

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


def _participant_rater_hash(participant_id: int) -> str:
    return f"participant:{participant_id}"


def _get_question_lookup(db: Session) -> Dict[int, tuple[str, int]]:
    questions = db.query(Question).all()
    return build_question_lookup(questions)


def _ensure_capacity(session: SessionModel, db: Session) -> None:
    current_count = (
        db.query(func.count(Participant.id))
        .filter(Participant.session_id == session.id)
        .scalar()
        or 0
    )
    if current_count >= session.max_raters:
        raise ProblemDetailsException(
            status_code=429,
            title="Capacity Reached",
            detail="해당 세션의 응답 한도를 초과했습니다.",
            type_suffix="rate-limit",
        )


@router.post(
    "/participants/{invite_token}",
    response_model=ParticipantRegistrationResponse,
    status_code=201,
)
async def register_participant(
    invite_token: str,
    payload: ParticipantRegistrationRequest,
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

    _ensure_capacity(session, db)

    display_name = (payload.display_name or "").strip() or "익명"

    participant = Participant(
        session_id=session.id,
        invite_token=invite_token,
        relation=payload.relation,
        display_name=display_name,
        consent_display=payload.consent_display,
    )

    try:
        db.add(participant)
        db.flush()
        db.commit()
    except ProblemDetailsException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return ParticipantRegistrationResponse(
        participant_id=participant.id,
        session_id=session.id,
        invite_token=invite_token,
        relation=participant.relation,
        display_name=participant.display_name,
        consent_display=participant.consent_display,
        answers_submitted=participant.answers_submitted_at is not None,
        answers_submitted_at=participant.answers_submitted_at,
    )


@router.post(
    "/answers/{participant_id}",
    response_model=ParticipantAnswerSubmitResponse,
    status_code=201,
)
async def submit_participant_answers(
    participant_id: int,
    payload: ParticipantAnswerSubmitRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise ProblemDetailsException(
            status_code=404,
            title="Participant Not Found",
            detail="참여자를 찾을 수 없습니다.",
            type_suffix="participant-not-found",
        )

    session = participant.session
    ensure_session_active(session)

    if participant.answers_submitted_at is not None:
        respondents = (
            db.query(func.count(Participant.id))
            .filter(
                Participant.session_id == session.id,
                Participant.answers_submitted_at.isnot(None),
            )
            .scalar()
            or 0
        )
        response.status_code = 200
        return ParticipantAnswerSubmitResponse(
            participant_id=participant.id,
            session_id=session.id,
            relation=participant.relation,
            axes_payload=participant.axes_payload or {},
            perceived_type=participant.perceived_type or "",
            respondent_count=respondents,
            unlocked=respondents >= UNLOCK_THRESHOLD,
            threshold=UNLOCK_THRESHOLD,
        )

    answers = payload.answers
    if not answers:
        raise ProblemDetailsException(
            status_code=400,
            title="Invalid Answers",
            detail="응답 문항 구성이 유효하지 않습니다.",
            type_suffix="answers-invalid",
            errors={"answers": ["문항 응답이 필요합니다."]},
        )

    validate_answers(session.mode, answers)

    seed_questions(db)
    lookup = _get_question_lookup(db)

    try:
        db.query(ParticipantAnswer).filter(
            ParticipantAnswer.participant_id == participant.id
        ).delete()

        rater_hash = _participant_rater_hash(participant.id)
        db.query(OtherResponse).filter(
            OtherResponse.session_id == session.id,
            OtherResponse.rater_hash == rater_hash,
        ).delete()

        for answer in answers:
            db.add(
                ParticipantAnswer(
                    participant_id=participant.id,
                    question_id=answer.question_id,
                    value=answer.value,
                )
            )
            db.add(
                OtherResponse(
                    session_id=session.id,
                    rater_hash=rater_hash,
                    participant_id=participant.id,
                    question_id=answer.question_id,
                    value=answer.value,
                    relation_tag=participant.relation.value,
                )
            )

        db.flush()

        answer_pairs = [(item.question_id, item.value) for item in answers]
        norms = compute_norms(answer_pairs, lookup)
        participant.axes_payload = {
            dim: round(value, 6) for dim, value in norms.items()
        }
        participant.perceived_type = norms_to_mbti(norms)
        now = datetime.now(timezone.utc)
        participant.answers_submitted_at = now
        participant.computed_at = now

        recalculate_aggregate(db, session)
        relation_result = recalculate_relation_aggregates(session.id, db)

        db.commit()
    except ProblemDetailsException:
        db.rollback()
        raise
    except ScoringError as exc:
        db.rollback()
        raise ProblemDetailsException(
            status_code=400,
            title="Scoring Failed",
            detail=str(exc),
            type_suffix="scoring-error",
        ) from exc
    except Exception:
        db.rollback()
        raise

    respondents = relation_result.total_respondents
    unlocked = respondents >= UNLOCK_THRESHOLD

    return ParticipantAnswerSubmitResponse(
        participant_id=participant.id,
        session_id=session.id,
        relation=participant.relation,
        axes_payload=participant.axes_payload or {},
        perceived_type=participant.perceived_type or "",
        respondent_count=respondents,
        unlocked=unlocked,
        threshold=UNLOCK_THRESHOLD,
    )


@router.get(
    "/participants/{invite_token}/preview",
    response_model=ParticipantPreviewResponse,
)
async def participant_preview(
    invite_token: str,
    request: Request,
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

    _ensure_owner_cookie(request, session)

    relation_result = recalculate_relation_aggregates(session.id, db)
    db.commit()

    respondents = relation_result.total_respondents
    unlocked = respondents >= UNLOCK_THRESHOLD

    relations_payload = [
        ParticipantPreviewRelation(
            relation=item.relation,
            respondent_count=item.respondent_count,
            top_type=item.top_type if unlocked else None,
            top_fraction=item.top_fraction if unlocked else None,
            second_type=item.second_type if unlocked else None,
            second_fraction=item.second_fraction if unlocked else None,
            consensus=item.consensus if unlocked else None,
            pgi=item.pgi if unlocked else None,
            axes_payload=item.axes_payload if unlocked else None,
        )
        for item in relation_result.relations
    ]

    participants = (
        db.query(Participant)
        .filter(Participant.session_id == session.id)
        .order_by(Participant.created_at.asc())
        .all()
    )

    participants_payload = [
        ParticipantPreviewParticipant(
            participant_id=item.id,
            display_name=item.display_name,
            relation=item.relation,
            consent_display=item.consent_display,
            answers_submitted_at=item.answers_submitted_at,
            perceived_type=item.perceived_type if unlocked else None,
            axes_payload=item.axes_payload if unlocked else None,
        )
        for item in participants
    ]

    return ParticipantPreviewResponse(
        session_id=session.id,
        invite_token=invite_token,
        respondent_count=respondents,
        threshold=UNLOCK_THRESHOLD,
        unlocked=unlocked,
        relations=relations_payload,
        participants=participants_payload,
    )
