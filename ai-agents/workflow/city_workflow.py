import time
from typing import TypedDict, Any

from langgraph.graph import StateGraph, START, END

from agents.issue_classifier import classify_issue
from agents.gemini_classifier import analyze_with_gemini
from schemas.issue import IssueAnalysis, IssueSeverity, IssueCategory
from rag.retriever import retrieve_guidance
from review.approval import review_manager


class CityWorkflowState(TypedDict, total=False):
    complaint: str
    rule_analysis: IssueAnalysis
    ai_analysis: IssueAnalysis
    final_analysis: IssueAnalysis
    civic_guidance: list[dict[str, Any]]
    error: str


SEVERITY_RANK = {
    IssueSeverity.LOW: 1,
    IssueSeverity.MEDIUM: 2,
    IssueSeverity.HIGH: 3,
    IssueSeverity.CRITICAL: 4,
}


def rule_classification_node(state: CityWorkflowState) -> dict:
    result = classify_issue(state.get("complaint", ""))
    return {"rule_analysis": result}





def gemini_analysis_node(state: CityWorkflowState) -> dict:
    complaint = state.get("complaint", "")
    rule_result = state["rule_analysis"]

    try:
        ai_result = analyze_with_gemini(complaint)
        return {"ai_analysis": ai_result}

    except Exception as exc:
        error_message = str(exc)
        message = error_message.lower()

        quota_error = any(
            marker in message
            for marker in [
                "429",
                "resource_exhausted",
                "quota exceeded",
                "rate limit",
            ]
        )

        fallback_reason = (
            "Gemini quota/rate limit reached; "
            "rule-based fallback used."
            if quota_error
            else "Gemini analysis failed; rule-based fallback used."
        )

        # Preserve the rule classifier's review decision.
        # Safety-critical cases are enforced in safety_review_node.
        fallback = rule_result.model_copy(
            update={
                "reasoning": [
                    *rule_result.reasoning,
                    fallback_reason,
                ],
            }
        )

        return {
            "ai_analysis": fallback,
            "error": f"{type(exc).__name__}: {error_message}",
        }



def rag_retrieval_node(state: CityWorkflowState) -> dict:
    analysis = state["ai_analysis"]

    # Vague complaints should not receive guessed departments.
    if analysis.category == IssueCategory.OTHER:
        return {"civic_guidance": []}

    results = retrieve_guidance(
        complaint=state.get("complaint", ""),
        category=analysis.category.value,
        top_k=3,
    )

    # Return only guides matching the predicted category.
    matching = [
        item for item in results
        if item.get("category") == analysis.category.value
    ]

    return {"civic_guidance": matching}




def safety_review_node(state: CityWorkflowState) -> dict:
    rule_result = state["rule_analysis"]
    ai_result = state["ai_analysis"]

    updates = {}
    reasoning = list(ai_result.reasoning)

    rule_rank = SEVERITY_RANK[rule_result.severity]
    ai_rank = SEVERITY_RANK[ai_result.severity]

    if rule_rank > ai_rank:
        updates["severity"] = rule_result.severity
        reasoning.extend(rule_result.reasoning)
        reasoning.append(
            "Safety gate preserved the higher rule-based severity."
        )

    elif ai_rank > rule_rank:
        reasoning.append(
            "AI analysis identified a higher severity than "
            "the rule-based classifier."
        )

    high_or_critical_detected = (
        rule_result.severity in [
            IssueSeverity.HIGH,
            IssueSeverity.CRITICAL,
        ]
        or ai_result.severity in [
            IssueSeverity.HIGH,
            IssueSeverity.CRITICAL,
        ]
    )

    requires_review = (
        ai_result.requires_human_review
        or rule_result.requires_human_review
        or ai_result.confidence < 0.70
        or ai_result.category == IssueCategory.OTHER
        or high_or_critical_detected
    )

    updates["requires_human_review"] = requires_review
    updates["reasoning"] = list(dict.fromkeys(reasoning))

    final_result = ai_result.model_copy(update=updates)

    return {"final_analysis": final_result}


def build_city_workflow():
    graph = StateGraph(CityWorkflowState)

    graph.add_node("rule_classification", rule_classification_node)
    graph.add_node("gemini_analysis", gemini_analysis_node)
    graph.add_node("rag_retrieval", rag_retrieval_node)
    graph.add_node("safety_review", safety_review_node)

    graph.add_edge(START, "rule_classification")
    graph.add_edge("rule_classification", "gemini_analysis")
    graph.add_edge("gemini_analysis", "rag_retrieval")
    graph.add_edge("rag_retrieval", "safety_review")
    graph.add_edge("safety_review", END)

    return graph.compile()


city_workflow = build_city_workflow()



def run_city_workflow(complaint: str) -> dict[str, Any]:
    complaint = complaint.strip()

    if not complaint:
        raise ValueError("Complaint cannot be empty.")

    result = city_workflow.invoke({"complaint": complaint})
    analysis = result["final_analysis"]

    review_info = None

    if analysis.requires_human_review:
        review_record = review_manager.submit_for_review(
            complaint=complaint,
            analysis=analysis.model_dump(mode="json"),
        )

        review_info = {
            "review_id": review_record["review_id"],
            "status": review_record["status"],
        }

    return {
        "analysis": analysis,
        "civic_guidance": result.get("civic_guidance", []),
        "error": result.get("error"),
        "review": review_info,
    }
