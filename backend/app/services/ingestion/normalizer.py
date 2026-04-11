import re

WORD_TO_INT = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


def _extract_single_number(value: str) -> float | None:
    matches = re.findall(r"-?\d+(?:,\d{3})*(?:\.\d+)?", value)
    if len(matches) != 1:
        return None

    try:
        return float(matches[0].replace(",", ""))
    except ValueError:
        return None


def _extract_word_number(value: str) -> int | None:
    tokens = re.findall(r"[a-z]+", value.lower())
    hits = [WORD_TO_INT[token] for token in tokens if token in WORD_TO_INT]
    if len(hits) != 1:
        return None
    return hits[0]


def parse_currency(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None

    text = value.lower().strip()
    number = _extract_single_number(text)
    if number is None:
        return None

    multiplier = 1.0
    suffix_match = re.search(r"-?\d+(?:,\d{3})*(?:\.\d+)?\s*([km])\b", text)
    if suffix_match:
        multiplier = 1_000.0 if suffix_match.group(1) == "k" else 1_000_000.0

    return float(number * multiplier)


def parse_percentage(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None

    text = value.lower().strip()
    number = _extract_single_number(text)
    if number is None:
        return None

    has_percent_marker = "%" in text or "percent" in text or "pct" in text
    if not has_percent_marker and 0 <= number <= 1:
        # Strict mode: reject ambiguous fractional DTI without explicit percent marker.
        return None

    return float(number)


def parse_integer(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None

    text = value.lower().strip()

    if re.search(r"\d", text):
        if re.search(r"\.\d*[1-9]", text):
            return None
        number = _extract_single_number(text)
        if number is None:
            return None
        return int(number)

    word_number = _extract_word_number(text)
    if word_number is not None:
        return int(word_number)

    return None


def parse_months(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None

    text = value.lower().strip()
    text = re.sub(r"\byrs?\b", "years", text)
    text = re.sub(r"\bmos?\b", "months", text)

    number = _extract_single_number(text)
    if number is None:
        word_number = _extract_word_number(text)
        if word_number is None:
            return None
        number = float(word_number)

    if "year" in text:
        return int(number * 12)

    if "month" in text or text.endswith("m") or text.isdigit():
        if number.is_integer():
            return int(number)
        return None

    if number.is_integer():
        return int(number)
    return None
