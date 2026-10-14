"""Turkish-aware matching (A1.06)."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mphone_core.textnorm import match, strip_accents_tr, tr_fold


@pytest.mark.parametrize(
    ("raw", "folded"),
    [
        ("İSTANBUL", "istanbul"),
        ("IĞDIR", "ığdır"),
        ("ŞİŞLİ", "şişli"),
        ("Çağrı", "çağrı"),
        ("ÖMER ÇELİK", "ömer çelik"),
        ("  Telefon   hakkında ", "telefon hakkında"),
        ("İ", "i"),  # decomposed İ
    ],
)
def test_tr_fold(raw: str, folded: str) -> None:
    assert tr_fold(raw) == folded


@pytest.mark.parametrize(
    ("query", "text", "exact", "score"),
    [
        ("Ayarlar", "Ayarlar", False, 1),
        ("ayarlar", "AYARLAR", False, 2),
        ("istanbul", "İSTANBUL", True, 2),
        ("ığdır", "IĞDIR", True, 2),
        ("info", "INFO", True, 2),  # English uppercase I must still match
        ("hakkında", "Telefon hakkında", False, 3),
        ("hakkinda", "Telefon hakkında", False, 4),
        ("gonder", "Gönder", False, 4),
        ("cagri", "ÇAĞRI", False, 4),
        ("Gönder", "Gönderildi", True, None),
        ("c", "ç", True, None),  # exact keeps accents distinct
        ("xyz", "Ayarlar", False, None),
        ("", "Ayarlar", False, None),
    ],
)
def test_match(query: str, text: str, exact: bool, score: int | None) -> None:
    assert match(query, text, exact) == score


def test_strip_accents() -> None:
    assert strip_accents_tr("çağrı ışığı söndü şule") == "cagri isigi sondu sule"


@given(st.text(max_size=40))
def test_fold_is_idempotent(s: str) -> None:
    assert tr_fold(tr_fold(s)) == tr_fold(s)


@given(st.text(min_size=1, max_size=30).filter(lambda s: s.strip()))
def test_text_always_matches_itself(s: str) -> None:
    assert match(s, s) == 1
    assert match(s, s, exact=True) == 1
