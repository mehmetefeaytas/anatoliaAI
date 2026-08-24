"""LLM çıkarıcı — sessiz hata yutmanın sonu.

İlgili: ../../../decisions/demo-onceden-doldurulmus-db.md (LLM kritik yolda olmamalı)
        CLAUDE.md §2, §7 (vLLM birincil, Ollama yedek), §21 (halüsinasyon yasağı)

## Neden bu dosya baştan yazıldı

Eski `extract()` şöyleydi:

    try:
        raw = self.client.generate_json(...)
    except Exception:
        return []

Bu tek satır, birbirinden tamamen farklı üç durumu aynı çıktıya indirgiyordu:

- LLM servisi hiç ayakta değil,
- servis ayakta ama şema parametresini reddediyor (400),
- servis çalışıyor, cevap veriyor ama JSON'u bozuk.

Üçünde de sonuç "LLM hiçbir alan bulamadı" idi. Ablasyon tablosu bu yüzden
`hibrit = kural-only` satırını **hata olmadan** basabiliyordu; yani jüriye
gösterilecek en önemli artefakt sessizce yalan söyleyebiliyordu.

Yeni tasarımın üç dayanağı:

1. **`LLMCallResult`** — her çağrı; hata metni, gecikme, ham çıktı, logprob'lar
   ve onarım sayısıyla birlikte döner. Hata bir DEĞERDİR, yok sayılan bir
   olay değil.
2. **`self.stats`** — `calls / ok / parse_error / http_error / schema_violation`
   sayaçları. "LLM çalıştı mı" sorusunun ölçülebilir cevabı.
3. **`LLM_STRICT=1`** — hata yutulmaz, exception yükselir. Eval ve ablasyon bu
   modda koşulur; böylece sahte bir "hibrit=kural-only" satırı basmak
   **imkânsız** olur. Üretim/demo yolu varsayılan (hoşgörülü) modda kalır:
   LLM kritik yolda değildir.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from dataclasses import field as dc_field
from pathlib import Path
from typing import Any, Callable, Optional, Protocol, Sequence, runtime_checkable

from ...schemas import ExtractedField, Extractor
from . import confidence as conf_mod
from .parse import parse_llm_json
from .schema import EXTRACTION_FIELDS, FEWSHOT, SYSTEM_PROMPT, guided_json_schema

logger = logging.getLogger(__name__)

# Ham çıktının loga/onarım prompt'una kaç karakteri girsin.
_RAW_PREVIEW = 400

# ÇIKARIM YOLUNUN ÇIKTI TOKEN BÜTÇESİ — özet yolununkinden AYRI, çünkü ölçüm
# ikisinin farklı sayılara ihtiyaç duyduğunu gösterdi.
#
# İstemcinin kendi varsayılanı (`OLLAMA_NUM_PREDICT`, 512) ÖZET işi için
# konmuştu ve orada doğru: özet şeması tek bir sınırsız dizgedir, gramer
# sonsuza kadar üretmeye izin verir ve kaçan üretim ölçülmüş bir arızaydı.
# Çıkarım şeması 12 tipli nesnedir; gramerin kendisi sınırlar, tavanın işi
# kaçağı kesmek değil çıktıyı SIĞDIRMAKTIR.
#
# ÖLÇÜLDÜ (2026-08-14, `qwen2.5:7b-instruct`, gerçek çıkarım yolu — few-shot
# prompt + `format` şeması dâhil — gold.v2'nin 48 belgesinin TAMAMI, bütçe
# bilerek 4096'ya açılarak `eval_count` okundu; 48/48 çağrı `done_reason=stop`,
# yani hiçbiri tavana çarpmadı ve sayılar gerçek ihtiyacı gösteriyor):
#
#     ortanca 390 · en çok 955 token
#     512'yi aşan: 12/48   ·   1024'ü aşan: 0/48
#
# Yani 512 altında her dört belgeden biri JSON'u kapatamadan kesiliyordu;
# ablasyonun `num_predict=2048` ile elle koşulmak zorunda kalmasının sebebi
# buydu. 1536 seçildi: ölçülen en yüksek ihtiyacın ~1,6 katı, hiçbir belgenin
# yaklaşmadığı 1024 çizgisinin üstünde ve vLLM kolunun zaten kullandığı sayı
# (`VLLMClient.max_tokens`) — yani iki kol aynı bütçede buluşuyor. Emniyet
# supabı olarak da iş görür: kaçan bir üretim 180 sn'lik zaman aşımına değil
# bu tavana çarpar.
CIKARIM_NUM_PREDICT = 1536

# MAKİNE-OKUR SAĞLIK GÜNLÜĞÜ — her LLM çağrısı bir JSONL satırı.
#
# Neden var: "384/384 temiz LLM çağrısı" iddiası iki jüri turu boyunca yalnız
# bir rapor tablosu satırıydı. `self.stats` sayaçları koşum bitince bellekle
# birlikte kayboluyordu; iddiayı denetlemek isteyen biri koşumu yeniden
# üretmek zorundaydı. Sayaç ÖZETTİR, günlük KANITTIR: hangi model, hangi
# alanlar, kaç ms, şema geçti mi, geçmediyse hangi sebeple.
SAGLIK_LOG_VARSAYILAN = "eval/reports/llm-sagligi.jsonl"

# `LLM_SAGLIK_LOG` bu değerlerden birine eşitse günlük KAPALIDIR.
_LOG_KAPALI = {"", "0", "off", "false", "no", "kapali"}

# YANIT ÖNBELLEĞİ (`LLM_ONBELLEK=<dizin>`) — varsayılan KAPALI.
#
# Neden var: ölçüm koşumu belge başına ~40 s sürüyor ve 134 belgelik gold
# ~90 dakika demek. Bu süre içinde süreç ölürse (yerel makinede bellek
# baskısı altında ÖLÇÜLDÜ: iki koşum işletim sistemi tarafından düşürüldü)
# hesaplanmış her çağrı çöpe gider ve koşum sıfırdan başlar. Önbellek
# koşumu YENİDEN BAŞLATILABİLİR kılar: ikinci deneme, ilk denemenin
# ürettiği yanıtları HTTP'ye hiç dokunmadan okur.
#
# Sıcaklık 0 olduğu için aynı istem aynı yanıtı verir; önbellek bu
# determinizmi diske yazmaktan başka bir şey yapmaz. Yine de bir çağrının
# önbellekten geldiği sağlık günlüğüne AÇIKÇA yazılır (`onbellek: true`) ve
# ayrı bir `cache_hit` sayacına yazılır; künye ayrıca
# `gercek_cagri = calls - cache_hit` yayımlar.
#
# `calls` sayacının anlamı DEĞİŞTİRİLMEDİ: o baştan beri "kaç çıkarım isteği
# geldi"yi sayıyor (onarım denemeleri ayrıca `repairs`e girer). Önbellek
# isabeti de bir çıkarım isteğidir, dolayısıyla `calls`a girer. Değişen şey,
# künyenin artık "kaç tanesi GERÇEKTEN modele gitti" sorusunu da
# cevaplaması. Bu ayrım olmadan `calls: 384, ok: 384` satırı 384 gerçek
# çağrı gibi okunabilirdi — kapatmaya çalıştığımız denetlenemezlik yeni bir
# kılıkta geri gelirdi.
_ONBELLEK_SURUM = "v1"


class LLMExtractionError(RuntimeError):
    """Katı (strict) modda LLM çağrısı başarısız olduğunda yükseltilir."""


@runtime_checkable
class LLMClient(Protocol):
    """Asgari LLM istemci arayüzü (vLLM, Ollama vb. buna uyar)."""

    def generate_json(self, system: str, user: str, schema: dict) -> dict: ...


@dataclass
class LLMCallResult:
    """Tek bir LLM çağrısının TAM sonucu — hata dahil.

    `error is None` ise çağrı başarılıdır. `fields` boş olabilir: model
    metinde gerçekten hiçbir alan bulamamış olabilir; bu bir hata DEĞİLDİR ve
    `error` ile karıştırılmamalıdır.
    """

    fields: list[ExtractedField] = dc_field(default_factory=list)
    error: Optional[str] = None
    latency_ms: float = 0.0
    raw_text: Optional[str] = None
    logprobs: list[dict] = dc_field(default_factory=list)
    retries: int = 0
    structured_mode: Optional[str] = None
    kanit_reddi: int = 0

    @property
    def ok(self) -> bool:
        return self.error is None


def _new_stats() -> dict[str, int]:
    return {"calls": 0, "ok": 0, "parse_error": 0, "http_error": 0,
            "schema_violation": 0, "repairs": 0, "kanit_reddi": 0,
            "cache_hit": 0}


class LLMExtractor:
    """Kuralların kaçırdığı alanları kısıtlı-decoding ile doldurur.

    client=None ise offline moddur: extract() boş liste döndürür (hata değil).
    """

    def __init__(self, client: Optional[LLMClient] = None,
                 strict: Optional[bool] = None, max_repairs: int = 1, *,
                 system_builder: Optional[Callable[[str], str]] = None,
                 fields: Optional[Sequence[str]] = None,
                 role: str = "genel",
                 num_predict: Optional[int] = None,
                 require_evidence: Optional[bool] = None,
                 saglik_log: Optional[str] = None,
                 onbellek: Optional[str] = None,
                 alan_basina: Optional[bool] = None):
        """
        num_predict: ÇIKARIM çağrılarının çıktı token bütçesi. Gerekçe ve
            ölçüm `CIKARIM_NUM_PREDICT` yanında. İstemci nesnesi burada
            DEĞİŞTİRİLMEZ; her çağrıda bütçeli bir KOPYA kullanılır, çünkü
            aynı istemciyi özet ve sohbet yolları da paylaşıyor. `None` ise
            `LLM_EXTRACT_NUM_PREDICT` ortam değişkeni, o da yoksa ölçülmüş
            varsayılan geçerlidir.
        system_builder: belge metnini alıp sistem prompt'u üretir. Neden
            sabit bir dize değil: terim kartları BELGEYE bağlıdır (bkz.
            domain/terminology.py) — hangi terimin enjekte edileceği ancak
            metin görüldüğünde bilinir. Verilmezse bugünkü sabit
            `SYSTEM_PROMPT` kullanılır, yani mevcut davranış değişmez.
        fields: bu ajanın sorumlu olduğu alan alt kümesi. Orkestrasyonda rol
            ayrımını taşır; verilmezse 12 alanın tamamı.
        role: yalnız log/rapor etiketi.
        """
        self.client = client
        # LLM_STRICT=1 -> hatalar yutulmaz. Açıkça verilen argüman env'i ezer.
        self.strict = (_env_flag("LLM_STRICT") if strict is None else bool(strict))
        self.max_repairs = max_repairs
        self.system_builder = system_builder
        self.fields: tuple[str, ...] = tuple(
            f for f in (fields or EXTRACTION_FIELDS) if f in EXTRACTION_FIELDS)
        if not self.fields:
            self.fields = tuple(EXTRACTION_FIELDS)
        self.role = role
        self.num_predict = int(
            num_predict if num_predict is not None
            else os.environ.get("LLM_EXTRACT_NUM_PREDICT", CIKARIM_NUM_PREDICT))
        # KANIT KAPISI — alıntısı metinde birebir bulunmayan değeri düşür.
        # Varsayılan `LLM_KANIT_ZORUNLU` ortam değişkeninden okunur; gerekçesi
        # ve ölçümü `docs/rapor/llm-uretim-devreye-alma.md`.
        self.require_evidence = (_env_flag("LLM_KANIT_ZORUNLU")
                                 if require_evidence is None
                                 else bool(require_evidence))
        self.saglik_log = _saglik_log_yolu(saglik_log)
        self.onbellek = _onbellek_dizini(onbellek)
        # SORGU GRANÜLARİTESİ. Varsayılan çoklu-alan (tek çağrıda tüm eksikler).
        # `True` ise eksik alan başına AYRI çağrı yapılır. Gerekçe:
        # `docs/rapor/llm-uretim-devreye-alma.md §10` — çoklu-alan kolunda
        # ölçülen hata "değer bulamama" değil, bulunan gerçek alıntıyı YANLIŞ
        # ALAN etiketine yakıştırmaktı (TP hiç artmadı, yalnız FP geldi).
        # Modele tek seferde 8-9 alan verildiğinde alan seçimi modelin işi
        # olur; tek alan verildiğinde o seçim yapısal olarak ortadan kalkar.
        # Bu bir HİPOTEZdir ve ölçülmek için eklendi, varsayılan olmak için
        # değil — maliyeti belge başına ~9 kat çağrıdır.
        self.alan_basina = (_env_flag("LLM_ALAN_BASINA")
                            if alan_basina is None else bool(alan_basina))
        self.stats = _new_stats()
        self.last_result: Optional[LLMCallResult] = None
        # Sağlık günlüğüne yazılacak istek künyesi (`call()` doldurur).
        self._son_istek: dict[str, Any] = {}
        self._onbellekten = False
        # (istemci, bütçe) -> bütçeli kopya. Anahtar ikisini birden taşır:
        # `client` veya `num_predict` sonradan değişirse kopya bayatlamasın.
        self._butceli: Optional[tuple[Any, int, Any]] = None

    def _system_for(self, text: str) -> str:
        """Bu belge için sistem prompt'u."""
        if self.system_builder is None:
            return SYSTEM_PROMPT
        return self.system_builder(text) or SYSTEM_PROMPT

    @property
    def available(self) -> bool:
        return self.client is not None

    @property
    def structured_mode(self) -> Optional[str]:
        """İstemcinin pazarlıkla bulduğu yapılandırılmış-çıktı modu (rapor için)."""
        return getattr(self.client, "structured_mode", None)

    def reset_stats(self) -> None:
        self.stats = _new_stats()

    # ------------------------------------------------------------------ #
    # Prompt
    # ------------------------------------------------------------------ #
    def _build_user_prompt(self, text: str, missing: list[str]) -> str:
        examples = "\n\n".join(
            f"# zor vaka: {ex['category']}\n"
            f"Metin: {ex['text']}\n"
            f"JSON: {json.dumps(ex['json'], ensure_ascii=False)}"
            for ex in FEWSHOT
        )
        wanted = missing or list(self.fields)
        return (
            "Aşağıdaki örneklerde KISALIK için yalnız ilgili alanlar gösterilmiştir; "
            "senin çıktında istenen alanların TAMAMI bulunmalıdır.\n\n"
            f"{examples}\n\n"
            f"Şu alanları çıkar (diğerlerini kural katmanı zaten buldu): "
            f"{json.dumps(wanted, ensure_ascii=False)}\n"
            + (
                # TEK ALAN kipi: modelin işi "hangi alan" değil "bu alan var mı".
                # Çoklu-alan kipinde model 8-9 etiket arasından seçim yapıyor ve
                # ölçüm bu seçimin hatalı olduğunu gösterdi (§10). Cümle bunu
                # açıkça daraltır; few-shot örnekleri AYNI kalır ki iki kol
                # arasındaki tek fark granülarite olsun.
                f"YALNIZ bu tek alanı değerlendir. Metinde tam olarak "
                f"'{wanted[0]}' bilgisi geçiyorsa değeri ve birebir alıntısını "
                f"ver; GEÇMİYORSA null yap. Başka hiçbir alan üretme.\n\n"
                if len(wanted) == 1 else
                "Listedeki HER alan için bir anahtar üret; bulamadığını "
                "null yap.\n\n"
            )
            + f"Metin: {text}\nJSON:"
        )

    @staticmethod
    def _repair_suffix(error: str, raw_text: Optional[str]) -> str:
        """Onarım denemesi: hatayı modele SÖYLE, körlemesine tekrar sorma."""
        preview = (raw_text or "")[:_RAW_PREVIEW]
        return (
            "\n\nÖNCEKİ YANITIN GEÇERSİZDİ.\n"
            f"Ayrıştırma hatası: {error}\n"
            f"Gönderdiğin çıktının başı: {preview!r}\n"
            "Bu kez SADECE tek bir geçerli JSON nesnesi döndür: açıklama yok, "
            "markdown kod çiti yok, <think> bloğu yok, sondaki virgül yok."
        )

    # ------------------------------------------------------------------ #
    # Çağrı
    # ------------------------------------------------------------------ #
    def call(self, text: str, missing: Optional[list[str]] = None) -> LLMCallResult:
        """LLM'i çağırır ve TAM sonucu döndürür (hata yutulmaz, döndürülür)."""
        if not self.available:
            return LLMCallResult(fields=[], error=None)

        wanted = [f for f in (missing or self.fields) if f in self.fields]
        if not wanted:
            wanted = list(self.fields)
        schema = guided_json_schema(wanted)
        user = self._build_user_prompt(text, wanted)

        started = time.perf_counter()
        self.stats["calls"] += 1
        self._son_istek = {
            "rol": self.role,
            "istenen_alanlar": list(wanted),
            "metin_uzunlugu": len(text or ""),
            "istem_uzunlugu": len(user),
        }
        kanit_reddi_once = self.stats["kanit_reddi"]
        self._onbellekten = False
        raw_text: Optional[str] = None
        logprobs: list[dict] = []
        last_error: Optional[str] = None
        retries = 0

        for attempt in range(self.max_repairs + 1):
            prompt = user if attempt == 0 else user + self._repair_suffix(
                last_error or "", raw_text)
            try:
                raw_text, logprobs, direct = self._invoke(
                    self._system_for(text), prompt, schema)
            except Exception as exc:                     # taşıma/HTTP/biçim hatası
                self.stats["http_error"] += 1
                msg = f"{type(exc).__name__}: {exc}"
                logger.error("LLM cagrisi basarisiz (%s): %s", type(exc).__name__, exc)
                return self._finish(LLMCallResult(
                    error=msg, latency_ms=_ms(started), raw_text=raw_text,
                    logprobs=logprobs, retries=retries,
                    structured_mode=self.structured_mode))

            if direct is not None:
                obj, perr = direct, None
            else:
                obj, perr = parse_llm_json(raw_text)

            if obj is None:
                last_error = perr or "bilinmeyen ayristirma hatasi"
                self.stats["parse_error"] += 1
                logger.warning("LLM cikti ayristirilamadi (deneme %d/%d): %s | ham=%r",
                               attempt + 1, self.max_repairs + 1, last_error,
                               (raw_text or "")[:_RAW_PREVIEW])
                if attempt < self.max_repairs:
                    retries += 1
                    self.stats["repairs"] += 1
                    continue
                return self._finish(LLMCallResult(
                    error=f"parse_error: {last_error}", latency_ms=_ms(started),
                    raw_text=raw_text, logprobs=logprobs, retries=retries,
                    structured_mode=self.structured_mode))

            fields, violations = self._to_fields(obj, text, logprobs)
            if violations:
                self.stats["schema_violation"] += 1
                logger.warning("LLM sema ihlali (yok sayilan anahtarlar): %s",
                               violations)
            self.stats["ok"] += 1
            return self._finish(LLMCallResult(
                fields=fields, latency_ms=_ms(started), raw_text=raw_text,
                logprobs=logprobs, retries=retries,
                structured_mode=self.structured_mode,
                kanit_reddi=self.stats["kanit_reddi"] - kanit_reddi_once))

        # Buraya düşülmez (döngü her dalda return eder) — savunma amaçlı.
        return self._finish(LLMCallResult(   # pragma: no cover
            error=last_error or "bilinmeyen hata", latency_ms=_ms(started),
            raw_text=raw_text, logprobs=logprobs, retries=retries,
            structured_mode=self.structured_mode))

    def _finish(self, result: LLMCallResult) -> LLMCallResult:
        self.last_result = result
        self._saglik_yaz(result)
        return result

    def _saglik_yaz(self, result: LLMCallResult) -> None:
        """Çağrıyı JSONL sağlık günlüğüne ekle (asla çıkarımı düşürmez).

        Günlük yazımı BEST-EFFORT'tur: disk dolu, dizin salt-okunur ya da yol
        hatalıysa çıkarım devam eder ve yalnız bir uyarı basılır. Aksi hâlde
        denetim artefaktı üretmek, denetlenen işi bozma riski doğururdu.
        """
        if self.saglik_log is None:
            return
        kayit = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            # Koşum etiketi (`LLM_KOSUM`). Tek dosyaya birden çok koşum
            # yazıldığında satırların hangi ölçüme ait olduğu ancak böyle
            # ayrılabilir; zaman damgası tek başına yetmez çünkü iki koşum
            # arasındaki sınır rapordan okunamaz.
            "kosum": os.environ.get("LLM_KOSUM") or None,
            "model": getattr(self.client, "model", None),
            "client": type(self.client).__name__ if self.client else None,
            "structured_mode": result.structured_mode,
            "num_predict": self.num_predict,
            "kanit_zorunlu": self.require_evidence,
            **self._son_istek,
            "sure_ms": round(result.latency_ms, 1),
            "sema_gecti": result.ok,
            "sebep": result.error,
            "onbellek": self._onbellekten,
            "onarim": result.retries,
            "uretilen_alan": len(result.fields),
            "kanit_reddi": result.kanit_reddi,
        }
        try:
            self.saglik_log.parent.mkdir(parents=True, exist_ok=True)
            with self.saglik_log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(kayit, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("LLM saglik gunlugu yazilamadi (%s): %s",
                           self.saglik_log, exc)

    def _invoke(self, system: str, user: str, schema: dict
                ) -> tuple[Optional[str], list[dict], Optional[dict]]:
        """İstemciyi çağırır.

        Zengin arayüz (`generate` -> LLMResponse) varsa tercih edilir: ham metin
        ve logprob'lar ancak böyle elde edilir. Yoksa eski `generate_json`
        arayüzüne düşülür (o zaman logprob ve ham metin yoktur).

        İstemci `self.client` DEĞİL, onun bütçeli kopyasıdır: çıkarım şeması
        özet şemasından geniştir ve ortak nesnenin tavanı özet için konmuştur
        (bkz. `CIKARIM_NUM_PREDICT`).
        """
        yol = self._onbellek_yolu(system, user, schema)
        if yol is not None and yol.is_file():
            try:
                kayit = json.loads(yol.read_text(encoding="utf-8"))
            except (ValueError, OSError) as exc:
                logger.warning("onbellek okunamadi (%s): %s", yol, exc)
            else:
                self.stats["cache_hit"] += 1
                self._onbellekten = True
                return (kayit.get("raw_text"), list(kayit.get("logprobs") or []),
                        None)

        istemci = self._butceli_istemci(schema)
        gen = getattr(istemci, "generate", None)
        if callable(gen):
            resp = gen(system, user, schema)
            ham = getattr(resp, "text", None)
            lp = list(getattr(resp, "logprobs", []) or [])
            dogrudan = None
        else:
            obj = istemci.generate_json(system, user, schema)  # type: ignore[union-attr]
            ham = json.dumps(obj, ensure_ascii=False) if isinstance(obj, dict) else None
            lp, dogrudan = [], obj if isinstance(obj, dict) else None
        if yol is not None and ham is not None:
            self._onbellege_yaz(yol, ham, lp)
        return ham, lp, dogrudan

    def _onbellek_yolu(self, system: str, user: str, schema: dict
                       ) -> Optional[Path]:
        """İstemin içerik-adresli önbellek yolu (önbellek kapalıysa None).

        Anahtar İSTEMİN TAMAMINI kapsar: model, sistem istemi, kullanıcı
        istemi, şema ve çıktı bütçesi. Biri değişirse anahtar değişir, yani
        bayat bir yanıt yeni bir yapılandırmaya sessizce sızamaz — önbelleğin
        tek gerçek riski budur.
        """
        if self.onbellek is None:
            return None
        h = hashlib.sha256()
        for parca in (_ONBELLEK_SURUM,
                      str(getattr(self.client, "model", "")),
                      type(self.client).__name__ if self.client else "",
                      str(self.num_predict), system, user,
                      json.dumps(schema, ensure_ascii=False, sort_keys=True)):
            h.update(parca.encode("utf-8"))
            h.update(b"\x00")
        return self.onbellek / f"{h.hexdigest()}.json"

    @staticmethod
    def _onbellege_yaz(yol: Path, raw_text: str, logprobs: list[dict]) -> None:
        """Yanıtı diske yazar (best-effort — ölçümü düşürmez)."""
        try:
            yol.parent.mkdir(parents=True, exist_ok=True)
            gecici = yol.with_suffix(".tmp")
            gecici.write_text(
                json.dumps({"raw_text": raw_text, "logprobs": logprobs},
                           ensure_ascii=False),
                encoding="utf-8")
            # Atomik yer değiştirme: yarım yazılmış bir dosya sonraki koşumda
            # "bozuk önbellek" olarak okunur ve o belge sessizce kaybedilirdi.
            gecici.replace(yol)
        except OSError as exc:
            logger.warning("onbellege yazilamadi (%s): %s", yol, exc)

    def _butceli_istemci(self, schema: dict) -> Any:
        """Çıkarım bütçesi uygulanmış istemci kopyası (bir kez kurulur).

        ## Neden kopyadan ÖNCE pazarlık

        `VLLMClient.negotiate()` çalışan yapılandırılmış-çıktı modunu ölçerek
        bulur ve sonucu `self.structured_mode`'a YAZAR. Kopya sığdır: pazarlık
        kopyada yapılırsa sonuç paylaşılan nesneye geri dönmez ve iki şey
        birden bozulur — paylaşılan istemci her çağrıda yeniden pazarlık eder
        (4 boş HTTP gidiş-dönüşü), `LLMExtractor.structured_mode` ise `None`
        raporlar, yani rapor "hangi modda koştuk" sorusunu cevaplayamaz.
        Pazarlık paylaşılan nesnede yapılıp kopya SONRA çıkarılınca cache
        kopyaya da taşınmış olur.

        Yöntemler `getattr` ile yoklanır çünkü `LLMClient` protokolü yalnız
        `generate_json` zorunlu kılar: testlerdeki sahte istemciler ve ileride
        eklenecek bir istemci `butceyle`/`negotiate` taşımayabilir. Taşımıyorsa
        bütçe SESSİZCE uygulanmaz — kabul edilebilir, çünkü tavanı olmayan bir
        istemcide kısıtlanacak bir şey de yoktur.
        """
        if self.client is None:
            return None
        pazarlik = getattr(self.client, "negotiate", None)
        if callable(pazarlik):
            pazarlik(schema)
        if (self._butceli is not None
                and self._butceli[0] is self.client
                and self._butceli[1] == self.num_predict):
            return self._butceli[2]
        butceyle = getattr(self.client, "butceyle", None)
        istemci = butceyle(self.num_predict) if callable(butceyle) else self.client
        self._butceli = (self.client, self.num_predict, istemci)
        return istemci

    # ------------------------------------------------------------------ #
    # Alan üretimi
    # ------------------------------------------------------------------ #
    def _to_fields(self, raw: dict, text: str, logprobs: list[dict]
                   ) -> tuple[list[ExtractedField], list[str]]:
        """Şema-geçerli JSON'u ExtractedField listesine çevirir.

        Logprob varsa güven ondan, yoksa modelin kendi bildirdiğinden alınır;
        hangisi olduğu `confidence_source`'a yazılır (kalibrasyon farklı
        kaynakları karıştıramasın diye).
        """
        lp_conf = conf_mod.field_confidences(logprobs, EXTRACTION_FIELDS)
        # Rol dışı alan ihlaldir: ajana yalnız kendi alanları soruldu ve
        # şema onları kısıtladı; fazlası sessizce kabul edilmemeli.
        out: list[ExtractedField] = []
        violations: list[str] = []

        for name, obj in (raw or {}).items():
            if name not in self.fields:
                violations.append(name)
                continue
            if obj is None:
                continue                      # açıkça "metinde yok" — doğru davranış
            if not isinstance(obj, dict):
                violations.append(name)
                continue
            value = obj.get("value")
            if value is None:
                continue                      # halüsinasyon yasağı: null eklenmez

            span_text = obj.get("source_span")
            span_text = span_text if isinstance(span_text, str) else None
            start, end = _locate(text, span_text)

            # KANIT KAPISI: alıntı metinde birebir bulunmuyorsa değer
            # düşürülür. `orchestrator._kanit_kapisi` ile AYNI ilke; burada
            # tek-ajanlı yolda da uygulanabilmesi için duruyor. Ölçülmüş
            # gerekçe: hibrit kolun halüsinasyonu esasen kanıtsız
            # değerlerden geliyor (`docs/rapor/ablasyon.md` §2).
            if self.require_evidence and start is None:
                self.stats["kanit_reddi"] += 1
                logger.debug("kanit kapisi: %s dusuruldu (alinti metinde yok)",
                             name)
                continue

            if name in lp_conf:
                score, source = lp_conf[name], conf_mod.SOURCE_LOGPROB
            else:
                score = conf_mod.self_reported(obj.get("confidence"))
                source = conf_mod.SOURCE_SELF_REPORTED

            out.append(ExtractedField(
                field_name=name,
                raw_value=text[start:end] if start is not None else span_text,
                canonical_value=value,
                confidence=score,
                source_span=span_text,
                extractor=Extractor.LLM,
                span_start=start,
                span_end=end,
                confidence_source=source,
            ))
        return out, violations

    # ------------------------------------------------------------------ #
    # Kamuya açık API
    # ------------------------------------------------------------------ #
    def extract(self, text: str, missing: Optional[list[str]] = None
                ) -> list[ExtractedField]:
        """Alanları çıkarır.

        Hoşgörülü modda (varsayılan) hata olursa boş liste döner — ama hata
        artık LOGLANIR ve `self.stats` / `self.last_result` üzerinden görülür.
        Katı modda (`LLM_STRICT=1`) `LLMExtractionError` yükseltilir.
        """
        if self.alan_basina:
            return self._extract_alan_basina(text, missing)
        result = self.call(text, missing)
        if result.error is not None:
            if self.strict:
                raise LLMExtractionError(
                    f"{result.error} | mode={result.structured_mode} "
                    f"| ham={(result.raw_text or '')[:_RAW_PREVIEW]!r}")
            return []
        return result.fields

    def _extract_alan_basina(self, text: str, missing: Optional[list[str]]
                             ) -> list[ExtractedField]:
        """Eksik alan başına AYRI çağrı yapar (`LLM_ALAN_BASINA=1`).

        Gerekçe `self.alan_basina` yanında. Hata davranışı çoklu-alan koluyla
        AYNI tutulur: katı modda ilk hata yükseltilir, hoşgörülü modda o alan
        atlanır ve kalan alanlar sorulmaya devam eder. İkincisi bilinçli —
        tek alanın başarısızlığı diğer sekiz alanın cevabını çöpe atmamalı.
        """
        wanted = [f for f in (missing or self.fields) if f in self.fields]
        if not wanted:
            wanted = list(self.fields)
        toplam: list[ExtractedField] = []
        for ad in wanted:
            result = self.call(text, [ad])
            if result.error is not None:
                if self.strict:
                    raise LLMExtractionError(
                        f"{result.error} | alan={ad} "
                        f"| mode={result.structured_mode} "
                        f"| ham={(result.raw_text or '')[:_RAW_PREVIEW]!r}")
                continue
            toplam.extend(result.fields)
        return toplam

    def summary(self) -> dict[str, Any]:
        """Rapor satırı: hangi modda, kaç çağrı, kaç hata, hangi bütçeyle.

        `num_predict` rapora bilerek giriyor. 2026-08-13 ablasyonu, çıkarımın
        512'lik ortak tavana takılması yüzünden `OLLAMA_NUM_PREDICT=2048` ELLE
        verilerek koşuldu ve `env.json` bunu HİÇ kaydetmedi: raporu okuyan
        biri koşumu tekrar üretemez, tabloyu hangi ayarın mümkün kıldığını
        göremezdi. Koşumun sonucunu belirleyen bir ayar künyeye yazılmalı.
        """
        return {
            "available": self.available,
            "strict": self.strict,
            "structured_mode": self.structured_mode,
            "client": type(self.client).__name__ if self.client else None,
            # Model etiketi künyeye GİRER: "hangi ağırlıkla ölçtük" sorusu
            # rapordan cevaplanabilir olmalı (bkz. `docs/rapor/ablasyon.md §6`).
            "model": getattr(self.client, "model", None),
            "num_predict": self.num_predict,
            "require_evidence": self.require_evidence,
            "saglik_log": str(self.saglik_log) if self.saglik_log else None,
            "onbellek": str(self.onbellek) if self.onbellek else None,
            # Sorgu granülaritesi künyeye GİRER: iki kolun sayıları yalnız bu
            # ayar bilinerek karşılaştırılabilir (bkz. §10 ablasyon tablosu).
            "alan_basina": self.alan_basina,
            # Modele GERÇEKTEN giden çağrı sayısı (önbellek isabetleri hariç).
            "gercek_cagri": self.stats["calls"] - self.stats["cache_hit"],
            **self.stats,
        }


class NullLLMExtractor(LLMExtractor):
    """Açıkça offline çıkarıcı (model yok). Hata üretmez; alan da üretmez."""

    def __init__(self):
        super().__init__(client=None)


# --------------------------------------------------------------------------- #
# Yardımcılar
# --------------------------------------------------------------------------- #
def _ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000.0


def _onbellek_dizini(explicit: Optional[str]) -> Optional[Path]:
    """Yanıt önbelleği dizini — ya da önbellek kapalıysa None.

    Varsayılan KAPALIdır. Gerekçe `_ONBELLEK_SURUM` yanında: önbellek bir
    ÖLÇÜM kolaylığıdır, üretim davranışı değil. Üretim koşumunda açık olması
    zararsızdır ama varsayılan yapılmadı — sessizce bayat yanıt servis eden
    bir üretim hattı, kapatmaya çalıştığımız sınıfın hatasıdır.
    """
    ham = explicit if explicit is not None else os.environ.get("LLM_ONBELLEK")
    if ham is None:
        return None
    ham = ham.strip()
    return None if ham.lower() in _LOG_KAPALI else Path(ham)


def _saglik_log_yolu(explicit: Optional[str]) -> Optional[Path]:
    """Sağlık günlüğü dosya yolu — ya da günlük kapalıysa None.

    Öncelik: açık argüman > `LLM_SAGLIK_LOG` > (yalnız gerçek bir backend
    istendiyse) varsayılan yol.

    Son basamak kasıtlı. Günlük koşulsuz açık olsaydı, sahte istemcilerle
    koşan birim testleri de aynı dosyaya satır yazardı ve artefakt "kaç gerçek
    çağrı yapıldı" sorusuna yanlış cevap verirdi — yani denetim kaydının
    kendisi kirlenirdi. `LLM_BACKEND` boşken hiç gerçek çağrı yapılmıyor
    (bkz. `default_extractor`), dolayısıyla yazılacak bir şey de yoktur.
    """
    if explicit is not None:
        ham = explicit.strip()
        return None if ham.lower() in _LOG_KAPALI else Path(ham)
    env = os.environ.get("LLM_SAGLIK_LOG")
    if env is not None:
        ham = env.strip()
        return None if ham.lower() in _LOG_KAPALI else Path(ham)
    if os.environ.get("LLM_BACKEND", "").strip():
        return Path(SAGLIK_LOG_VARSAYILAN)
    return None


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _locate(text: str, span: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    """`source_span`'i kaynak metinde bulup karakter offset'i üretir.

    Model kaynak parçasını birebir kopyalamadıysa (kendi cümlesini yazdıysa)
    offset üretilmez — yanlış yeri vurgulamaktansa hiç vurgulamamak yeğdir
    (`ExtractedField.verify_span` bunu eval'de denetler).
    """
    if not span:
        return None, None
    idx = text.find(span)
    if idx < 0:
        return None, None
    return idx, idx + len(span)


#: SSB EVREN çıkarım servisi — yarışmanın tüm takımlarına açık UZAK uç.
#: Anahtar burada TUTULMAZ (§5.10; bkz. docs/evren-servisi.md); yalnız uç
#: adresi ve model takma adı varsayılan olarak yazılıdır.
EVREN_URL_VARSAYILAN = "https://evren-llmapi.ssyz.org.tr"
EVREN_MODEL_VARSAYILAN = "llm-large"


class _KademeAtlanir(Exception):
    """Kademe kurulamadı ama bu bir HATA değil — atlanıp devam edilecek.

    `evren` kademesi anahtarsız kaldığında olur. Teslim edilen kopyada
    `EVREN_API_KEY` bulunmaz; orada zincirin yerel kademeye düşmesi BEKLENEN
    davranıştır, kurulum hatası değil.
    """


def _kademe_kur(ad: str) -> Any:
    """Tek bir kademenin istemcisini kurar (ağa çıkmaz; pazarlık tembeldir)."""
    if ad == "ollama":
        from .clients import OllamaClient
        return OllamaClient()
    if ad == "vllm":
        from .clients import VLLMClient
        return VLLMClient()
    if ad == "evren":
        from .clients import VLLMClient
        anahtar = os.environ.get("EVREN_API_KEY", "").strip()
        if not anahtar:
            raise _KademeAtlanir("EVREN_API_KEY tanimli degil")
        return VLLMClient(
            base_url=(os.environ.get("EVREN_URL", "").strip()
                      or EVREN_URL_VARSAYILAN),
            model=(os.environ.get("EVREN_MODEL", "").strip()
                   or EVREN_MODEL_VARSAYILAN),
            api_key=anahtar)
    raise ValueError(
        f"bilinmeyen LLM_BACKEND kademesi: {ad!r} (evren|vllm|ollama)")


def default_extractor(strict: Optional[bool] = None) -> LLMExtractor:
    """Ortama göre çıkarıcı seç.

    `LLM_BACKEND` virgülle ayrılmış bir KADEME LİSTESİ kabul eder:
    `evren,ollama` = "EVREN'i dene, düşerse yerel Ollama devralsın"
    (bkz. `cascade.CascadingClient`). Tek değer eski davranıştır ve zincire
    SARILMAZ — böylece mevcut raporlardaki `client` alanı ve model adı biçim
    değiştirmez.

    Kurulamazsa:
    - hoşgörülü modda GEREKÇELİ log basılır ve NullLLMExtractor'a düşülür,
    - katı modda (`LLM_STRICT=1`) exception yükselir.

    Katı mod ablasyon için kritiktir: "LLM_BACKEND=vllm verdim ama sessizce
    kural-only koştu" durumu jüriye yanlış tablo gösterir. Aynı gerekçe zincir
    için de geçerli: TÜM kademeler atlanırsa katı modda yükseltilir.

    Anahtarsız `evren` kademesi bunun istisnasıdır ve sessizce atlanır —
    zincirde başka kademe varsa koşum onunla sürer (bkz. `_KademeAtlanir`).
    """
    strict_mode = _env_flag("LLM_STRICT") if strict is None else bool(strict)
    backend = os.environ.get("LLM_BACKEND", "").strip().lower()

    if not backend:
        logger.info("LLM_BACKEND bos -> NullLLMExtractor (kural-only, kasitli offline)")
        return NullLLMExtractor()

    kademeler = [p.strip() for p in backend.split(",") if p.strip()]
    try:
        istemciler: list[Any] = []
        atlanan: list[str] = []
        for ad in kademeler:
            try:
                istemciler.append(_kademe_kur(ad))
            except _KademeAtlanir as exc:
                atlanan.append(f"{ad} ({exc})")
                logger.info("LLM kademesi atlandi: %s -> %s", ad, exc)
        if not istemciler:
            raise ValueError(
                "hicbir kademe kurulamadi; atlanan: " + ", ".join(atlanan))
        if len(istemciler) == 1:
            return LLMExtractor(istemciler[0], strict=strict_mode)
        from .cascade import CascadingClient
        logger.info("LLM zinciri kuruldu: %s",
                    " -> ".join(type(c).__name__ for c in istemciler))
        return LLMExtractor(CascadingClient(istemciler), strict=strict_mode)
    except Exception as exc:
        msg = (f"LLM_BACKEND={backend!r} istendi ama istemci kurulamadi: "
               f"{type(exc).__name__}: {exc}")
        if strict_mode:
            raise LLMExtractionError(msg) from exc
        logger.error("%s -> NullLLMExtractor'a dusuluyor (kural-only)", msg)
        return NullLLMExtractor()
