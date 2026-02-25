from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    FieldValidationInfo,
    HttpUrl,
    field_validator,
)

from app.models import ParticipantRelation

DIMENSIONS = ("EI", "SN", "TF", "JP")


class QuestionSchema(BaseModel):
    id: int
    code: str
    dim: str
    sign: int
    context: str
    prompt_self: str
    prompt_other: str
    theme: str
    scenario: str

    @field_validator("dim")
    @classmethod
    def validate_dim(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in DIMENSIONS:
            raise ValueError(f"Unsupported dimension '{value}'")
        return normalized

    @field_validator("sign")
    @classmethod
    def validate_sign(cls, value: int) -> int:
        if value not in (-1, 1):
            raise ValueError("sign must be -1 or 1")
        return value


class SessionCreate(BaseModel):
    owner_email: Optional[EmailStr] = None
    owner_nickname: Optional[str] = Field(default=None, max_length=120)
    mode: str = Field(pattern="^(basic|couple|friend|work|partner|family)$")
    max_raters: int = Field(default=50, ge=1, le=500)
    expires_in_hours: int = Field(default=72, ge=1, le=720)
    anonymous: bool = True


class SessionResponse(BaseModel):
    session_id: str
    invite_token: str
    owner_exchange_url: Optional[str] = None
    expires_at: datetime
    mode: str
    max_raters: int
    anonymous: bool


class InviteUpdate(BaseModel):
    session_id: str
    expires_in_hours: Optional[int] = Field(default=None, ge=1, le=720)
    max_raters: Optional[int] = Field(default=None, ge=1, le=500)
    anonymous: Optional[bool] = None


class AnswerItem(BaseModel):
    question_id: int
    value: int = Field(ge=1, le=5)


class SelfSubmitRequest(BaseModel):
    session_id: str
    answers: List[AnswerItem]


class SelfSubmitResponse(BaseModel):
    session_id: str
    self_norm: Dict[str, float]
    self_radar: Dict[str, float]


class OtherSubmitRequest(BaseModel):
    invite_token: str
    answers: List[AnswerItem]
    relation_tag: Optional[str] = Field(default=None, max_length=30)
    rater_key: Optional[str] = Field(default=None, max_length=120)


class OtherSubmitResponse(BaseModel):
    session_id: str
    accepted: bool
    respondents: int


class ResultDetail(BaseModel):
    session_id: str
    mode: str
    n: int
    self_norm: Dict[str, float]
    other_norm: Optional[Dict[str, float]]
    gap: Optional[Dict[str, float]]
    sigma: Optional[Dict[str, float]]
    gap_score: Optional[float]
    radar_self: Dict[str, float]
    radar_other: Optional[Dict[str, float]]
    unlocked: bool


class ProblemDetails(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    errors: Optional[Dict[str, List[str]]] = None


class ParticipantRegistrationRequest(BaseModel):
    relation: ParticipantRelation
    display_name: Optional[str] = Field(default=None, max_length=120)
    consent_display: bool = False


class ParticipantRegistrationResponse(BaseModel):
    participant_id: int
    session_id: str
    invite_token: str
    relation: ParticipantRelation
    display_name: Optional[str]
    consent_display: bool
    answers_submitted: bool
    answers_submitted_at: Optional[datetime]


class ParticipantAnswerSubmitRequest(BaseModel):
    answers: List[AnswerItem]


class ParticipantAnswerSubmitResponse(BaseModel):
    participant_id: int
    session_id: str
    relation: ParticipantRelation
    axes_payload: Dict[str, float]
    perceived_type: str
    respondent_count: int
    unlocked: bool
    threshold: int


class ParticipantPreviewParticipant(BaseModel):
    participant_id: int
    display_name: Optional[str]
    relation: ParticipantRelation
    consent_display: bool
    answers_submitted_at: Optional[datetime]
    perceived_type: Optional[str]
    axes_payload: Optional[Dict[str, float]]


class ParticipantPreviewRelation(BaseModel):
    relation: ParticipantRelation
    respondent_count: int
    top_type: Optional[str]
    top_fraction: Optional[float]
    second_type: Optional[str]
    second_fraction: Optional[float]
    consensus: Optional[float]
    pgi: Optional[float]
    axes_payload: Optional[Dict[str, float]]


class ParticipantPreviewResponse(BaseModel):
    session_id: str
    invite_token: str
    respondent_count: int
    threshold: int
    unlocked: bool
    relations: List[ParticipantPreviewRelation]
    participants: List[ParticipantPreviewParticipant]


class ParticipantReportAxis(BaseModel):
    dimension: str
    self_value: float
    participant_value: float
    delta: float


class ParticipantReportResponse(BaseModel):
    participant_id: int
    session_id: str
    self_type: str
    participant_type: str
    self_axes: Dict[str, float]
    participant_axes: Dict[str, float]
    diff_axes: List[ParticipantReportAxis]
    respondent_count: int


class SessionRelationReportItem(BaseModel):
    relation: ParticipantRelation
    respondent_count: int
    top_type: Optional[str]
    top_fraction: Optional[float]
    second_type: Optional[str]
    second_fraction: Optional[float]
    consensus: Optional[float]
    pgi: Optional[float]
    axes_payload: Optional[Dict[str, float]]


VALID_MBTI_TYPES = {
    "ISTJ",
    "ISFJ",
    "INFJ",
    "INTJ",
    "ISTP",
    "ISFP",
    "INFP",
    "INTP",
    "ESTP",
    "ESFP",
    "ENFP",
    "ENTP",
    "ESTJ",
    "ESFJ",
    "ENFJ",
    "ENTJ",
}


class ProfileCreateRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=20)
    avatar_url: HttpUrl | None = None
    mbti_source: str = Field(default="input", pattern="^(input|self_test)$")
    mbti_value: Optional[str] = Field(default=None, max_length=4)
    show_public: bool = True

    @field_validator("mbti_value")
    @classmethod
    def validate_mbti_value(
        cls, value: Optional[str], info: FieldValidationInfo
    ) -> Optional[str]:
        source = info.data.get("mbti_source", "input")
        if source == "input":
            if not value:
                raise ValueError("MBTI 값을 입력해 주세요.")
            upper_value = value.upper()
            if upper_value not in VALID_MBTI_TYPES:
                raise ValueError("MBTI 형식이 올바르지 않습니다.")
            return upper_value
        # self_test 경로에서는 값이 없어야 한다.
        return None


class ProfileResponse(BaseModel):
    profile_id: int
    display_name: str
    avatar_url: Optional[str]
    mbti_source: str
    mbti_value: Optional[str]
    show_public: bool
    created_at: datetime
    updated_at: datetime


class SessionReportResponse(BaseModel):
    session_id: str
    self_type: Optional[str]
    respondent_count: int
    threshold: int
    unlocked: bool
    relations: List[SessionRelationReportItem]


class InviteCreateRequest(BaseModel):
    expires_in_days: int = Field(default=3, ge=1, le=30)
    max_raters: int = Field(default=50, ge=1, le=500)


class InviteCreateResponse(BaseModel):
    session_id: str
    invite_token: str
    invite_url: str
    owner_exchange_url: Optional[str] = None
    expires_at: datetime
    max_raters: int
    show_public: bool
    owner_display_name: str
    owner_avatar_url: Optional[str]


class InviteStatusResponse(BaseModel):
    respondent_count: int
    threshold: int
    unlocked: bool
    expires_at: datetime
    max_raters: int
    updated_at: Optional[datetime] = None
