"""TKBB Katılım Sözlüğü hasadı — ayrıştırma ve devam modu.

İlgili: ../scripts/tkbb_sozluk_hasat.py
        ../src/domain/terminology.py (`_ikincil_yukle` — bu çıktıyı okur)

AĞSIZ: sayfa HTML'inin birebir iskeleti teste gömülü. Hasat ucuna bağlı bir
test, ağ koptuğunda kodun kusuru varmış gibi kırmızıya dönerdi — bu oturumda
hasadın 189 id'de ağ hatası aldığı ölçüldü, yani risk gerçek.
"""

from __future__ import annotations

import unittest

from scripts.tkbb_sozluk_hasat import TABAN, ayristir

# Gerçek sayfanın iskeleti: h1 = terim, p.text-siyah = tanım, Örnekler bloğu.
HTML = """<html><body>
<nav>Anasayfa Kurumsal</nav>
<div class="flex flex-col bg-sozluk-bg bg-cover w-full">
  <div class="relative z-50 bg-[#fff]">Sonuçlar sonuç bulundu</div>
  <div class="flex flex-col justify-center">
    <h1 class="mb-[40px] text-center">murabaha</h1>
    <p class="text-siyah text-[18px]">Sermaye sağlayan finansal kurum kredi
    vermek yerine müşterinin almak istediği bir varlığı üçüncü taraftan satın
    alıp maliyetin üzerine kâr ekleyerek satar.</p>
  </div>
  <div class="flex flex-col rounded-[32px] bg-x">
    <div class="text-[24px] text-mavi">Örnekler</div>
    <div class="text-[#18181C]/40">TÜRKÇE</div>
    <span>Bunlar emek-sermaye ortaklığı (mudârabe) gibi akit çeşitlerinin
    meşruluğunu ortaya koyar ve uzun bir örnek cümlesidir.</span>
    <span>kısa</span>
  </div>
</div></body></html>"""

# Var olmayan bir id: gezinme iskeleti döner, terim yok.
BOS_HTML = """<html><body><nav>Anasayfa</nav>
<div class="flex flex-col bg-sozluk-bg">
  <div>Sonuçlar sonuç bulundu</div>
</div></body></html>"""

DUYURU_HTML = """<html><body>
<div class="bg-sozluk-bg">
  <h1>TÜRKİYE'NİN GRİ LİSTEDEN ÇIKARILMASI HAKKINDA KAMUOYU DUYURUSU</h1>
  <p class="text-siyah">Uzun bir duyuru metni buraya gelir ve tanım sanılabilir.</p>
</div></body></html>"""


class TestAyristirma(unittest.TestCase):
    def test_terim_tanim_ve_kaynak(self):
        k = ayristir(HTML, 344)
        self.assertIsNotNone(k)
        self.assertEqual(k["terim"], "murabaha")
        self.assertEqual(k["id"], "tkbb-344")
        self.assertIn("maliyetin üzerine kâr", k["tanim"])
        self.assertEqual(k["kaynak_url"], f"{TABAN}/344")
        self.assertIn("TKBB", k["kaynak_kurum"])

    def test_tanim_bosluklari_normalize_edilir(self):
        """Çok satırlı HTML tek satıra inmeli; sözlük kaydı tek paragraftır."""
        k = ayristir(HTML, 344)
        self.assertNotIn("\n", k["tanim"])
        self.assertNotIn("  ", k["tanim"])

    def test_ornekler_toplanir_kisalar_ATLANIR(self):
        k = ayristir(HTML, 344)
        self.assertEqual(len(k["ornekler"]), 1)
        self.assertIn("mudârabe", k["ornekler"][0])

    def test_terimsiz_sayfa_None(self):
        """Var olmayan id gezinme iskeleti döner — kayıt üretmemeli."""
        self.assertIsNone(ayristir(BOS_HTML, 999))

    def test_DUYURU_basligi_terim_sanilmaz(self):
        """Gürültü deseni olmadan duyuru başlığı sözlüğe girerdi."""
        self.assertIsNone(ayristir(DUYURU_HTML, 5))

    def test_konteyner_yoksa_None(self):
        self.assertIsNone(ayristir("<html><body><h1>x</h1></body></html>", 1))


class TestGetirDurumu(unittest.TestCase):
    """HTTP 500 ('kayıt yok') ile ağ kopması AYRI sayılmalı.

    İlk sürüm ikisini aynı `except`te topluyordu ve 700 id'lik hasat "189 ağ
    hatası" raporladı — oysa ölçüldü ki var olmayan id'ler HTTP 500 döndürüyor
    (id 1, 5, 50, 690) ve bu normaldir. Ayrım, tekrar koşumun gerekli olup
    olmadığını söylüyor.
    """

    def test_500_ve_404_kayit_YOK_sayilir(self):
        import urllib.error

        from scripts import tkbb_sozluk_hasat as H
        gercek = H.urllib.request.urlopen
        for kod in (404, 500):
            def _patla(*a, **k):
                raise urllib.error.HTTPError(TABAN, kod, "x", {}, None)  # noqa: B023
            H.urllib.request.urlopen = _patla
            try:
                self.assertEqual(H._getir(1)[1], "yok")
            finally:
                H.urllib.request.urlopen = gercek

    def test_baglanti_hatasi_AG_sayilir(self):
        import urllib.error

        from scripts import tkbb_sozluk_hasat as H
        gercek = H.urllib.request.urlopen

        def _patla(*a, **k):
            raise urllib.error.URLError("nodename nor servname provided")
        H.urllib.request.urlopen = _patla
        try:
            self.assertEqual(H._getir(1)[1], "ag")
        finally:
            H.urllib.request.urlopen = gercek

    def test_503_AG_sayilir(self):
        """Geçici sunucu hatası tekrar denenebilir; 'yok' değil."""
        import urllib.error

        from scripts import tkbb_sozluk_hasat as H
        gercek = H.urllib.request.urlopen

        def _patla(*a, **k):
            raise urllib.error.HTTPError(TABAN, 503, "x", {}, None)
        H.urllib.request.urlopen = _patla
        try:
            self.assertEqual(H._getir(1)[1], "ag")
        finally:
            H.urllib.request.urlopen = gercek


if __name__ == "__main__":
    unittest.main()
