"""Kâr payı ORANI toplama — bankaların hesaplama uçlarından yapılandırılmış veri.

İlgili: CLAUDE.md §6 (zor anlama), §10 (normalizasyon), §17 (adil kıyas),
        docs/rapor/banka-siteleri-veri-kaynagi-haritasi.md §1–§2

## Neden ayrı bir hat

Şartnamenin manşet örneği tam olarak şudur:

    A Bankası | Konut finansmanı | %1,89 | 120 ay | Dosya masrafı yok

Ama **aylık kâr payı oranı HTML'de YOKTUR.** Ürün sayfalarında yalnızca
*etiket* bulunur ("Aylık Kâr Oranı"); değer istemci-taraflı hesaplama aracının
arkasındadır. Ölçüm (2026-08-03, 1684 belgelik korpus): `kar_payi_orani` alanı
yalnızca **73** belgede var ve finansman ürün sayfalarının HİÇBİRİNDE sayısal
değer yok.

Bu modül oranı kaynağından alır. İki strateji:

1. **JSON ucu** (Emlak Katılım, Albaraka) — parametreli GET; ürün × tutar × vade
   ızgarası üzerinde sorgulanır. En güvenilir ve en ucuz yol.
2. **Tarayıcı ile sürme** (Kuveyt Türk) — JSON ucu yok; oran ancak hesaplama
   aracı çalıştırıldıktan sonra DOM'a yazılır (`id="ProfitRate"`).

## Neden adaptörler KOD, ızgara CONFIG

Her bankanın ucu farklı yol, farklı parametre adı ve farklı yanıt şeması
kullanıyor; bunu "config" gibi göstermek yanıltıcı olurdu. Gerçek seam şudur:
**adaptör kodda, hangi ürün/tutar/vade sorulacağı config'de.** Yeni banka
eklemek = bir adaptör sınıfı + `RATE_ADAPTERS`'a bir satır.

## Halüsinasyon yasağı (CLAUDE.md §19)

Bir alan yanıtta yoksa `None` bırakılır; asla türetilip uydurulmaz. Yanıt
beklenen şemada değilse kayıt DÜŞÜRÜLÜR ve gerekçesi rapora yazılır.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from .collector import utc_now_iso
from .fetcher import StaticFetcher

# Toplama yöntemi (provenance)
METHOD_RATE_API = "rate-api"
METHOD_RATE_BROWSER = "rate-browser"
METHOD_RATE_CATALOG = "rate-catalog"  # sayfaya gömülü ürün/oran kataloğu
METHOD_RATE_TABLE = "rate-table"      # yayımlanmış HTML oran tablosu

# Ürün türü — bankalar arası kıyas ancak AYNI tür içinde yapılır (§17).
KIND_FINANCING = "finansman"      # murabaha: aylık kâr oranı ödenir
KIND_PROFIT_SHARE = "katilma"     # katılma hesabı: kâr payı alınır

# Varsayılan sorgu ızgarası. Küçük tutuldu: her istek 3 sn gecikmeli
# (CLAUDE.md §14) ve amaç kapsam değil KIYASLANABİLİR birkaç nokta.
DEFAULT_FINANCING_AMOUNTS = (100_000, 500_000, 1_000_000)
DEFAULT_FINANCING_TERMS = (12, 36, 60, 120)
DEFAULT_DEPOSIT_AMOUNTS = (50_000, 250_000)
DEFAULT_DEPOSIT_TERM_DAYS = (32, 92, 182, 365)


@dataclass
class RateQuote:
    """Tek bir (banka, ürün, tutar, vade) noktası için oran kaydı.

    Alanlar `null` olabilir — bankanın ucu o alanı vermiyorsa uydurulmaz.
    """

    bank_slug: str
    kind: str                     # KIND_FINANCING | KIND_PROFIT_SHARE
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    amount: Optional[float] = None
    # Tutar DİLİMİ üst sınırı (yayımlanmış tablolarda "250-100,000,000" gibi).
    amount_max: Optional[float] = None
    # Tutarın birimi. None = para birimi cinsinden. Altın/gümüş hesaplarında
    # dilim GRAM cinsindendir ("50 gr.") ve TL tutarıyla kıyaslanamaz (§17).
    amount_unit: Optional[str] = None
    term_months: Optional[int] = None
    term_days: Optional[int] = None
    currency: str = "TRY"
    # Finansman tarafı
    monthly_rate: Optional[float] = None        # aylık kâr oranı (%)
    annual_cost_rate: Optional[float] = None    # yıllık maliyet oranı (%)
    installment: Optional[float] = None
    total_payment: Optional[float] = None
    total_expense: Optional[float] = None
    fees: dict[str, float] = field(default_factory=dict)
    # Katılma hesabı tarafı
    gross_annual_rate: Optional[float] = None
    net_annual_rate: Optional[float] = None
    segment: Optional[str] = None
    # Provenance (CLAUDE.md §14)
    source_url: Optional[str] = None
    collected_at: Optional[str] = None
    method: str = METHOD_RATE_API
    note: Optional[str] = None

    def to_json(self) -> dict[str, Any]:
        out = {
            "bank_slug": self.bank_slug, "kind": self.kind,
            "product_code": self.product_code, "product_name": self.product_name,
            "amount": self.amount, "amount_max": self.amount_max,
            "amount_unit": self.amount_unit,
            "term_months": self.term_months,
            "term_days": self.term_days, "currency": self.currency,
            "monthly_rate": self.monthly_rate,
            "annual_cost_rate": self.annual_cost_rate,
            "installment": self.installment, "total_payment": self.total_payment,
            "total_expense": self.total_expense,
            "fees": self.fees or None,
            "gross_annual_rate": self.gross_annual_rate,
            "net_annual_rate": self.net_annual_rate, "segment": self.segment,
            "source_url": self.source_url, "collected_at": self.collected_at,
            "method": self.method, "note": self.note,
        }
        return {k: v for k, v in out.items() if v is not None}


@dataclass
class RateGrid:
    """Hangi ürün/tutar/vade noktalarının sorulacağı."""

    financing_amounts: tuple[int, ...] = DEFAULT_FINANCING_AMOUNTS
    financing_terms: tuple[int, ...] = DEFAULT_FINANCING_TERMS
    deposit_amounts: tuple[int, ...] = DEFAULT_DEPOSIT_AMOUNTS
    deposit_term_days: tuple[int, ...] = DEFAULT_DEPOSIT_TERM_DAYS
    max_requests: int = 200  # emniyet supabı


def _num(value: Any) -> Optional[float]:
    """Sayıya çevirir; çevrilemezse None (uydurma yok)."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    # "% 40.828621" / "102.351,20 TRY" / "%2,9900"
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    else:
        parts = s.split(".")
        if len(parts) > 2 and all(len(p) == 3 for p in parts[1:]):
            s = s.replace(".", "")
        elif len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
            # "1.500" → binlik; "40.828" → ondalık olabilir. Oranlarda 1-3 hane
            # tam kısım + 3 hane kesir yaygın olduğu için ondalık bırakılır.
            pass
    try:
        return float(s)
    except ValueError:
        return None


