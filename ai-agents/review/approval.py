
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4
from typing import Any


class ReviewError(ValueError):
    """Raised when a review operation is invalid."""


class ReviewManager:
    """
    In-memory human review manager.

    Demo only: records disappear when the Python process restarts.
    Authentication must be implemented by the application backend.
    """

    def __init__(self):
        self._records: dict[str, dict[str, Any]] = {}
        self._audit_log: list[dict[str, Any]] = []
        self._lock = RLock()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def submit_for_review(
        self,
        complaint: str,
        analysis: dict[str, Any],
    ) -> dict[str, Any]:
        complaint = complaint.strip()

        if not complaint:
            raise ReviewError("Complaint cannot be empty.")

        if not analysis:
            raise ReviewError("Analysis cannot be empty.")

        severity = str(analysis.get("severity", "")).lower()
        requires_review = analysis.get("requires_human_review", False)

        if not isinstance(requires_review, bool):
            raise ReviewError("requires_human_review must be a boolean.")

        if severity not in {"low", "medium", "high", "critical"}:
            raise ReviewError("Invalid or missing severity.")

        if not requires_review and severity not in {"high", "critical"}:
            raise ReviewError(
                "This complaint does not require human review."
            )

        review_id = str(uuid4())

        record = {
            "review_id": review_id,
            "complaint": complaint,
            "analysis": dict(analysis),
            "status": "pending",
            "submitted_at": self._now(),
            "decision": None,
        }

        with self._lock:
            self._records[review_id] = record
            self._audit_log.append({
                "event": "submitted",
                "review_id": review_id,
                "timestamp": record["submitted_at"],
            })

            return dict(record)

    def list_pending(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                dict(record)
                for record in self._records.values()
                if record["status"] == "pending"
            ]

    def decide(
        self,
        review_id: str,
        reviewer_id: str,
        decision: str,
        reason: str,
    ) -> dict[str, Any]:
        reviewer_id = reviewer_id.strip()
        reason = reason.strip()
        decision = decision.strip().lower()

        if not reviewer_id:
            raise ReviewError("Reviewer identity is required.")

        if decision not in {"approved", "rejected"}:
            raise ReviewError(
                "Decision must be 'approved' or 'rejected'."
            )

        if not reason:
            raise ReviewError("A decision reason is required.")

        with self._lock:
            record = self._records.get(review_id)

            if record is None:
                raise ReviewError("Review record not found.")

            if record["status"] != "pending":
                raise ReviewError(
                    "This review has already been decided."
                )

            timestamp = self._now()

            decision_record = {
                "reviewer_id": reviewer_id,
                "decision": decision,
                "reason": reason,
                "timestamp": timestamp,
            }

            record["status"] = decision
            record["decision"] = decision_record

            self._audit_log.append({
                "event": decision,
                "review_id": review_id,
                **decision_record,
            })

            return dict(record)

    def get_audit_log(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(entry) for entry in self._audit_log]


review_manager = ReviewManager()
