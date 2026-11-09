"""Tokenization and sentence splitting helpers."""

import re
from decimal import Decimal, InvalidOperation

WORD_RE = re.compile(r"[a-z0-9']+")
SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?]+(?:[\"')\]]+)?|[^.!?\n]+$", re.MULTILINE)
NUMBER_RE = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?!\w|\.\d)")

# Small stopword list: support scoring compares content tokens only.
STOPWORDS = frozenset(
    "a an and are as at be but by for from has have he her his i in is it its "
    "of on or she so that the their they this to was we were which will with you".split()
)


def content_tokens(text):
    """Lowercase content tokens (stopwords removed)."""
    return [t for t in WORD_RE.findall(text.lower()) if t not in STOPWORDS]


DECIMAL_RE = re.compile(r"(?<=\d)\.(?=\d)")


def split_sentences(text):
    """Split text into sentence strings; decimal points are not boundaries."""
    masked = DECIMAL_RE.sub("\x00", text)
    parts = SENTENCE_RE.findall(masked)
    return [s.replace("\x00", ".").strip() for s in parts if s.strip()]


def extract_numbers(text):
    """Extract numeric literals as normalized strings (commas stripped)."""
    return [m.replace(",", "") for m in NUMBER_RE.findall(text)]


def numbers_present(number, haystack_numbers):
    """Exact decimal-value equality, without binary64 rounding or infinity aliasing."""
    try:
        value = Decimal(number)
        if not value.is_finite():
            return False
        for other in haystack_numbers:
            try:
                candidate = Decimal(other)
                if candidate.is_finite() and candidate == value:
                    return True
            except (InvalidOperation, ValueError, TypeError):
                continue
        return False
    except (InvalidOperation, ValueError, TypeError):
        return False
