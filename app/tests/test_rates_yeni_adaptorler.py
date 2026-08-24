"""Ziraat Katılım ve Dünya Katılım oran adaptörleri.

İlgili: ../src/scraping/rates.py (`ZiraatKatilimAdapter`, `RateAdapter._post_form`)
        test_rates.py (öteki adaptörlerin testleri, aynı sahte nesneler)

AĞSIZ: bankanın gerçek yanıtının birebir iskeleti teste gömülü. Ağa bağlı bir
test, banka sayfayı güncellediği gün kodun kusuru varmış gibi kırmızıya dönerdi.

## Bu adaptörün var olma sebebi

Ziraat Katılım korpusta 291 belge veriyor ama oran yalnız **1'inde** geçiyor
(%0,3). Banka oranı kampanya metninde değil, hesaplama aracının arkasındaki
uçta yayımlıyor. Adaptör o boşluğu kapatıyor: 17 ürün, 31 kayıt.

## Kilitlenen üç karar

1. **Ürün kimlikleri SAYFADAN okunuyor**, sabit yazılmıyor.
2. **Oransız ürün kayıt ÜRETMEZ** — `%0` bir oran değil, ölçememedir.
3. **Ödeme planı ucuna HİÇ gidilmiyor** — o uç, tek bir parametreyle
   istemcinin gönderdiği oranı gerçek banka oranıymış gibi döndürebiliyor.
"""

from __future__ import annotations

import json
import unittest

from src.scraping.rates import (
    KIND_FINANCING,
    DunyaKatilimAdapter,
    RateGrid,
    ZiraatKatilimAdapter,
)


class _Resp:
    def __init__(self, status: int, body, ctype: str = "application/json"):
        self.status_code = status
        self.headers = {"Content-Type": ctype}
        self._body = body

    def json(self):
        return json.loads(self._body) if isinstance(self._body, str) else self._body

    @property
    def text(self):
        return self._body if isinstance(self._body, str) else json.dumps(self._body)


class _Session:
    """`eid`e göre yanıt döndüren sahte oturum; POST gövdesini de kaydeder."""

    def __init__(self, yanitlar: dict[str, object]):
        self.yanitlar = yanitlar
        self.posts: list[tuple[str, dict]] = []

    def post(self, url, data=None, timeout=None, headers=None, **kw):
        self.posts.append((url, dict(data or {})))
        eid = str((data or {}).get("eid"))
        y = self.yanitlar.get(eid)
        return _Resp(200, y) if y is not None else _Resp(404, "")

    def get(self, url, timeout=None, headers=None, **kw):   # kullanılmıyor
        return _Resp(404, "")


class _Limiter:
    def wait(self, url):
        pass


class _Fetcher:
    timeout = 5.0

    def __init__(self, session, sayfa: str = ""):
        self._session = session
        self.limiter = _Limiter()
        self.sayfa = sayfa

    @property
    def available(self) -> bool:
        return True

    def fetch(self, url: str):
        from src.scraping.fetcher import FetchResult
        if not self.sayfa:
            return FetchResult(url, status=404)
        return FetchResult(url, status=200, html=self.sayfa, final_url=url)

    def close(self):
        pass


class _AllowAll:
    @staticmethod
    def allows(url):
        return True, "izin"


class _DenyAll:
    @staticmethod
    def allows(url):
        return False, "robots disallow"


# Hesaplama sayfasının seçim listesi — gerçek düzenin iskeleti.
SAYFA = """<html><body>
<select id="edit-finansman-type" name="finans_type">
  <option value="">Seçiniz</option>
  <option value="25961206">KONUT FINANSMANI (0-10.000.000 TL/1-120 AY))</option>
  <option value="64445629">TAŞIT FINANSMANI(1-48 AY)</option>
  <option value="99999999">ORANSIZ ÜRÜN</option>
</select></body></html>"""

YANITLAR = {
    "25961206": {"status": True, "data": {
        "action": "remove", "msg": "", "range": list(range(1, 121)),
        "ratio": "3.19", "maximum_amount": 9999999, "minimum_amount": "1"}},
    "64445629": {"status": True, "data": {
        "action": "remove",
        "msg": "*Fatura bedelinin azami %70'i kadar finansman kullanabilirsiniz.",
        "range": list(range(1, 49)),
        "ratio": "3.29", "maximum_amount": 279999, "minimum_amount": "1"}},
    # Oran yok: kayıt ÜRETİLMEMELİ.
    "99999999": {"status": True, "data": {
        "range": [1, 12], "ratio": "0", "maximum_amount": 1000}},
}

