import pytest

from app.services.value_parsing import parse_count, parse_crore, parse_score


class TestParseCrore:
    @pytest.mark.parametrize("raw,expected", [
        ("8.45", 8.45),
        ("₹8.45 Cr", 8.45),
        ("Rs. 8.45 Crore", 8.45),
        ("rs 5 crores", 5.0),
        ("INR 12.5", 12.5),
        ("5,00,00,000", 5.0),        # absolute rupees → crore
        ("84500000", 8.45),           # absolute rupees → crore
        ("50 lakh", 0.5),             # 100 lakh = 1 crore
        ("₹ 6.10 Cr.", 6.10),
    ])
    def test_parses(self, raw, expected):
        assert parse_crore(raw) == pytest.approx(expected)

    @pytest.mark.parametrize("raw", ["eight crore", "", "N/A", "approx five"])
    def test_rejects_non_numeric(self, raw):
        with pytest.raises(ValueError):
            parse_crore(raw)


class TestParseCount:
    def test_parses(self):
        assert parse_count(" 5 ") == 5

    def test_rejects(self):
        with pytest.raises(ValueError):
            parse_count("several")


class TestParseScore:
    def test_parses(self):
        assert parse_score("0.85") == 0.85

    def test_rejects_out_of_range(self):
        with pytest.raises(ValueError):
            parse_score("1.5")
