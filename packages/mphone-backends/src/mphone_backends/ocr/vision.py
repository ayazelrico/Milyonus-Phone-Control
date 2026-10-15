# pyright: reportAttributeAccessIssue=false
# pyobjc builds Foundation/Vision attributes at runtime; the type checker cannot see them.
"""Apple Vision OCR (macOS). Accurate mode, Turkish first (ADR-0013).

Vision returns normalised bounding boxes with the origin at the BOTTOM-left; protocol boxes use
pixels from the TOP-left. The flip happens here and nowhere else.
"""

import sys
from collections.abc import Sequence
from typing import Any

from mphone_core.ocr import box

from . import LANG_CODES, png_size


class VisionEngine:
    name = "vision"

    def available(self) -> bool:
        if sys.platform != "darwin":
            return False
        try:
            import Vision  # noqa: F401  # pyright: ignore[reportMissingImports, reportUnusedImport]
        except ImportError:
            return False
        return True

    def recognize(self, png: bytes, langs: Sequence[str] = ("tr", "en")) -> list[dict[str, Any]]:
        import Foundation  # pyright: ignore[reportMissingImports]
        import Vision  # pyright: ignore[reportMissingImports]

        width, height = png_size(png)
        data = Foundation.NSData.dataWithBytes_length_(png, len(png))
        handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(data, None)
        request = Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        supported, _ = request.supportedRecognitionLanguagesAndReturnError_(None)
        wanted = [LANG_CODES.get(code, code) for code in langs]
        request.setRecognitionLanguages_([c for c in wanted if c in supported] or ["en-US"])
        request.setUsesLanguageCorrection_(True)
        ok, error = handler.performRequests_error_([request], None)
        if not ok:
            raise RuntimeError(f"Vision OCR failed: {error}")
        boxes: list[dict[str, Any]] = []
        for observation in request.results() or []:
            candidates = observation.topCandidates_(1)
            if not candidates:
                continue
            best = candidates[0]
            rect = observation.boundingBox()
            left = rect.origin.x * width
            top = (1.0 - rect.origin.y - rect.size.height) * height
            boxes.append(
                box(
                    str(best.string()),
                    float(best.confidence()),
                    left,
                    top,
                    rect.size.width * width,
                    rect.size.height * height,
                )
            )
        boxes.sort(key=lambda b: (b["y"], b["x"]))
        return boxes