IZGARA = RateGrid(financing_amounts=(100000,), financing_terms=(12, 36, 60, 120),
                  deposit_amounts=(), deposit_term_days=(), max_requests=50)


def _adaptor(sayfa: str = SAYFA, robots=_AllowAll):
    return ZiraatKatilimAdapter(_Fetcher(_Session(YANITLAR), sayfa), robots=robots())


class TestUrunKesfi(unittest.TestCase):
    def test_urunler_SAYFADAN_okunur(self) -> None:
        """Sabit liste, banka ürün eklediğinde sessizce eskir."""
        a = _adaptor()
        self.assertEqual([ad for _, ad in a._urunler()],
                         ["KONUT FINANSMANI (0-10.000.000 TL/1-120 AY))",
                          "ORANSIZ ÜRÜN", "TAŞIT FINANSMANI(1-48 AY)"])

    def test_bos_secim_degeri_ATLANIR(self) -> None:
        """`value=""` bir ürün değil; eid olarak gönderilirse 404 üretirdi."""
        self.assertNotIn("", dict(_adaptor()._urunler()))

    def test_sayfa_bos_donerse_gerekce_KAYITLI(self) -> None:
        a = _adaptor(sayfa="")
        self.assertEqual(a._urunler(), [])
        self.assertTrue(any("bos dondu" in f["reason"] for f in a.failures))

    def test_desen_tutmazsa_SESSIZ_kalmaz(self) -> None:
        """Sayfa düzeni değişirse 0 kayıt döner; sebebi yazılmalı."""
        a = _adaptor(sayfa="<html><body>düzen değişti</body></html>")
        self.assertEqual(a._urunler(), [])
        self.assertTrue(any("secim listesi bulunamadi" in f["reason"]
                            for f in a.failures))


class TestOranlar(unittest.TestCase):
    def setUp(self) -> None:
        self.a = _adaptor()
        self.q = self.a.quotes(IZGARA)

    def test_oran_ve_urun_dogru(self) -> None:
        konut = [x for x in self.q if x.product_code == "25961206"]
        self.assertTrue(konut)
        self.assertEqual({x.monthly_rate for x in konut}, {3.19})
        self.assertEqual({x.kind for x in konut}, {KIND_FINANCING})

    def test_vade_urunun_ARALIGINA_kisitlanir(self) -> None:
        """Taşıt 1-48 ay; ızgaranın 60 ve 120'si dışarıda kalmalı."""
        tasit = sorted(x.term_months for x in self.q
                       if x.product_code == "64445629")
        self.assertEqual(tasit, [12, 36])

    def test_oransiz_urun_kayit_URETMEZ(self) -> None:
        """`%0` bir oran değil, ölçememedir — uydurulmaz."""
        self.assertFalse([x for x in self.q if x.product_code == "99999999"])
        self.assertTrue(any("oran DONDURMEDI" in n for n in self.a.notes))

    def test_tutar_BOS_birakilir(self) -> None:
        """Oran tutara göre değişmiyor; tek tutar yazmak olmayan bağımlılığı ima ederdi."""
        self.assertTrue(all(x.amount is None for x in self.q))
        self.assertTrue(any(x.amount_max == 9999999 for x in self.q))

    def test_ucret_UYDURULMAZ(self) -> None:
        """Banka tahsis/ekspertiz yayımlamıyor — `fees` boş kalmalı."""
        self.assertTrue(all(not x.fees for x in self.q))

    def test_bankanin_kendi_uyarisi_kayitta(self) -> None:
        tasit = next(x for x in self.q if x.product_code == "64445629")
        self.assertIn("%70", tasit.note)
        self.assertIn("bağlayıcı fiyat değildir", tasit.note)


class TestOdemePlaniUcunaGIDILMEZ(unittest.TestCase):
    """O uç, `finansman_is_bank_ratio=false` ile UYDURMA oran döndürebiliyor."""

    def test_yalniz_get_vade_cagrilir(self) -> None:
        a = _adaptor()
        a.quotes(IZGARA)
        yollar = {u for u, _ in a.fetcher._session.posts}
        self.assertEqual(yollar, {ZiraatKatilimAdapter.VADE_URL})
        self.assertFalse([u for u in yollar if "finansmanhesapla" in u])


class TestRobots(unittest.TestCase):
    def test_robots_engelliyse_istek_ATILMAZ(self) -> None:
        a = _adaptor(robots=_DenyAll)
        self.assertEqual(a.quotes(IZGARA), [])
        self.assertTrue(any(f["reason"] == "robots disallow" for f in a.failures))


