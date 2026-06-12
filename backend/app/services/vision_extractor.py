import base64
import json

from openai import AsyncOpenAI

from app.config import settings
from app.models.bidder import CriterionExtraction
from app.models.tender import Criterion, CriterionType

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
    Sends document page images to Qwen2.5-VL-72B via OpenRouter.
    Groups criteria into semantic clusters to reduce API calls.
    """

    CRITERION_TYPE_CLUSTERS: dict[str, list[CriterionType]] = {
        "financial": [CriterionType.CURRENCY_THRESHOLD],
        "count_date": [CriterionType.COUNT_MINIMUM, CriterionType.DATE_RANGE],
        "boolean_similarity": [CriterionType.BOOLEAN_PRESENCE, CriterionType.SIMILARITY_SCORE],
    }

    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
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
            extractions = await self._call_qwen(page_png_bytes, cluster_criteria)
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

    async def _call_qwen(
        self, page_png_bytes: bytes, criteria: list[Criterion]
    ) -> list[CriterionExtraction]:
        b64 = base64.b64encode(page_png_bytes).decode()
        criteria_json = json.dumps([
            {"criterion_id": c.criterion_id, "label": c.label,
             "type": c.criterion_type, "params": c.params.model_dump(mode="json")}
            for c in criteria
        ], indent=2)

        response = await self._client.chat.completions.create(
            model="qwen/qwen2.5-vl-72b-instruct:free",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text",
                     "text": EXTRACTION_PROMPT_TEMPLATE.format(criteria_json=criteria_json)},
                ],
            }],
            temperature=0.0,
            max_tokens=1500,
        )

        raw = response.choices[0].message.content
        items: list[dict] = json.loads(_strip_json_fences(raw))
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
        try:
            if criterion.criterion_type == CriterionType.CURRENCY_THRESHOLD:
                float(value.replace(",", "").replace("₹", "").replace("Cr", "").strip())
            elif criterion.criterion_type == CriterionType.COUNT_MINIMUM:
                int(value.strip())
            elif criterion.criterion_type == CriterionType.SIMILARITY_SCORE:
                score = float(value.strip())
                if not 0.0 <= score <= 1.0:
                    return False
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
