"""LLM assistant interface (rulebook §12, Rule 02, ADR-005).

The interface deliberately omits an ``approve`` method. LLM outputs are always
advisory candidates that a human confirms; the domain layer rejects any
attempt to short-circuit invariants.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExtractionRequest:
    ocr_text: str
    user_intent: str | None = None


@dataclass(frozen=True)
class CandidateField:
    key: str
    value: str
    confidence: float                # 0..1


@dataclass(frozen=True)
class ExtractionResult:
    candidates: list[CandidateField]
    explanation: str
    provider: str


class LlmProvider(Protocol):
    def extract_candidates(self, request: ExtractionRequest) -> ExtractionResult: ...
    def summarize(self, text: str) -> str: ...
    def explain(self, question: str, context: str) -> str: ...


class NoopLlmProvider:
    def extract_candidates(self, request: ExtractionRequest) -> ExtractionResult:
        return ExtractionResult(candidates=[], explanation="", provider="noop")

    def summarize(self, text: str) -> str:
        return text[:280]

    def explain(self, question: str, context: str) -> str:
        return (
            "LLM assist is disabled. The manual structured workflow (rulebook "
            "§12 fallback) remains available."
        )


def build_llm_provider() -> LlmProvider:
    from app.core.config import settings
    if settings.llm_provider == "noop":
        return NoopLlmProvider()
    raise RuntimeError(f"Unknown LLM provider {settings.llm_provider!r}")


__all__ = [
    "ExtractionRequest",
    "CandidateField",
    "ExtractionResult",
    "LlmProvider",
    "NoopLlmProvider",
    "build_llm_provider",
]