if __name__ == "__main__":                   # pragma: no cover
    unittest.main()


# --------------------------------------------------------------------------- #
# Dünya Katılım — antiforgery + uydurma oran kapısı
# --------------------------------------------------------------------------- #


DK_SAYFA = """<html><body>
<input name="__RequestVerificationToken" type="hidden" value="TOKEN-123" />
<select id="loanSelect" class="data-source" name="state">
  <option value="TUKETICIIHTIYAC">T&#252;ketici &#304;htiya&#231; Finansman&#305;</option>
  <option value="KONUTTUKETICI">Konut Yeni</option>
</select></body></html>"""


class _DKSession:
    """Ürün koduna göre yanıt; gönderilen gövdeyi kaydeder."""

    def __init__(self):
        self.posts: list[dict] = []

    def post(self, url, data=None, timeout=None, headers=None, **kw):
        d = dict(data or {})
        self.posts.append(d)
        if d.get("productCode") == "KONUTTUKETICI":
            return _Resp(200, {"result": "RATEERROR",
                               "message": "Uygun bir oran tanım detayı yok"})
        return _Resp(200, {"result": "SUCCESS", "rate": 3.99,
                           "monthlyInterest": 11401.85, "totalPayment": 136822.12})

    def get(self, url, timeout=None, headers=None, **kw):
        return _Resp(404, "")


def _dk(sayfa: str = DK_SAYFA, robots=_AllowAll):
    return DunyaKatilimAdapter(_Fetcher(_DKSession(), sayfa), robots=robots())


DK_IZGARA = RateGrid(financing_amounts=(100000,), financing_terms=(12,),
                     deposit_amounts=(), deposit_term_days=(), max_requests=50)


class TestDunyaKatalog(unittest.TestCase):
    def test_token_ve_urunler_ayni_sayfadan(self) -> None:
        token, urunler = _dk()._katalog()
        self.assertEqual(token, "TOKEN-123")
        self.assertEqual([k for k, _ in urunler],
                         ["KONUTTUKETICI", "TUKETICIIHTIYAC"])

    def test_urun_adi_HTML_escape_cozulur(self) -> None:
        """Banka `&#252;` gibi kaçışlarla dönüyor; ham hâli ekranda bozuk görünürdü."""
        _, urunler = _dk()._katalog()
        self.assertIn("Tüketici İhtiyaç Finansmanı", dict(urunler).values())

    def test_token_yoksa_istek_ATILMAZ(self) -> None:
        a = _dk(sayfa="<html><body>düzen değişti</body></html>")
        self.assertEqual(a.quotes(DK_IZGARA), [])
        self.assertTrue(any("token yok" in f["reason"] for f in a.failures))


class TestDunyaUydurmaOranKapisi(unittest.TestCase):
    """`userSelected=true` gönderilirse uç KENDİ verdiğin oranı geri veriyor."""

    def test_userSelected_HER_ZAMAN_false(self) -> None:
        a = _dk()
        a.quotes(DK_IZGARA)
        for govde in a.fetcher._session.posts:
            self.assertEqual(govde["userSelected"], "false")
            self.assertEqual(govde["userRate"], "0,00")

    def test_tutar_AYRACSIZ_tamsayi(self) -> None:
        """`amount=200,000` uçta 200 TL olarak okunuyor ve SUCCESS dönüyor."""
        a = _dk()
        a.quotes(DK_IZGARA)
        for govde in a.fetcher._session.posts:
            self.assertEqual(govde["amount"], "100000")
            self.assertNotIn(",", govde["amount"])
            self.assertNotIn(".", govde["amount"])

    def test_token_her_isteğe_konur(self) -> None:
        a = _dk()
        a.quotes(DK_IZGARA)
        self.assertTrue(all(g["__RequestVerificationToken"] == "TOKEN-123"
                            for g in a.fetcher._session.posts))


class TestDunyaHataYolu(unittest.TestCase):
    def test_RATEERROR_kayit_URETMEZ(self) -> None:
        a = _dk()
        q = a.quotes(DK_IZGARA)
        self.assertEqual({x.product_code for x in q}, {"TUKETICIIHTIYAC"})
        self.assertTrue(any("RATEERROR" in n for n in a.notes))

    def test_basarili_kayit_dolu(self) -> None:
        q = _dk().quotes(DK_IZGARA)
        x = q[0]
        self.assertEqual((x.monthly_rate, x.total_payment), (3.99, 136822.12))
        self.assertFalse(x.fees, "banka ücreti bu uçtan gelmiyor — uydurulmamalı")
