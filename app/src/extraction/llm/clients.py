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
    4. `tools=[...]` + `tool_choice`        — şema bir FONKSİYON İMZASI
       olarak geçer. Ölçüldü (24 Ağu 2026, SSB EVREN): `response_format`
       sarmalayıcısını HTTP 500 ile reddeden uç, AYNI şemayı tool calling
       ile kabul etti ve 12 alanın tamamını doğru yapıda döndürdü. Yani
       sorun şemanın kendisi değil, onu taşıyan alandı.
       Çıktı `message.tool_calls[0].function.arguments` içinde gelir,
       `content` boş kalır (bkz. `_yanit_metni`).
    5. `response_format={"type":"json_object"}`
       ŞEMA kısıtı yok ama JSON kısıtı VAR: sunucu geçerli bir JSON nesnesi
       üretmeye zorlar, alanlar prompt'tan öğrenilir. Ölçüldü (24 Ağu 2026,
       SSB EVREN `llm-large`): karmaşık şemamız `json_schema`da HTTP 500
       veriyor, `guided_json` sessizce yok sayılıyor — bu mod ikisinin de
       düştüğü yerde çalışan tek KISITLI seçenek.
    6. `prompt_only`                             — şema prompt'a metin olarak
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
import logging
import os
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Denenme sırası — soldan sağa. Bkz. modül başlığı.
STRUCTURED_MODES = ("json_schema", "structured_outputs", "guided_json",
                    "tool_calling", "json_object", "prompt_only")

Transport = Callable[[str, dict, float], dict]

#: `tool_calling` modunda şemayı taşıyan fonksiyonun adı. Sabit tutulur:
#: `tool_choice` ile birebir eşleşmek zorunda ve değişken bir ad hata
#: ayıklamayı zorlaştırırdı.
TOOL_ADI = "kampanya_cikarimi"


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


#: Soket zaman aşımının kaç katı bir DUVAR-SAATİ sınırı uygulanacağı.
#: `LLM_DEADLINE_CARPANI` ile ayarlanabilir; 0 (veya negatif) sınırı kapatır.
_DEADLINE_CARPANI_VARSAYILAN = 1.5


def _deadline(timeout: float) -> float:
    try:
        carpan = float(os.environ.get("LLM_DEADLINE_CARPANI",
                                      _DEADLINE_CARPANI_VARSAYILAN))
    except ValueError:                                 # pragma: no cover
        carpan = _DEADLINE_CARPANI_VARSAYILAN
    return timeout * carpan if carpan > 0 else 0.0


def _urllib_transport(url: str, payload: dict, timeout: float,
                      api_key: str = "") -> dict:
    """Varsayılan taşıma: saf stdlib POST + **duvar-saati sınırı**.

    ## Neden ayrı bir sınır gerekiyor — ölçülmüş donma

    `urlopen(..., timeout=t)` bir SOKET zaman aşımıdır: her `recv` çağrısı
    için ayrı ayrı işler. Sunucu bağlantıyı açık tutup veri göndermezse
    (ya da çok yavaş damlatırsa) süre **hiç dolmaz**.

    Ölçüldü (2026-08-08): `build_summaries` koşumu `OLLAMA_TIMEOUT=900`
    verilmiş olmasına rağmen Ollama'ya **açık bir TCP soketiyle 18 dakika
    uykuda** bekledi — %0 CPU, log'a tek satır yazmadan. Zaman aşımı
    tetiklenmedi çünkü tetiklenecek bir `recv` yoktu.

    Demo açısından bu, tek gerçek donma riskiydi: jüri önünde model takılırsa
    arayüz **süresiz** bekler. Bu yüzden çağrı bir arka plan iş parçacığında
    koşuyor ve `join(deadline)` ile üstten sınırlanıyor.

    İş parçacığı `daemon`: sınır dolduğunda onu öldüremeyiz (Python'da
    güvenli bir iptal yok), ama süreç sonlanırken beklemez ve çağıran
    kontrolü **geri alır**. Sızan iş parçacığı asılı soketle birlikte
    süreçle ölür.
    """
    sinir = _deadline(timeout)
    if sinir <= 0:                                     # sınır kapatılmış
        return _urllib_transport_ic(url, payload, timeout, api_key)

    kutu: dict[str, Any] = {}

    def _kos() -> None:
        try:
            kutu["sonuc"] = _urllib_transport_ic(url, payload, timeout,
                                                 api_key)
        except BaseException as exc:
            kutu["hata"] = exc

    th = threading.Thread(target=_kos, daemon=True,
                          name="llm-transport")
    th.start()
    th.join(sinir)
    if th.is_alive():
        raise LLMTransportError(
            f"{url} {sinir:.0f} sn duvar-saati sınırını aştı (soket zaman "
            f"aşımı {timeout:.0f} sn tetiklenmedi — bağlantı açık ama veri "
            f"gelmiyor). Sınır: LLM_DEADLINE_CARPANI.")
    if "hata" in kutu:
        raise kutu["hata"]
    return kutu["sonuc"]


