"""OCR engine registry (A1.11): honest Unsupported until an engine is available."""

from collections.abc import Sequence
from typing import Any

import pytest

from mphone_core import ocr
from mphone_protocol import Unsupported


class Stub:
    name = "stub"

    def __init__(self, ok: bool) -> None:
        self.ok = ok

    def available(self) -> bool:
        return self.ok

    def recognize(self, png: bytes, langs: Sequence[str] = ("tr", "en")) -> list[dict[str, Any]]:
        return [ocr.box("Gönder", 0.987654, 100, 200, 80, 40)]


def test_no_engine_is_unsupported_not_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ocr, "_FACTORIES", {})
    with pytest.raises(Unsupported) as e:
        ocr.get_engine()
    assert e.value.user_action


def test_auto_picks_first_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ocr, "_FACTORIES", {})
    ocr.register("vision", lambda: Stub(False))
    ocr.register("rapidocr", lambda: Stub(True))
    engine = ocr.get_engine()
    assert engine.available()
    assert engine.recognize(b"") == [
        {"text": "Gönder", "confidence": 0.988, "source": "pixels", "x": 140, "y": 220, "w": 80, "h": 40}
    ]
    with pytest.raises(Unsupported):
        ocr.get_engine("vision")
