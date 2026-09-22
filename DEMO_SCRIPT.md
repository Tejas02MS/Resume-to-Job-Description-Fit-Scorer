# 3–5 Minute Walkthrough Script

**0:00–0:30 — Intro**
“I'm showing a Resume to Job-Description Fit Scorer built with Python, FastAPI, Pydantic, PyMuPDF and Gemini. It extracts criteria, scores each separately, then applies configurable weights.”

**0:30–1:30 — Live input**
Open `/docs`, use a new job description and a resume that were not included in the repository. Submit `/analyze`. Point out the overall score, criteria, evidence, missing items, reasoning and latency.

**1:30–2:30 — Code**
Open `app/main.py`. Explain that the endpoint validates the upload, parses the resume, extracts criteria, scores each criterion independently, calibrates the raw score, and computes the weighted overall score.
Open `app/scoring.py` and explain the 15% midpoint compression.

**2:30–3:15 — Prompt**
Open `app/llm.py`. Show the scoring prompt and explain the explicit 0/25/50/75/100 anchors and the instruction to use only resume evidence.

**3:15–4:00 — Edge case + calibration**
Run `python calibration/run_calibration.py` and show the A/B gap. Then upload a blank/image-only PDF or otherwise unreadable PDF and show the controlled parser error.

**4:00–4:30 — Close**
Mention the tracked latency metric and the unfinished items: OCR, larger labeled benchmark, frontend/auth/deployment.
