"""Belgeler arası çelişki tespiti + yanlış-pozitif korumaları.

İlgili: ../src/comparison/contradiction.py
        ../src/comparison/scan.py
        CLAUDE.md §18 (yenilikçilik hedefi #2), §17 (adil kıyas)

Bu dosyanın omurgası **yanlış pozitif** testleridir. Modülün değeri bulduğu
çelişki sayısında değil, bulduklarının gerçek olmasındadır: jüri önünde bir
hayalet çelişki on gerçek çelişkiden çok zarar verir. Her koruma, 849 belgelik
gerçek korpusta ÖLÇÜLMÜŞ bir hayalet kaynağını kapatır ve testi o gerçek
metinden türetilmiştir.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.comparison.contradiction import (  # noqa: E402
    MAX_SCOPE_CHARS,
    detect,
    detect_across,
    end_date_claims,
    group_by_product,
    product_key,
)
from src.extraction.rules.extract import extract_all  # noqa: E402
from src.schemas import Campaign, ExtractedField, Extractor  # noqa: E402

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def _campaign(text: str, *, bank: str = "test", url: str | None = None) -> Campaign:
    return Campaign(bank_slug=bank, raw_text=text, source_url=url,
                    fields=extract_all(text))


def _field(name: str, value, *, raw: str = "", start=None, end=None) -> ExtractedField:
    return ExtractedField(name, raw, value, 0.9, "", Extractor.RULE,
                          span_start=start, span_end=end)


# --------------------------------------------------------------------------- #
# 1) Kapsam koruması — "masrafsız" iddiası ile ücret aynı şey hakkında mı?
# --------------------------------------------------------------------------- #

class TestKapsamKorumasi(unittest.TestCase):
    """Gerçek korpus hayaleti: iki iddia aynı sayfada ama farklı hizmet hakkında."""

    def test_uzak_span_celiski_saymaz(self):
        # GERÇEK HAYALET (hayat-finans/products/urun-ve-hizmet-ucretleri.txt):
        # "Havale TL ... Ücretsizdir" (offset 152) ile "Finansman Tahsis Ücreti
        # TL %0,25" (offset 2524) — 2.372 karakter arayla, FARKLI hizmetler.
        # Eski kod bunu korpustaki TEK çelişki olarak raporluyordu.
        c = Campaign(bank_slug="hayat-finans", raw_text="x" * 4000, fields=[
            _field("masraf_durumu", {"has_fee": False, "amount": 0.0},
                   raw="Ücretsizdir", start=152, end=163),
            _field("tahsis_ucreti", {"value": 0.25, "currency": "TRY"},
                   raw="%0,25", start=2524, end=2529),
        ])
        self.assertEqual(detect(c), [])

    def test_yakin_span_celiski_sayar(self):
        c = Campaign(bank_slug="x", raw_text="y" * 200, fields=[
            _field("masraf_durumu", {"has_fee": False, "amount": 0.0},
                   raw="masrafsız", start=10, end=19),
            _field("tahsis_ucreti", {"value": 500.0, "currency": "TRY"},
                   raw="500 TL", start=40, end=46),
        ])
        self.assertEqual([k.kind for k in detect(c)], ["masrafsiz_ama_ucret"])

    def test_esik_sinirinda_davranis(self):
        for gap, expected in ((MAX_SCOPE_CHARS - 10, 1), (MAX_SCOPE_CHARS + 10, 0)):
            c = Campaign(bank_slug="x", raw_text="y" * 5000, fields=[
                _field("masraf_durumu", {"has_fee": False, "amount": 0.0},
                       raw="masrafsız", start=0, end=9),
                _field("tahsis_ucreti", {"value": 500.0, "currency": "TRY"},
                       raw="500 TL", start=9 + gap, end=15 + gap),
            ])
            self.assertEqual(len(detect(c)), expected, f"gap={gap}")

    def test_offset_yoksa_reddetmez(self):
        # Sentetik/LLM verisinde offset olmayabilir; kanıt yoksa suçlama da yok.
        c = Campaign(bank_slug="x", raw_text="masrafsız ama tahsis ücreti 500 TL",
                     fields=[
                         _field("masraf_durumu", {"has_fee": False, "amount": 0.0}),
                         _field("tahsis_ucreti", {"value": 500.0, "currency": "TRY"}),
                     ])
        self.assertEqual([k.kind for k in detect(c)], ["masrafsiz_ama_ucret"])


class TestOranBicimliUcret(unittest.TestCase):
    """Tahsis ücreti oran tablosundan `{"rate": X}` olarak da gelebilir."""

    def test_oran_bicimli_ucret_gorulur(self):
        # Eski `_positive` yalnız "value"/"amount" anahtarlarına bakıyordu;
        # oran tablosundan gelen ücret (%0,50) sessizce yok sayılıyordu.
        c = Campaign(bank_slug="x", raw_text="z" * 100, fields=[
            _field("masraf_durumu", {"has_fee": False, "amount": 0.0},
                   raw="masrafsız", start=0, end=9),
            _field("tahsis_ucreti", {"rate": 0.5}, raw="%0,50", start=20, end=25),
        ])
        cons = detect(c)
        self.assertEqual([k.kind for k in cons], ["masrafsiz_ama_ucret"])
        self.assertIn("%0.5", cons[0].detail)

    def test_sifir_oran_celiski_degil(self):
        c = Campaign(bank_slug="x", raw_text="z" * 100, fields=[
            _field("masraf_durumu", {"has_fee": False, "amount": 0.0},
                   raw="masrafsız", start=0, end=9),
            _field("tahsis_ucreti", {"rate": 0.0}, raw="%0", start=20, end=22),
        ])
        self.assertEqual(detect(c), [])


# --------------------------------------------------------------------------- #
# 2) Kampanya geçerlilik tarihi iddiaları
# --------------------------------------------------------------------------- #

# GERÇEK KORPUS ÖRNEĞİ — albaraka/live/detay-temmuz-ayina-ozel-fatura-kampanyasi.txt
# Sayfa başında "01.07.2026 - 31.07.2026", koşullarda "31 Temmuz 2027". Bir yıl fark.
ALBARAKA_TEMMUZ = (
    "Temmuz Ayına Özel Fatura Kampanyası Anasayfa Kampanyalar "
    "Kampanya Başlangıç ve Bitiş 01.07.2026 - 31.07.2026 Müşteri Ol "
    "Kampanya Şartları: Kampanya müşteri bazındadır. "
    "Verilen talimatlar için 31 Ağustos 2026 tarihine kadar ilgili fatura "
    "ödemesinin en az bir kez kredi kartından otomatik tahsil edilmesi "
    "gerekmektedir. "
    "Kampanya 31 Temmuz 2027 tarihine kadar geçerlidir."
)

# GERÇEK KORPUS ÖRNEĞİ — albaraka/live/detay-arzumda-25-indirim.txt
ALBARAKA_ARZUM = (
    "Arzum'da %25 İndirim! Anasayfa Kampanyalar Detay "
    "Kampanya Koşulları Kampanyada www.arzum.com.tr web sitesinden yapacağınız "
    "alışverişlerde %25 indirim uygulanacaktır. "
    "Kampanya 31.12.2025 tarihine kadar geçerlidir."
)


class TestBitisTarihiIddiasi(unittest.TestCase):
    def test_yalniz_kampanya_gecerliligi_sayilir(self):
        # "31 Ağustos 2026 tarihine kadar ... tahsil edilmesi gerekmektedir"
        # bir YÜKÜMLÜLÜK tarihidir, kampanya geçerliliği değil — alınmamalı.
        isos = [c.iso for c in end_date_claims(ALBARAKA_TEMMUZ)]
        self.assertEqual(isos, ["2026-07-31", "2027-07-31"])

    def test_belge_ici_celisen_bitis(self):
        c = _campaign(ALBARAKA_TEMMUZ, bank="albaraka",
                      url="https://www.albaraka.com.tr/tr/kampanyalar/detay/"
                          "temmuz-ayina-ozel-fatura-kampanyasi")
        cons = [k for k in detect(c) if k.kind == "celisen_kampanya_bitisi"]
        self.assertEqual(len(cons), 1)
        self.assertEqual({e.value for e in cons[0].evidence},
                         {"2026-07-31", "2027-07-31"})
        # Her iki taraf da kaynağını taşımalı (jüri "nereden biliyorsun" sorar).
        for e in cons[0].evidence:
            self.assertTrue(e.source_url)
            self.assertTrue(e.source_span)
            self.assertIsNotNone(e.span_start)

    def test_tutarli_tarih_celiski_uretmez(self):
        text = ("Kampanya Başlangıç ve Bitiş 01.07.2026 - 31.07.2026 "
                "Kampanya 31.07.2026 tarihine kadar geçerlidir.")
        self.assertEqual(detect(_campaign(text)), [])


class TestSuresiDolmusKampanya(unittest.TestCase):
    URL = "https://www.albaraka.com.tr/tr/kampanyalar/detay/arzumda-25-indirim"

    def test_suresi_dolmus_yakalanir(self):
        c = _campaign(ALBARAKA_ARZUM, bank="albaraka", url=self.URL)
        cons = [k for k in detect(c, as_of="2026-07-30")
                if k.kind == "suresi_dolmus_kampanya"]
        self.assertEqual(len(cons), 1)
        self.assertEqual(cons[0].evidence[0].value, "2025-12-31")

    def test_as_of_verilmezse_kural_kapali(self):
        # Varsayılan kapalı: çıktının tarama gününe göre sessizce değişmemesi
        # için (demo yeniden-üretilebilirliği, CLAUDE.md §11).
        c = _campaign(ALBARAKA_ARZUM, bank="albaraka", url=self.URL)
        self.assertEqual(detect(c), [])

    def test_suresi_gecmemis_kampanya_temiz(self):
        c = _campaign(ALBARAKA_ARZUM, bank="albaraka", url=self.URL)
        self.assertEqual(detect(c, as_of="2025-06-01"), [])

    def test_banka_kendisi_bitti_diyorsa_celiski_yok(self):
        # GERÇEK HAYALET: Dünya Katılım şablonu damgayı sayfa SONUNA koyuyor
        # ("Kart Kampanyaları Sona erdi Bitiş Tarihi: 30 Nisan 2026").
        # Banka dürüst davranmış — çelişki değil.
        text = ALBARAKA_ARZUM + " Kart Kampanyaları Sona erdi Bitiş Tarihi: 31 Aralık 2025"
        self.assertEqual(detect(_campaign(text, url=self.URL), as_of="2026-07-30"), [])

    def test_arsiv_sayfasi_celiski_degil(self):
        url = ("https://www.kuveytturk.com.tr/kampanyalar/kampanya-arsivi/"
               "eski-bir-kampanya")
        self.assertEqual(detect(_campaign(ALBARAKA_ARZUM, url=url),
                                as_of="2026-07-30"), [])

    def test_kampanya_olmayan_sayfa_kural_disi(self):
        url = "https://www.albaraka.com.tr/tr/finansmanlar/konut-finansmani"
        self.assertEqual(detect(_campaign(ALBARAKA_ARZUM, url=url),
                                as_of="2026-07-30"), [])

    def test_liste_sayfasi_tumu_icin_hukum_vermez(self):
        # GERÇEK HAYALET (tom-katilim/live/kampanyalar.txt): 4 kampanyalık liste.
        # Biri süresi dolmuş diye sayfanın tamamı "süresi dolmuş" sayılamaz.
        text = ("Kampanyalar "
                "Kampanya Koşulları Kampanya 26 Aralık 2025 - 25 Mart 2026 "
                "tarihleri arasında yapılacak harcamalarda geçerlidir. "
                "Kampanya Koşulları Kampanya 19.01.2026 - 30.09.2026 tarihleri "
                "arasında yapılacak ödemelerde geçerlidir.")
        url = "https://www.tombank.com.tr/kampanyalar.html"
        cons = [k for k in detect(_campaign(text, url=url), as_of="2026-07-30")
                if k.kind == "suresi_dolmus_kampanya"]
        self.assertEqual(cons, [])

    def test_ayni_pencere_iki_kez_yazilmis_liste_degildir(self):
        # GERÇEK VAKA (albaraka/live/detay-roamy-esimden-50-indirim.txt):
        # üstte "1 Ağustos – 31 Aralık 2025", koşullarda "01.08.2025-31.12.2025".
        # Aynı pencere, iki yazım — bu bir liste DEĞİL.
        text = ("Roamy eSIM'den %50 İndirim Anasayfa Kampanyalar Detay "
                "Kampanya Detayları 1 Ağustos – 31 Aralık 2025 "
                "Kampanya Koşulları: Kampanya 01.08.2025-31.12.2025 tarihleri "
                "arasında geçerli olacaktır.")
        url = ("https://www.albaraka.com.tr/tr/kampanyalar/detay/"
               "roamy-esimden-50-indirim")
        cons = [k for k in detect(_campaign(text, url=url), as_of="2026-07-30")
                if k.kind == "suresi_dolmus_kampanya"]
        self.assertEqual(len(cons), 1)


# --------------------------------------------------------------------------- #
# 3) Ürün eşleştirme — yanlış eşleştirme hayalet çelişki üretir
# --------------------------------------------------------------------------- #

class TestUrunEslestirme(unittest.TestCase):
    def test_url_yapragi_anahtar_olur(self):
        c = _campaign("x", url="https://www.vakifkatilim.com.tr/tr/kendim-icin/"
                                "finansmanlar/konut-finansmani")
        self.assertEqual(product_key(c), "konut-finansmani")

    def test_gezinme_parcalari_atilir(self):
        # Yaprak "detay" olsaydı onlarca alakasız kampanya aynı ürün sanılırdı.
        c = _campaign("x", url="https://www.vakifkatilim.com.tr/tr/kendim-icin/"
                                "kampanyalar/detay")
        self.assertIsNone(product_key(c))

    def test_surum_soneki_kirpilir(self):
        a = _campaign("x", url="https://b.com/kampanyalar/detay/n11-indirim")
        b = _campaign("y", url="https://b.com/kampanyalar/detay/n11-indirim_1")
        c = _campaign("z", url="https://b.com/kampanyalar/detay/n11-indirim-2")
        self.assertEqual(product_key(a), product_key(b))
        self.assertEqual(product_key(a), product_key(c))

    def test_uzanti_atilir(self):
        c = _campaign("x", url="https://www.tombank.com.tr/kampanyalar.html")
        self.assertIsNone(product_key(c))  # "kampanyalar" gezinme parçası

    def test_cok_kisa_yaprak_reddedilir(self):
        # 8 karakterden kısa yaprak fazla jenerik; eşleştirmeye güvenilmez.
        c = _campaign("x", url="https://b.com/urunler/kart")
        self.assertIsNone(product_key(c))

    def test_fixture_ve_urlsiz_belge_eslesmez(self):
        self.assertIsNone(product_key(_campaign("x")))
        self.assertIsNone(product_key(_campaign("x", url="file:///tmp/a.txt")))

    def test_grup_ayni_metni_tekiller(self):
        # Korpusta 32 çift belge aynı URL'i paylaşıyor ve metinleri byte-özdeş;
        # bunları "iki farklı sayfa" saymak yanıltıcı olurdu.
        url = "https://b.com/finansmanlar/konut-finansmani"
        same = [_campaign("aynı metin", bank="b", url=url) for _ in range(3)]
        self.assertEqual(group_by_product(same), {})

    def test_farkli_banka_ayni_urun_gruplanmaz(self):
        # Farklı bankaların aynı ürünü ÇELİŞMEZ, rekabet eder (CLAUDE.md §17).
        a = _campaign("A metni", bank="banka-a",
                      url="https://a.com/finansmanlar/konut-finansmani")
        b = _campaign("B metni", bank="banka-b",
                      url="https://b.com/finansmanlar/konut-finansmani")
        self.assertEqual(group_by_product([a, b]), {})


# --------------------------------------------------------------------------- #
# 4) Belgeler arası kurallar
# --------------------------------------------------------------------------- #

def _rate_page(bank: str, slug: str, body: str, rate) -> Campaign:
    return Campaign(
        bank_slug=bank, raw_text=body,
        source_url=f"https://{bank}.com.tr/finansmanlar/{slug}",
        fields=[_field("kar_payi_orani", rate, raw=str(rate))],
    )


class TestCaprazKarPayi(unittest.TestCase):
    def test_ayni_urun_farkli_oran_yakalanir(self):
        a = _rate_page("x", "konut-finansmani", "A sayfası", 1.89)
        b = _rate_page("x", "konut-finansmani", "B sayfası", 2.49)
        cons = detect_across([a, b])
        self.assertEqual([k.kind for k in cons], ["capraz_kar_payi_uyusmazligi"])
        self.assertEqual(cons[0].scope, "cross")
        self.assertEqual(cons[0].match_key, "x/konut-finansmani")
        self.assertEqual({e.value for e in cons[0].evidence}, {1.89, 2.49})
        self.assertEqual({e.source_url for e in cons[0].evidence},
                         {a.source_url, b.source_url})

    def test_ayni_deger_farkli_yazim_celiski_degil(self):
        # "%1,89" ve "1.89%" normalizasyondan sonra AYNI değerdir.
        a = _rate_page("x", "konut-finansmani", "A sayfası", 1.89)
        b = _rate_page("x", "konut-finansmani", "B sayfası", 1.890)
        self.assertEqual(detect_across([a, b]), [])

    def test_aralik_icindeki_nokta_deger_celiski_degil(self):
        # %1,89–2,49 aralığı içindeki %2,00 tutarlıdır.
        a = _rate_page("x", "konut-finansmani", "A sayfası",
                       {"min": 1.89, "max": 2.49})
        b = _rate_page("x", "konut-finansmani", "B sayfası", 2.00)
        self.assertEqual(detect_across([a, b]), [])

    def test_kesisen_araliklar_celiski_degil(self):
        a = _rate_page("x", "konut-finansmani", "A", {"min": 1.89, "max": 2.49})
        b = _rate_page("x", "konut-finansmani", "B", {"min": 2.40, "max": 3.10})
        self.assertEqual(detect_across([a, b]), [])

    def test_kesismeyen_araliklar_celiskidir(self):
        a = _rate_page("x", "konut-finansmani", "A", {"min": 1.89, "max": 2.49})
        b = _rate_page("x", "konut-finansmani", "B", {"min": 3.40, "max": 4.10})
        self.assertEqual([k.kind for k in detect_across([a, b])],
                         ["capraz_kar_payi_uyusmazligi"])

    def test_segmente_ozel_sayfa_kiyas_disi(self):
        # GERÇEK HAYALET (Türkiye Finans ihtiyaç finansmanı): liste oranı ile
        # "banka çalışanlarına özel" kampanya oranı farklıdır — koşul farklı,
        # çelişki değil (CLAUDE.md §17 adil kıyas).
        a = _rate_page("x", "ihtiyac-finansmani", "Liste oranları", 4.09)
        b = _rate_page("x", "ihtiyac-finansmani",
                       "Banka çalışanlarına özel ihtiyaç finansmanı", 3.96)
        self.assertEqual(detect_across([a, b]), [])


class TestCaprazBitisTarihi(unittest.TestCase):
    def _page(self, slug: str, date: str, n: int) -> Campaign:
        body = ("Kampanya Koşulları Kampanya " + date + " tarihine kadar "
                "geçerlidir. Ayrıntılar için şubelerimize başvurun. Sıra no "
                + str(n))
        return Campaign(
            bank_slug="x", raw_text=body,
            source_url="https://x.com.tr/kampanyalar/detay/" + slug,
        )

    def test_ayni_kampanya_farkli_bitis(self):
        a = self._page("yaz-indirim-kampanyasi", "31.12.2026", 1)
        b = self._page("yaz-indirim-kampanyasi_1", "31.10.2026", 2)
        cons = detect_across([a, b])
        self.assertEqual([k.kind for k in cons], ["capraz_kampanya_bitisi"])
        self.assertEqual({e.value for e in cons[0].evidence},
                         {"2026-12-31", "2026-10-31"})

    def test_ayni_bitis_celiski_degil(self):
        a = self._page("yaz-indirim-kampanyasi", "31.12.2026", 1)
        b = self._page("yaz-indirim-kampanyasi_1", "31.12.2026", 2)
        self.assertEqual(detect_across([a, b]), [])

    def test_ardisik_surumler_celiski_degil(self):
        # GERÇEK HAYALET (Vakıf Katılım n11 kampanyası): aynı kampanyanın iki
        # ardışık sürümü, İKİSİ DE "Kampanya Süresi Dolmuştur" damgalı.
        a = self._page("n11-alisverisinize-300-tl-indirim", "15.11.2025", 1)
        b = self._page("n11-alisverisinize-300-tl-indirim_1", "07.01.2026", 2)
        a.raw_text += " Kampanya Süresi Dolmuştur"
        b.raw_text += " Kampanya Süresi Dolmuştur"
        self.assertEqual(detect_across([a, b]), [])


# --------------------------------------------------------------------------- #
# 5) Gerçek korpus regresyonu — hayalet alarmı
# --------------------------------------------------------------------------- #

@unittest.skipUnless(RAW_DIR.is_dir(), "data/raw yok")
class TestKorpusRegresyonu(unittest.TestCase):
    """849 gerçek belgede tespit hem BULMALI hem ABARTMAMALI.

    Ölçüm (2026-07-30 snapshot): 6 çelişki — 5 "süresi dolmuş kampanya",
    1 "belge içi çelişen bitiş tarihi". Altısı da elle doğrulandı.
    """

    @classmethod
    def setUpClass(cls):
        from src.comparison.scan import scan
        cls.found, cls.stats = scan(RAW_DIR)

    def test_bilinen_gercek_celiski_bulunur(self):
        kinds = {(rel, con.kind) for rel, con in self.found}
        self.assertIn(
            ("albaraka/live/detay-temmuz-ayina-ozel-fatura-kampanyasi.txt",
             "celisen_kampanya_bitisi"), kinds)
        self.assertIn(("albaraka/live/detay-arzumda-25-indirim.txt",
                       "suresi_dolmus_kampanya"), kinds)

    def test_hayalet_alarmi(self):
        # Korpusta 849 belge var; çelişki sayısı bir anda patlıyorsa bir koruma
        # düşmüş demektir. Ölçülen değer 6; tavan bilerek dar tutuldu.
        self.assertLessEqual(len(self.found), 12,
                             f"Beklenmedik çelişki artışı: "
                             f"{self.stats['tur_dagilimi']}")

    def test_her_celiskinin_kaniti_var(self):
        for rel, con in self.found:
            self.assertTrue(con.evidence, f"kanıtsız çelişki: {rel} {con.kind}")
            for e in con.evidence:
                self.assertTrue(e.source_url, f"kaynaksız kanıt: {rel}")
                self.assertIsNotNone(e.value)

    def test_urun_eslestirici_calisiyor(self):
        # Eşleştirici gerçekten grup kuruyor mu? (0 grup kursaydı belgeler arası
        # katman sessizce ölü olurdu — bu projede bir kez yaşanmış bir hata.)
        self.assertGreaterEqual(self.stats["eslesen_urun_grubu"], 20)


if __name__ == "__main__":
    unittest.main()