class RateAdapter:
    """Banka başına oran toplama arayüzü."""

    slug = ""
    kinds: tuple[str, ...] = ()

    def __init__(self, fetcher: StaticFetcher, robots=None) -> None:
        self.fetcher = fetcher
        self.robots = robots
        self.notes: list[str] = []
        self.failures: list[dict[str, Any]] = []
        self.requests = 0

    # --- yardımcılar ---------------------------------------------------- #

    def _allowed(self, url: str) -> bool:
        if self.robots is None:
            return True
        ok, reason = self.robots.allows(url)
        if not ok:
            self.failures.append({"url": url, "reason": "robots disallow",
                                  "detail": reason})
        return ok

    def _get_json(self, url: str, *, ajax: bool = False) -> Optional[Any]:
        """JSON çeker. Yanıt JSON değilse None + gerekçe (sessiz geçmez).

        `ajax=True` → `X-Requested-With: XMLHttpRequest`. Albaraka'da bu başlık
        OLMADAN uç 200 ile ANA SAYFA HTML'i döndürüyor; başlıksız istek sessiz
        veri kaybı üretir, bu yüzden içerik tipi de doğrulanır.
        """
        if not self._allowed(url):
            return None
        if not self.fetcher.available:  # oturumu da kuran özellik
            self.failures.append({"url": url, "reason": "requests kurulu degil"})
            return None
        session = getattr(self.fetcher, "_session", None)
        if session is None:
            self.failures.append({"url": url, "reason": "HTTP oturumu yok"})
            return None
        headers = {"Accept": "application/json, text/javascript, */*; q=0.01"}
        if ajax:
            headers["X-Requested-With"] = "XMLHttpRequest"
        self.fetcher.limiter.wait(url)
        self.requests += 1
        try:
            resp = session.get(url, timeout=self.fetcher.timeout, headers=headers)
        except Exception as exc:
            self.failures.append({"url": url, "reason": "baglanti hatasi",
                                  "detail": f"{type(exc).__name__}: {exc}"[:150]})
            return None
        if resp.status_code != 200:
            self.failures.append({"url": url, "reason": f"HTTP {resp.status_code}"})
            return None
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "json" not in ctype:
            self.failures.append({
                "url": url, "reason": "JSON degil",
                "detail": f"content-type={ctype or 'yok'} — AJAX basligi eksik olabilir"})
            return None
        try:
            return resp.json()
        except ValueError:
            self.failures.append({"url": url, "reason": "JSON ayristirilamadi"})
            return None

    def quotes(self, grid: RateGrid) -> list[RateQuote]:  # pragma: no cover
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# Türkiye Emlak Katılım — /Plugins/* (2026-08-03 doğrulandı)
# --------------------------------------------------------------------------- #