def _urllib_transport_ic(url: str, payload: dict, timeout: float,
                         api_key: str = "") -> dict:
    """Asıl POST. Hataları LLMError'a çevirir.

    `api_key` boşsa `Authorization` başlığı HİÇ gönderilmez: yerel
    vLLM/Ollama kimlik doğrulaması istemez ve gereksiz başlık geriye
    uyumu bozar. Uzak OpenAI-uyumlu uçlar (SSB EVREN) ister.
    """
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=data, headers=headers)
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


def _yanit_metni(choice: dict) -> Optional[str]:
    """Yanıt metnini çıkarır — `tool_calling` dâhil.

    Tool calling'de model çıktıyı `tool_calls[0].function.arguments`
    içine yazar ve `content` boş kalır. Yalnız `content`e bakan bir okuyucu
    bunu "model boş cevap verdi" diye okur; üst katman da onu geçerli bir
    "özetlenecek şey yok" cevabı sayıp çıkarımı SESSİZCE kaybeder.
    """
    mesaj = (choice or {}).get("message") or {}
    icerik = mesaj.get("content")
    if icerik:
        return icerik
    cagrilar = mesaj.get("tool_calls")
    if isinstance(cagrilar, list) and cagrilar:
        islev = (cagrilar[0] or {}).get("function") or {}
        arg = islev.get("arguments")
        if isinstance(arg, str):
            return arg
    return icerik


