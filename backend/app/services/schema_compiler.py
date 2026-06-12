import json

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.config import settings
from app.models.tender import Criterion

# Gemini Flash has a 1M-token window; cap input defensively well below it
MAX_TENDER_CHARS = 800_000

COMPILE_SYSTEM_PROMPT = """
You are a government procurement expert. Extract ALL eligibility criteria from the tender document.
For each criterion output a JSON object with these exact fields:
- criterion_id: string (C-01, C-02, ...)
- label: string (short human-readable name)
- criterion_type: one of [CurrencyThreshold, CountMinimum, BooleanPresence, DateRange, SimilarityScore]
- mandatory: boolean
- params: object matching the criterion_type (see schema below)
- accepted_evidence: list of strings
- source_text: verbatim sentence(s) from the tender that this criterion is derived from

Output ONLY a JSON array of criteria. No preamble. No markdown.

Params schema per type:
- CurrencyThreshold: { "minimum_crore": float, "currency": "INR" }
- CountMinimum: { "minimum_count": int, "within_years": int|null }
- BooleanPresence: { "accepted_values": list[str] }
- DateRange: { "not_expired_as_of": ISO8601|null, "issued_after": ISO8601|null }
- SimilarityScore: { "description": str, "pass_threshold": 0.7, "fail_threshold": 0.4 }
"""

SELF_CRITIQUE_PROMPT = """
You previously extracted these criteria from a tender document:
{existing_criteria}

Re-read the tender text below and answer: are there any eligibility conditions
present in the tender that are NOT in the list above?

If yes, return ONLY the missing criteria as a JSON array (same format as before).
If no, return an empty JSON array [].
Output ONLY JSON. No preamble.

Tender text:
{tender_text}
"""


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[: -3]
    return text.strip()


class SchemaCompiler:
    """
    Calls Gemini 2.5 Flash to transform raw tender text into a typed EvaluationSchema.
    Runs a self-critique pass to catch missed criteria.
    """

    def __init__(self):
        genai.configure(api_key=settings.google_api_key)
        self._model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )

    async def compile(self, tender_text: str) -> list[Criterion]:
        tender_text = tender_text[:MAX_TENDER_CHARS]

        # Pass 1: initial extraction
        criteria_data: list[dict] = await self._generate_json(
            [COMPILE_SYSTEM_PROMPT, tender_text]
        )
        criteria = [Criterion(**c) for c in criteria_data]

        # Pass 2: self-critique (catches missed criteria)
        critique_prompt = SELF_CRITIQUE_PROMPT.format(
            existing_criteria=json.dumps(criteria_data, indent=2),
            tender_text=tender_text[:50000],  # critique pass needs less context
        )
        additional: list[dict] = await self._generate_json(critique_prompt)
        if additional:
            # Re-index criterion_ids to continue sequence
            offset = len(criteria)
            for i, c in enumerate(additional):
                c["criterion_id"] = f"C-{offset + i + 1:02d}"
            criteria.extend([Criterion(**c) for c in additional])

        return criteria

    @retry(stop=stop_after_attempt(4),
           wait=wait_random_exponential(multiplier=2, max=60),
           reraise=True)
    async def _generate_json(self, prompt) -> list[dict]:
        # Retries cover both transient API errors (429, timeouts) and the
        # occasional malformed-JSON response at temperature 0.
        response = await self._model.generate_content_async(prompt)
        return json.loads(_strip_json_fences(response.text))
