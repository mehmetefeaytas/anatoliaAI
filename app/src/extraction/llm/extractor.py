"""LLM çıkarıcı arayüzü + offline fallback + vLLM/Ollama yolu.

İlgili: ../../../decisions/demo-onceden-doldurulmus-db.md (LLM kritik yolda olmamalı)
        CLAUDE.md §2, §7 (vLLM birincil, Ollama yedek, quantize)

Tasarım: LLM OPSİYONELdir. Model yoksa NullLLMExtractor devreye girer ve hiçbir
alan üretmez (pipeline yalnız kurallarla çalışır). Bu, on-prem/offline testi ve
demo sağlamlığını garanti eder.
"""

from __future__ import annotations

import json
from typing import Optional, Protocol

from ...schemas import ExtractedField, Extractor
from .schema import FEWSHOT, SYSTEM_PROMPT, guided_json_schema


class LLMClient(Protocol):
    """Asgari LLM istemci arayüzü (vLLM, Ollama vb. buna uyar)."""

    def generate_json(self, system: str, user: str, schema: dict) -> dict: ...


class LLMExtractor:
    """Kuralların kaçırdığı alanları guided_json ile doldurur.

    client=None ise offline moddur: extract() boş liste döndürür.
    """

    def __init__(self, client: Optional[LLMClient] = None):
        self.client = client

    @property
    def available(self) -> bool:
        return self.client is not None

    def _build_user_prompt(self, text: str, missing: list[str]) -> str:
        examples = "\n".join(
            f"Metin: {ex['text']}\nJSON: {json.dumps(ex['json'], ensure_ascii=False)}"
            for ex in FEWSHOT
        )
        return (
            f"{examples}\n\n"
            f"Sadece şu alanlara odaklan (kurallar diğerlerini buldu): {missing}\n"
            f"Metin: {text}\nJSON:"
        )

    def extract(self, text: str, missing: Optional[list[str]] = None) -> list[ExtractedField]:
        """missing: kuralların bulamadığı alan adları. None ise tüm şema denenir."""
        if not self.available:
            return []
        missing = missing or []
        user = self._build_user_prompt(text, missing)
        try:
            raw = self.client.generate_json(SYSTEM_PROMPT, user, guided_json_schema())
        except Exception:
            # LLM hatası pipeline'ı durdurmaz (CLAUDE.md: hata→logla→devam)
            return []
        return self._parse(raw)

    @staticmethod
    def _parse(raw: dict) -> list[ExtractedField]:
        out: list[ExtractedField] = []
        for name, obj in (raw or {}).items():
            if not obj:
                continue
            val = obj.get("value")
            if val is None:
                continue  # halüsinasyon yasağı: null alan eklenmez
            out.append(ExtractedField(
                field_name=name,
                raw_value=obj.get("source_span"),
                canonical_value=val,
                confidence=float(obj.get("confidence", 0.5)),
                source_span=obj.get("source_span"),
                extractor=Extractor.LLM,
            ))
        return out


class NullLLMExtractor(LLMExtractor):
    """Açıkça offline çıkarıcı (model yok)."""

    def __init__(self):
        super().__init__(client=None)


def default_extractor() -> LLMExtractor:
    """Ortama göre çıkarıcı seç.

    LLM_BACKEND env değişkeni 'vllm'/'ollama' ise ilgili istemci kurulmaya çalışılır;
    kurulamazsa (offline/model yok) NullLLMExtractor'a düşülür.
    """
    import os

    backend = os.environ.get("LLM_BACKEND", "").lower()
    if not backend:
        return NullLLMExtractor()
    try:
        if backend == "ollama":
            from .clients import OllamaClient
            return LLMExtractor(OllamaClient())
        if backend == "vllm":
            from .clients import VLLMClient
            return LLMExtractor(VLLMClient())
    except Exception:
        pass
    return NullLLMExtractor()
