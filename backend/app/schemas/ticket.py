from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TicketStatus = Literal[
    "submitted",
    "under_review",
    "assigned",
    "in_progress",
    "resolved",
    "rejected",
]


class StatusUpdate(BaseModel):
    status: TicketStatus
    note: str | None = Field(default=None, max_length=1000)


class DepartmentAssignment(BaseModel):
    department: str | None = None


class TicketHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_id: int
    old_status: str
    new_status: str
    note: str | None
    changed_at: datetime
