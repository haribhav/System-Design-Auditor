from __future__ import annotations


def compute_overall(modules: dict) -> dict:
    if not modules:
        return {"score": 0.0, "confidence": 0.0}

    risk_map = {"low": 0, "medium": 1, "high": 2}
    scores = []
    risks = []
    evidence_count = 0

    for module in modules.values():
        scores.append(float(module.get("score", 0)))
        risks.append(risk_map.get(module.get("risk", "medium"), 1))

        for finding in module.get("findings", []):
            evidence_count += len(finding.get("evidence", []))
        for rec in module.get("recommendations", []):
            evidence_count += len(rec.get("evidence", []))

    avg_score = sum(scores) / len(scores)
    avg_risk = sum(risks) / len(risks)

    final_score = max(0.0, min(10.0, round(avg_score - (avg_risk * 0.6), 2)))
    confidence = max(0.0, min(1.0, round(evidence_count / 20, 2)))

    return {"score": final_score, "confidence": confidence}
