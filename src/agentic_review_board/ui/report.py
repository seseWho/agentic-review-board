"""Shareable exports built only from the trusted Review snapshot."""

import json

from agentic_review_board.domain.execution import Review, StageStatus


def review_json(review: Review) -> str:
    """Serialize the complete trusted execution record for machine analysis."""
    return review.model_dump_json(indent=2)


def review_markdown(review: Review) -> str:
    """Render a compact Markdown report suitable for sharing with stakeholders."""
    data = review.model_dump(mode="json")
    review_input = data["review_input"]
    lines = [
        f"# {review_input.get('title') or 'Agentic Review'}",
        "",
        f"**Review status:** `{data['status']}`",
        "",
        "## Case",
        "",
        review_input["description"],
        "",
        f"**Objective:** {review_input.get('objective') or 'Not specified'}",
        "",
        "## Agent execution",
        "",
        "| Agent | Status | Trusted output |",
        "|---|---|---|",
    ]
    for stage in data["stages"]:
        trusted = "Yes" if stage["status"] == StageStatus.COMPLETED.value else "No"
        lines.append(f"| {stage['identity']} | {stage['status']} | {trusted} |")

    final_stage = next(
        (stage for stage in data["stages"] if stage["identity"] == "COORDINATOR"),
        None,
    )
    final = final_stage.get("output") if final_stage else None
    if isinstance(final, dict):
        lines.extend(
            [
                "",
                "## Decision support",
                "",
                f"**Recommendation:** `{final.get('recommendation_outcome', 'NOT_AVAILABLE')}`",
                "",
                f"**Situation summary:** {final.get('situation_summary', '')}",
                "",
                f"**Preferred alternative:** `{final.get('preferred_alternative_id') or 'NONE'}`",
                "",
                f"**Conclusion rationale:** {final.get('conclusion_rationale', '')}",
                "",
                f"**Confidence:** `{final.get('confidence', 'NOT_AVAILABLE')}`",
                "",
            ]
        )

    lines.extend(["## Trusted artifacts", ""])
    for stage in data["stages"]:
        if stage["status"] != StageStatus.COMPLETED.value:
            continue
        lines.extend(
            [
                f"### {stage['identity']}",
                "",
                "```json",
                json.dumps(stage["output"], ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )
    return "\n".join(lines)
