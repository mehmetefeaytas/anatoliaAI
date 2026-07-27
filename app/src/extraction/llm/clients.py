"""Somut LLM istemcileri — vLLM (OpenAI-uyumlu) ve Ollama. Açık kaynak, on-prem.

Bu istemciler yalnız ilgili servis ayaktayken kullanılır; import/çağrı hatası
default_extractor() tarafından yakalanıp NullLLMExtractor'a düşülür.
Hiçbir ücretli API kullanılmaz — sadece localhost servisleri.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Optional


def _post_json(url: str, payload: dict, timeout: float = 60.0) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class VLLMClient:
    """vLLM'in OpenAI-uyumlu /v1/chat/completions ucu + guided_json.

    Varsayılan: http://localhost:8001  (docker-compose'ta vllm servisi host'a
    8001'den yayınlanır; 8000 API'nin KENDİ portudur — eski varsayılan 8000
    olduğu için host'ta uvicorn + Docker'da vllm senaryosu kendi kendine
    istek atıyordu.)

    Model: Qwen3-8B (Apache-2.0, birincil). Trendyol-LLM-8B-T1 yalnızca
    docs/model-license-audit.md'deki taban model denetiminden geçerse.
    """

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or os.environ.get("VLLM_URL",
                         "http://localhost:8001")).rstrip("/")
        self.model = model or os.environ.get("VLLM_MODEL", "Qwen/Qwen3-8B")

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "guided_json": schema,  # vLLM kısıtlı decoding
        }
        resp = _post_json(f"{self.base_url}/v1/chat/completions", payload)
        content = resp["choices"][0]["message"]["content"]
        return json.loads(content)


class OllamaClient:
    """Ollama /api/chat + format=json (demo yedeği, CPU/GPU offline).

    Varsayılan: http://localhost:11434
    """

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or os.environ.get("OLLAMA_URL",
                         "http://localhost:11434")).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "format": schema,   # Ollama yapılandırılmış çıktı
            "stream": False,
            "options": {"temperature": 0},
        }
        resp = _post_json(f"{self.base_url}/api/chat", payload)
        return json.loads(resp["message"]["content"])