class EmlakKatilimAdapter(RateAdapter):
    """`/Plugins/CalculateLoansProduct` + `/Plugins/CalculateProfitShareRate`.

    Doğrulanmış örnek yanıt (KONUT, 1.000.000 TL, 120 ay):
        {"Success":true,"Data":{"ProfitRate":1.99,"TotalCost":27.47,
         "TotalInstallmentAmount":2635735.62,"CommissionAmount":5250,
         "ExpertiseAmount":11000,"HypothecAmount":3684,"TotalExpense":19934,
         "InstallmentContractList":[...]}}
    """

    slug = "turkiye-emlak-katilim"
    kinds = (KIND_FINANCING, KIND_PROFIT_SHARE)
    BASE = "https://www.emlakkatilim.com.tr"
    # `ProductTypeId` değerleri hesaplama sayfasının SEÇENEK LİSTESİNDEN alındı
    # (2026-08-03: `value="ARACBINEK2EL"` vb.) + `KONUT` canlı doğrulandı.
    #
    # UYDURMA KOD KULLANILMAZ: tahmin edilen `IHTIYAC` / `ISYERI` kodları uçtan
    # HER ZAMAN "fiyatlanmamış" yanıt aldı (oran 0, toplam = ana para). Uç bu
    # durumda `Success: true` döndürüyor; yani geçersiz kod SESSİZCE %0 oran gibi
    # görünüyor. `_is_priced` kapısı bunu keser.
    PRODUCTS = (
        ("KONUT", "Konut Finansmanı"),
        ("GMENKULKONUTYENI", "Konut Finansmanı (sıfır konut)"),
        ("ARACBINEK2EL", "Taşıt Finansmanı (2. el binek)"),
        ("ARACBINEKYENI", "Taşıt Finansmanı (sıfır binek)"),
        ("EVOFISGERECLERI", "Ev/Ofis Gereçleri Finansmanı"),
    )

    def quotes(self, grid: RateGrid) -> list[RateQuote]:
        out: list[RateQuote] = []
        out.extend(self._financing(grid))
        out.extend(self._deposit(grid))
        return out

    def _financing(self, grid: RateGrid) -> list[RateQuote]:
        out: list[RateQuote] = []
        unpriced: dict[str, int] = {}
        for code, name in self.PRODUCTS:
            for amount in grid.financing_amounts:
                for term in grid.financing_terms:
                    if self.requests >= grid.max_requests:
                        continue
                    url = (f"{self.BASE}/Plugins/CalculateLoansProduct"
                           f"?CalculationTypeId=1&ProductTypeId={code}"
                           f"&LoanAmount={amount}&LoanMaturity={term}"
                           f"&LoanSegmentId=1")
                    data = self._get_json(url)
                    if data is None:
                        # Gerekçe `_get_json` içinde ZATEN kaydedildi (robots,
                        # HTTP, JSON değil...). İkinci bir kayıt eklemek raporu
                        # yanıltır: tek başarısızlık iki satır görünür.
                        continue
                    if not isinstance(data, dict) or not data.get("Success"):
                        self.failures.append({
                            "url": url, "reason": "Success=false",
                            "detail": str(data)[:120]})
                        continue
                    d = data.get("Data") or {}
                    rate = _num(d.get("ProfitRate"))
                    if rate is None:
                        self.failures.append({"url": url,
                                              "reason": "ProfitRate yok"})
                        continue
                    # Uç, geçersiz (ürün, tutar, vade) üçlüsünde hata DÖNDÜRMÜYOR;
                    # kâr eklenmemiş yanıt veriyor. Kaydetmek %0 oran uydurmak olur.
                    if not _is_priced(d, float(amount)):
                        unpriced[code] = unpriced.get(code, 0) + 1
                        continue
                    out.append(RateQuote(
                        bank_slug=self.slug, kind=KIND_FINANCING,
                        product_code=code, product_name=name,
                        amount=float(amount), term_months=int(term),
                        monthly_rate=rate,
                        annual_cost_rate=_num(d.get("TotalCost")),
                        installment=_first_installment(d),
                        total_payment=_num(d.get("TotalInstallmentAmount")),
                        total_expense=_num(d.get("TotalExpense")),
                        fees=_clean_fees({
                            "komisyon": _num(d.get("CommissionAmount")),
                            "ekspertiz": _num(d.get("ExpertiseAmount")),
                            "ipotek": _num(d.get("HypothecAmount")),
                        }),
                        source_url=url, collected_at=utc_now_iso(),
                        method=METHOD_RATE_API))
        for code, n in sorted(unpriced.items()):
            self.notes.append(
                f"{self.slug}: {code} — {n} (tutar, vade) noktasi FIYATLANMAMIS "
                f"yanit verdi (oran 0 + toplam = ana para); kayit UYDURULMADI")
        return out

    def _deposit(self, grid: RateGrid) -> list[RateQuote]:
        out: list[RateQuote] = []
        for amount in grid.deposit_amounts:
            for days in grid.deposit_term_days:
                if self.requests >= grid.max_requests:
                    continue
                url = (f"{self.BASE}/Plugins/CalculateProfitShareRate"
                       f"?LanguageId=1&Money={amount}&Fec=0"
                       f"&profitShareInstallment=0&MaturityTerm={days}"
                       f"&profitShareInstallmentValueDay={days}")
                data = self._get_json(url)
                if data is None:
                    continue  # gerekçe `_get_json` içinde kaydedildi
                if not isinstance(data, dict) or not data.get("Success"):
                    self.failures.append({"url": url, "reason": "Success=false",
                                          "detail": str(data)[:120]})
                    continue
                d = data.get("Data") or {}
                gross = _num(d.get("GrossProfitShareYearly"))
                net = _num(d.get("NetProfitShareYearly"))
                if gross is None and net is None:
                    self.failures.append({"url": url, "reason": "oran alani yok"})
                    continue
                out.append(RateQuote(
                    bank_slug=self.slug, kind=KIND_PROFIT_SHARE,
                    product_name="Katılma Hesabı",
                    amount=float(amount), term_days=int(days),
                    gross_annual_rate=gross, net_annual_rate=net,
                    segment=d.get("SegmentName"),
                    source_url=url, collected_at=utc_now_iso(),
                    method=METHOD_RATE_API))
        return out


def _is_priced(data: dict[str, Any], amount: float) -> bool:
    """Yanıt gerçekten FİYATLANMIŞ mı, yoksa uç isteği aynen geri mi verdi?

    Emlak Katılım ucu geçersiz (ürün, tutar, vade) üçlüsünde hata DÖNDÜRMÜYOR:
    `Success: true` + `ProfitRate: 0` + `TotalInstallmentAmount == LoanAmount`
    yanıtı geliyor. Yani kâr hiç eklenmemiş.

    Doğrulanmış örnekler (2026-08-03):
        ARACBINEK2EL 1.000.000 TL / 120 ay → oran 0,   toplam 1.000.000  (geçersiz)
        ARACBINEK2EL   300.000 TL /  36 ay → oran 4,29 toplam   701.790  (geçerli)
        IHTIYAC        100.000 TL /  12 ay → oran 0,   toplam   100.000  (kod yok)

    Bu kapı olmadan geçersiz kombinasyonlar korpusa **%0 kâr payı oranı** olarak
    girerdi — CLAUDE.md §19'un yasakladığı tam da bu (bilgi yoksa `null`).

    KABUL EDİLEN SINIR: gerçek bir %0 kampanyalı finansman da toplam = ana para
    verirdi ve bu kapı onu da düşürür. Bilinçli tercih: bir oranı YANLIŞ
    kaydetmek, eksik kaydetmekten daha kötüdür.
    """
    total = _num(data.get("TotalInstallmentAmount"))
    if total is None:
        return False
    # 1 TL tolerans: yuvarlama farkı fiyatlanmış saymaya yetmez.
    return total > amount + 1.0


def _first_installment(d: dict[str, Any]) -> Optional[float]:
    """Ödeme planındaki ilk taksit tutarı (varsa)."""
    lst = d.get("InstallmentContractList")
    if isinstance(lst, list) and lst and isinstance(lst[0], dict):
        return _num(lst[0].get("Amount"))
    return None


def _clean_fees(fees: dict[str, Optional[float]]) -> dict[str, float]:
    return {k: v for k, v in fees.items() if v is not None}


# --------------------------------------------------------------------------- #
# Albaraka Türk — /plugins/* + sayfaya gömülü ürün kataloğu
# --------------------------------------------------------------------------- #

