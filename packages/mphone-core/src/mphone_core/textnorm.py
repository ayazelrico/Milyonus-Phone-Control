"""Turkish-aware text matching (A1.06, CLAUDE.md §8.2).

`str.lower()` is wrong for Turkish: "İ".lower() is "i̇" (i + combining dot) and "I".lower() is "i"
where Turkish wants "ı". Screens mix Turkish and English ("INFO" next to "IĞDIR"), so matching
tries both foldings and treats either as a hit.

Match scores, best first (lower is better):
    1  identical
    2  equal after folding (Turkish or default casefold)
    3  query contained after folding
    4  query contained after folding and dropping Turkish accents (ç→c, ğ→g, ı→i, ö→o, ş→s, ü→u)
exact=True stops at 2.
"""

import re
import unicodedata

_TR_UPPER = str.maketrans({"I": "ı", "İ": "i"})
_ACCENTS = str.maketrans(
    {"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u"}
)
_SPACE = re.compile(r"\s+")


def _clean(s: str) -> str:
    return _SPACE.sub(" ", unicodedata.normalize("NFC", s)).strip()


def tr_fold(s: str) -> str:
    """Lowercase the Turkish way: I→ı, İ→i, then lower(). Collapses whitespace."""
    folded = _clean(s).translate(_TR_UPPER).lower()
    # NFC "İ" is one code point, but a decomposed "I" + U+0307 can survive as "i̇": drop the dot.
    return folded.replace("i̇", "i")


def default_fold(s: str) -> str:
    """Lowercase the English way (I→i)."""
    return _clean(s).casefold().replace("i̇", "i")


def strip_accents_tr(s: str) -> str:
    """Drop Turkish diacritics from already-folded text, for a last-resort match."""
    return s.translate(_ACCENTS)


def _forms(s: str) -> tuple[str, str]:
    return tr_fold(s), default_fold(s)


def match(query: str, text: str, exact: bool = False) -> int | None:
    """Score how well `text` matches `query` (see module doc), or None for no match."""
    if not query.strip():
        return None
    if _clean(query) == _clean(text):
        return 1
    q_forms, t_forms = _forms(query), _forms(text)
    if any(q == t for q, t in zip(q_forms, t_forms, strict=True)):
        return 2
    if exact:
        return None
    if any(q in t for q, t in zip(q_forms, t_forms, strict=True)):
        return 3
    if any(strip_accents_tr(q) in strip_accents_tr(t) for q in q_forms for t in t_forms):
        return 4
    return None
