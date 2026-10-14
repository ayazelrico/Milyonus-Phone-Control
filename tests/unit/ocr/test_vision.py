"""Apple Vision on a rendered Turkish screen (macOS only)."""

import sys
from pathlib import Path

import pytest

from mphone_backends.ocr.vision import VisionEngine
from mphone_core.helpers import connect
from mphone_core.textnorm import match

pytestmark = [pytest.mark.macos, pytest.mark.skipif(sys.platform != "darwin", reason="Vision is macOS-only")]


def test_vision_reads_a_turkish_settings_screen() -> None:
    engine = VisionEngine()
    if not engine.available():
        pytest.skip("pyobjc Vision not installed")
    p = connect("fake:settings_about")
    p.open_app("Ayarlar")
    path = Path(p.send("screen.capture")["path"])
    got = engine.recognize(path.read_bytes())
    truth = [b for b in p.screen() if b["text"] and b["y"] > 100]
    found = 0
    for t in truth:
        hit = next((g for g in got if match(t["text"], g["text"]) is not None), None)
        if hit is None:
            continue
        found += 1
        assert abs(hit["y"] - t["y"]) < 40  # coordinates land on the same row (bottom-left flip done)
    assert found >= len(truth) - 1, [g["text"] for g in got]
    assert all(g["source"] == "pixels" for g in got)
