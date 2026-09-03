from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit raw risk references against upstream data.")
    parser.add_argument("--review-artifact", required=True, type=Path)
    parser.add_argument("--raw-risk", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    review = json.loads(args.review_artifact.read_text(encoding="utf-8"))
    raw = json.loads(args.raw_risk.read_text(encoding="utf-8"))
    analysis = review["stages"][0]["output"]
    alternatives = review["stages"][1]["output"]["alternatives"]

    findings = {
        kind: analysis[field]
        for kind, field in {
            "FACT": "facts",
            "CONSTRAINT": "constraints",
            "ASSUMPTION": "assumptions",
            "MISSING_INFORMATION": "missing_information",
            "UNCERTAINTY": "uncertainties",
        }.items()
    }
    alternatives_by_id = {alternative["id"]: alternative for alternative in alternatives}
    characteristic_fields = {
        "DESCRIPTION": "description",
        "ADVANTAGE": "advantages",
        "DISADVANTAGE": "disadvantages",
        "ASSUMPTION": "assumptions",
        "IMPLEMENTATION_COMPLEXITY": "implementation_complexity",
        "RELEVANT_CONSTRAINT": "relevant_constraints",
    }

    failures: list[str] = []
    for risk in raw["risks"]:
        risk_id = risk["id"]
        for alternative_id in risk["affected_scope"].get("alternative_ids", []):
            if alternative_id not in alternatives_by_id:
                failures.append(f"{risk_id}: unknown scope alternative {alternative_id!r}")

        for reference in risk["basis"]:
            source = reference["source"]
            if source == "PROBLEM_ANALYSIS":
                candidates = findings[reference["kind"]]
                matches = [
                    finding
                    for finding in candidates
                    if finding["text"] == reference["text"]
                    and (reference.get("id") is None or finding.get("id") == reference["id"])
                ]
                if len(matches) != 1:
                    failures.append(
                        f"{risk_id}: unresolved analysis {reference['kind']} "
                        f"text={reference['text']!r} id={reference.get('id')!r}"
                    )
            elif source == "SOLUTION_ALTERNATIVE":
                alternative = alternatives_by_id.get(reference["alternative_id"])
                if alternative is None:
                    failures.append(
                        f"{risk_id}: unknown basis alternative {reference['alternative_id']!r}"
                    )
                    continue
                field = characteristic_fields[reference["characteristic"]]
                current = alternative[field]
                matches_value = (
                    reference["value"] in current
                    if isinstance(current, list)
                    else reference["value"] == current
                )
                if not matches_value:
                    failures.append(
                        f"{risk_id}: unresolved {reference['alternative_id']} "
                        f"{reference['characteristic']} value={reference['value']!r}"
                    )

    if failures:
        print("\n".join(failures))
        return 1
    print("all audited risk references resolve exactly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
