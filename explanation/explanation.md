# One-Page Explanation — Resume to Job-Description Fit Scorer

## 1. Design parameter — calibration strength (15%)

I chose to compress the LLM's 0–100 criterion scores by 15% toward the midpoint of 50:

```text
calibrated_score = 50 + 0.85 × (raw_score - 50)
```

I chose this because similar resumes should not receive excessively different scores because of small wording differences. The scoring prompt uses explicit score anchors: 0, 25, 50, 75, and 100.

The calibration demonstration uses three sample resumes. Two are intentionally similar, and the third is more different. The project uses a 15-point gap as a practical calibration guardrail. In the demonstration, Resume A and Resume B have a raw score gap of 4.00 points and a calibrated gap of 3.40 points, so they remain within the guardrail.

The 15-point threshold is a project-level diagnostic and is not an industry-standard hiring threshold.

## 2. Failure actually observed

Two important failures were observed during testing.

First, an unreadable/non-text PDF produced no usable resume text. Sending an empty resume to the LLM could produce a misleading score, so the parser/API flow was changed to return a controlled HTTP 422 validation error instead.

Second, during live Gemini testing, the first LLM request succeeded but the second request returned HTTP 429 `RESOURCE_EXHAUSTED` because the Gemini free-tier request quota was exceeded. The application detects quota exhaustion and returns a controlled HTTP 502 response instead of repeatedly retrying the request.

A production follow-up would add OCR for scanned or image-only PDFs and use an API plan with sufficient quota for production workloads.

## 3. Metric tracked

I tracked end-to-end API latency in milliseconds and expose it in successful responses. This measures the operational cost of the complete pipeline, including job-criterion extraction and resume scoring.

I also track the score gap between similar resumes in the calibration demonstration. This provides a simple stability diagnostic without claiming model accuracy.

A larger labeled dataset is still required to measure actual predictive accuracy or agreement with human evaluators.

## 4. What is not finished / next steps

The project does not currently include OCR, a large human-labeled evaluation dataset, authentication, a frontend, persistent storage, or deployment. These were outside the required local-service scope.

The next steps would be:

1. Add OCR for image-only/scanned resumes.
2. Build a human-labeled resume/job-description benchmark.
3. Measure scoring agreement and ranking performance against that benchmark.
4. Add automated regression tests for scoring and parsing.
5. Add structured-output validation for the LLM responses.
6. Deploy with appropriate API quota, monitoring, authentication, and rate limiting.

The LLM pipeline already uses two calls: one call extracts the five job criteria and one call scores all five criteria together. This reduces unnecessary LLM requests compared with making a separate request for every criterion.

## Honest status

The core workflow is implemented and locally tested, including resume parsing, validation, criterion extraction, criterion scoring architecture, configurable weights, calibration, and controlled error handling.

A complete live two-call analysis was partially demonstrated: the first Gemini request succeeded, while the second was blocked by the external free-tier quota. This limitation is documented rather than presented as a successful end-to-end result.

The main remaining uncertainty is scoring accuracy on a larger human-labeled dataset.