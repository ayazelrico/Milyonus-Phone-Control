"""OCR engines behind one interface (A1.11, ADR-0013).

Engines turn a PNG into protocol boxes with `source: "pixels"`. Concrete engines arrive in P2:
`vision` (macOS), `rapidocr` (Linux/Windows/server). Until one is available, `get_engine()`
raises Unsupported instead of returning nothing — an empty list would read as "the screen is
blank", which is a lie.
"""

from collections.abc import Callable, Sequence
from typing import Any, Protocol

from mphone_protocol import Unsupported

BoxDict = dict[str, Any]


class OcrEngine(Protocol):
    name: str

    def available(self) -> bool: ...

    def recognize(self, png: bytes, langs: Sequence[str] = ("tr", "en")) -> list[BoxDict]: ...


_FACTORIES: dict[str, Callable[[], OcrEngine]] = {}
_PREFERENCE = ("vision", "rapidocr")


def register(name: str, factory: Callable[[], OcrEngine]) -> None:
    _FACTORIES[name] = factory


def box(text: str, confidence: float, left: float, top: float, width: float, height: float) -> BoxDict:
    """A pixel-OCR box from a top-left rectangle; x, y become the tap-ready centre."""
    return {
        "text": text,
        "confidence": round(float(confidence), 3),
        "source": "pixels",
        "x": round(left + width / 2),
        "y": round(top + height / 2),
        "w": round(width),
        "h": round(height),
    }


def get_engine(name: str = "auto") -> OcrEngine:
    names = list(_PREFERENCE) if name == "auto" else [name]
    for candidate in names:
        factory = _FACTORIES.get(candidate)
        if factory is None:
            continue
        engine = factory()
        if engine.available():
            return engine
    raise Unsupported(
        f"no OCR engine available (wanted {name!r}, registered {sorted(_FACTORIES) or 'none'})",
        user_action="macOS'ta pyobjc Vision, diğer sistemlerde "
        "`uv pip install rapidocr-onnxruntime` gerekir.",
    )
