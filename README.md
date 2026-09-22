# Resume to Job-Description Fit Scorer

A small applied-AI service that accepts a job description plus a PDF/TXT resume and returns a structured, criterion-by-criterion fit assessment.

## Why this design

The system deliberately separates:
1. **Parsing** — PyMuPDF for PDFs and UTF-8 decoding for TXT.
2. **Criterion extraction** — Gemini extracts five fixed categories.
3. **Criterion scoring** — Gemini scores each category independently using explicit anchors.
4. **Calibration** — scores are temperature-0 and compressed 15% toward the midpoint to reduce large score gaps caused by small wording differences.
5. **Weighted aggregation** — weights are configuration, not embedded in the formula.

## Requirements

- Python 3.11+
- Gemini API key
- No frontend/database/authentication required

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Put your Gemini API key in `.env`.

Run:
```powershell
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

## Usage

Use `POST /analyze` in Swagger. Provide:
- `job_description`: at least 80 characters
- `resume`: PDF or TXT

Example with curl:
```bash
curl -X POST "http://127.0.0.1:8000/analyze" ^
  -F "job_description=We need a Python FastAPI developer with React and MongoDB..." ^
  -F "resume=@sample_data/resume_a.txt"
```

The response contains:
- overall score
- extracted criteria
- per-criterion score
- weighted contribution
- evidence
- missing requirements
- reasoning
- parser warning
- total latency

## Configurable weights

The default weights live in `app/config.py`:
- skills: 0.40
- experience: 0.25
- education: 0.10
- responsibilities: 0.15
- domain: 0.10

`normalized_weights()` normalizes them before use, so changing the values does not require changing scoring logic.

## LLM error handling

Gemini calls are wrapped in `LLMError`. The API returns HTTP 502 instead of an unhandled traceback. Missing API keys are also detected. Invalid/corrupt/unreadable resumes return a controlled HTTP 422 response.

## Parser-unreadable case

A PDF that contains no extractable text produces a parser warning / controlled 422 response rather than silently scoring an empty resume. For a real production system, OCR would be the next addition.

## Calibration demonstration

Run:
```powershell
python calibration/run_calibration.py
```

This evaluates `resume_a.txt`, `resume_b.txt`, and `resume_c.txt` against the same job description. A and B are intentionally near-duplicates. The script reports their score gap and marks PASS when it is <= 15 points.

The 15-point threshold is a practical calibration guardrail for this take-home, not a universal industry standard.

## What works

- PDF and TXT ingestion
- Pydantic validation
- LLM criterion extraction
- independent criterion scoring
- configurable weights
- calibrated aggregation
- evidence/reasoning in the result
- controlled parser and LLM failures
- latency measurement
- calibration sample script

## What does not

- No OCR for image-only/scanned PDFs
- No persistent database
- No authentication/deployment/frontend
- No automated benchmark over a large labeled dataset
- LLM results still depend on the quality of the supplied resume and job description

## Metric

The API reports end-to-end latency in milliseconds. The calibration script also records the score gap between similar resumes. The metric is used to understand operational cost/latency and scoring stability, not to claim model accuracy without labeled ground truth.

## Safety / interpretation

Scores are decision support, not an automatic hiring decision. Evidence and missing items should be reviewed by a recruiter.

## Project structure

```text
app/
  config.py       # settings and weights
  llm.py          # Gemini calls + error handling
  parser.py       # PDF/TXT extraction
  scoring.py      # calibration and weighted aggregation
  schemas.py      # Pydantic models
  main.py         # FastAPI endpoint
calibration/
  run_calibration.py
sample_data/
  job_description.txt
  resume_a.txt
  resume_b.txt
  resume_c.txt
explanation/
  explanation.md
```
