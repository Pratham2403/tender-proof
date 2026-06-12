"""
Deterministic parsing of LLM-extracted values into typed Python values.
Shared by the rule engine (verdict comparisons) and the vision extractor
(type-validation confidence heuristics) so both always agree on what parses.
"""

# Order matters: longer tokens are stripped before their prefixes
_CURRENCY_TOKENS = [
    "₹", "rs.", "rs", "inr", "crores", "crore", "cr.", "cr", "lakhs", "lakh", ","
]

# An annual-turnover threshold expressed in crore is always a small number;
# anything above this is almost certainly an absolute rupee figure.
_RUPEES_HEURISTIC_CUTOFF = 100_000.0
_RUPEES_PER_CRORE = 10_000_000.0


def parse_crore(value: str) -> float:
    """
    Parse a currency string into a value in crore.

    Handles: "8.45", "₹8.45 Cr", "Rs. 8.45 Crore", "8,45,00,000" (absolute
    rupees — converted to crore via magnitude heuristic).
    Raises ValueError if the remainder is not numeric.
    """
    s = value.strip().lower()
    is_lakh = "lakh" in s
    for tok in _CURRENCY_TOKENS:
        s = s.replace(tok, "")
    amount = float(s.strip())
    if is_lakh:
        return amount / 100.0  # 100 lakh = 1 crore
    if amount > _RUPEES_HEURISTIC_CUTOFF:
        return amount / _RUPEES_PER_CRORE
    return amount


def parse_count(value: str) -> int:
    return int(value.strip())


def parse_score(value: str) -> float:
    score = float(value.strip())
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"similarity score {score} outside [0, 1]")
    return score
