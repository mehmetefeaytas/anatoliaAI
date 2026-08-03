"""Kâr payı oranı toplama testleri.

İlgili: ../src/scraping/rates.py, ../src/scraping/harvest_rates.py

## Neden bu testler

Bu hat, şartnamenin manşet alanını (`kar_payi_orani`) üretiyor. Yanlış bir sayı
kaydetmek, eksik kaydetmekten daha kötüdür (CLAUDE.md §19 halüsinasyon yasağı).
İki ölçülmüş tuzak var:

1. **Uç, geçersiz kombinasyonda HATA DÖNDÜRMÜYOR.** Emlak Katılım
   `Success: true` + `ProfitRate: 0` + `TotalInstallmentAmount == LoanAmount`
   yanıtı veriyor. Kapı olmadan bunlar korpusa "%0 kâr payı oranı" olarak girer.
   Doğrulandı: `ARACBINEK2EL` 1.000.000 TL / 120 ay → oran 0, toplam = ana para.
2. **AJAX başlığı eksikse uç 200 ile HTML döndürüyor.** Albaraka'da
   `X-Requested-With` olmadan ana sayfa HTML'i geliyor; içerik tipi
   doğrulanmazsa sessiz veri kaybı olur.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.scraping.rates import (
    KIND_FINANCING,
    KIND_PROFIT_SHARE,
    METHOD_RATE_CATALOG,
    METHOD_RATE_TABLE,
    AlbarakaAdapter,
    EmlakKatilimAdapter,
    KuveytTurkBrowserAdapter,
    RateGrid,
    RateQuote,
    TurkiyeFinansTableAdapter,
    VakifKatilimBlockedAdapter,
    _is_priced,
    _num,
    _num_en,
    _unescape,
    adapter_for,
    available_slugs,
    quotes_to_jsonl,
)


class _Resp:
    def __init__(self, status: int, body, ctype: str = "application/json"):
        self.status_code = status
        self.headers = {"Content-Type": ctype}
        self._body = body

    def json(self):
        if isinstance(self._body, str):
            return json.loads(self._body)
        return self._body

    @property
    def text(self):
        return self._body if isinstance(self._body, str) else json.dumps(self._body)


class _Session:
    def __init__(self, routes: dict, require_ajax: bool = False):
        self.routes = routes
        self.require_ajax = require_ajax
        self.calls: list[tuple[str, dict]] = []

    def get(self, url, timeout=None, headers=None, **kw):
        headers = headers or {}
        self.calls.append((url, headers))
        if self.require_ajax and headers.get("X-Requested-With") != "XMLHttpRequest":
            # Gerçek davranış: 200 + HTML (sessiz tuzak)
            return _Resp(200, "<html><body>ana sayfa</body></html>", "text/html")
        for pattern, resp in self.routes.items():
            if pattern in url:
                return resp
        return _Resp(404, "")


class _Limiter:
    def wait(self, url):  # gecikme testte yok
        pass


class _Fetcher:
    """`StaticFetcher` arayüzünün test ikizi."""

    timeout = 5.0

    def __init__(self, session: _Session, html_pages: dict | None = None):
        self._session = session
        self.limiter = _Limiter()
        self.html_pages = html_pages or {}

    @property
    def available(self) -> bool:
        return True

    def fetch(self, url: str):
        from src.scraping.fetcher import FetchResult

        body = self.html_pages.get(url)
        if body is None:
            return FetchResult(url, status=404)
        return FetchResult(url, status=200, html=body, final_url=url)

    def close(self):
        pass


class _AllowAll:
    @staticmethod
    def allows(url):
        return True, "izin"


class _DenyAll:
    @staticmethod
    def allows(url):
        return False, "robots.txt Disallow"


class TestNumParsing(unittest.TestCase):
    def test_yuzde_ve_para_isaretleri_temizlenir(self):
        self.assertEqual(_num("% 40.828621"), 40.828621)
        self.assertEqual(_num("%2,9900"), 2.99)
        self.assertEqual(_num("102.351,20 TRY"), 102351.20)

    def test_cok_gruplu_binlik(self):
        self.assertEqual(_num("2.500.001"), 2500001.0)

    def test_gecersiz_deger_none(self):
        self.assertIsNone(_num(None))
        self.assertIsNone(_num("—"))
        self.assertIsNone(_num(True), "bool sayı sayılmamalı")

    def test_html_varlik_cozulur(self):
        self.assertEqual(_unescape("DİJİTAL ARA&#199; FİNANSMANI"),
                         "DİJİTAL ARAÇ FİNANSMANI")


class TestPricingGate(unittest.TestCase):
    """Fiyatlanmamış yanıt oran olarak KAYDEDİLMEMELİ."""

    def test_toplam_ana_paraya_esitse_fiyatlanmamis(self):
        self.assertFalse(_is_priced({"TotalInstallmentAmount": 1_000_000},
                                    1_000_000))

    def test_toplam_ana_paradan_buyukse_fiyatlanmis(self):
        self.assertTrue(_is_priced({"TotalInstallmentAmount": 701_790.97},
                                   300_000))

    def test_toplam_yoksa_fiyatlanmamis(self):
        self.assertFalse(_is_priced({}, 100_000))


class TestEmlakAdapter(unittest.TestCase):
    def _adapter(self, *, priced: bool, robots=_AllowAll):
        total = 701_790.97 if priced else 300_000
        loan = {"Success": True, "Data": {
            "ProfitRate": 4.29 if priced else 0,
            "TotalCost": 92.81, "TotalInstallmentAmount": total,
            "CommissionAmount": 1500, "ExpertiseAmount": 0, "HypothecAmount": 0,
            "TotalExpense": 1500,
            "InstallmentContractList": [{"Amount": 19_494.19}],
        }}
        deposit = {"Success": True, "Data": {
            "GrossProfitShareYearly": 36.27, "NetProfitShareYearly": 29.92,
            "SegmentName": "Altın",
        }}
        session = _Session({"CalculateLoansProduct": _Resp(200, loan),
                            "CalculateProfitShareRate": _Resp(200, deposit)})
        return EmlakKatilimAdapter(_Fetcher(session), robots=robots()), session

    def test_fiyatlanmis_yanit_kaydedilir(self):
        a, _ = self._adapter(priced=True)
        grid = RateGrid(financing_amounts=(300_000,), financing_terms=(36,),
                        deposit_amounts=(), deposit_term_days=())
        qs = a.quotes(grid)
        self.assertEqual(len(qs), len(EmlakKatilimAdapter.PRODUCTS))
        q = qs[0]
        self.assertEqual(q.monthly_rate, 4.29)
        self.assertEqual(q.installment, 19_494.19)
        self.assertEqual(q.fees["komisyon"], 1500)
        # 0 BİLGİDİR, yokluk değildir: "ekspertiz ücreti 0" ile "ekspertiz
        # ücreti bilinmiyor" farklı şeylerdir. Projenin `masrafsız ≠ null`
        # ayrımıyla aynı ilke (CLAUDE.md §6). Bu yüzden 0 taşınır, None atılır.
        self.assertEqual(q.fees["ekspertiz"], 0.0)
        self.assertEqual(q.fees["ipotek"], 0.0)

    def test_fiyatlanmamis_yanit_KAYDEDILMEZ(self):
        """En kritik koruma: %0 oran uydurulmamalı."""
        a, _ = self._adapter(priced=False)
        grid = RateGrid(financing_amounts=(1_000_000,), financing_terms=(120,),
                        deposit_amounts=(), deposit_term_days=())
        qs = a.quotes(grid)
        self.assertEqual(qs, [])
        self.assertTrue(any("FIYATLANMAMIS" in n for n in a.notes),
                        f"gerekçe rapora yazılmalı: {a.notes}")

    def test_katilma_hesabi_oranlari(self):
        a, _ = self._adapter(priced=True)
        grid = RateGrid(financing_amounts=(), financing_terms=(),
                        deposit_amounts=(250_000,), deposit_term_days=(92,))
        qs = [q for q in a.quotes(grid) if q.kind == KIND_PROFIT_SHARE]
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].gross_annual_rate, 36.27)
        self.assertEqual(qs[0].net_annual_rate, 29.92)
        self.assertEqual(qs[0].segment, "Altın")
        self.assertEqual(qs[0].term_days, 92)

    def test_robots_disallow_istek_atilmaz(self):
        a, session = self._adapter(priced=True, robots=_DenyAll)
        grid = RateGrid(financing_amounts=(300_000,), financing_terms=(36,),
                        deposit_amounts=(), deposit_term_days=())
        self.assertEqual(a.quotes(grid), [])
        self.assertEqual(session.calls, [], "robots engelinde istek atılmamalı")
        self.assertTrue(all(f["reason"] == "robots disallow" for f in a.failures))


class TestAlbarakaAdapter(unittest.TestCase):
    CATALOG_PAGE = (
        "<html><body><script>var x = "
        '{&quot;ProductCode&quot;:&quot;KONTKRD&quot;,'
        '&quot;ProductParCode&quot;:&quot;1&quot;,'
        '&quot;ProjectParCode&quot;:null,'
        '&quot;ProjectCode&quot;:&quot;YOKKNTF&quot;,'
        '&quot;CampaingCode&quot;:&quot;YKKNT0B&quot;,'
        '&quot;CampaignName&quot;:&quot;İLK EVİM KONUT FİNANSMANI&quot;,'
        '&quot;profitRate&quot;:3.04,&quot;JsonData&quot;:null,'
        '&quot;AmountMinValue&quot;:1.0,&quot;AmountMaxValue&quot;:9999999.0,'
        '&quot;MaturityMinValue&quot;:1,&quot;MaturityMaxValue&quot;:120,'
        '&quot;Selected&quot;:true,&quot;ApplicationName&quot;:null,'
        '&quot;ApplicationLink&quot;:null,&quot;DetailTitle&quot;:null,'
        '&quot;DetailInformation&quot;:null,&quot;XkampMinAmount&quot;:0.0,'
        '&quot;XkampMaxAmount&quot;:0.0,&quot;XkampMinAmountManuel&quot;:0.0,'
        '&quot;XkampMaxAmountManuel&quot;:9999999.0}'
        "</script></body></html>"
    )

    def _adapter(self, robots=_AllowAll):
        url = AlbarakaAdapter.BASE + AlbarakaAdapter.CALC_PAGE
        fetcher = _Fetcher(_Session({}), html_pages={url: self.CATALOG_PAGE})
        return AlbarakaAdapter(fetcher, robots=robots())

    def test_gomulu_katalog_okunur(self):
        a = self._adapter()
        qs = a.quotes(RateGrid())
        self.assertEqual(len(qs), 1)
        q = qs[0]
        self.assertEqual(q.kind, KIND_FINANCING)
        self.assertEqual(q.monthly_rate, 3.04)
        self.assertEqual(q.term_months, 120)
        self.assertEqual(q.product_code, "KONTKRD/YKKNT0B")
        self.assertEqual(q.product_name, "İLK EVİM KONUT FİNANSMANI")
        self.assertEqual(q.method, METHOD_RATE_CATALOG)
        self.assertIn("ÜST SINIR", q.note or "",
                      "tutar/vade'nin üst sınır olduğu belirtilmeli")

    def test_katilma_hesabi_toplanmadigi_raporlanir(self):
        """robots sınırı sessizce geçilmemeli, gerekçesi rapora yazılmalı."""
        a = self._adapter()
        a.quotes(RateGrid())
        self.assertTrue(any("katilma hesabi orani TOPLANMADI" in n
                            for n in a.notes), a.notes)

    def test_kinds_katilma_iddia_etmez(self):
        self.assertEqual(AlbarakaAdapter.kinds, (KIND_FINANCING,))

    def test_robots_disallow_sayfa_cekilmez(self):
        a = self._adapter(robots=_DenyAll)
        self.assertEqual([q for q in a.quotes(RateGrid())], [])
        self.assertTrue(a.failures)


class TestAjaxHeaderTrap(unittest.TestCase):
    """AJAX başlığı olmayan istekte 200 + HTML gelir; bu JSON sayılmamalı."""

    def test_html_yaniti_json_sayilmaz(self):
        session = _Session({"anything": _Resp(200, {"ok": True})},
                           require_ajax=True)
        a = EmlakKatilimAdapter(_Fetcher(session), robots=_AllowAll())
        got = a._get_json("https://x.test/anything", ajax=False)
        self.assertIsNone(got)
        self.assertTrue(any("JSON degil" in f["reason"] for f in a.failures),
                        a.failures)

    def test_ajax_basligiyla_json_gelir(self):
        session = _Session({"anything": _Resp(200, {"ok": True})},
                           require_ajax=True)
        a = EmlakKatilimAdapter(_Fetcher(session), robots=_AllowAll())
        got = a._get_json("https://x.test/anything", ajax=True)
        self.assertEqual(got, {"ok": True})


class _FakeDriver:
    """`_PlaywrightDriver` ikizi — tarayıcı olmadan adaptör mantığını test eder."""

    def __init__(self, results, start_error=None):
        self.results = results          # url -> sonuç (dict | str)
        self.start_error = start_error
        self.calls: list[tuple[str, object]] = []
        self.closed = False

    def start(self):
        return self.start_error

    def quote(self, url, term=None):
        self.calls.append((url, term))
        r = self.results.get(url, "hesaplama araci bulunamadi")
        return r(term) if callable(r) else r

    def close(self):
        self.closed = True


class TestKuveytTurkBrowserAdapter(unittest.TestCase):
    URL = (KuveytTurkBrowserAdapter.BASE
           + KuveytTurkBrowserAdapter.PRODUCT_PAGES[0][0])

    def _adapter(self, driver, robots=_AllowAll):
        a = KuveytTurkBrowserAdapter(_Fetcher(_Session({})), robots=robots(),
                                     browser=driver)
        a.PRODUCT_PAGES = ((KuveytTurkBrowserAdapter.PRODUCT_PAGES[0][0],
                            "Konut Finansmanı"),)
        return a

    def test_playwright_yoksa_zarifce_atlar(self):
        d = _FakeDriver({}, start_error="playwright kurulu degil")
        a = self._adapter(d)
        self.assertEqual(a.quotes(RateGrid()), [])
        self.assertTrue(any("playwright kurulu degil" in n for n in a.notes))

    def test_sayfanin_kullandigi_girdiyle_etiketlenir(self):
        """Kayıt istenen değerle DEĞİL, sayfanın hesapladığı değerle etiketlenir."""
        d = _FakeDriver({self.URL: {
            "monthly_rate": "%2,9900", "annual_cost_rate": "%65,5966",
            "installment": "3.079,76 TL", "total_payment": "369.577,03 TL",
            "total_expense": "28.720,00 TL",
            "used_amount": "100.000,00 TL", "used_term": "120",
            "fees": {"tahsis": "575,00 TL", "ipotek": "4.500,00 TL"},
        }})
        a = self._adapter(d)
        qs = a.quotes(RateGrid(financing_terms=(), max_requests=5))
        self.assertEqual(len(qs), 1)
        q = qs[0]
        self.assertEqual(q.monthly_rate, 2.99)
        self.assertEqual(q.amount, 100_000.0, "sayfanın kullandığı tutar")
        self.assertEqual(q.term_months, 120, "sayfanın kullandığı vade")
        self.assertEqual(q.installment, 3079.76)
        self.assertEqual(q.fees["tahsis"], 575.0)
        self.assertIn("SAYFANIN kullandigi", q.note or "")

    def test_diyalog_girdiyi_yansitmazsa_kayit_dusurulur(self):
        """Kanıtsız sayı yazmak yasak: tutar/vade okunamazsa kayıt olmaz."""
        d = _FakeDriver({self.URL: {"monthly_rate": "%2,9900"}})
        a = self._adapter(d)
        self.assertEqual(a.quotes(RateGrid(financing_terms=())), [])
        self.assertTrue(any(f["reason"] == "girdi dogrulanamadi"
                            for f in a.failures), a.failures)

    def test_oran_sifirsa_kayit_uydurulmaz(self):
        d = _FakeDriver({self.URL: {
            "monthly_rate": "%0", "used_amount": "1.000,00 TL",
            "used_term": "48"}})
        a = self._adapter(d)
        self.assertEqual(a.quotes(RateGrid(financing_terms=())), [])
        self.assertTrue(any("UYDURULMADI" in n for n in a.notes), a.notes)

    def test_ayni_nokta_bir_kez_kaydedilir(self):
        """Vade zorlaması oturmazsa sayfa aynı noktayı döndürür; tekilleştirilir."""
        d = _FakeDriver({self.URL: {
            "monthly_rate": "%2,9900", "used_amount": "100.000,00 TL",
            "used_term": "120"}})
        a = self._adapter(d)
        qs = a.quotes(RateGrid(financing_terms=(36, 60), max_requests=9))
        self.assertEqual(len(qs), 1, "aynı (tutar, vade) noktası tek kayıt olmalı")
        self.assertGreaterEqual(len(d.calls), 3, "vade varyasyonları denenmeli")

    def test_istenen_vade_oturmazsa_sessizce_atlanir(self):
        """Vade tutmadıysa hata değil: varsayılan nokta zaten alınmıştır."""
        def result(term):
            return {"monthly_rate": "%2,9900", "used_amount": "100.000,00 TL",
                    "used_term": "120"}  # istenen vade ne olursa olsun 120
        d = _FakeDriver({self.URL: result})
        a = self._adapter(d)
        qs = a.quotes(RateGrid(financing_terms=(36,), max_requests=5))
        self.assertEqual(len(qs), 1)
        self.assertEqual(a.failures, [], "oturmayan vade başarısızlık sayılmamalı")

    def test_robots_disallow_tarayici_surulmez(self):
        d = _FakeDriver({self.URL: {"monthly_rate": "%2,99"}})
        a = self._adapter(d, robots=_DenyAll)
        self.assertEqual(a.quotes(RateGrid()), [])
        self.assertEqual(d.calls, [], "robots engelinde sayfa açılmamalı")

    def test_surucu_her_durumda_kapatilir(self):
        d = _FakeDriver({self.URL: "hata"})
        a = self._adapter(d)
        a.quotes(RateGrid(financing_terms=()))
        self.assertTrue(d.closed, "tarayıcı sızdırılmamalı")


TF_PAGE = """
<html><body>
<div class="tab-wrapper karoranlari">
  <ul><li><a>TL</a></li><li><a>USD</a></li><li><a>YAU</a></li></ul>
  <div class="tab-content">
    <div class="tab-item"><table>
      <tr><th>Katılma Hesabı</th><th>1 Ay (%)</th><th>1 Yıl (%)</th>
          <th>1 Yıldan Uzun Vade (%)</th></tr>
      <tr><td>250-100,000,000</td><td>28.03</td><td>31.29</td><td>31.30</td></tr>
    </table></div>
    <div class="tab-item"><table>
      <tr><th>Katılma Hesabı</th><th>1 Ay (%)</th><th>1 Yıl (%)</th>
          <th>1 Yıldan Uzun Vade (%)</th></tr>
      <tr><td>250-9,999,999</td><td>0.61</td><td>0.61</td><td>-</td></tr>
    </table></div>
    <div class="tab-item"><table>
      <tr><th>Katılma Hesabı</th><th>1 Ay (%)</th><th>1 Yıl (%)</th>
          <th>1 Yıldan Uzun Vade (%)</th></tr>
      <tr><td>50 gr.</td><td>0.04</td><td>0.04</td><td>-</td></tr>
    </table></div>
  </div>
