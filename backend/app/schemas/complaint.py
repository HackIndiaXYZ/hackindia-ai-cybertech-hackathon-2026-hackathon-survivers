from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


IssueCategory = Literal[
    "pothole",
    "garbage",
    "streetlight",
    "water_leakage",
    "drainage",
]

ComplaintStatus = Literal[
    "submitted",
    "under_review",
    "assigned",
    "in_progress",
    "resolved",
    "rejected",
]


class ComplaintCreate(BaseModel):
    category: IssueCategory
    description: str = Field(min_length=5, max_length=2000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: str
    category: IssueCategory
    description: str
    latitude: float
    longitude: float
    department: str | None
    status: ComplaintStatus
    created_at: datetime
