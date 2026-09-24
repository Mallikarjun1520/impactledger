"""OCR provider interface (rulebook §12, ADR-005).

OCR extracts fields from an uploaded document; it never decides truth. The
default provider is a no-op that returns an empty extraction so the manual
review workflow (rulebook §12 fallback) is always available.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OcrRequest:
    filename: str
    content_type: str
    data: bytes


@dataclass(frozen=True)
class OcrExtraction:
    text: str
    fields: dict[str, str]
    confidence: float                # 0..1; 0 for the noop provider


class OcrProvider(Protocol):
    def extract(self, request: OcrRequest) -> OcrExtraction: ...


class NoopOcrProvider:
    def extract(self, request: OcrRequest) -> OcrExtraction:
        return OcrExtraction(text="", fields={}, confidence=0.0)


def build_ocr_provider() -> OcrProvider:
    from app.core.config import settings
    # Additional providers can be added here without touching call sites.
    if settings.ocr_provider == "noop":
        return NoopOcrProvider()
    raise RuntimeError(f"Unknown OCR provider {settings.ocr_provider!r}")


__all__ = [
    "OcrRequest",
    "OcrExtraction",
    "OcrProvider",
    "NoopOcrProvider",
    "build_ocr_provider",
]
