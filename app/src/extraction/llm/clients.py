"""Somut LLM istemcileri — vLLM (OpenAI-uyumlu) ve Ollama. Açık kaynak, on-prem.

İlgili: CLAUDE.md §2 (Colab = runner, teslim = on-prem), §7 (vLLM birincil,
        Ollama yedek), §19 (LLM çıktısı her zaman şema ile), §20 (ücretli API yok)

Hiçbir ücretli API kullanılmaz — yalnızca localhost servisleri, saf `urllib`.

## Yetenek pazarlığı (capability negotiation) — bu dosyanın asıl işi

Yapılandırılmış çıktı (structured output) parametresinin adı vLLM'de üç kez
değişti ve hangisinin geçerli olduğu sürüme göre değişiyor. Eski kod tek bir
adı (`guided_json`) sabit kodluyordu; sunucu onu tanımazsa 400 döner, üst
katman hatayı yutar, sonuç **"LLM hiç alan bulamadı"** olarak görünürdü —
gerçekte hiç çalışmamışken.

Çözüm sürüm TAHMİN ETMEK değil, ÖLÇMEKtir: kurulumda dört mod sırayla
1-token'lık gerçek bir istekle denenir, ilk çalışan `self.structured_mode`'a
yazılır ve süreç boyunca yeniden denenmez.

    1. `response_format={"type":"json_schema", ...,"strict":true}`
       OpenAI standardı. En dayanıklı: vLLM, SGLang, llama.cpp server, LM Studio
       ve TGI hepsi bunu tanır.
    2. `structured_outputs={"json": <schema>}`   — vLLM'in güncel yerel adı.
    3. `guided_json=<schema>`                    — eski ad, hâlâ kabul ediliyor.
    4. `prompt_only`                             — şema prompt'a metin olarak
       gömülür, çıktı `parse.py` ile sökülür. Kısıt YOK; son çare.

`self.structured_mode` dışarıdan okunabilir; eval raporuna ve smoke
notebook'una hangi modun çalıştığı basılır (hangi kanıtla konuştuğumuz belli
olsun diye).

## Neden `transport` enjekte edilebilir

Testler ağ İSTEMEZ. `transport` bir `(url, payload, timeout) -> dict`
çağrılabiliridir; varsayılanı urllib'dir, testlerde sahte bir fonksiyon
verilir. Böylece pazarlık mantığı, logprob eşlemesi ve hata yolları GPU'suz
ve internetsiz koşulabilir.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# Denenme sırası — soldan sağa. Bkz. modül başlığı.
STRUCTURED_MODES = ("json_schema", "structured_outputs", "guided_json", "prompt_only")

Transport = Callable[[str, dict, float], dict]


class LLMError(Exception):
    """LLM katmanının taban hatası."""


class LLMTransportError(LLMError):
    """Sunucuya ULAŞILAMADI (bağlantı reddi, DNS, timeout).

    `LLMHTTPError`'dan ayrı tutulur: HTTP hatası "bu parametreyi bilmiyorum"
    demektir (sıradaki modu dene), taşıma hatası "servis ayakta değil"
    demektir (denemeye devam etmenin anlamı yok, hemen bildir).
    """


class LLMHTTPError(LLMError):
    """Sunucu ayakta ama isteği reddetti (4xx/5xx)."""

    def __init__(self, status: int, body: str, url: str = ""):
        super().__init__(f"HTTP {status} @ {url}: {body[:400]}")
        self.status = status
        self.body = body
        self.url = url


@dataclass
class LLMResponse:
    """Tek bir LLM çağrısının ham sonucu.

    `logprobs`: [{"token": str, "logprob": float}, ...]. Boş liste = sunucu
    logprob vermedi (Ollama, ya da devre dışı bırakılmış vLLM).
    """

    text: str
    mode: str
    logprobs: list[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


def _urllib_transport(url: str, payload: dict, timeout: float) -> dict:
    """Varsayılan taşıma: saf stdlib POST. Hataları LLMError'a çevirir."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:          # sunucu cevap verdi, reddetti
        try:
            body = exc.read().decode("utf-8", "replace")
        except Exception:                          # pragma: no cover - nadir
            body = ""
        raise LLMHTTPError(exc.code, body, url) from exc
    except urllib.error.URLError as exc:           # bağlantı kurulamadı
        raise LLMTransportError(f"{url} ulasilamadi: {exc.reason}") from exc
    except json.JSONDecodeError as exc:            # JSON olmayan gövde
        raise LLMTransportError(f"{url} JSON olmayan yanit dondu: {exc}") from exc
    except OSError as exc:                         # timeout vb.
        raise LLMTransportError(f"{url} baglanti hatasi: {exc}") from exc


def _schema_instruction(schema: dict) -> str:
    """`prompt_only` modunda şemayı prompt'a gömen ek yönerge."""
    return (
        "\n\nÇıktın SADECE aşağıdaki JSON Schema'ya uyan tek bir JSON nesnesi "
        "olmalıdır. Şema dışında hiçbir anahtar üretme, açıklama yazma, "
        "markdown kod çiti kullanma.\n"
        f"JSON Schema:\n{json.dumps(schema, ensure_ascii=False)}"
    )


