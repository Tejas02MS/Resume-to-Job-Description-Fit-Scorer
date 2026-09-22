import json
import time
from google import genai
from google.genai import types
from pydantic import BaseModel

class LLMError(Exception):
    pass

class CriterionOutput(BaseModel):
    name: str
    requirement: str
    weight: float

class CriteriaOutput(BaseModel):
    criteria: list[CriterionOutput]

class ScoreOutput(BaseModel):
    score: float
    evidence: list[str]
    missing: list[str]
    reasoning: str

class GeminiService:
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise LLMError("GEMINI_API_KEY is not configured.")
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def _generate(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        started = time.perf_counter()
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            if not response.parsed:
                data = json.loads(response.text)
                return schema.model_validate(data)
            return response.parsed
        except Exception as exc:
            raise LLMError(f"LLM call failed: {exc}") from exc
        finally:
            self.last_latency_ms = (time.perf_counter() - started) * 1000

    def extract_criteria(self, job_description: str, weights: dict[str, float]) -> CriteriaOutput:
        prompt = f"""You are extracting hiring criteria, not ranking candidates.
Return exactly five criterion categories: skills, experience, education, responsibilities, domain.
Use the provided weights exactly. Combine related requirements within each category.
JOB DESCRIPTION:
{job_description}
WEIGHTS:
{json.dumps(weights)}
"""
        return self._generate(prompt, CriteriaOutput)

    def score_criterion(self, resume: str, criterion: CriterionOutput) -> ScoreOutput:
        prompt = f"""Score one resume against one job criterion.
Use ONLY evidence in the resume. Do not infer missing experience.
Scoring anchors:
0 = no evidence or directly contradictory
25 = weak/adjacent evidence
50 = partial match
75 = strong match with minor gaps
100 = clear, direct match
Keep scoring consistent across similar resumes. Do not reward formatting or writing style.
Return concise evidence quotes/paraphrases, missing items, and reasoning.

CRITERION:
{criterion.name}: {criterion.requirement}
RESUME:
{resume}
"""
        return self._generate(prompt, ScoreOutput)
