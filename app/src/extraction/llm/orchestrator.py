"""Çok-ajanlı çıkarım orkestrasyonu — T0 -> A1‖A2 -> J.

İlgili: ./agents.py (roller), ./extractor.py (LLMExtractor),
        ../reconcile.py (çıktı oraya beslenir), ../../../eval/predictors.py,
        ../silver/consensus.py (mekanik kapı LLM'den ÖNCE deseni)

## Akış

    T0  terminoloji yönlendirici   deterministik, LLM YOK
    A1  sayısal alan ajanı         yalnız ÖNERİR
    A2  bağlamsal alan ajanı       yalnız ÖNERİR
    K   kanıt kapısı               deterministik, LLM'den ÖNCE
    J   hakem                      yalnız REDDEDER

## Güvenlik değişmezi

Ajanlar değer öneremez-yazamaz; hakem değer yazamaz, yalnız reddeder;
reddedilen alan bu modülden hiç çıkmaz ve `reconcile()` orada kural değerini
kullanır. Bunun sonucu: **orkestrasyonun en kötü hâli kural-only'dir.**

Bu, keyfi bir tercih değil ölçümün dayattığı bir kısıt. `docs/rapor/ablasyon.md`
hibrit kolun kuraldan daha kötü olduğunu gösterdi (mikro-F1 0,612 -> 0,575,
halüsinasyon 0,102 -> 0,163). LLM'in yazma yetkisi olduğu sürece bu regresyon
tekrarlanabilir; yetki alınınca yapısal olarak tekrarlanamaz.

## Terim müdahalesi — üç kol, tek anahtar çifti

Ö1 deneyi (`docs/rapor/o1-terim-deneyi.md`) iki mentör kaynağının çelişkisini
ölçümle kapatır ve üç kolun tamamı bu sınıfın iki anahtarıyla kurulur:

    temel           terim_karti=False, sadelestirme=False   müdahale yok
    sadeleştirme    terim_karti=False, sadelestirme=True    metinde DEĞİŞTİR (D2)
    sözlük kartı    terim_karti=True,  sadelestirme=False   kartı ENJEKTE et

İkisi aynı anda açılabilir ama açılmamalıdır: o zaman ölçüm iki değişkenli
olur ve hangi müdahalenin etkidiği söylenemez.

## Sadeleştirme kolunda metin kimliği — sessiz tuzak

Sadeleştirme AÇIKSA ajanlar, kanıt kapısı ve hakem AYNI (değiştirilmiş) metni
görmek zorundadır. Ajanın değiştirilmiş metinden aldığı alıntı özgün metinde
birebir GEÇMEZ; kanıt kapısı özgün metne bakarsa kolun tüm önerilerini düşürür
ve kol sessizce kural-only'ye dönüşür — tam olarak `extractor.py`'nin baştan
yazılma sebebi olan hata sınıfı.

Bunun bir BEDELİ vardır ve raporda yazılıdır: bu kolda `source_span`
değiştirilmiş metne aittir, yani alan bazlı kaynak vurgulama (CLAUDE.md §18-1)
özgün belgeye götürmez. Kart kolunda böyle bir bedel yoktur.

## Hakem çökerse ne olur — SESSİZ DEĞİL

Hakem çağrısı başarısız olursa tüm LLM önerileri düşer (fail-closed) ve sonuç
kural-only olur. Bu doğru davranıştır ama TEHLİKELİ bir yan etkisi var:
ablasyon tablosunda "orkestra" satırı sessizce "kural" satırına dönüşürdü —
`extractor.py`'nin baştan yazılma sebebi tam olarak buydu. Bu yüzden hata
`OrkestrasyonRaporu.hakem_hata`'ya yazılır, loglanır ve katı modda exception
yükseltilir.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any, Optional

from ...domain.terminology import simplify_text
from ...schemas import ExtractedField
from .agents import (
    HAKEM_SEMASI,
    HAKEM_SYSTEM,
    ROLLER,
    AgentRole,
    ajan_kur,
    hakem_user_prompt,
)
from .extractor import LLMClient, LLMExtractionError, _env_flag
from .parse import parse_llm_json

logger = logging.getLogger(__name__)


@dataclass
class OrkestrasyonRaporu:
    """Tek belgelik akışın sayımları — ölçüm ve hata ayıklama için."""

    rol_onerisi: dict[str, int] = dc_field(default_factory=dict)
    rol_hatasi: dict[str, str] = dc_field(default_factory=dict)
    kanit_kapisi_red: int = 0
    kalem_kapisi_red: int = 0
    hakem_red: int = 0
    hakem_hata: Optional[str] = None
    gecen: int = 0
    sadelestirme_degisim: int = 0
    sadelestirme_bozucu: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {"rol_onerisi": dict(self.rol_onerisi),
                "rol_hatasi": dict(self.rol_hatasi),
                "kanit_kapisi_red": self.kanit_kapisi_red,
                "kalem_kapisi_red": self.kalem_kapisi_red,
                "hakem_red": self.hakem_red,
                "hakem_hata": self.hakem_hata,
                "gecen": self.gecen,
                "sadelestirme_degisim": self.sadelestirme_degisim,
                "sadelestirme_bozucu": self.sadelestirme_bozucu}


def _yeni_sayaclar() -> dict[str, int]:
    return {"belge": 0, "oneri": 0, "kanit_kapisi_red": 0, "kalem_kapisi_red": 0,
            "hakem_red": 0, "hakem_hata": 0, "gecen": 0,
            "sadelestirme_degisim": 0, "sadelestirme_bozucu": 0}


def _tek_deger(degerler: list[Any]) -> Any:
    """Hepsi aynıysa o değer; değilse sıralı liste. Boşsa `None`.

    Künyeye tekil bir sayı yazmak, ajanlar farklı ayarlarla koşarken YALAN
    olurdu. Böyle bir durum bugün yok ama künyenin doğruluğu buna
    bağlanmamalı.
    """
    tekil = set(degerler)
    if not tekil:
        return None
    return degerler[0] if len(tekil) == 1 else sorted(tekil)


#: Ücret alanları ve onlarla KARIŞAN komşu kalemler.
#:
#: Neden deterministik kapı, hakem prompt'u değil — ÖLÇÜLDÜ: hakem beş kontrol
#: vakasının dördünü doğru bildi ama tam bu vakayı kaçırdı ("Taşıt Rehin Tesis
#: Ücreti 350,92 TL" alıntısını `tahsis_ucreti` önerisi için KABUL etti).
#:
#: Aynı karışma daha önce ücret çapraz denetiminde de ölçülmüştü ve orada
#: `crosscheck_fees.py::_BASKA_KALEM_RE` ile çözülmüştü. Sistematik ve bilinen
#: bir hata için LLM'e güvenmek yerine mekanik kapı konur; hakem prompt'unu bu
#: vakaya göre yamalamak, ölçüm kümesine aşırı uydurma olurdu.
_UCRET_ALANLARI = frozenset({"tahsis_ucreti", "masraf_durumu"})

_BASKA_KALEM_RE = re.compile(
    r"rehin|ekspertiz|ipotek|sigorta|noter|de[ğg]erleme|fek|muvafakat|"
    r"yenileme|üyelik|uyelik|kasa|kiral(?:ama|ik)", re.IGNORECASE)

#: Alanın KENDİ etiketi — alıntıda varsa başka kalem geçse bile karışma yok
#: ("Tahsis ücreti alınmaz; rehin ücreti ayrıca tahsil edilir" meşrudur).
_KENDI_ETIKETI = {
    "tahsis_ucreti": re.compile(r"tahsis|dosya\s*masraf", re.IGNORECASE),
    "masraf_durumu": re.compile(r"masraf|ücret|ucret|komisyon", re.IGNORECASE),
}


class LLMOrchestrator:
    """`LLMExtractor` ile aynı arayüz: `.available` + `.extract(text, missing)`.

    Bu uyumluluk kasıtlı — `reconcile()` ve `eval/predictors.py` hiç
    değişmeden orkestrasyonu kullanabilsin diye.
    """

    def __init__(self, client: Optional[LLMClient] = None, *,
                 strict: Optional[bool] = None,
                 judge: bool = True,
                 terim_karti: bool = True,
                 sadelestirme: bool = False,
                 kanit_kapisi: bool = True,
                 roller: tuple[AgentRole, ...] = ROLLER):
        self.client = client
        self.strict = _env_flag("LLM_STRICT") if strict is None else bool(strict)
        self.judge = judge
        self.terim_karti = terim_karti
        # Ö1 sadeleştirme kolu. Varsayılan KAPALI: ölçülmek için var, teslim
        # edilen yol olmak için değil (bkz. modül başlığı).
        self.sadelestirme = sadelestirme
        self.kanit_kapisi = kanit_kapisi
        self.roller = roller
        self.ajanlar = {
            r.ad: ajan_kur(client, r, strict=False, terim_karti=terim_karti)
            for r in roller}
        self.stats = _yeni_sayaclar()
        self.last_report: Optional[OrkestrasyonRaporu] = None

    # ------------------------------------------------------------------ #
    @property
    def available(self) -> bool:
        return self.client is not None

    @property
    def structured_mode(self) -> Optional[str]:
        return getattr(self.client, "structured_mode", None)

    def reset_stats(self) -> None:
        self.stats = _yeni_sayaclar()
        for a in self.ajanlar.values():
            a.reset_stats()

    def summary(self) -> dict[str, Any]:
        """Rapor satırı — `LLMExtractor.summary()` ile AYNI sözleşme.

        Bu metot eksikti ve ölçüm koşusu 30 dakika sonunda, tam rapor
        yazılırken `AttributeError` ile çöktü: sayılar hesaplanmıştı ama
        diske hiç yazılmadı. Arayüz uyumluluğu `.available`/`.extract` ile
        bitmiyor — `eval/predictors.py::llm_summary` bunu da çağırıyor.
        """
        # Ajanların LLM çağrı sayaçları ÜST DÜZEYE toplanır. Testte yakalandı:
        # `LLMExtractor.summary()` bu anahtarları taşıyor ve rapor katmanı
        # onları okuyor; orkestrasyon kolunda eksik kalsalardı "kaç çağrı,
        # kaç ayrıştırma hatası" sorusu sessizce cevapsız kalırdı.
        toplam = {k: 0 for k in ("calls", "ok", "parse_error", "http_error",
                                 "schema_violation", "repairs")}
        for a in self.ajanlar.values():
            for k in toplam:
                toplam[k] += a.stats.get(k, 0)

        return {
            "available": self.available,
            "strict": self.strict,
            "structured_mode": self.structured_mode,
            "client": type(self.client).__name__ if self.client else None,
            # Ajanların çıktı bütçesi — hepsi aynı `LLMExtractor` varsayılanını
            # kullanır, farklıysa tekil değer yerine liste yazılır ki künye
            # yalan söylemesin. Neden künyede: bkz. `LLMExtractor.summary()`.
            "num_predict": _tek_deger(
                [a.num_predict for a in self.ajanlar.values()]),
            **toplam,
            "orkestrasyon": True,
            "hakem": self.judge,
            "terim_karti": self.terim_karti,
            "sadelestirme": self.sadelestirme,
            "kanit_kapisi": self.kanit_kapisi,
            "roller": [r.ad for r in self.roller],
            **self.stats,
            "ajan_sayaclari": {ad: dict(a.stats)
                               for ad, a in self.ajanlar.items()},
        }

    # ------------------------------------------------------------------ #
    def extract(self, text: str,
                missing: Optional[list[str]] = None) -> list[ExtractedField]:
        rapor = OrkestrasyonRaporu()
        self.last_report = rapor
        if not self.available:
            return []
        self.stats["belge"] += 1

        # Bu noktadan SONRA `text` değil `metin` kullanılır. Sadeleştirme
        # kolunda ajan, kanıt kapısı ve hakem aynı metni görmek zorundadır;
        # aksi halde kanıt kapısı tüm önerileri düşürür ve kol sessizce
        # kural-only'ye döner (bkz. modül başlığı).
        metin = self._sadelestir(text, rapor)

        oneriler = self._rolleri_kostur(metin, missing, rapor)
        rapor.rol_onerisi = {r: len([f for f in oneriler if f[0] == r])
                             for r in self.ajanlar}
        alanlar = [f for _, f in oneriler]
        self.stats["oneri"] += len(alanlar)

        if self.kanit_kapisi:
            alanlar = self._kanit_kapisi(metin, alanlar, rapor)
            alanlar = self._kalem_kapisi(alanlar, rapor)

        if self.judge and alanlar:
            alanlar = self._hakem(metin, alanlar, rapor)

        rapor.gecen = len(alanlar)
        self.stats["gecen"] += len(alanlar)
        return alanlar

    # ------------------------------------------------------------------ #
    def _sadelestir(self, text: str, rapor: OrkestrasyonRaporu) -> str:
        """Ö1 D2 kolu: terimi yerinde bırakmak yerine metinde DEĞİŞTİR.

        Kapalıyken metni AYNEN döndürür — kol dışında hiçbir davranış değişmez.
        Açıkken kaç değişiklik yapıldığı ve bunların kaçının sözlüğün kendi
        verisiyle anlam bozucu olduğu rapora yazılır; deneyin ölçtüğü sayı bu.
        """
        if not self.sadelestirme:
            return text
        sonuc = simplify_text(text or "")
        rapor.sadelestirme_degisim = len(sonuc.replacements)
        rapor.sadelestirme_bozucu = len(sonuc.bozucu)
        self.stats["sadelestirme_degisim"] += rapor.sadelestirme_degisim
        self.stats["sadelestirme_bozucu"] += rapor.sadelestirme_bozucu
        if sonuc.bozucu:
            logger.debug("sadelestirme: %d degisim, %d anlam bozucu",
                         rapor.sadelestirme_degisim, rapor.sadelestirme_bozucu)
        return sonuc.text

    # ------------------------------------------------------------------ #
    def _rolleri_kostur(self, text: str, missing: Optional[list[str]],
                        rapor: OrkestrasyonRaporu,
                        ) -> list[tuple[str, ExtractedField]]:
        """Her rolü kendi alan alt kümesiyle koştur.

        Bir rolün çökmesi diğerini düşürmez: hata rapora yazılır ve o rolün
        alanları boş kalır (kural değeri devreye girer).
        """
        cikti: list[tuple[str, ExtractedField]] = []
        for ad, ajan in self.ajanlar.items():
            istenen = list(ajan.fields)
            if missing is not None:
                istenen = [f for f in istenen if f in set(missing)]
                if not istenen:
                    continue
            sonuc = ajan.call(text, istenen)
            if not sonuc.ok:
                rapor.rol_hatasi[ad] = sonuc.error or "bilinmeyen"
                logger.warning("orkestrasyon: rol %s basarisiz: %s",
                               ad, sonuc.error)
                if self.strict:
                    raise LLMExtractionError(
                        f"orkestrasyon rolu {ad!r} basarisiz: {sonuc.error}")
                continue
            cikti.extend((ad, f) for f in sonuc.fields if f.is_present)
        return cikti

    # ------------------------------------------------------------------ #
    def _kanit_kapisi(self, text: str, alanlar: list[ExtractedField],
                      rapor: OrkestrasyonRaporu) -> list[ExtractedField]:
        """Kanıtı metinde BİREBİR bulunmayan öneriyi LLM'e sormadan düşür.

        `consensus.py`'deki `evidence_is_verbatim` ile aynı ilke: mekanik
        kapılar LLM oylarından ÖNCE çalışır, çünkü onlar modelin beyanına
        bakmaz. Ölçülen halüsinasyon oranı (hibrit kolda 0,163) esasen
        kanıtsız değerlerden geliyor.

        `span_start`, `_locate()` alıntıyı metinde bulduğunda dolar; None ise
        alıntı ya hiç verilmemiş ya da metinde geçmiyordur.
        """
        gecen: list[ExtractedField] = []
        for f in alanlar:
            if f.span_start is None:
                rapor.kanit_kapisi_red += 1
                self.stats["kanit_kapisi_red"] += 1
                logger.debug("kanit kapisi: %s dusuruldu (alinti metinde yok)",
                             f.field_name)
                continue
            gecen.append(f)
        return gecen

    # ------------------------------------------------------------------ #
    def _kalem_kapisi(self, alanlar: list[ExtractedField],
                      rapor: OrkestrasyonRaporu) -> list[ExtractedField]:
        """Ücret alanında KOMŞU KALEM karışmasını düşür.

        Ölçüldü — hakem bu vakayı kaçırıyor: "Taşıt Rehin Tesis Ücreti 350,92
        TL" alıntısı `tahsis_ucreti` önerisi için kabul edilmişti. Aynı karışma
        `crosscheck_fees.py`'de de ölçülmüş ve orada mekanik kapıyla
        çözülmüştü.

        Kapı DAR: alıntı alanın kendi etiketini de taşıyorsa düşürülmez —
        "Tahsis ücreti alınmaz; rehin ücreti ayrıca tahsil edilir" meşrudur.
        """
        gecen: list[ExtractedField] = []
        for f in alanlar:
            span = f.source_span or ""
            if (f.field_name in _UCRET_ALANLARI
                    and _BASKA_KALEM_RE.search(span)
                    and not _KENDI_ETIKETI[f.field_name].search(span)):
                rapor.kalem_kapisi_red += 1
                self.stats["kalem_kapisi_red"] += 1
                logger.debug("kalem kapisi: %s dusuruldu (komsu kalem: %r)",
                             f.field_name, span[:60])
                continue
            gecen.append(f)
        return gecen

    # ------------------------------------------------------------------ #
    def _hakem(self, text: str, alanlar: list[ExtractedField],
               rapor: OrkestrasyonRaporu) -> list[ExtractedField]:
        """Hakem yalnız REDDEDER. Çökerse fail-closed ve GÜRÜLTÜLÜ."""
        oneriler = [{"alan": f.field_name,
                     "deger": f.canonical_value,
                     "source_span": f.source_span} for f in alanlar]
        try:
            kararlar = self._hakem_cagir(text, oneriler)
        except Exception as exc:
            msg = f"{type(exc).__name__}: {exc}"
            rapor.hakem_hata = msg
            self.stats["hakem_hata"] += 1
            # Fail-closed: hakem denetleyemediyse hiçbir LLM önerisi geçmez.
            # Sessiz olsaydı ablasyonda "orkestra" satırı "kural" satırına
            # dönüşür ve tablo yalan söylerdi.
            logger.error("orkestrasyon: hakem basarisiz (%s) -> TUM oneriler "
                         "dusuruldu, sonuc kural-only", msg)
            if self.strict:
                raise LLMExtractionError(f"hakem basarisiz: {msg}") from exc
            rapor.hakem_red += len(alanlar)
            self.stats["hakem_red"] += len(alanlar)
            return []

        reddedilen = {ad for ad, kabul in kararlar.items() if not kabul}
        gecen = [f for f in alanlar if f.field_name not in reddedilen]
        dusen = len(alanlar) - len(gecen)
        rapor.hakem_red += dusen
        self.stats["hakem_red"] += dusen
        return gecen

    def _hakem_cagir(self, text: str, oneriler: list[dict]) -> dict[str, bool]:
        """alan -> kabul. Karar verilmeyen alan KABUL sayılır.

        Neden kabul: hakemin yetkisi reddetmektir. Hakkında hiç karar
        üretmediği bir alanı reddetmek, ona sessizce yazma yetkisi vermek
        olurdu — üstelik model bir alanı atlayarak onu düşürebilirdi.
        """
        gen = getattr(self.client, "generate", None)
        user = hakem_user_prompt(text, oneriler)
        if callable(gen):
            resp = gen(HAKEM_SYSTEM, user, HAKEM_SEMASI)
            obj, err = parse_llm_json(getattr(resp, "text", None))
        else:
            ham = self.client.generate_json(HAKEM_SYSTEM, user, HAKEM_SEMASI)
            obj, err = (ham, None) if isinstance(ham, dict) else (None, "dict degil")
        if obj is None:
            raise ValueError(f"hakem ciktisi ayristirilamadi: {err}")

        kararlar: dict[str, bool] = {}
        for k in (obj.get("kararlar") or []):
            if isinstance(k, dict) and isinstance(k.get("alan"), str):
                kararlar[k["alan"]] = bool(k.get("kabul", True))
        return kararlar


# --------------------------------------------------------------------------- #

def default_orchestrator(strict: Optional[bool] = None, **kw) -> LLMOrchestrator:
    """Ortama göre orkestratör (`LLM_BACKEND`). Kurulamazsa istemcisiz döner.

    `extractor.default_extractor()` ile aynı gerekçe zinciri: katı modda hata
    yükselir, hoşgörülü modda gerekçeli log basılıp offline'a düşülür.
    """
    from .extractor import default_extractor
    taban = default_extractor(strict=strict)
    return LLMOrchestrator(taban.client, strict=strict, **kw)


def rapor_ozeti(orc: LLMOrchestrator) -> str:
    """Ablasyon raporuna girecek tek satırlık özet."""
    s = orc.stats
    return (f"belge={s['belge']} oneri={s['oneri']} "
            f"kanit_kapisi_red={s['kanit_kapisi_red']} "
            f"kalem_kapisi_red={s['kalem_kapisi_red']} "
            f"hakem_red={s['hakem_red']} hakem_hata={s['hakem_hata']} "
            f"gecen={s['gecen']} "
            f"sadelestirme_degisim={s['sadelestirme_degisim']} "
            f"sadelestirme_bozucu={s['sadelestirme_bozucu']}")


__all__ = ["LLMOrchestrator", "OrkestrasyonRaporu", "default_orchestrator",
           "rapor_ozeti"]
