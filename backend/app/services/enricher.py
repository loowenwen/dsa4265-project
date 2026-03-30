import re

UNSURE_TOKENS = [
    "unknown",
    "not provided",
    "no additional",
    "cannot identify",
    "n/a",
    "na",
]

DEMOGRAPHIC_PATTERNS = {
    "age": r"\bage\s*[:\-]\s*([A-Za-z0-9 ]{1,40})",
    "gender": r"\bgender\s*[:\-]\s*([A-Za-z ]{1,40})",
    "marital_status": r"\bmarital\s+status\s*[:\-]\s*([A-Za-z ]{1,40})",
    "nationality": r"\bnationality\s*[:\-]\s*([A-Za-z ]{1,40})",
    "citizenship": r"\bcitizenship\s*[:\-]\s*([A-Za-z ]{1,40})",
    "dependents": r"\bdependents?\s*[:\-]\s*([A-Za-z0-9 ]{1,40})",
}


def extract_demographic_information(text: str | None) -> tuple[str, str | None]:
    if text is None or not text.strip():
        return "cannot identify", None

    lowered = text.lower()
    found_pairs: list[str] = []
    source_snippets: list[str] = []

    for key, pattern in DEMOGRAPHIC_PATTERNS.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        value = match.group(1).strip(" .")
        if not value:
            continue
        if value.lower() in UNSURE_TOKENS:
            continue

        found_pairs.append(f"{key}: {value}")
        source_snippets.append(match.group(0).strip())

    if found_pairs:
        return "; ".join(found_pairs), "; ".join(source_snippets)

    if any(token in lowered for token in UNSURE_TOKENS) or "?" in text:
        return "cannot identify", None

    return "cannot identify", None
