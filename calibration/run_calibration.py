import os, sys, statistics, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings
from app.parser import extract_resume_text
from app.llm import GeminiService
from app.scoring import calibrated_score, overall_score
from app.schemas import CriterionScore

def main():
    settings = get_settings()
    llm = GeminiService(settings.gemini_api_key, settings.gemini_model)
    job = Path("sample_data/job_description.txt").read_text()
    weights = settings.normalized_weights()
    criteria = llm.extract_criteria(job, weights).criteria
    results = {}
    for name in ["resume_a.txt", "resume_b.txt", "resume_c.txt"]:
        text, _ = extract_resume_text(name, Path("sample_data", name).read_bytes())
        scores=[]
        for c in criteria:
            raw=llm.score_criterion(text,c)
            s=calibrated_score(raw.score)
            scores.append(CriterionScore(name=c.name, requirement=c.requirement, score=s,
                weighted_score=s*weights.get(c.name,0), evidence=raw.evidence,
                reasoning=raw.reasoning, missing=raw.missing))
        results[name]=overall_score(scores, weights)
    ab_gap=abs(results["resume_a.txt"]-results["resume_b.txt"])
    print(json.dumps(results, indent=2))
    print(f"Similar-resume A/B gap: {ab_gap:.2f} points")
    print("PASS" if ab_gap <= 15 else "REVIEW: gap exceeds 15 points")
    Path("calibration/results.json").write_text(json.dumps({"scores":results,"ab_gap":ab_gap},indent=2))
if __name__ == "__main__":
    main()
