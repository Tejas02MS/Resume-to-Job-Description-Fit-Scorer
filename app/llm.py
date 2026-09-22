import json
import time
from typing import Any

from google import genai

from app.config import get_settings


class LLMError(Exception):
    """Raised when the LLM cannot complete a request."""


def _is_retryable_error(exc: Exception) -> bool:
    """
    Return True only for temporary Gemini/API failures
    where a short retry may succeed.

    Quota exhaustion is deliberately excluded because
    retrying immediately will not restore the quota.
    """
    message = str(exc).lower()

    if (
        "resource_exhausted" in message
        or "quota exceeded" in message
        or "exceeded your current quota" in message
        or "generate_content_free_tier_requests" in message
    ):
        return False

    retryable_indicators = [
        "500",
        "502",
        "503",
        "504",
        "temporarily unavailable",
        "high demand",
        "overloaded",
    ]

    return any(
        indicator in message
        for indicator in retryable_indicators
    )


def _call_gemini(prompt: str, max_retries: int = 3) -> str:
    """
    Send a prompt to Gemini with retry and error handling.
    """

    settings = get_settings()

    if not settings.gemini_api_key:
        raise LLMError(
            "GEMINI_API_KEY is not configured. "
            "Add it to your .env file."
        )

    client = genai.Client(
        api_key=settings.gemini_api_key
    )

    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            print(
                f"Calling Gemini model '{settings.gemini_model}' "
                f"(attempt {attempt + 1}/{max_retries + 1})"
            )

            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
            )

            if not response:
                raise LLMError(
                    "Gemini returned no response."
                )

            if not response.text:
                raise LLMError(
                    "Gemini returned an empty response."
                )

            print("Gemini request successful.")

            return response.text

        except Exception as exc:
            last_error = exc

            print(
                f"Gemini request failed: {exc}"
            )

            error_message = str(exc).lower()

            # Never retry quota exhaustion.
            if (
                "resource_exhausted" in error_message
                or "quota exceeded" in error_message
                or "exceeded your current quota" in error_message
                or "generate_content_free_tier_requests"
                in error_message
            ):
                raise LLMError(
                    "Gemini API quota has been exhausted. "
                    "Please wait for the quota to reset or "
                    "use a project/API key with available quota."
                ) from exc

            if not _is_retryable_error(exc):
                raise LLMError(
                    f"Gemini request failed: {exc}"
                ) from exc

            if attempt == max_retries:
                break

            wait_seconds = 2 ** attempt

            print(
                f"Temporary Gemini failure detected. "
                f"Retrying in {wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)

    raise LLMError(
        "Gemini is temporarily unavailable after "
        f"{max_retries + 1} attempts. "
        f"Last error: {last_error}"
    )


def extract_job_criteria(
    job_description: str,
) -> list[dict[str, Any]]:
    """
    Extract exactly five standardized hiring criteria
    from the job description.

    Gemini call #1.
    """

    prompt = f"""
You are a job-description analysis system.

Extract exactly five important hiring criteria from the
job description.

Use these categories:

1. skills
2. experience
3. education
4. responsibilities
5. domain

Return ONLY valid JSON.

Expected format:

[
  {{
    "name": "skills",
    "requirement": "..."
  }},
  {{
    "name": "experience",
    "requirement": "..."
  }},
  {{
    "name": "education",
    "requirement": "..."
  }},
  {{
    "name": "responsibilities",
    "requirement": "..."
  }},
  {{
    "name": "domain",
    "requirement": "..."
  }}
]

Rules:

- Extract requirements only from the job description.
- Do not invent requirements.
- Keep each requirement concise.
- Return exactly five objects.
- The names must be exactly:
  skills, experience, education, responsibilities, domain.
- Return ONLY JSON.
- Do not use markdown code fences.

Job description:

{job_description}
"""

    raw_response = _call_gemini(prompt)

    try:
        result = json.loads(raw_response)

    except json.JSONDecodeError as exc:
        raise LLMError(
            "Gemini returned invalid JSON while extracting "
            "job criteria."
        ) from exc

    if not isinstance(result, list):
        raise LLMError(
            "Gemini returned an invalid criteria structure."
        )

    if len(result) != 5:
        raise LLMError(
            f"Expected 5 criteria but received {len(result)}."
        )

    expected_names = {
        "skills",
        "experience",
        "education",
        "responsibilities",
        "domain",
    }

    cleaned_result: list[dict[str, Any]] = []

    for item in result:

        if not isinstance(item, dict):
            raise LLMError(
                "Gemini returned an invalid criterion object."
            )

        name = str(
            item.get("name", "")
        ).strip()

        requirement = str(
            item.get("requirement", "")
        ).strip()

        if name not in expected_names:
            raise LLMError(
                f"Invalid criterion name returned by Gemini: {name}"
            )

        if not requirement:
            raise LLMError(
                f"Empty requirement returned for criterion: {name}"
            )

        cleaned_result.append(
            {
                "name": name,
                "requirement": requirement,
            }
        )

    return cleaned_result


def score_all_criteria(
    resume_text: str,
    criteria: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Score all five criteria in a single Gemini request.

    Gemini call #2.

    Each criterion is still scored independently,
    but all scores are generated in one structured response.
    """

    criteria_json = json.dumps(
        criteria,
        indent=2,
    )

    prompt = f"""
You are a resume-to-job-description fit scoring system.

Evaluate the resume against each job criterion independently.

JOB CRITERIA:

{criteria_json}

RESUME:

{resume_text}

For EACH criterion, independently determine how well the
resume satisfies the requirement.

Use ONLY evidence explicitly present in the resume.

Do NOT:

- invent experience
- assume unstated skills
- give credit for unsupported claims
- use information outside the resume
- infer qualifications that are not mentioned
- give credit simply because two technologies are related

SCORING SCALE:

0 = no evidence or contradictory evidence

25 = weak or indirect evidence

50 = partial match

75 = strong match with minor gaps

100 = clear and direct match

Return ONLY valid JSON.

Expected format:

[
  {{
    "name": "skills",
    "score": 75,
    "evidence": [
      "Specific evidence from the resume"
    ],
    "reasoning": "Explanation of why this score was assigned.",
    "missing": [
      "Relevant missing requirement"
    ]
  }},
  {{
    "name": "experience",
    "score": 50,
    "evidence": [],
    "reasoning": "...",
    "missing": []
  }},
  {{
    "name": "education",
    "score": 100,
    "evidence": [],
    "reasoning": "...",
    "missing": []
  }},
  {{
    "name": "responsibilities",
    "score": 75,
    "evidence": [],
    "reasoning": "...",
    "missing": []
  }},
  {{
    "name": "domain",
    "score": 50,
    "evidence": [],
    "reasoning": "...",
    "missing": []
  }}
]

Rules:

- Return exactly five objects.
- Use the same criterion names supplied in the input.
- score must be between 0 and 100.
- evidence must contain resume evidence.
- reasoning must explain the score.
- missing must contain relevant gaps.
- Do not use markdown.
- Return JSON only.
- Do not add extra fields.
"""

    raw_response = _call_gemini(prompt)

    try:
        result = json.loads(raw_response)

    except json.JSONDecodeError as exc:
        raise LLMError(
            "Gemini returned invalid JSON while scoring "
            "the resume."
        ) from exc

    if not isinstance(result, list):
        raise LLMError(
            "Gemini returned an invalid scoring structure."
        )

    if len(result) != 5:
        raise LLMError(
            f"Expected 5 criterion scores but received "
            f"{len(result)}."
        )

    expected_names = {
        criterion["name"]
        for criterion in criteria
    }

    returned_names = set()

    cleaned_results: list[dict[str, Any]] = []

    for item in result:

        if not isinstance(item, dict):
            raise LLMError(
                "Gemini returned an invalid scoring object."
            )

        name = str(
            item.get("name", "")
        ).strip()

        if name not in expected_names:
            raise LLMError(
                f"Unexpected criterion returned by Gemini: {name}"
            )

        if name in returned_names:
            raise LLMError(
                f"Duplicate criterion returned by Gemini: {name}"
            )

        returned_names.add(name)

        score = item.get("score")

        if not isinstance(score, (int, float)):
            raise LLMError(
                f"Invalid score returned for criterion: {name}"
            )

        if score < 0 or score > 100:
            raise LLMError(
                f"Score outside 0-100 range for criterion: {name}"
            )

        evidence = item.get(
            "evidence",
            [],
        )

        reasoning = item.get(
            "reasoning",
            "",
        )

        missing = item.get(
            "missing",
            [],
        )

        if not isinstance(evidence, list):
            raise LLMError(
                f"Invalid evidence returned for criterion: {name}"
            )

        if not isinstance(reasoning, str):
            raise LLMError(
                f"Invalid reasoning returned for criterion: {name}"
            )

        if not isinstance(missing, list):
            raise LLMError(
                f"Invalid missing items returned for criterion: {name}"
            )

        cleaned_results.append(
            {
                "name": name,
                "score": float(score),
                "evidence": [
                    str(value)
                    for value in evidence
                ],
                "reasoning": reasoning,
                "missing": [
                    str(value)
                    for value in missing
                ],
            }
        )

    if returned_names != expected_names:
        missing_names = expected_names - returned_names

        raise LLMError(
            "Gemini did not return all required criteria. "
            f"Missing: {sorted(missing_names)}"
        )

    # Keep the same order as the criteria extracted from
    # the job description.
    result_by_name = {
        item["name"]: item
        for item in cleaned_results
    }

    ordered_results = [
        result_by_name[criterion["name"]]
        for criterion in criteria
    ]

    return ordered_results