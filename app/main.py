import time
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from .config import get_settings
from .parser import extract_resume_text, ResumeParseError
from .llm import GeminiService, LLMError
from .scoring import calibrated_score, overall_score
from .schemas import AnalysisResponse, CriterionScore, Criterion

app = FastAPI(title="Resume to Job-Description Fit Scorer", version="1.0.0")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    job_description: str = Form(...),
    resume: UploadFile = File(...),
):
    started = time.perf_counter()
    settings = get_settings()
    if len(job_description.strip()) < 80:
        raise HTTPException(422, "Job description must contain at least 80 characters.")
    content = await resume.read()
    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(413, f"Resume exceeds {settings.max_file_size_mb} MB.")
    try:
        resume_text, parser_warning = extract_resume_text(resume.filename or "resume.txt", content)
    except ResumeParseError as exc:
        raise HTTPException(422, str(exc))
    if not resume_text:
        raise HTTPException(422, "Resume parser could not read any text. Try a text-based PDF or TXT.")

    try:
        llm = GeminiService(settings.gemini_api_key, settings.gemini_model)
        weights = settings.normalized_weights()
        extracted = llm.extract_criteria(job_description, weights)
        criterion_scores = []
        for c in extracted.criteria:
            raw = llm.score_criterion(resume_text, c)
            score = calibrated_score(raw.score)
            criterion_scores.append(CriterionScore(
                name=c.name,
                requirement=c.requirement,
                score=score,
                weighted_score=round(score * weights.get(c.name, 0), 2),
                evidence=raw.evidence,
                reasoning=raw.reasoning,
                missing=raw.missing,
            ))
    except LLMError as exc:
        raise HTTPException(502, str(exc))

    overall = overall_score(criterion_scores, weights)
    elapsed = (time.perf_counter() - started) * 1000
    return AnalysisResponse(
        overall_score=overall,
        criteria=criterion_scores,
        summary="Overall fit is the weighted combination of separately scored criteria.",
        calibration_note="Scores are temperature-0 and compressed 15% toward 50 to reduce large gaps from small wording changes.",
        latency_ms=round(elapsed, 2),
        parser_warning=parser_warning,
        resume_filename=resume.filename or "resume",
        job_criteria=[Criterion(**c.model_dump()) for c in extracted.criteria],
    )
