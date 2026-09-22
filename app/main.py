import time

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from .config import get_settings
from .parser import (
    extract_resume_text,
    ResumeParseError,
)
from .llm import (
    extract_job_criteria,
    score_all_criteria,
    LLMError,
)
from .scoring import (
    calibrated_score,
    overall_score,
)
from .schemas import (
    AnalysisResponse,
    CriterionScore,
    Criterion,
)


app = FastAPI(
    title="Resume to Job-Description Fit Scorer",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post(
    "/analyze",
    response_model=AnalysisResponse,
)
async def analyze(
    job_description: str = Form(...),
    resume: UploadFile = File(...),
):
    started = time.perf_counter()

    settings = get_settings()

    # ---------------------------------------------------------
    # Validate job description
    # ---------------------------------------------------------

    if len(job_description.strip()) < 80:
        raise HTTPException(
            status_code=422,
            detail=(
                "Job description must contain "
                "at least 80 characters."
            ),
        )

    # ---------------------------------------------------------
    # Read uploaded resume
    # ---------------------------------------------------------

    content = await resume.read()

    # ---------------------------------------------------------
    # Validate file size
    # ---------------------------------------------------------

    if (
        len(content)
        > settings.max_file_size_mb * 1024 * 1024
    ):
        raise HTTPException(
            status_code=413,
            detail=(
                f"Resume exceeds "
                f"{settings.max_file_size_mb} MB."
            ),
        )

    # ---------------------------------------------------------
    # Extract resume text
    # ---------------------------------------------------------

    try:
        resume_text, parser_warning = extract_resume_text(
            resume.filename or "resume.txt",
            content,
        )

    except ResumeParseError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    # ---------------------------------------------------------
    # Make sure parser actually found text
    # ---------------------------------------------------------

    if not resume_text.strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "Resume parser could not read any text. "
                "Try a text-based PDF or TXT."
            ),
        )

    # ---------------------------------------------------------
    # Gemini analysis
    # ---------------------------------------------------------

    try:
        weights = settings.normalized_weights()

        # -----------------------------------------------------
        # Gemini call #1
        # Extract five job criteria
        # -----------------------------------------------------

        extracted_criteria = extract_job_criteria(
            job_description
        )

        # -----------------------------------------------------
        # Gemini call #2
        # Score all five criteria
        # -----------------------------------------------------

        raw_scores = score_all_criteria(
            resume_text=resume_text,
            criteria=extracted_criteria,
        )

        # -----------------------------------------------------
        # Build criterion score objects
        # -----------------------------------------------------

        criterion_scores = []

        for raw_result in raw_scores:

            name = raw_result["name"]

            requirement = next(
                criterion["requirement"]
                for criterion in extracted_criteria
                if criterion["name"] == name
            )

            raw_score = raw_result["score"]

            # Apply calibration.
            calibrated = calibrated_score(
                raw_score
            )

            criterion_scores.append(
                CriterionScore(
                    name=name,
                    requirement=requirement,
                    score=calibrated,
                    weighted_score=round(
                        calibrated
                        * weights.get(name, 0),
                        2,
                    ),
                    evidence=raw_result.get(
                        "evidence",
                        [],
                    ),
                    reasoning=raw_result.get(
                        "reasoning",
                        "",
                    ),
                    missing=raw_result.get(
                        "missing",
                        [],
                    ),
                )
            )

    except LLMError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    # ---------------------------------------------------------
    # Calculate overall score
    # ---------------------------------------------------------

    overall = overall_score(
        criterion_scores,
        weights,
    )

    # ---------------------------------------------------------
    # Calculate latency
    # ---------------------------------------------------------

    elapsed = (
        time.perf_counter() - started
    ) * 1000

    # ---------------------------------------------------------
    # Build final response
    # ---------------------------------------------------------

    return AnalysisResponse(
        overall_score=overall,

        summary=(
            "Overall fit is the weighted combination "
            "of separately scored criteria."
        ),

        calibration_note=(
            "Scores are calibrated by compressing "
            "raw scores 15% toward 50 to reduce large "
            "gaps caused by small wording changes."
        ),

        latency_ms=round(
            elapsed,
            2,
        ),

        parser_warning=parser_warning,

        resume_filename=(
            resume.filename or "resume"
        ),

        job_criteria=[
            Criterion(
                name=criterion["name"],
                requirement=criterion["requirement"],
                weight=weights.get(
                    criterion["name"],
                    0,
                ),
            )
            for criterion in extracted_criteria
        ],

        criteria=criterion_scores,
    )