class AlbarakaAdapter(RateAdapter):
    """Albaraka iki kaynak sunar:

    1. **Gömülü katalog** (`METHOD_RATE_CATALOG`): finansman hesaplama sayfasının
       HTML'inde 16 ürünün `profitRate` / vade / tutar sınırı JSON olarak duruyor.
       Tek istekle tüm ürün-oran eşlemesi alınır — en ucuz kaynak.
    2. **Katılma hesabı oranı TOPLANMIYOR** — gerekçe aşağıda.

    ## Katılma hesabı ucu neden kullanılmıyor (robots.txt sınırı)

    `/plugins/getProfitShareCalculate` yolu robots.txt'te engelli DEĞİL, ama uç
    yalnızca `Slug=...&searchUrl=%2Ftr%2Farama` parametreleriyle yanıt veriyor;
    bu parametreler olmadan sunucu bağlantıyı kapatıyor (`RemoteDisconnected`).
    Ve o parametreli URL robots.txt'in `*search*` / `/*slug` kurallarına takılıyor.

    Yani **çalışan tek URL biçimi robots ile engelli.** Sayfanın statik HTML'inde
    de oran yok (değerler sayfanın kendi AJAX çağrısıyla geliyor). Dolayısıyla bu
    veri robots-uyumlu biçimde alınamıyor ve TOPLANMIYOR (CLAUDE.md §14).

    Finansman tarafı etkilenmiyor: oranlar izinli hesaplama sayfasının HTML'ine
    gömülü kataloğdan, tek istekle alınıyor.
    """

    slug = "albaraka"
    kinds = (KIND_FINANCING,)
    BASE = "https://www.albaraka.com.tr"
    CALC_PAGE = "/tr/hesaplama-araclari/finansman-hesaplama"
    LANG_ID = "bf2689d9-071e-4a20-9450-b1dbdd39778f"

    _CATALOG_RE = re.compile(
        r'\{&quot;ProductCode&quot;[\s\S]{0,1500}?'
        r'&quot;XkampMaxAmountManuel&quot;:[0-9.]+\}')

    def quotes(self, grid: RateGrid) -> list[RateQuote]:
        out = self._catalog()
        self.notes.append(
            f"{self.slug}: katilma hesabi orani TOPLANMADI — calisan tek URL "
            f"bicimi robots.txt'in *search*/*slug kurallarina takiliyor, "
            f"parametresiz uc baglantiyi kapatiyor, statik HTML'de oran yok "
            f"(bkz. sinif docstring'i)")
        return out

    def _catalog(self) -> list[RateQuote]:
        url = self.BASE + self.CALC_PAGE
        if not self._allowed(url):
            return []
        self.requests += 1
        res = self.fetcher.fetch(url)
        if not res.ok:
            self.failures.append({"url": url,
                                  "reason": f"HTTP {res.status}" if res.status
                                  else "baglanti hatasi",
                                  "detail": res.error or ""})
            return []
        seen: set[tuple[str, str]] = set()
        out: list[RateQuote] = []
        for m in self._CATALOG_RE.finditer(res.html or ""):
            try:
                j = json.loads(m.group(0).replace("&quot;", '"'))
            except ValueError:
                continue
            key = (str(j.get("ProductCode")), str(j.get("CampaingCode")))
            if key in seen:
                continue
            seen.add(key)
            rate = _num(j.get("profitRate"))
            if rate is None:
                continue
            out.append(RateQuote(
                bank_slug=self.slug, kind=KIND_FINANCING,
                product_code=f"{j.get('ProductCode')}/{j.get('CampaingCode')}",
                # Katalog JSON'u HTML içine gömülü olduğu için adlar HTML
                # varlığı taşıyor ("DİJİTAL ARA&#199;" → "DİJİTAL ARAÇ").
                product_name=_unescape(j.get("CampaignName")),
                monthly_rate=rate,
                term_months=_int(j.get("MaturityMaxValue")),
                amount=_num(j.get("AmountMaxValue")),
                source_url=url, collected_at=utc_now_iso(),
                method=METHOD_RATE_CATALOG,
                note="sayfaya gömülü ürün kataloğundan; tutar/vade ÜST SINIR "
                     "değerleridir, tek bir hesaplama noktası değil"))
        if not out:
            self.notes.append(f"{self.slug}: gomulu katalog bulunamadi "
                              f"(sayfa yapisi degismis olabilir)")
        return out

    def _deposit(self, grid: RateGrid) -> list[RateQuote]:
        out: list[RateQuote] = []
        for amount in grid.deposit_amounts:
            for days in grid.deposit_term_days:
                if self.requests >= grid.max_requests:
                    continue
                months = max(1, round(days / 30))
                url = (f"{self.BASE}/plugins/getProfitShareCalculate"
                       f"?langId={self.LANG_ID}&language=tr"
                       f"&Slug=kar-payi-hesaplama&searchUrl=%2Ftr%2Farama"
                       f"&customFinancingName=&DepositedAmount={amount}"
                       f"&Currency=TRY&Maturity={months}&Period=MONTH"
                       f"&Type=KTLMHSP")
                data = self._get_json(url, ajax=True)
                if not isinstance(data, dict) or not data.get("Result"):
                    continue
                d = data.get("Data") or {}
                gross = _num(d.get("GrossRate"))
                net = _num(d.get("NetRate"))
                if gross is None and net is None:
                    self.failures.append({"url": url, "reason": "oran alani yok"})
                    continue
                out.append(RateQuote(
                    bank_slug=self.slug, kind=KIND_PROFIT_SHARE,
                    product_name="Katılma Hesabı",
                    amount=float(amount), term_months=months, term_days=int(days),
                    gross_annual_rate=gross, net_annual_rate=net,
                    source_url=url, collected_at=utc_now_iso(),
                    method=METHOD_RATE_API))
        return out


def _int(value: Any) -> Optional[int]:
    n = _num(value)
    return int(n) if n is not None else None


def _num_en(value: Any) -> Optional[float]:
    """İNGİLİZCE biçimli sayıyı çevirir: binlik ',' ondalık '.'.

    Türkiye Finans oran tabloları TR değil EN biçim kullanıyor
    ("250-100,000,000", "28.03"). `_num` (TR öncelikli) bu değerleri BOZAR:
    "100,000,000" → virgülü ondalık sanıp geçersiz sayı üretir. Bu yüzden
    tablo ayrıştırıcısı ayrı bir çeviriciyle çalışır.
    """
    if value is None or isinstance(value, bool):
        return None
    s = re.sub(r"[^\d,.\-]", "", str(value)).strip(",.")
    if not s or not re.search(r"\d", s):
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def _unescape(value: Any) -> Optional[str]:
    """HTML varlıklarını çözer ve boşlukları sadeleştirir."""
    if value is None:
        return None
    import html

    return re.sub(r"\s+", " ", html.unescape(str(value))).strip() or None


