import base64
import json
import logging

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.config import settings
from app.models.bidder import CriterionExtraction
from app.models.tender import Criterion, CriterionType
from app.services.value_parsing import parse_count, parse_crore, parse_score

logger = logging.getLogger("tenderproof.vision_extractor")

EXTRACTION_PROMPT_TEMPLATE = """
You are extracting information from a government procurement bid document page.

For each criterion below, examine this document page and extract the relevant value.
Respond with a JSON array — one object per criterion — with these fields:
- criterion_id: string (copy from input)
- extracted_value: string | null  (null if not found on this page)
- confidence: float 0.0–1.0 (your confidence the extracted value is correct)
- raw_text: string | null (verbatim passage from the page supporting the extraction)

For SimilarityScore criteria, extracted_value must be a similarity score between
0.0 and 1.0 measuring how well the page content matches the criterion description.
Be conservative with confidence. If the page image is blurry, partially cut off,
or the value is ambiguous, reflect that in a lower confidence score (< 0.6).
Output ONLY a JSON array. No preamble. No markdown.

Criteria to extract:
{criteria_json}
"""

CONFIDENCE_BOOST_ON_VALID_PARSE = 0.10
MAX_CONFIDENCE = 1.0
CONFIDENCE_CAP_ON_PARSE_FAILURE = 0.50


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[: -3]
    return text.strip()


class VisionExtractor:
    """
    Sends document page images to Gemini 2.5 Flash Lite (Google AI Studio free tier).
    Groups criteria into semantic clusters to reduce API calls.

    Failure containment: each cluster call retries with exponential backoff
    and jitter (handles 429s and transient malformed JSON). If a cluster still
    fails after all retries, its criteria get no extraction from this page —
    the confidence-0 fallback routes them to REVIEW rather than crashing the
    bidder's whole extraction job.
    """

    CRITERION_TYPE_CLUSTERS: dict[str, list[CriterionType]] = {
        "financial": [CriterionType.CURRENCY_THRESHOLD],
        "count_date": [CriterionType.COUNT_MINIMUM, CriterionType.DATE_RANGE],
        "boolean_similarity": [CriterionType.BOOLEAN_PRESENCE, CriterionType.SIMILARITY_SCORE],
    }

    def __init__(self):
        genai.configure(api_key=settings.google_api_key)
        self._model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite",
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )

    async def extract_page(
        self,
        page_png_bytes: bytes,
        criteria: list[Criterion],
    ) -> list[CriterionExtraction]:
        """
        Extracts criterion values from a single page image.
        Returns one CriterionExtraction per criterion (extracted_value may be None).
        """
        clusters = self._cluster_criteria(criteria)
        all_extractions: dict[str, CriterionExtraction] = {}

        for cluster_criteria in clusters:
            try:
                extractions = await self._call_gemini(page_png_bytes, cluster_criteria)
            except Exception:
                logger.warning(
                    "vision extraction failed for cluster %s after retries; "
                    "routing its criteria to REVIEW via confidence 0",
                    [c.criterion_id for c in cluster_criteria],
                    exc_info=True,
                )
                continue
            for ext in extractions:
                existing = all_extractions.get(ext.criterion_id)
                if existing is None or ext.confidence > existing.confidence:
                    all_extractions[ext.criterion_id] = ext

        # Ensure every criterion has an entry (None if not found)
        for c in criteria:
            if c.criterion_id not in all_extractions:
                all_extractions[c.criterion_id] = CriterionExtraction(
                    criterion_id=c.criterion_id,
                    extracted_value=None,
                    confidence=0.0,
                    document_name=None,
                    page_number=None,
                    raw_text=None,
                )
        return list(all_extractions.values())

    @retry(stop=stop_after_attempt(4),
           wait=wait_random_exponential(multiplier=2, max=60),
           reraise=True)
    async def _call_gemini(
        self, page_png_bytes: bytes, criteria: list[Criterion]
    ) -> list[CriterionExtraction]:
        criteria_json = json.dumps([
            {"criterion_id": c.criterion_id, "label": c.label,
             "type": c.criterion_type, "params": c.params.model_dump(mode="json")}
            for c in criteria
        ], indent=2)

        image_part = {
            "inline_data": {
                "mime_type": "image/png",
                "data": base64.b64encode(page_png_bytes).decode(),
            }
        }
        text_part = EXTRACTION_PROMPT_TEMPLATE.format(criteria_json=criteria_json)

        response = await self._model.generate_content_async([image_part, text_part])
        items: list[dict] = json.loads(_strip_json_fences(response.text))
        return [self._build_extraction(item, criteria) for item in items]

    def _build_extraction(self, item: dict, criteria: list[Criterion]) -> CriterionExtraction:
        criterion = next((c for c in criteria if c.criterion_id == item.get("criterion_id")), None)
        confidence = float(item.get("confidence", 0.0))
        value = item.get("extracted_value")
        if value is not None:
            value = str(value)

        if value is not None and criterion is not None:
            if self._validate_value_type(value, criterion):
                confidence = min(confidence + CONFIDENCE_BOOST_ON_VALID_PARSE, MAX_CONFIDENCE)
            else:
                confidence = min(confidence, CONFIDENCE_CAP_ON_PARSE_FAILURE)

        return CriterionExtraction(
            criterion_id=item.get("criterion_id", ""),
            extracted_value=value,
            confidence=confidence,
            document_name=None,  # Set by caller (knows the file context)
            page_number=None,    # Set by caller
            raw_text=item.get("raw_text"),
        )

    def _validate_value_type(self, value: str, criterion: Criterion) -> bool:
        # Must agree with the rule engine's parsing, so a value that gets a
        # confidence boost here can never hit a parse error at verdict time.
        try:
            if criterion.criterion_type == CriterionType.CURRENCY_THRESHOLD:
                parse_crore(value)
            elif criterion.criterion_type == CriterionType.COUNT_MINIMUM:
                parse_count(value)
            elif criterion.criterion_type == CriterionType.SIMILARITY_SCORE:
                parse_score(value)
            return True
        except (ValueError, AttributeError):
            return False

    def _cluster_criteria(self, criteria: list[Criterion]) -> list[list[Criterion]]:
        clusters: dict[str, list[Criterion]] = {k: [] for k in self.CRITERION_TYPE_CLUSTERS}
        for c in criteria:
            for cluster_name, types in self.CRITERION_TYPE_CLUSTERS.items():
                if c.criterion_type in types:
                    clusters[cluster_name].append(c)
                    break
        return [v for v in clusters.values() if v]
