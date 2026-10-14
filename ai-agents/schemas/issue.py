
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IssueCategory(str, Enum):
    ROADS = "roads"
    WATER = "water"
    ELECTRICITY = "electricity"
    SANITATION = "sanitation"
    WASTE = "waste"
    DRAINAGE = "drainage"
    PUBLIC_SAFETY = "public_safety"
    OTHER = "other"


class IssueSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueAnalysis(BaseModel):
    summary: str = Field(min_length=1)
    category: IssueCategory
    severity: IssueSeverity
    confidence: float = Field(ge=0.0, le=1.0)
    location: Optional[str] = None
    evidence_needed: list[str] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)
    requires_human_review: bool = False