# --------------------------------------------------------------------------- #
# Kuveyt Türk — hesaplama aracını TARAYICI ile sürme
# --------------------------------------------------------------------------- #

class KuveytTurkBrowserAdapter(RateAdapter):
    """Kuveyt Türk'te parametreli JSON ucu YOK; oran ancak etkileşimle çıkar.

    2026-08-03 doğrulaması:
      * Sayfa JS paketlerinde ve gizli alanlarda oran BULUNMUYOR
        (`txtProfilRate` boş gelir).
      * "Ödeme Planı" düğmesine basıldığında oran `id="ProfitRate"` düğümüne
        yazılıyor; birlikte tam amortisman tablosu da geliyor.
      * Statik hasat bu yüzden oranı `%0` olarak kaydediyordu.

    Bu adaptör `playwright` ile "Ödeme Planı" düğmesine basar ve sonucu DOM'dan
    okur. `playwright` (veya tarayıcı ikilisi) yoksa hiçbir şey yapmaz, gerekçe
    rapora yazılır — hat çökmez (kod tabanındaki zarif düşüş deseni).

    ## Neden IZGARA sürülmüyor, VARSAYILAN nokta okunuyor

    Tutar alanı (`input[name="p1"]`) bir `priceRange`/`moneyformat` eklentisiyle
    yönetiliyor ve programatik değişikliği GERİ ALIYOR. Denenen ve güvenilir
    ÇALIŞMAYAN yollar: `fill()`, doğrudan `.value` atama + olay tetikleme,
    seçim + `Backspace` + karakter karakter yazma. Vade alanı oturuyor, tutar
    oturmuyor; tek seferlik başarılar yeniden üretilemedi.

    Bu yüzden adaptör tutarı ZORLAMAZ. Sayfa geçerli bir varsayılanla yükleniyor
    (konut için 100.000 TL / 120 ay) ve ödeme planı diyaloğu kullanılan
    tutar/vadeyi GERİ YANSITIYOR. Adaptör bu yansımayı kaydın tutar/vadesi
    olarak alır — yani **istenen değer değil, sayfanın gerçekten hesapladığı
    değer** kaydedilir. Böylece kayıt her zaman kendi girdisiyle tutarlıdır.

    Vade değişimi denenir (vade alanı oturuyor); sonuç yalnızca diyalog yansıması
    isteneni doğruluyorsa kaydedilir. Doğrulanmayan nokta DÜŞÜRÜLÜR.

    Form seçicileri canlı sayfadan tespit edildi:
        tutar : input[name="p1"]  (1.000–3.000.000 sınırlı, TR binlik maskeli)
        vade  : #maturity         (1–120)
        düğme : "Ödeme Planı"
        sonuç : #ProfitRate + diyalogdaki etiket/değer listesi
    "Kâr Oranı Belirle" alanı BOŞ bırakılır; doldurulursa bankanın oranı değil
    kullanıcının girdiği oran hesaplanır.
    """

    slug = "kuveyt-turk"
    kinds = (KIND_FINANCING,)
    BASE = "https://www.kuveytturk.com.tr"
    # Hesaplama aracı BULUNAN ürün sayfaları (korpustan doğrulandı).
    PRODUCT_PAGES = (
        ("/kendim-icin/finansmanlar/konut-finansmanlari/konut-finansmani",
         "Konut Finansmanı"),
        ("/kendim-icin/finansmanlar/arac-finansmanlari/arac-finansmani",
         "Taşıt Finansmanı"),
        ("/kendim-icin/finansmanlar/arac-finansmanlari/togg-finansmani",
         "TOGG Finansmanı"),
        ("/kendim-icin/finansmanlar/ihtiyac-finansmani",
         "İhtiyaç Finansmanı"),
    )
    # Ödeme planı diyaloğundaki etiket → RateQuote alanı
    _LABELS = {
        "Aylık Kâr Oranı": "monthly_rate",
        "Yıllık Maliyet Oranı": "annual_cost_rate",
        "Taksit Tutarı": "installment",
        "Ödenecek Toplam Tutar": "total_payment",
        "Toplam Masraf": "total_expense",
    }
    _FEE_LABELS = {
        "Finansman Tahsis Ücreti": "tahsis",
        "İpotek Tesis Bedeli": "ipotek",
        "Ekspertiz Ücreti": "ekspertiz",
    }

    def __init__(self, fetcher: StaticFetcher, robots=None,
                 browser=None) -> None:
        super().__init__(fetcher, robots=robots)
        self._browser = browser  # test edilebilirlik için enjekte edilebilir

    def quotes(self, grid: RateGrid) -> list[RateQuote]:
        driver = self._browser or _PlaywrightDriver()
        reason = driver.start()
        if reason:
            self.notes.append(f"{self.slug}: {reason} — oran turu atlandi")
            return []
        out: list[RateQuote] = []
        try:
            for path, name in self.PRODUCT_PAGES:
                url = self.BASE + path
                if not self._allowed(url):
                    continue
                # `None` = sayfanın varsayılan vadesi (zorlama yok).
                # Diğerleri denenir; yalnızca diyalog yansıması doğrularsa yazılır.
                seen_points: set[tuple[float, int]] = set()
                for term in (None, *grid.financing_terms):
                    if self.requests >= grid.max_requests:
                        continue
                    self.fetcher.limiter.wait(url)
                    self.requests += 1
                    res = driver.quote(url, term)
                    if isinstance(res, str):  # hata mesajı
                        self.failures.append({
                            "url": url, "reason": "tarayici",
                            "detail": f"vade={term or 'varsayilan'}: {res}"[:150]})
                        continue
                    rate = _num(res.get("monthly_rate"))
                    used_amount = _num(res.get("used_amount"))
                    used_term = _num(res.get("used_term"))
                    if rate is None or rate == 0:
                        self.notes.append(
                            f"{self.slug}: {name} vade={term or 'varsayilan'} — "
                            f"oran uretilmedi, kayit UYDURULMADI")
                        continue
                    # KAYIT, SAYFANIN GERÇEKTEN KULLANDIĞI GİRDİYLE etiketlenir.
                    # Diyalog bunları geri yansıtıyor; okunamıyorsa kayıt
                    # DÜŞÜRÜLÜR (kanıtsız sayı yazmaktan iyidir).
                    if used_amount is None or used_term is None:
                        self.failures.append({
                            "url": url, "reason": "girdi dogrulanamadi",
                            "detail": "diyalog tutar/vadeyi yansitmadi — "
                                      "kayit DUSURULDU"})
                        continue
                    if term is not None and int(used_term) != int(term):
                        # Vade oturmadı: bu nokta istenmiş olan DEĞİL.
                        # Varsayılan nokta zaten kaydedildiği için sessizce geçilir.
                        continue
                    point = (used_amount, int(used_term))
                    if point in seen_points:
                        continue
                    seen_points.add(point)
                    out.append(RateQuote(
                        bank_slug=self.slug, kind=KIND_FINANCING,
                        product_name=name, amount=used_amount,
                        term_months=int(used_term), monthly_rate=rate,
                        annual_cost_rate=_num(res.get("annual_cost_rate")),
                        installment=_num(res.get("installment")),
                        total_payment=_num(res.get("total_payment")),
                        total_expense=_num(res.get("total_expense")),
                        fees=_clean_fees({k: _num(v) for k, v
                                          in (res.get("fees") or {}).items()}),
                        source_url=url, collected_at=utc_now_iso(),
                        method=METHOD_RATE_BROWSER,
                        note="hesaplama araci tarayici ile surulerek alindi; "
                             "tutar/vade SAYFANIN kullandigi degerlerdir"))
        finally:
            driver.close()
        return out