def _kisit_uygulandi(ham: dict, mode: str = "") -> bool:
    """Prob yanıtı kısıtlı decoding'in imzasını taşıyor mu?

    Kısıtlı decoding'de ilk token `{` olmak ZORUNDADIR; kısıt yoksa model
    kendi cümlesine başlar. Ölçüldü (2026-08-24, SSB EVREN `llm-large`):
    `guided_json` gönderildiğinde sunucu HTTP 200 döndü ama kısıtı hiç
    uygulamadı — prob yanıtı `'P'` ("Pong!") oldu.

    İçerik BOŞSA ya da biçim tanınmazsa `True` döner: kararsızlık yanlış
    elemeye yol açmamalı. Çalışan bir modu elemek, sistemi gereksizce
    `prompt_only`a düşürür — yanlış eleme yanlış kabulden pahalıdır.
    """
    try:
        mesaj = ham["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        return True
    # `tool_calling`: kısıt `tool_calls` içinde gelir ve `content` boş
    # kalır. Onun varlığı kısıtın UYGULANDIĞININ kanıtıdır; aksi hâlde
    # prob bu modu eler ve daha zayıf `json_object`a düşerdik.
    if isinstance(mesaj, dict) and mesaj.get("tool_calls"):
        return True
    icerik = mesaj.get("content") if isinstance(mesaj, dict) else None
    # Prob 1 TOKEN istiyor ve o tek token tool çağrısını TAMAMLAMAYA
    # yetmez: sunucu `tool_calls`ı ayrıştıramaz, `content`e ham başlangıç
    # işaretini (`<tool_call>`) bırakır. Ölçüldü (24 Ağu, EVREN): prob
    # yanıtı tam olarak `'<tool_call>'` geldi ve `{` ile başlamadığı için
    # mod ELENDİ — oysa o işaret kısıtın uygulandığının kanıtıydı. Sonuç:
    # ablasyon yine kısıtsız `json_object` ile koşuyordu.
    if (mode == "tool_calling" and isinstance(icerik, str)
            and "tool_call" in icerik.lower()):
        return True
    if not isinstance(icerik, str):
        return True
    kirpik = icerik.strip()
    if not kirpik:
        return True
    return kirpik.startswith("{")


def bearer_transport(api_key: str) -> Transport:
    """`Authorization: Bearer` ekleyen taşıma üreteci.

    `Transport` imzası `(url, payload, timeout) -> dict` olarak SABİT:
    onlarca test sahte taşıma enjekte ediyor ve imza değişse hepsi
    kırılırdı. Anahtar bu yüzden bir closure'a kapatılır, imzaya
    eklenmez.
    """
    def _t(url: str, payload: dict, timeout: float) -> dict:
        return _urllib_transport(url, payload, timeout, api_key)

    return _t


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
        api_key: Optional[str] = None,
        kisit_probu: Optional[bool] = None,
        model_dogrula: Optional[bool] = None,
    ):
        self.base_url = (base_url or os.environ.get(
            "VLLM_URL", "http://localhost:8001")).rstrip("/")
        self.model = model or os.environ.get("VLLM_MODEL", "Qwen/Qwen3-8B")
        # Anahtar: argüman > env. Boşsa başlık hiç eklenmez (yerel uçlar).
        # AÇIKÇA enjekte edilmiş `transport` her koşulda kazanır — ağsız
        # CI'da sahte taşımayla koşan testler env'den etkilenmemeli.
        self.api_key = (api_key if api_key is not None
                        else os.environ.get("VLLM_API_KEY", "")).strip()
        if transport is not None:
            self.transport: Transport = transport
        elif self.api_key:
            self.transport = bearer_transport(self.api_key)
        else:
            self.transport = _urllib_transport
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
        # Model adı sunucunun listesinde mi? Ölçüldü (24 Ağu, EVREN):
        # bilinmeyen bir ad HTTP 200 ile KABUL ediliyor ve yanıtın `model`
        # alanı o uydurma adı geri veriyor — yani sapma yanıta bakılarak
        # anlaşılamıyor. Bir harf yanlış yazılan `VLLM_MODEL`, koşumu başka
        # bir modelle yapar ve artefakt yanlış adı raporlar.
        #
        # AÇIK `transport` bunu KAPATIR: o, "burada gerçek sunucu yok"
        # demenin kendisidir (onlarca test sahte taşımayla koşuyor).
        # Anahtarsız yerel uçta da kapalı: tuzak yalnız uzak uçta ölçüldü
        # ve yerel model adı HF yolu olabiliyor.
        if model_dogrula is not None:
            self.model_dogrula = bool(model_dogrula)
        elif transport is not None:
            self.model_dogrula = False
        else:
            ham_bayrak = os.environ.get("VLLM_MODEL_DOGRULA", "").strip().lower()
            if ham_bayrak:
                self.model_dogrula = ham_bayrak not in {"0", "false", "no", "off"}
            else:
                self.model_dogrula = bool(self.api_key)
        self._model_dogrulandi = False

        # Pazarlık probu kısıtın UYGULANDIĞINI da sınar mı? Kapatma kapısı
        # bilerek var: sunucusunun boş prob yanıtı döndürdüğünü bilen biri
        # eski davranışa dönebilsin (env: VLLM_KISIT_PROBU=0).
        self.kisit_probu = (
            kisit_probu if kisit_probu is not None
            else os.environ.get("VLLM_KISIT_PROBU", "1").strip().lower()
            not in {"0", "false", "no", "off"})

        # Pazarlıkta hangi mod neden elendi — rapora/loga düşer.
        self.negotiation_log: list[tuple[str, str]] = []

    # ------------------------------------------------------------------ #
    # Model adı doğrulaması
    # ------------------------------------------------------------------ #
    def model_listesi_al(self) -> list[str]:
        """`GET /v1/models` — sunucunun tanıdığı model adları.

        Ayrı bir metod, çünkü testler bunu değiştirerek ağa çıkmadan
        doğrulama mantığını sınayabilsin. Hata YUTULMAZ; çağıran karar
        verir (bkz. `_dogrula_model`).
        """
        istek = urllib.request.Request(
            f"{self.base_url}/v1/models",
            headers=({"Authorization": f"Bearer {self.api_key}"}
                     if self.api_key else {}))
        with urllib.request.urlopen(istek, timeout=30) as yanit:
            ham = json.loads(yanit.read().decode("utf-8"))
        veri = (ham or {}).get("data")
        if not isinstance(veri, list):
            return []
        return [d.get("id") for d in veri if isinstance(d, dict) and d.get("id")]

    def _dogrula_model(self) -> None:
        """Model sunucunun listesinde mi? Bir kez koşar.

        Liste ALINAMAZSA koşum DURMAZ: doğrulama bir güvencedir, ön koşul
        değil. Geçici bir ağ dalgalanmasının tüm ablasyonu düşürmesi, onun
        önlediği hatadan pahalı olurdu — uyarı loglanır, pazarlık sürer.
        """
        self._model_dogrulandi = True
        try:
            modeller = self.model_listesi_al()
        except Exception as exc:
            logger.warning("model listesi alinamadi (%s: %s) -> ad "
                           "dogrulanmadan devam ediliyor",
                           type(exc).__name__, exc)
            return
        if not modeller:                     # boş liste eleme yapmaz
            return
        if self.model not in modeller:
            raise LLMError(
                f"model {self.model!r} sunucunun listesinde YOK. Bu uc "
                f"bilinmeyen adlari SESSIZCE kabul edip baska bir modele "
                f"dusuruyor; koşum yanlis modelle yapilirdi. "
                f"Gecerli adlar: {', '.join(sorted(modeller))}")

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
        # `json_object` ŞEMAYI kısıtlamaz, yalnız JSON biçimini kısıtlar:
        # alan adları prompt'tan öğrenilmek zorunda, tıpkı `prompt_only`da.
        if mode in ("prompt_only", "json_object"):
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
        elif mode == "json_object":
            payload["response_format"] = {"type": "json_object"}
        elif mode == "tool_calling":
            # Şema bir fonksiyon imzası olarak geçiyor; `tool_choice` ile
            # model bu fonksiyonu çağırmaya ZORLANIYOR (yoksa serbest
            # metinle cevap verip kısıtı atlayabilir).
            payload["tools"] = [{
                "type": "function",
                "function": {
                    "name": TOOL_ADI,
                    "description": ("Belge metninden finansal alanlari "
                                    "cikarir"),
                    "parameters": schema,
                },
            }]
            payload["tool_choice"] = {
                "type": "function", "function": {"name": TOOL_ADI}}

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
        HTTP 200 ama ilk token `{` DEĞİL = "parametreyi tanıdım, kısıtı
        uygulamadım" -> sıradaki mod (bkz. `_kisit_uygulandi`).
        Taşıma hatası = "servis ayakta değil" -> hemen yükselt, tüm modları
        boşuna deneme.

        Raises:
            LLMTransportError: sunucuya ulaşılamıyor.
            LLMHTTPError: sunucu ayakta ama hiçbir mod kabul edilmedi.
        """
        if self.model_dogrula and not self._model_dogrulandi:
            self._dogrula_model()
        if self.structured_mode and not force:
            return self.structured_mode

        self.negotiation_log = []
        last_http: Optional[LLMHTTPError] = None
        for mode in STRUCTURED_MODES:
            payload = self.build_payload(
                system="ping", user="{}", schema=schema, mode=mode,
                max_tokens=1, logprobs=False)
            try:
                ham = self.transport(self.endpoint, payload, self.timeout)
            except LLMHTTPError as exc:
                self.negotiation_log.append((mode, f"HTTP {exc.status}"))
                last_http = exc
                continue
            except LLMTransportError:
                self.negotiation_log.append((mode, "servise ulasilamadi"))
                raise
            # HTTP 200 "parametreyi TANIDIM" demek; "UYGULADIM" demek
            # değil. `prompt_only` proba tabi değildir: orada kısıt zaten
            # yok, son çaredir ve elenirse hiç mod kalmaz.
            if (self.kisit_probu and mode != "prompt_only"
                    and not _kisit_uygulandi(ham, mode)):
                self.negotiation_log.append(
                    (mode, "HTTP 200 ama kisit UYGULANMADI"))
                continue
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
            text = _yanit_metni(choice)
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"beklenmeyen yanit bicimi: {exc}; "
                           f"anahtarlar={list(raw) if isinstance(raw, dict) else raw}"
                           ) from exc
        return LLMResponse(text=text or "", mode=mode,
                           logprobs=_extract_logprobs(choice), raw=raw)

    def sicaklikla(self, temperature: float) -> "VLLMClient":
        """Yalnız sıcaklığı farklı bir KOPYA döndürür (bkz. `OllamaClient`)."""
        return _sicaklik_kopyasi(self, temperature)

    def butceyle(self, token: int) -> "VLLMClient":
        """Yalnız çıktı token bütçesi farklı bir KOPYA (bkz. `OllamaClient`).

        Ollama'da alan adı `num_predict`, burada `max_tokens`. Çağıran taraf
        (`LLMExtractor`) bu farkı bilmesin diye iki sınıfta da aynı ad.
        """
        return _butce_kopyasi(self, "max_tokens", token)

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

def _birimsiz_sayi(v: str) -> bool:
    """`"-1"` / `"300"` gibi birim taşımayan süre değeri mi.

    `"30m"`, `"1h30m"`, `"-1s"` için False döner. Boş dize de False'tur:
    sessizce `"s"` eklemek `""`yi geçersiz bir süreye (`"s"`) çevirirdi.
    Boş dizeyi çağıran taraf varsayılana düşürür.
    """
    if not v:
        return False
    govde = v[1:] if v[0] in "+-" else v
    return govde.isdigit()




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
        timeout: Optional[float] = None,
        keep_alive: Optional[str] = None,
        num_ctx: Optional[int] = None,
        num_predict: Optional[int] = None,
        temperature: float = 0.0,
    ):
        self.base_url = (base_url or os.environ.get(
            "OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        # `qwen2.5:7b` DEĞİL: Ollama etiketleri birebir eşleşir, kısaltma
        # çözülmez. Ablasyonda ölçülen ve `docs/rapor/ablasyon.md §6`da künyesi
        # verilen ağırlık `qwen2.5:7b-instruct` (Q4_K_M, Apache-2.0). Eski
        # varsayılan kurulu değildi; `OLLAMA_MODEL` elle verilmeyen her koşum
        # "model not found" ile düşüyordu.
        self.model = model or os.environ.get(
            "OLLAMA_MODEL", "qwen2.5:7b-instruct")
        self.transport: Transport = transport or _urllib_transport
        # Sabit 180 sn DEĞİL. Bu sınır boştaki makinede bol, yüklü makinede
        # yetersiz: 48 belgelik bir ablasyon, aynı anda koşan bir ince ayarla
        # çakışınca `timed out` ile düştü. Demo donanımı da bizimkinden yavaş
        # olabilir ve on-prem iddiası (%20) "yavaş donanımda da koşar" demek
        # zorunda. `LLM_STRICT=1` altında zaman aşımı sessiz bir kural-only
        # düşüşü değil, gürültülü bir hata üretir — yani sınır fazla dar
        # olduğunda ölçüm kaybedilir, bozulmaz. Yine de ayarlanabilir olmalı.
        self.timeout = float(
            timeout if timeout is not None
            else os.environ.get("OLLAMA_TIMEOUT", 180.0))
        # `keep_alive` İSTEK GÖVDESİNE gider, sunucu env'ine değil — ve iki
        # bağlam aynı değeri farklı kabul ediyor. Ollama'nın kendi belgesi
        # "modeli bellekte süresiz tut" için `OLLAMA_KEEP_ALIVE=-1` diyor;
        # sunucu bunu env olarak kabul eder ama `/api/chat` gövdesindeki
        # `keep_alive` alanı Go'nun `time.ParseDuration`'ıyla çözülür ve
        # birimsiz `-1` için
        #     HTTP 400 {"error": "time: missing unit in duration \"-1\""}
        # döner. ÖLÇÜLDÜ (2026-08-19, Colab A100): `colab/02_ablasyon.py`
        # env'i `-1` yazıyordu; `kural` kolu 8 saniyede koştu, `llm`,
        # `hibrit` ve `hibrit-verify` kollarının ÜÇÜ DE 0 saniyede düştü.
        # `LLM_STRICT=1` sayesinde sessizce kural-only'ye düşmedi, gürültülü
        # patladı — ama hata alt sürecin stderr'inde kaldığı için tablo
        # "eksik kolla" üretildi.
        #
        # Belgesi `-1` öneren bir sistemin istemcisi `-1`i kabul etmek
        # zorunda. Birimsiz tam sayı Ollama CLI'ının kendi kuralıyla SANİYE
        # sayılır ve negatif değer "süresiz" anlamını korur.
        # Sondaki `or "30m"`: env TANIMLI ama BOŞ olabilir (`OLLAMA_KEEP_ALIVE=`)
        # ve `os.environ.get` o hâlde varsayılanı değil boş dizeyi döndürür.
        # Boş dize istek gövdesine girse Ollama yine 400 verirdi — aynı
        # arızanın ikinci kapısı.
        ka = str(keep_alive or os.environ.get("OLLAMA_KEEP_ALIVE", "30m")
                 ).strip() or "30m"
        self.keep_alive = f"{ka}s" if _birimsiz_sayi(ka) else ka
        self.num_ctx = int(num_ctx or os.environ.get("OLLAMA_NUM_CTX", 8192))
        # ÇIKTI TOKEN SINIRI. Ollama varsayılanı sınırsızdır ve bu ölçülmüş bir
        # arızaya yol açıyordu (2026-08-08, özet üretimi, qwen2.5:7b-instruct):
        # model geçerli bir özet üretiyor, JSON'u kapatmadan `<tool_call>`
        # yazıyor ve çöp döngüsüne giriyordu. Sonuç iki farklı hata olarak
        # görünüyordu ama kök neden tekti:
        #
        #   * döngü zaman aşımına kadar sürerse -> LLMTransportError (180 sn)
        #   * bağlam dolup çıktı kesilirse      -> LLMError "kesik yanit"
        #
        # 10 belgelik ölçümde 4'ü düşüyordu ve iki hang tek başına 360 sn
        # yiyordu. Sınır + durdurucu ile aynı belgeler 4-8 sn'de bitiyor.
        #
        # 512 ÖZET İŞİNİN sayısıdır ve orada doğrudur. ÇIKARIM İÇİN DEĞİLDİR:
        # "12 alan + span çıktısını rahat kapsıyor" diyen eski yorum ölçümle
        # yanlışlandı (2026-08-14, `qwen2.5:7b-instruct`, gerçek çıkarım yolu,
        # 48 gold belgenin tamamı): ihtiyaç ortanca 390, en çok 955 token ve
        # belgelerin 12/48'i 512'yi AŞIYOR. Yani bu varsayılan altında her
        # dört belgeden biri JSON'u kapatamadan kesiliyordu.
        #
        # Ayrım şemaların şeklinden geliyor, kolaylıktan değil:
        #   özet   -> {"ozet": <string>} — tek sınırsız dizge, gramer sonsuza
        #             kadar üretmeye izin verir; kaçan üretim ÖLÇÜLDÜ, sıkı
        #             tavan burada gerçek bir emniyet supabıdır.
        #   çıkarım-> 12 tipli nesne; gramerin kendisi sınırlıyor, tavanın işi
        #             kaçağı kesmek değil sığdırmak.
        # Bu yüzden çıkarım yolu kendi bütçesini `LLMExtractor` üzerinden
        # `butceyle()` ile alır; buradaki varsayılan özet yolunun sayısıdır.
        self.num_predict = int(num_predict if num_predict is not None
                               else os.environ.get("OLLAMA_NUM_PREDICT", 512))
        self.temperature = temperature
        # DÜŞÜNME KİPİ KAPALI (varsayılan). Qwen3 ve sonrası "thinking" model
        # ailesidir: cevaptan önce muhakeme token'ı üretir. Bu, yukarıdaki
        # `num_predict` sınırıyla birleşince sessiz bir arızaya yol açıyor —
        # bütçe muhakemeye gidiyor ve cevap HİÇ üretilmiyor.
        #
        # ÖLÇÜLDÜ (2026-08-13, `qwen3.5:9b-q4_K_M`, bu sınıfın gerçek
        # ayarlarıyla: /api/chat + format şeması + num_predict=512):
        #
        #   think verilmedi -> 29,2 sn · 512 token · içerik BOŞ
        #   think=False     ->  3,5 sn ·  63 token · içerik dolu
        #
        # Yani bayrak konmadan koşulan bir ablasyon, modeli kalitesizliğinden
        # değil YANLIŞ ÇAĞRILDIĞI için elerdi. vLLM kolunda karşılığı zaten
        # vardı (`chat_template_kwargs.enable_thinking = False`); Ollama kolu
        # eksikti.
        #
        # Düşünmeyen modelde de GÜVENLİ: `qwen2.5:7b-instruct` bayrakla ve
        # bayraksız aynı çıktıyı veriyor, hata dönmüyor (aynı ölçüm). Bu yüzden
        # model adına bakan bir koşul YAZILMADI — koşul, yeni bir model ailesi
        # geldiğinde sessizce yanlış tarafa düşerdi.
        #
        # `OLLAMA_THINK=1` ile açılabilir: muhakemenin çıkarım kalitesine
        # etkisini ÖLÇMEK isteyen biri için kapı açık kalsın, ama ölçmeden
        # açılan bir kip varsayılan olamaz.
        self.think = (os.environ.get("OLLAMA_THINK", "").strip().lower()
                      in {"1", "true", "evet"})
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
            # Gerekçe ve ölçüm `__init__` içinde, `self.think` yanında.
            "think": self.think,
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
                "num_predict": self.num_predict,
                # `<tool_call>` qwen ailesinin araç çağrısı kaçış belirtecidir.
                # Yapılandırılmış çıktı modunda bile üretiliyor ve ARDINDAN
                # model çöp üretmeye başlıyor (ölçüldü). Burada durdurmak,
                # kaçışın maliyetini sıfıra indirir; çıktının kendisi zaten
                # o noktada tamamlanmış oluyor.
                "stop": ["<tool_call>"],
            },
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

    def sicaklikla(self, temperature: float) -> "OllamaClient":
        """Yalnız sıcaklığı farklı bir KOPYA döndürür.

        ## Neden kopya, neden yerinde değiştirme değil

        Çağıran taraf (`src/summarize/ozet.py`) alfabe kapısına takılan bir
        özeti yeniden denerken sıcaklığı yükseltiyor. `self.temperature`'ı
        geçici olarak değiştirip geri koymak çok daha kısa olurdu — ve YANLIŞ
        olurdu: API'de bu istemci nesnesi sohbet, canlı çıkarım ve özet
        yollarının ORTAK nesnesidir. Özet işi sıcaklığı 0,7'ye çekerken aynı
        anda koşan bir alan çıkarımı o sıcaklıkta cevap alırdı; ölçülen bir
        yol, ölçülmemiş bir ayarla koşmuş olurdu ve iz bırakmazdı.

        Kopya sığdır: taşıma (transport) paylaşılır, yalnız ayar farklıdır.
        """
        return _sicaklik_kopyasi(self, temperature)

    def butceyle(self, token: int) -> "OllamaClient":
        """Yalnız çıktı token bütçesi farklı bir KOPYA döndürür.

        `sicaklikla` ile aynı gerekçe (bkz. yukarısı): bu nesne özet, sohbet
        ve çıkarım yollarının ORTAK nesnesidir. Çıkarım işi bütçeyi yerinde
        büyütseydi, aynı anda koşan bir özet işi ölçülmemiş bir tavanla
        koşardı ve kaçan üretime karşı konmuş emniyet supabı sessizce
        gevşemiş olurdu.
        """
        return _butce_kopyasi(self, "num_predict", token)

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        from .parse import parse_llm_json

        resp = self.generate(system, user, schema)
        obj, err = parse_llm_json(resp.text)
        if obj is None:
            raise LLMError(f"cikti ayristirilamadi ({err}); ham={resp.text[:300]!r}")
        return obj


def _sicaklik_kopyasi(istemci: Any, temperature: float) -> Any:
    """Sığ kopya + yeni sıcaklık. İki istemci sınıfı için ortak."""
    import copy

    kopya = copy.copy(istemci)
    kopya.temperature = float(temperature)
    return kopya


def _butce_kopyasi(istemci: Any, alan: str, token: int) -> Any:
    """Sığ kopya + yeni çıktı bütçesi. İki istemci sınıfı için ortak.

    `alan` sınıfa göre değişir (`num_predict` / `max_tokens`); ortak olan,
    kopya döndürülmesi ve paylaşılan nesnenin dokunulmadan kalmasıdır.
    """
    import copy

    kopya = copy.copy(istemci)
    setattr(kopya, alan, int(token))
    return kopya