class VLLMClient:
    """vLLM'in OpenAI-uyumlu `/v1/chat/completions` ucu + yetenek pazarlığı.

    Varsayılan: http://localhost:8001  (docker-compose'ta vllm servisi host'a
    8001'den yayınlanır; 8000 API'nin KENDİ portudur — eski varsayılan 8000
    olduğu için host'ta uvicorn + Docker'da vllm senaryosunda API kendi kendine
    istek atıyordu.)

    Model: Qwen3 ailesi (Apache-2.0). Trendyol-LLM-8B-T1 yalnızca
    docs/model-license-audit.md'deki taban model denetiminden geçerse.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        transport: Optional[Transport] = None,
        timeout: float = 120.0,
        structured_mode: Optional[str] = None,
        max_tokens: int = 1536,
        temperature: float = 0.0,
        enable_thinking: bool = False,
        request_logprobs: bool = True,
    ):
        self.base_url = (base_url or os.environ.get(
            "VLLM_URL", "http://localhost:8001")).rstrip("/")
        self.model = model or os.environ.get("VLLM_MODEL", "Qwen/Qwen3-8B")
        self.transport: Transport = transport or _urllib_transport
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        # Kısıtlı decoding ile "düşünme" modu çakışır: model <think> bloğunu
        # gramerin dışında üretmeye çalışır. Varsayılan olarak KAPALI.
        self.enable_thinking = enable_thinking
        self.request_logprobs = request_logprobs

        # Pazarlık sonucu. Elle verilirse pazarlık atlanır (env: VLLM_STRUCTURED_MODE).
        self.structured_mode: Optional[str] = (
            structured_mode or os.environ.get("VLLM_STRUCTURED_MODE") or None)
        if self.structured_mode and self.structured_mode not in STRUCTURED_MODES:
            raise ValueError(
                f"bilinmeyen structured_mode: {self.structured_mode!r} "
                f"(gecerli: {STRUCTURED_MODES})")
        # Pazarlıkta hangi mod neden elendi — rapora/loga düşer.
        self.negotiation_log: list[tuple[str, str]] = []

    # ------------------------------------------------------------------ #
    # İstek kurulumu
    # ------------------------------------------------------------------ #
    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/v1/chat/completions"

    def build_payload(self, system: str, user: str, schema: dict, mode: str,
                      max_tokens: Optional[int] = None,
                      logprobs: Optional[bool] = None) -> dict:
        """Seçilen moda göre istek gövdesini kurar."""
        if mode not in STRUCTURED_MODES:
            raise ValueError(f"bilinmeyen mod: {mode!r}")
        if mode == "prompt_only":
            system = system + _schema_instruction(schema)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }

        if mode == "json_schema":
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "kampanya_cikarimi",
                    "schema": schema,
                    "strict": True,
                },
            }
        elif mode == "structured_outputs":
            payload["structured_outputs"] = {"json": schema}
        elif mode == "guided_json":
            payload["guided_json"] = schema

        # Alan bazlı güven skoru logprob'lardan üretilir (confidence.py).
        want_logprobs = self.request_logprobs if logprobs is None else logprobs
        if want_logprobs:
            payload["logprobs"] = True
            payload["top_logprobs"] = 1

        if not self.enable_thinking:
            payload["chat_template_kwargs"] = {"enable_thinking": False}

        return payload

    # ------------------------------------------------------------------ #
    # Pazarlık
    # ------------------------------------------------------------------ #
    def negotiate(self, schema: dict, force: bool = False) -> str:
        """Çalışan yapılandırılmış-çıktı modunu ÖLÇEREK bulur ve cache'ler.

        Her mod 1 token'lık gerçek bir istekle denenir (ucuz ama gerçek).
        HTTP hatası = "bu parametreyi bilmiyorum" -> sıradaki mod.
        Taşıma hatası = "servis ayakta değil" -> hemen yükselt, tüm modları
        boşuna deneme.

        Raises:
            LLMTransportError: sunucuya ulaşılamıyor.
            LLMHTTPError: sunucu ayakta ama hiçbir mod kabul edilmedi.
        """
        if self.structured_mode and not force:
            return self.structured_mode

        self.negotiation_log = []
        last_http: Optional[LLMHTTPError] = None
        for mode in STRUCTURED_MODES:
            payload = self.build_payload(
                system="ping", user="{}", schema=schema, mode=mode,
                max_tokens=1, logprobs=False)
            try:
                self.transport(self.endpoint, payload, self.timeout)
            except LLMHTTPError as exc:
                self.negotiation_log.append((mode, f"HTTP {exc.status}"))
                last_http = exc
                continue
            except LLMTransportError:
                self.negotiation_log.append((mode, "servise ulasilamadi"))
                raise
            self.negotiation_log.append((mode, "OK"))
            self.structured_mode = mode
            return mode

        raise LLMHTTPError(
            last_http.status if last_http else 0,
            "hicbir yapilandirilmis-cikti modu kabul edilmedi: "
            + "; ".join(f"{m}={r}" for m, r in self.negotiation_log),
            self.endpoint,
        )

    # ------------------------------------------------------------------ #
    # Çağrı
    # ------------------------------------------------------------------ #
    def generate(self, system: str, user: str, schema: dict) -> LLMResponse:
        """Tek çağrı; ham metin + logprob'ları döndürür (ayrıştırma YAPMAZ).

        Ayrıştırma bilerek burada değil: hangi ham metnin geldiği hata
        ayıklama için üst katmanda loglanmalı (bkz. extractor.py).
        """
        mode = self.negotiate(schema)
        payload = self.build_payload(system, user, schema, mode)
        raw = self.transport(self.endpoint, payload, self.timeout)
        try:
            choice = raw["choices"][0]
            text = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"beklenmeyen yanit bicimi: {exc}; "
                           f"anahtarlar={list(raw) if isinstance(raw, dict) else raw}"
                           ) from exc
        return LLMResponse(text=text or "", mode=mode,
                           logprobs=_extract_logprobs(choice), raw=raw)

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        """Geriye uyumlu kısayol: çağır + ayrıştır (hata olursa yükselt)."""
        from .parse import parse_llm_json

        resp = self.generate(system, user, schema)
        obj, err = parse_llm_json(resp.text)
        if obj is None:
            raise LLMError(f"cikti ayristirilamadi ({err}); ham={resp.text[:300]!r}")
        return obj


def _extract_logprobs(choice: dict) -> list[dict]:
    """OpenAI biçimi `choices[i].logprobs.content` listesini sadeleştirir.

    Beklenen biçim: [{"token": "...", "logprob": -0.01, "top_logprobs": [...]}]
    Sunucu logprob vermezse boş liste döner (hata değil — Ollama hiç vermez).
    """
    lp = (choice or {}).get("logprobs")
    if not isinstance(lp, dict):
        return []
    content = lp.get("content")
    if not isinstance(content, list):
        return []
    out: list[dict] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        token = item.get("token")
        logprob = item.get("logprob")
        if token is None or logprob is None:
            continue
        try:
            out.append({"token": str(token), "logprob": float(logprob)})
        except (TypeError, ValueError):
            continue
    return out


class OllamaClient:
    """Ollama `/api/chat` + `format=<schema>` — demo yedeği (CPU/GPU, offline).

    Varsayılan: http://localhost:11434

    `keep_alive`: modelin GPU/RAM'de tutulma süresi. Varsayılan 5 dakikadır;
    4 dakikalık sunum sırasında model bellekten düşerse bir sonraki soru
    yeniden yükleme (10-30 sn) bekler. Demo için "30m" verilir.

    `num_ctx`: bağlam penceresi. Ollama varsayılanı 2048'dir ve altı few-shot
    örneği + uzun kampanya metni bunu SESSİZCE taşırır (baştan kırpar, yani
    sistem yönergesi kaybolur). Bu yüzden açıkça set edilir.

    Ollama logprob DÖNDÜRMEZ; güven skoru modelin kendi bildirdiği değerden
    alınır ve `confidence_source="self_reported"` olarak işaretlenir.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        transport: Optional[Transport] = None,
        timeout: float = 180.0,
        keep_alive: Optional[str] = None,
        num_ctx: Optional[int] = None,
        temperature: float = 0.0,
    ):
        self.base_url = (base_url or os.environ.get(
            "OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
        self.transport: Transport = transport or _urllib_transport
        self.timeout = timeout
        self.keep_alive = keep_alive or os.environ.get("OLLAMA_KEEP_ALIVE", "30m")
        self.num_ctx = int(num_ctx or os.environ.get("OLLAMA_NUM_CTX", 8192))
        self.temperature = temperature
        # Ollama tek moda sahiptir; pazarlık gerekmez ama arayüz aynı olsun.
        self.structured_mode = "ollama_format"
        self.negotiation_log: list[tuple[str, str]] = [("ollama_format", "OK")]

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/api/chat"

    def build_payload(self, system: str, user: str, schema: dict) -> dict:
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "format": schema,          # Ollama yapılandırılmış çıktı
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {"temperature": self.temperature, "num_ctx": self.num_ctx},
        }

    def negotiate(self, schema: dict, force: bool = False) -> str:
        return self.structured_mode

    def generate(self, system: str, user: str, schema: dict) -> LLMResponse:
        raw = self.transport(self.endpoint, self.build_payload(system, user, schema),
                             self.timeout)
        try:
            text = raw["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMError(f"beklenmeyen Ollama yaniti: {exc}") from exc
        # logprobs=[] -> güven modelin kendi bildirdiğinden alınır.
        return LLMResponse(text=text or "", mode=self.structured_mode,
                           logprobs=[], raw=raw)

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        from .parse import parse_llm_json

        resp = self.generate(system, user, schema)
        obj, err = parse_llm_json(resp.text)
        if obj is None:
            raise LLMError(f"cikti ayristirilamadi ({err}); ham={resp.text[:300]!r}")
        return obj