class _PlaywrightDriver:
    """Kuveyt Türk hesaplama aracını süren ince Playwright sarmalayıcısı."""

    AMOUNT_SEL = 'input[name="p1"]'
    TERM_SEL = "#maturity"
    BUTTON_TEXT = "Ödeme Planı"
    RATE_SEL = "#ProfitRate"

    def __init__(self, timeout_ms: int = 30000) -> None:
        self.timeout_ms = timeout_ms
        self._pw = None
        self._browser = None
        self._ctx = None

    def start(self) -> Optional[str]:
        """Tarayıcıyı açar. Hata mesajı döner (None = hazır)."""
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except ModuleNotFoundError:
            return "playwright kurulu degil"
        try:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True)
            self._ctx = self._browser.new_context(
                user_agent="AnatoliaAI-Research/1.0 (+TEKNOFEST 2026; arastirma amacli)",
                locale="tr-TR", viewport={"width": 1440, "height": 900})
        except Exception as exc:
            self.close()
            return f"tarayici baslatilamadi: {type(exc).__name__}: {exc}"[:150]
        return None

    def quote(self, url: str, term: Optional[int] = None):
        """Ödeme planını üretir. Sözlük ya da hata dizgesi döner.

        `term=None` → sayfanın varsayılan girdileriyle hesaplar (hiçbir alan
        doldurulmaz). Tutar HİÇBİR durumda zorlanmaz: maske programatik
        değişikliği geri alıyor (bkz. `KuveytTurkBrowserAdapter` docstring'i).
        """
        page = None
        try:
            page = self._ctx.new_page()  # type: ignore[union-attr]
            page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")
            try:
                page.wait_for_selector(self.AMOUNT_SEL, timeout=10000)
            except Exception:
                return "hesaplama araci bulunamadi"
            # MASKELİ ALAN DOLDURMA — sıra kritik ve ölçümle bulundu.
            #
            # `fill()` ve doğrudan `.value` ataması ÇALIŞMIYOR: alan bir
            # `priceRange`/`moneyformat` eklentisiyle yönetiliyor, kendi iç
            # modelini tutuyor ve dışarıdan yazılan değeri geri alıyor.
            # Salt `pressSequentially` de yetmiyor: alan zaten dolu ve
            # `maxlength=9` olduğu için yeni rakamlar sığmıyor, maske değeri
            # eski hâline döndürüyor.
            #
            # Çalışan dizi: seç → Backspace ile TEMİZLE → rakamları yaz.
            # (Bu bulunmadan önce adaptör 500.000/60 istediği hâlde varsayılan
            #  100.000/120 sonucunu kaydediyordu — sessiz veri bozulması.)
            if term is not None:
                # Yalnızca VADE denenir; oturmazsa hata değil — çağıran taraf
                # noktayı sessizce atlar (varsayılan nokta zaten alınmıştır).
                self._clear_and_type(page, self.TERM_SEL, str(int(term)))
                page.keyboard.press("Tab")
                page.wait_for_timeout(400)
            page.get_by_role("button", name=self.BUTTON_TEXT).first.click()
            try:
                page.wait_for_function(
                    "() => { const e = document.querySelector('#ProfitRate');"
                    " return e && /\\d/.test(e.textContent || ''); }",
                    timeout=12000)
            except Exception:
                return "odeme plani uretilmedi"
            return page.evaluate(_EXTRACT_JS)
        except Exception as exc:
            return f"{type(exc).__name__}: {exc}"[:150]
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass

    @staticmethod
    def _clear_and_type(page, selector: str, value: str) -> None:
        """Maskeli alanı temizleyip değeri kullanıcı gibi yazar."""
        page.click(selector)
        page.evaluate(
            "sel => { const e = document.querySelector(sel);"
            " e.focus(); e.setSelectionRange(0, (e.value || '').length); }",
            selector)
        page.keyboard.press("Backspace")
        page.locator(selector).press_sequentially(value, delay=15)

    def close(self) -> None:
        for obj in (self._ctx, self._browser, self._pw):
            try:
                if obj is not None:
                    (obj.stop if hasattr(obj, "stop") else obj.close)()
            except Exception:
                pass
        self._ctx = self._browser = self._pw = None


