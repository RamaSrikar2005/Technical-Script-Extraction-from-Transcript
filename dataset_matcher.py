import json
import re
import os
from rapidfuzz import fuzz

_DATASET_PATH = os.path.join(os.path.dirname(__file__), "skills_dataset.json")

with open(_DATASET_PATH) as f:
    DATASET = json.load(f)

# Pre-compile patterns and build a flat lookup: (category, canonical_name) per term
_ENTRIES: list[tuple[str, str, str]] = []  # (category, canonical_name, term_lower)
for category, skills in DATASET.items():
    for skill in skills:
        terms = [skill["name"]] + skill.get("aliases", [])
        for term in terms:
            _ENTRIES.append((category, skill["name"], term.lower()))

# Sorted longest-first so multi-word terms match before single words
_ENTRIES.sort(key=lambda e: len(e[2]), reverse=True)


def _extract_tokens(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9.+#\-]*", text)
    tokens = list(words)
    for i in range(len(words) - 1):
        tokens.append(f"{words[i]} {words[i+1]}")
    for i in range(len(words) - 2):
        tokens.append(f"{words[i]} {words[i+1]} {words[i+2]}")
    return tokens


def match_from_dataset(transcript: str) -> dict:
    text_lower = transcript.lower()
    found: dict[str, set] = {cat: set() for cat in DATASET}

    # Step 1 — exact / alias substring match with word boundaries
    for category, canonical, term in _ENTRIES:
        pattern = r"(?<![a-z0-9\-#./+])" + re.escape(term) + r"(?![a-z0-9\-#./+])"
        if re.search(pattern, text_lower):
            found[category].add(canonical)

    # Step 2 — fuzzy match on transcript tokens for typo/misspelling coverage
    # Both token and term must be >= 5 chars to avoid short common words
    # matching short aliases (e.g. "and" fuzzy-matching "antd")
    tokens = _extract_tokens(transcript)
    for token in tokens:
        tok_lower = token.lower()
        if len(tok_lower) < 5:
            continue
        for category, canonical, term in _ENTRIES:
            if canonical in found[category]:
                continue
            if len(term) < 5:
                continue
            if abs(len(tok_lower) - len(term)) > 4:
                continue
            score = fuzz.ratio(tok_lower, term)
            if score >= 85:
                found[category].add(canonical)

    return {cat: sorted(skills) for cat, skills in found.items()}


def merge(dataset_result: dict, llm_result: dict) -> dict:
    merged = {}
    for cat in DATASET:
        combined = set(dataset_result.get(cat, []))
        for skill in llm_result.get(cat, []):
            combined.add(skill)
        merged[cat] = sorted(combined)
    return merged
