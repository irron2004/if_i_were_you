from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import List

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )


class ParticipantRelation(str, PyEnum):
    FRIEND = "friend"
    COWORKER = "coworker"
    FAMILY = "family"
    PARTNER = "partner"
    OTHER = "other"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    nickname: Mapped[str | None] = mapped_column(String(120))

    sessions: Mapped[List["Session"]] = relationship(back_populates="owner")


class OwnerProfile(Base, TimestampMixin):
    __tablename__ = "owner_profiles"
    __table_args__ = (UniqueConstraint("owner_key", name="uq_owner_profile_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_key: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    mbti_source: Mapped[str] = mapped_column(
        String(20), default="input", nullable=False
    )
    mbti_value: Mapped[str | None] = mapped_column(String(4))
    show_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Session(Base, TimestampMixin):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    invite_token: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    owner_token_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    max_raters: Mapped[int] = mapped_column(Integer, default=50)
    self_mbti: Mapped[str | None] = mapped_column(String(4))
    snapshot_owner_name: Mapped[str | None] = mapped_column(String(120))
    snapshot_owner_avatar: Mapped[str | None] = mapped_column(String(255))

    owner: Mapped[User | None] = relationship(back_populates="sessions")
    self_responses: Mapped[List["SelfResponse"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    other_responses: Mapped[List["OtherResponse"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    aggregate: Mapped[Aggregate | None] = relationship(
        back_populates="session", uselist=False, cascade="all, delete-orphan"
    )
    participants: Mapped[List["Participant"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    relation_aggregates: Mapped[List["RelationAggregate"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    dim: Mapped[str] = mapped_column(String(4), nullable=False)
    sign: Mapped[int] = mapped_column(Integer, nullable=False)
    context: Mapped[str] = mapped_column(String(20), nullable=False)
    prompt_self: Mapped[str] = mapped_column(String(512), nullable=False)
    prompt_other: Mapped[str] = mapped_column(String(512), nullable=False)
    theme: Mapped[str] = mapped_column(String(60), nullable=False)
    scenario: Mapped[str] = mapped_column(String(120), nullable=False)


class SelfResponse(Base, TimestampMixin):
    __tablename__ = "responses_self"

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), primary_key=True
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id"), primary_key=True
    )
    value: Mapped[int] = mapped_column(Integer, nullable=False)

    session: Mapped[Session] = relationship(back_populates="self_responses")
    question: Mapped[Question] = relationship()


class OtherResponse(Base, TimestampMixin):
    __tablename__ = "responses_other"
    __table_args__ = (
        UniqueConstraint("session_id", "rater_hash", "question_id", name="uq_other"),
    )

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), primary_key=True
    )
    rater_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    participant_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("participants.id"), nullable=True
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id"), primary_key=True
    )
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    relation_tag: Mapped[str | None] = mapped_column(String(30))

    session: Mapped[Session] = relationship(back_populates="other_responses")
    question: Mapped[Question] = relationship()
    participant: Mapped["Participant | None"] = relationship(
        back_populates="legacy_responses"
    )


class Aggregate(Base, TimestampMixin):
    __tablename__ = "aggregates"

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), primary_key=True
    )
    ei_self: Mapped[float | None] = mapped_column(Float)
    sn_self: Mapped[float | None] = mapped_column(Float)
    tf_self: Mapped[float | None] = mapped_column(Float)
    jp_self: Mapped[float | None] = mapped_column(Float)
    ei_other: Mapped[float | None] = mapped_column(Float)
    sn_other: Mapped[float | None] = mapped_column(Float)
    tf_other: Mapped[float | None] = mapped_column(Float)
    jp_other: Mapped[float | None] = mapped_column(Float)
    ei_gap: Mapped[float | None] = mapped_column(Float)
    sn_gap: Mapped[float | None] = mapped_column(Float)
    tf_gap: Mapped[float | None] = mapped_column(Float)
    jp_gap: Mapped[float | None] = mapped_column(Float)
    ei_sigma: Mapped[float | None] = mapped_column(Float)
    sn_sigma: Mapped[float | None] = mapped_column(Float)
    tf_sigma: Mapped[float | None] = mapped_column(Float)
    jp_sigma: Mapped[float | None] = mapped_column(Float)
    n: Mapped[int] = mapped_column(Integer, default=0)
    gap_score: Mapped[float | None] = mapped_column(Float)

    session: Mapped[Session] = relationship(back_populates="aggregate")


class Participant(Base, TimestampMixin):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=False
    )
    invite_token: Mapped[str] = mapped_column(String(60), nullable=False)
    relation: Mapped[ParticipantRelation] = mapped_column(
        SAEnum(ParticipantRelation, name="participantrelation"),
        nullable=False,
    )
    display_name: Mapped[str | None] = mapped_column(String(120))
    consent_display: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    perceived_type: Mapped[str | None] = mapped_column(String(4))
    axes_payload: Mapped[dict[str, float] | None] = mapped_column(JSON)
    answers_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    session: Mapped[Session] = relationship(back_populates="participants")
    answers: Mapped[List["ParticipantAnswer"]] = relationship(
        back_populates="participant", cascade="all, delete-orphan"
    )
    legacy_responses: Mapped[List["OtherResponse"]] = relationship(
        back_populates="participant"
    )


class ParticipantAnswer(Base, TimestampMixin):
    __tablename__ = "participant_answers"

    participant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("participants.id"), primary_key=True
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id"), primary_key=True
    )
    value: Mapped[int] = mapped_column(Integer, nullable=False)

    participant: Mapped[Participant] = relationship(back_populates="answers")
    question: Mapped[Question] = relationship()


class RelationAggregate(Base, TimestampMixin):
    __tablename__ = "relation_aggregates"
    __table_args__ = (
        UniqueConstraint("session_id", "relation", name="uq_relation_per_session"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=False
    )
    relation: Mapped[ParticipantRelation] = mapped_column(
        SAEnum(ParticipantRelation, name="participantrelation"),
        nullable=False,
    )
    respondent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    top_type: Mapped[str | None] = mapped_column(String(4))
    top_fraction: Mapped[float | None] = mapped_column(Float)
    second_type: Mapped[str | None] = mapped_column(String(4))
    second_fraction: Mapped[float | None] = mapped_column(Float)
    consensus: Mapped[float | None] = mapped_column(Float)
    pgi: Mapped[float | None] = mapped_column(Float)
    axes_payload: Mapped[dict[str, float] | None] = mapped_column(JSON)

    session: Mapped[Session] = relationship(back_populates="relation_aggregates")