# Ödeme planı diyaloğundaki etiket/değer çiftlerini okur. Diyalog yapısı
# `<div class="title">Etiket</div><div class="value">%2,9900</div>` biçiminde.
_EXTRACT_JS = r"""
() => {
  const out = { fees: {} };
  const map = {
    'Aylık Kâr Oranı': 'monthly_rate',
    'Yıllık Maliyet Oranı': 'annual_cost_rate',
    'Taksit Tutarı': 'installment',
    'Ödenecek Toplam Tutar': 'total_payment',
    'Toplam Masraf': 'total_expense',
  };
  const feeMap = {
    'Finansman Tahsis Ücreti': 'tahsis',
    'İpotek Tesis Bedeli': 'ipotek',
    'Ekspertiz Ücreti': 'ekspertiz',
  };
  // Sayfanın GERÇEKTEN kullandığı girdiler — doğrulama kapısı bunları ister.
  const usedMap = {
    'Finansman Tutarı': 'used_amount',
    'Taksit Sayısı': 'used_term',
  };
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  for (const li of document.querySelectorAll('li')) {
    const t = norm(li.querySelector('.title')?.textContent);
    const v = norm(li.querySelector('.value')?.textContent);
    if (!t || !v) continue;
    if (map[t] && out[map[t]] === undefined) out[map[t]] = v;
    if (feeMap[t] && out.fees[feeMap[t]] === undefined) out.fees[feeMap[t]] = v;
    if (usedMap[t] && out[usedMap[t]] === undefined) out[usedMap[t]] = v;
  }
  if (out.monthly_rate === undefined) {
    const e = document.querySelector('#ProfitRate');
    if (e) out.monthly_rate = norm(e.textContent);
  }
  return out;
}
"""


# --------------------------------------------------------------------------- #
# Türkiye Finans — YAYIMLANMIŞ oran tablosu (statik HTML)
# --------------------------------------------------------------------------- #

class TurkiyeFinansTableAdapter(RateAdapter):
    """Katılma hesabı oranlarını yayımlanmış HTML tablosundan okur.

    En ucuz ve en zengin kaynak: TEK istek, 20 tablo, tutar dilimi × vade ×
    hesap türü × PARA BİRİMİ kırılımı.

    ## Para birimi tespiti neden zorunlu

    Sayfa 5 sekme taşıyor: TL · USD · EUR · YAU (altın) · YAG (gümüş). Her sekme
    aynı 4 hesap türü tablosunu tekrar eder. Sekme tespit edilmezse USD %0,61 ile
    TL %28,03 aynı kümede karışır — karşılaştırma motorunu felaket biçimde
    yanıltır (CLAUDE.md §17 adil kıyas).

    Panel eşlemesi DOM sırasıyla yapılır: `div.tab-wrapper` içindeki `li a`
    etiketleri sekme adlarını, `div.tab-item` panelleri aynı sırada içerikleri
    verir (2026-08-03'te 5 sekme / 5 panel olarak doğrulandı).

    ## Altın/gümüşte tutar GRAM'dır

    YAU/YAG panellerinde dilim "50 gr." / "5,000 gr." biçiminde. Bu bir para
    tutarı DEĞİL; `amount_unit="gram"` ile işaretlenir ki TL tutarıyla
    kıyaslanmasın.

    ## Sayı biçimi TUZAĞI

    Tablodaki sayılar İNGİLİZCE biçimde ("100,000,000", "28.03"). TR ayrıştırıcı
    bunları bozar; `_num_en` kullanılır.
    """

    slug = "turkiye-finans"
    kinds = (KIND_PROFIT_SHARE,)
    BASE = "https://www.turkiyefinans.com.tr"
    PAGES = (
        ("/tr-tr/bireysel/Sayfalar/Kar-Payi-Oranlari.aspx", "bireysel"),
        ("/tr-tr/bireysel/Sayfalar/Kar-Paylasim-Oranlari.aspx", "paylasim"),
    )
    # Sekme etiketi → ISO/emtia kodu
    CURRENCY_MAP = {
        "TL": "TRY", "TRY": "TRY", "USD": "USD", "EUR": "EUR",
        "YAU": "XAU", "YAG": "XAG",
    }
    GRAM_CURRENCIES = ("XAU", "XAG")
    # Vade başlığı → ay. "1 Yıldan Uzun Vade" üst sınırsızdır: ay atanmaz,
    # `note` alanında belirtilir (uydurma vade yazmak yerine).
    TERM_MAP = {
        "1 ay": 1, "3 ay": 3, "6 ay": 6, "1 yıl": 12, "1 yil": 12,
        "12 ay": 12, "2 yıl": 24, "2 yil": 24,
    }
    OPEN_TERM_MARKERS = ("uzun vade", "üzeri", "uzeri")

    def quotes(self, grid: RateGrid) -> list[RateQuote]:
        try:
            from bs4 import BeautifulSoup  # type: ignore
        except ModuleNotFoundError:
            self.notes.append(f"{self.slug}: beautifulsoup4 yok — tablo "
                              f"ayristirilamadi")
            return []
        out: list[RateQuote] = []
        seen: set[tuple] = set()
        for path, label in self.PAGES:
            url = self.BASE + path
            if not self._allowed(url):
                continue
            self.requests += 1
            res = self.fetcher.fetch(url)
            if not res.ok:
                self.failures.append({
                    "url": url,
                    "reason": f"HTTP {res.status}" if res.status else "baglanti hatasi",
                    "detail": res.error or ""})
                continue
            found = self._parse(BeautifulSoup(res.html or "", "html.parser"),
                                url, label)
            for q in found:
                key = (q.product_name, q.currency, q.amount, q.term_months,
                       q.gross_annual_rate, q.note)
                if key in seen:
                    continue
                seen.add(key)
                out.append(q)
        if not out:
            self.notes.append(f"{self.slug}: oran tablosu bulunamadi "
                              f"(sayfa yapisi degismis olabilir)")
        return out

    def _parse(self, soup, url: str, page_label: str) -> list[RateQuote]:
        out: list[RateQuote] = []
        wrappers = soup.select("div.tab-wrapper") or [soup]
        for wrap in wrappers:
            tabs = [a.get_text(" ", strip=True)
                    for a in wrap.select("li a")]
            panels = wrap.select("div.tab-item")
            if not panels:
                continue
            if len(tabs) != len(panels):
                # Eşleme güvenilir değil: para birimi UYDURMAK yerine atla.
                self.notes.append(
                    f"{self.slug}: sekme({len(tabs)})/panel({len(panels)}) "
                    f"sayisi uyusmuyor — para birimi belirlenemedi, atlandi")
                continue
            # `strict=True`: uzunluk eşitliği yukarıda zaten doğrulandı; burada
            # sessiz kırpma olursa para birimi YANLIŞ eşlenirdi.
            for tab, panel in zip(tabs, panels, strict=True):
                currency = self.CURRENCY_MAP.get(tab.upper())
                if currency is None:
                    self.notes.append(
                        f"{self.slug}: bilinmeyen sekme '{tab}' — atlandi")
                    continue
                for table in panel.find_all("table"):
                    out.extend(self._parse_table(table, currency, url,
                                                 page_label))
        return out

    def _parse_table(self, table, currency: str, url: str,
                     page_label: str) -> list[RateQuote]:
        rows = table.find_all("tr")
        if len(rows) < 2:
            return []
        header = [c.get_text(" ", strip=True) for c in rows[0].find_all(["th", "td"])]
        if not header:
            return []
        account = header[0] or "Katılma Hesabı"
        out: list[RateQuote] = []
        for row in rows[1:]:
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            if len(cells) < 2:
                continue
            bracket = cells[0]
            low, high = self._parse_bracket(bracket)
            for idx, raw in enumerate(cells[1:], start=1):
                if idx >= len(header):
                    break
                rate = _num_en(raw)
                if rate is None:
                    continue  # "-" → o vadede oran yayımlanmamış
                term, open_ended = self._parse_term(header[idx])
                notes = [f"yayimlanmis oran tablosu ({page_label})"]
                if open_ended:
                    notes.append("vade '1 yıldan uzun' — üst sınır yok")
                if bracket:
                    notes.append(f"tutar dilimi: {bracket}")
                out.append(RateQuote(
                    bank_slug=self.slug, kind=KIND_PROFIT_SHARE,
                    product_name=account, currency=currency,
                    amount=low, amount_max=high,
                    amount_unit="gram" if currency in self.GRAM_CURRENCIES else None,
                    term_months=term,
                    gross_annual_rate=rate,
                    source_url=url, collected_at=utc_now_iso(),
                    method=METHOD_RATE_TABLE,
                    note="; ".join(notes)))
        return out

    def _parse_bracket(self, text: str) -> tuple[Optional[float], Optional[float]]:
        """'250-100,000,000' / '50 gr.' → (alt, üst). Belirsizse (None, None)."""
        nums = [_num_en(p) for p in re.findall(r"[\d.,]+", text or "")]
        nums = [n for n in nums if n is not None]
        if len(nums) >= 2:
            return nums[0], nums[1]
        if len(nums) == 1:
            return nums[0], None
        return None, None

    def _parse_term(self, header: str) -> tuple[Optional[int], bool]:
        """Vade başlığını aya çevirir. (ay, üst-sınırsız-mı) döner."""
        h = (header or "").lower().replace("(%)", "").strip()
        for marker in self.OPEN_TERM_MARKERS:
            if marker in h:
                return None, True
        for key, months in self.TERM_MAP.items():
            if key in h:
                return months, False
        m = re.search(r"(\d{1,3})\s*ay", h)
        if m:
            return int(m.group(1)), False
        return None, False


