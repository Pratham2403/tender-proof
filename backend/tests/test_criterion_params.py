"""
The params union must resolve deterministically from raw dicts (the shape
criteria take after a MongoDB round-trip) using criterion_type as the
discriminator — never by smart-union scoring.
"""

from app.models.tender import (
    BooleanPresenceParams,
    CountMinimumParams,
    Criterion,
    CurrencyThresholdParams,
    DateRangeParams,
    SimilarityScoreParams,
)


def make(ctype: str, params: dict) -> Criterion:
    return Criterion(criterion_id="C-01", label="x", criterion_type=ctype,
                     mandatory=True, params=params,
                     accepted_evidence=[], source_text="")


def test_each_type_resolves_to_its_own_params_model():
    cases = {
        "CurrencyThreshold": ({"minimum_crore": 5.0}, CurrencyThresholdParams),
        "CountMinimum": ({"minimum_count": 3, "within_years": 5}, CountMinimumParams),
        "BooleanPresence": ({"accepted_values": ["GST"]}, BooleanPresenceParams),
        "DateRange": ({"not_expired_as_of": "2025-03-31T00:00:00"}, DateRangeParams),
        "SimilarityScore": ({"description": "similar work"}, SimilarityScoreParams),
    }
    for ctype, (params, expected_cls) in cases.items():
        c = make(ctype, params)
        assert type(c.params) is expected_cls, ctype


def test_ambiguous_empty_dict_resolves_by_type():
    # {} validates against several param models; the discriminator must win
    c = make("BooleanPresence", {})
    assert type(c.params) is BooleanPresenceParams
    c = make("DateRange", {})
    assert type(c.params) is DateRangeParams


def test_round_trip_through_dump_is_stable():
    c = make("CountMinimum", {"minimum_count": 3, "within_years": 5})
    c2 = Criterion(**c.model_dump())
    assert type(c2.params) is CountMinimumParams
    assert c2.params.minimum_count == 3
    assert c2.params.within_years == 5
