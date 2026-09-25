"""Deterministic FAQ intent matcher; no AI calls."""
import re
import unicodedata
from difflib import SequenceMatcher
from dataclasses import dataclass

STOPWORDS = {"what", "is", "the", "a", "an", "of", "do", "i", "how", "can", "to", "for", "my", "and", "does", "mean", "explain", "tell", "me"}
SYNONYMS = [("isi", "isi", "isi mark", "isi certification"), ("hallmark", "hallmarking"), ("certification", "certify", "certified")]

def normalize_question(text: str) -> str:
    """Normalize while preserving letters from all supported Unicode scripts."""
    text = unicodedata.normalize("NFKC", text or "").casefold().strip()
    # Keep Unicode letters/numbers; turn punctuation and symbols into spaces.
    text = "".join(
        ch if (ch.isspace() or unicodedata.category(ch)[0] in {"L", "M", "N"}) else " "
        for ch in text
    )
    return re.sub(r"\s+", " ", text).strip()

def _tokens(text: str) -> set[str]:
    tokens = set(normalize_question(text).split()) - STOPWORDS
    for group in SYNONYMS:
        if tokens.intersection(group):
            tokens.difference_update(group)
            tokens.add(group[0])
    return tokens

@dataclass(frozen=True)
class FAQMatch:
    question: str
    answer: str
    category: str | None
    confidence: float

class FAQMatcher:
    def __init__(self, faqs, threshold: float = 0.62):
        self.faqs = list(faqs)
        self.threshold = threshold

    def match(self, question: str, category: str | None = None) -> FAQMatch | None:
        normalized = normalize_question(question)
        best = None
        for faq in self.faqs:
            faq_q = faq.get("q", "")
            faq_norm = normalize_question(faq_q)
            if normalized == faq_norm:
                score = 1.0
            else:
                a, b = _tokens(normalized), _tokens(faq_norm)
                overlap = len(a & b) / max(len(a | b), 1)
                sequence = SequenceMatcher(None, normalized, faq_norm).ratio()
                score = 0.70 * overlap + 0.30 * sequence
                # Strong domain term match supports paraphrases such as
                # "What does ISI mean?" -> "What is the ISI mark?"
                if "isi" in a and "isi" in b:
                    score = max(score, 0.75)
                faq_category = faq.get("category")
                if category and faq_category:
                    score += 0.10 if category == faq_category else -0.05
            score = max(0.0, min(1.0, score))
            if best is None or score > best.confidence:
                best = FAQMatch(faq_q, faq.get("a", ""), faq.get("category"), score)
        return best if best and best.confidence >= self.threshold else None
