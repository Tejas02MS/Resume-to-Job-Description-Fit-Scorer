from .schemas import CriterionScore

def calibrated_score(raw: float) -> float:
    # Calibration is deliberately conservative: compress extreme LLM outputs
    # toward the 50-point midpoint so small wording changes do not create large gaps.
    raw = max(0.0, min(100.0, raw))
    return round(50 + 0.85 * (raw - 50), 2)

def overall_score(scores: list[CriterionScore], weights: dict[str, float]) -> float:
    total = sum(s.score * weights.get(s.name, 0) for s in scores)
    return round(total, 2)
