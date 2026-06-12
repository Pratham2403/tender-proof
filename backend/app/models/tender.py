from datetime import datetime
from enum import Enum
from typing import Union

from beanie import Document
from pydantic import BaseModel, Field, model_validator


class CriterionType(str, Enum):
    CURRENCY_THRESHOLD = "CurrencyThreshold"
    COUNT_MINIMUM = "CountMinimum"
    BOOLEAN_PRESENCE = "BooleanPresence"
    DATE_RANGE = "DateRange"
    SIMILARITY_SCORE = "SimilarityScore"


class CurrencyThresholdParams(BaseModel):
    minimum_crore: float
    currency: str = "INR"


class CountMinimumParams(BaseModel):
    minimum_count: int
    within_years: int | None = None  # e.g. "3 projects in last 5 years"


class BooleanPresenceParams(BaseModel):
    accepted_values: list[str] = []  # e.g. ["GST", "GSTIN"] for flexible matching


class DateRangeParams(BaseModel):
    not_expired_as_of: datetime | None = None
    issued_after: datetime | None = None


class SimilarityScoreParams(BaseModel):
    description: str  # Natural language description of "similar" for LLM
    pass_threshold: float = 0.7
    fail_threshold: float = 0.4


CriterionParams = Union[
    CurrencyThresholdParams,
    CountMinimumParams,
    BooleanPresenceParams,
    DateRangeParams,
    SimilarityScoreParams,
]

_PARAMS_BY_TYPE: dict[CriterionType, type[BaseModel]] = {
    CriterionType.CURRENCY_THRESHOLD: CurrencyThresholdParams,
    CriterionType.COUNT_MINIMUM: CountMinimumParams,
    CriterionType.BOOLEAN_PRESENCE: BooleanPresenceParams,
    CriterionType.DATE_RANGE: DateRangeParams,
    CriterionType.SIMILARITY_SCORE: SimilarityScoreParams,
}


class Criterion(BaseModel):
    criterion_id: str          # e.g. "C-01", "C-02" — stable, assigned at compile time
    label: str                 # Human-readable label: "Annual Turnover Minimum"
    criterion_type: CriterionType
    mandatory: bool
    params: CriterionParams
    accepted_evidence: list[str] = []
    source_text: str = ""

    @model_validator(mode="before")
    @classmethod
    def _resolve_params_by_type(cls, data):
        # The params union is ambiguous for overlapping shapes (e.g. an empty
        # dict validates as several of the param models). criterion_type is
        # the discriminator, so resolve params against it explicitly instead
        # of relying on smart-union scoring — this must be deterministic for
        # MongoDB round-trips.
        if isinstance(data, dict):
            ctype = data.get("criterion_type")
            params = data.get("params")
            if ctype is not None and params is not None:
                expected = _PARAMS_BY_TYPE[CriterionType(ctype)]
                if isinstance(params, BaseModel):
                    params = params.model_dump()
                if not isinstance(params, expected):
                    data = {**data, "params": expected(**params)}
        return data


class TenderStatus(str, Enum):
    UPLOADING = "UPLOADING"
    COMPILING = "COMPILING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    EVALUATING = "EVALUATING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class Tender(Document):
    title: str
    file_path: str
    status: TenderStatus = TenderStatus.UPLOADING
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "tenders"


class SchemaStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"


class EvaluationSchema(Document):
    tender_id: str                  # Reference to Tender._id as string
    criteria: list[Criterion]
    status: SchemaStatus = SchemaStatus.PENDING_APPROVAL
    approved_by: str | None = None
    approved_at: datetime | None = None
    compiled_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "evaluation_schemas"