</div></body></html>
"""


class TestEnglishNumberParsing(unittest.TestCase):
    """TF tabloları İNGİLİZCE biçim kullanıyor; TR ayrıştırıcı bunları bozar."""

    def test_binlik_virgul_ondalik_nokta(self):
        self.assertEqual(_num_en("100,000,000"), 100_000_000.0)
        self.assertEqual(_num_en("28.03"), 28.03)
        self.assertEqual(_num_en("5,000 gr."), 5000.0)

    def test_tr_ayristirici_ile_farki_belgeleniyor(self):
        """`_num` (TR) '100,000,000' değerini DOĞRU çeviremez — bu yüzden ayrı."""
        self.assertNotEqual(_num("100,000,000"), 100_000_000.0)
        self.assertEqual(_num_en("100,000,000"), 100_000_000.0)

    def test_tire_none(self):
        self.assertIsNone(_num_en("-"))


class TestTurkiyeFinansTableAdapter(unittest.TestCase):
    def _adapter(self, page: str = TF_PAGE, robots=_AllowAll):
        pages = {TurkiyeFinansTableAdapter.BASE + p: page
                 for p, _ in TurkiyeFinansTableAdapter.PAGES}
        return TurkiyeFinansTableAdapter(
            _Fetcher(_Session({}), html_pages=pages), robots=robots())

    def test_para_birimi_sekmeden_dogru_eslenir(self):
        """EN KRİTİK: sekme tespit edilmezse USD %0,61 ile TL %28,03 karışır."""
        qs = self._adapter().quotes(RateGrid())
        by_cur = {}
        for q in qs:
            by_cur.setdefault(q.currency, []).append(q)
        self.assertEqual(set(by_cur), {"TRY", "USD", "XAU"})
        self.assertEqual(by_cur["TRY"][0].gross_annual_rate, 28.03)
        self.assertEqual(by_cur["USD"][0].gross_annual_rate, 0.61)
        self.assertEqual(by_cur["XAU"][0].gross_annual_rate, 0.04)

    def test_altin_tutari_gram_olarak_isaretlenir(self):
        qs = [q for q in self._adapter().quotes(RateGrid()) if q.currency == "XAU"]
        self.assertTrue(qs)
        self.assertEqual(qs[0].amount, 50.0)
        self.assertEqual(qs[0].amount_unit, "gram",
                         "gram TL ile kıyaslanmamalı (§17)")

    def test_tutar_dilimi_alt_ve_ust_sinir(self):
        q = next(q for q in self._adapter().quotes(RateGrid())
                 if q.currency == "TRY")
        self.assertEqual(q.amount, 250.0)
        self.assertEqual(q.amount_max, 100_000_000.0)
        self.assertIsNone(q.amount_unit, "TL diliminde birim işareti olmamalı")

    def test_tire_olan_vade_kaydedilmez(self):
        """'-' oran yayımlanmamış demek; 0 ya da uydurma değer yazılmamalı.

        Fixture'da USD tablosunun 3 vade sütunundan biri '-'. Adaptör iki TF
        sayfasını da tarar (`PAGES`) ve ikisi ayrı kaynaktır — bu yüzden sayım
        SAYFA BAŞINA yapılır.
        """
        usd = [q for q in self._adapter().quotes(RateGrid())
               if q.currency == "USD"]
        per_page = len(usd) / len(TurkiyeFinansTableAdapter.PAGES)
        self.assertEqual(per_page, 2, "'-' sütunu kayıt üretmemeli")
        self.assertTrue(all(q.gross_annual_rate for q in usd),
                        "hiçbir kayıt 0/None oran taşımamalı")

    def test_uzun_vade_ay_uydurmaz(self):
        q = next(q for q in self._adapter().quotes(RateGrid())
                 if q.currency == "TRY" and q.gross_annual_rate == 31.30)
        self.assertIsNone(q.term_months, "'1 yıldan uzun' vadeye ay atanmamalı")
        self.assertIn("üst sınır yok", q.note or "")

    def test_vade_basliklari_aya_cevrilir(self):
        terms = {q.term_months for q in self._adapter().quotes(RateGrid())
                 if q.currency == "TRY"}
        self.assertIn(1, terms)
        self.assertIn(12, terms, "'1 Yıl' → 12 ay")

    def test_sekme_panel_sayisi_uyusmazsa_atlanir(self):
        """Para birimi UYDURMAK yerine tablo atlanır."""
        bad = TF_PAGE.replace("<li><a>YAU</a></li>", "")
        a = self._adapter(page=bad)
        qs = a.quotes(RateGrid())
        self.assertEqual(qs, [])
        self.assertTrue(any("para birimi belirlenemedi" in n for n in a.notes),
                        a.notes)

    def test_yontem_etiketi(self):
        q = self._adapter().quotes(RateGrid())[0]
        self.assertEqual(q.method, METHOD_RATE_TABLE)
        self.assertEqual(q.kind, KIND_PROFIT_SHARE)

    def test_robots_disallow_sayfa_cekilmez(self):
        a = self._adapter(robots=_DenyAll)
        self.assertEqual(a.quotes(RateGrid()), [])
        self.assertTrue(a.failures)


class TestVakifBlockedAdapter(unittest.TestCase):
    """robots.txt engeli SESSİZ kalmamalı; gerekçe rapora yazılmalı."""

    def test_kayit_uretmez_ama_gerekce_yazar(self):
        a = VakifKatilimBlockedAdapter(_Fetcher(_Session({})), robots=_AllowAll())
        self.assertEqual(a.quotes(RateGrid()), [])
        self.assertEqual(a.requests, 0, "engelli kaynağa istek atılmamalı")
        note = " ".join(a.notes)
        self.assertIn("TOPLANMADI", note)
        self.assertIn("/documents/", note, "engellenen yol belirtilmeli")
        self.assertIn("manual/", note, "şartname §5.1 alternatifi belirtilmeli")

    def test_hicbir_tur_iddia_etmez(self):
        self.assertEqual(VakifKatilimBlockedAdapter.kinds, ())


class TestRegistryAndSerialization(unittest.TestCase):
    def test_adaptor_kaydi(self):
        self.assertIn("albaraka", available_slugs())
        self.assertIn("turkiye-emlak-katilim", available_slugs())
        self.assertIs(adapter_for("albaraka"), AlbarakaAdapter)
        self.assertIsNone(adapter_for("bilinmeyen-banka"))

    def test_jsonl_null_alanlari_atar(self):
        q = RateQuote(bank_slug="b", kind=KIND_FINANCING, monthly_rate=1.89)
        line = json.loads(quotes_to_jsonl([q]).strip())
        self.assertEqual(line["monthly_rate"], 1.89)
        self.assertNotIn("gross_annual_rate", line,
                         "boş alan JSONL'e yazılmamalı (halüsinasyon yasağı)")
        self.assertEqual(line["currency"], "TRY")

    def test_max_requests_emniyet_supabi(self):
        loan = {"Success": True, "Data": {
            "ProfitRate": 4.29, "TotalInstallmentAmount": 999_999_999,
            "InstallmentContractList": [],
        }}
        session = _Session({"CalculateLoansProduct": _Resp(200, loan)})
        a = EmlakKatilimAdapter(_Fetcher(session), robots=_AllowAll())
        grid = RateGrid(financing_amounts=(1, 2, 3), financing_terms=(1, 2, 3),
                        deposit_amounts=(), deposit_term_days=(), max_requests=4)
        a.quotes(grid)
        self.assertLessEqual(a.requests, 4)


if __name__ == "__main__":
    unittest.main()