class VakifKatilimBlockedAdapter(RateAdapter):
    """Vakıf Katılım oranları robots.txt ile ERİŞİLEMEZ — bu bir kayıt tutucudur.

    2026-08-03 doğrulaması:
      * `/tr/kendim-icin/hesaplar/katilma-hesaplari/kar-paylasim-oranlari`
        sayfasında oran TABLOSU YOK (tarayıcıda da 0 tablo).
      * Oranlar tek bir PDF'te yayımlanıyor:
        `/documents/PerakendeBankacilik/kar-paylasim-oranlari.pdf`
      * Vakıf `robots.txt` `/documents/` yolunu AÇIKÇA engelliyor; yalnızca
        `.jpg/.png/.jpeg` uzantılarına izin var. Yani bu dışlama kazara değil,
        bankanın bilinçli tercihi.

    Bu yüzden oran TOPLANMAZ (CLAUDE.md §14). Adaptör kayıtlıdır ki rapor
    "adaptörü yok" demek yerine GERÇEK gerekçeyi göstersin — sessiz eksik,
    belgelenmiş eksikten kötüdür. Şartname §5.1 bu belge için manuel toplamaya
    izin verir; elle indirilip `data/raw/vakif-katilim/manual/` altına konabilir.
    """

    slug = "vakif-katilim"
    kinds = ()
    RATE_PDF = ("https://www.vakifkatilim.com.tr/documents/PerakendeBankacilik/"
                "kar-paylasim-oranlari.pdf")

    def quotes(self, grid: RateGrid) -> list[RateQuote]:
        self.notes.append(
            f"{self.slug}: oran TOPLANMADI — oranlar yalnizca {self.RATE_PDF} "
            f"belgesinde ve robots.txt '/documents/' yolunu acikca engelliyor. "
            f"Sartname 5.1 geregi elle indirilip manual/ altina konabilir.")
        return []


# Yeni banka eklemek = bir adaptör sınıfı + buraya bir satır (§18-3).
RATE_ADAPTERS: dict[str, type[RateAdapter]] = {
    TurkiyeFinansTableAdapter.slug: TurkiyeFinansTableAdapter,
    VakifKatilimBlockedAdapter.slug: VakifKatilimBlockedAdapter,
    EmlakKatilimAdapter.slug: EmlakKatilimAdapter,
    AlbarakaAdapter.slug: AlbarakaAdapter,
    KuveytTurkBrowserAdapter.slug: KuveytTurkBrowserAdapter,
}


def adapter_for(slug: str) -> Optional[type[RateAdapter]]:
    return RATE_ADAPTERS.get(slug)


def available_slugs() -> list[str]:
    return sorted(RATE_ADAPTERS)


def quotes_to_jsonl(quotes: Iterable[RateQuote]) -> str:
    return "".join(json.dumps(q.to_json(), ensure_ascii=False) + "\n"
                   for q in quotes)


__all__ = [
    "RateQuote", "RateGrid", "RateAdapter", "EmlakKatilimAdapter",
    "AlbarakaAdapter", "KuveytTurkBrowserAdapter", "TurkiyeFinansTableAdapter",
    "VakifKatilimBlockedAdapter",
    "RATE_ADAPTERS", "adapter_for", "available_slugs",
    "quotes_to_jsonl", "KIND_FINANCING", "KIND_PROFIT_SHARE",
    "METHOD_RATE_API", "METHOD_RATE_BROWSER", "METHOD_RATE_CATALOG",
    "METHOD_RATE_TABLE",
]
