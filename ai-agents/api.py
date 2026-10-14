
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from review.approval import ReviewError, review_manager
from workflow.city_workflow import run_city_workflow


app = FastAPI(
    title="Fix My City — AI Review API",
    description=(
        "AI-powered civic complaint analysis and human review "
        "queue for local development."
    ),
    version="0.1.0",
)


class ComplaintRequest(BaseModel):
    complaint: str = Field(min_length=1, max_length=5000)


class ReviewDecisionRequest(BaseModel):
    reviewer_id: str = Field(min_length=1, max_length=100)
    decision: Literal["approved", "rejected"]
    reason: str = Field(min_length=1, max_length=1000)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Fix My City AI API"}


@app.post("/complaints/analyze")
def analyze_complaint(request: ComplaintRequest):
    complaint = request.complaint.strip()

    if not complaint:
        raise HTTPException(
            status_code=422,
            detail="Complaint cannot be blank.",
        )

    try:
        result = run_city_workflow(complaint)
        analysis = result["analysis"]

        return {
            "analysis": analysis.model_dump(mode="json"),
            "civic_guidance": result.get("civic_guidance", []),
            "error": result.get("error"),
            "review": result.get("review"),
        }

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        # Avoid returning internal exception details to API clients.
        raise HTTPException(
            status_code=500,
            detail="Complaint analysis failed. Check the server logs.",
        ) from exc


@app.get("/reviews/pending")
def get_pending_reviews():
    return {"items": review_manager.list_pending()}


@app.post("/reviews/{review_id}/decision")
def submit_review_decision(
    review_id: str,
    request: ReviewDecisionRequest,
):
    try:
        result = review_manager.decide(
            review_id=review_id,
            reviewer_id=request.reviewer_id,
            decision=request.decision,
            reason=request.reason,
        )
        return result

    except ReviewError as exc:
        message = str(exc)
        status_code = (
            404 if message == "Review record not found." else 400
        )
        raise HTTPException(
            status_code=status_code,
            detail=message,
        ) from exc


@app.get("/reviews/audit")
def get_review_audit():
    return {"items": review_manager.get_audit_log()}
