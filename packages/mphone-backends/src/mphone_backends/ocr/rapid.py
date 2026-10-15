"""RapidOCR (ONNX PaddleOCR) for Linux, Windows and servers: `pip install mphone-backends[rapidocr]`.

Images never leave the machine (KVKK); see ADR-0013.
"""

from collections.abc import Sequence
from typing import Any

from mphone_core.ocr import box


class RapidEngine:
    name = "rapidocr"

    def __init__(self) -> None:
        self._engine: Any = None

    def available(self) -> bool:
        try:
            import rapidocr_onnxruntime  # noqa: F401  # pyright: ignore[reportMissingImports, reportUnusedImport]
        except ImportError:
            return False
        return True

    def recognize(self, png: bytes, langs: Sequence[str] = ("tr", "en")) -> list[dict[str, Any]]:
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR  # pyright: ignore[reportMissingImports]

            self._engine = RapidOCR()
        result, _ = self._engine(png)
        boxes: list[dict[str, Any]] = []
        for quad, text, confidence in result or []:
            xs = [p[0] for p in quad]
            ys = [p[1] for p in quad]
            boxes.append(
                box(str(text), float(confidence), min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
            )
        boxes.sort(key=lambda b: (b["y"], b["x"]))
        return boxes
