"""Şartname s.11 metinleri → s.12 TABLOSU, hücre hücre.

İlgili: ../src/comparison/compare.py («Şartname Senaryo-1 tablosu» bloğu)
        ../src/api/main.py (`GET /urun-tablosu`)
        raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf s.11–12
        tests/test_sartname_vade_kalibi.py (aynı üç metnin ÇIKARIM katmanı)
        tests/test_sartname_kiyas_kalibi.py (s.13 chatbot kalıbı)

## Bu testin varlık sebebi

Şartname s.11'de üç bankanın kampanya metnini, s.12'de de o metinlerden
BEKLENEN çıktı tablosunu birebir veriyor. Jürinin elindeki tek resmî
girdi/çıktı çiftidir. `test_sartname_vade_kalibi.py` bu çiftin İKİ kolonunu
(vade, kâr payı) ÇIKARIM katmanında ölçüyor; bu test **yedi kolonun
tamamını** kıyas + uç katmanında ölçer, yani jüriye gösterilecek tablonun
kendisini.

Beklenen tablo (s.12, birebir):

    Banka      Ürün Türü         Kâr Payı  Vade    Kampanya Avantajı
               Masraf Durumu     Kampanya Süresi
    ------------------------------------------------------------------
    A Bankası  Konut finansmanı  %1,89     120 ay  50.000 TL'ye kadar
                                                   masraf alınmıyor
               Dosya masrafı yok  31 Aralık 2026
    B Bankası  Konut finansmanı  %1,95     120 ay  Ekspertiz ücreti banka
                                                   tarafından karşılanıyor
               Ekspertiz ücretsiz Belirtilmemiş
    C Bankası  Konut finansmanı  %1,87     96 ay   5.000 TL alışveriş çeki
               Masraf belirtilmemiş  Belirtilmemiş

## Neye EŞİTLİK, neye İÇERME iddia ediliyor

Test iki tür hücre ayırır ve bu ayrım bilinçlidir:

* **Kanonik hücreler** (Banka, Ürün Türü, Kâr Payı, Vade, Süre, Masraf) —
  şartnamenin yazdığı değerin KANONİK karşılığına birebir eşit olmalı.
  Şartname sunum biçimini yazıyor ("31 Aralık 2026"), sistem kanonik biçimi
  saklıyor ("2026-12-31"); ikisi aynı olguysa test kanonik tarafı ölçer,
  çünkü Türkçe biçimlendirme arayüzün işidir (`web/app/lib/format.ts`) ve
  sunucuda ikinci bir biçimlendirici tutmak aynı kararı iki yerde
  yaşatmak olurdu.
* **Kampanya Avantajı** — şartnamenin hücresi bir YENİDEN YAZIMdır
  ("50.000 TL'ye kadar masraf alınmıyor"). Birebir üretmek serbest metin
  üretmek olurdu ve yasak (CLAUDE.md §21). Test bunun yerine hücrenin
  DOĞRU ÇIKARIM SATIRINDAN geldiğini ve kanıtını taşıdığını ölçer.

## KAPANMIŞ AÇIK (2026-08-16) — B Bankası satırı

Bu test ilk yazıldığında B Bankası'nın "Kampanya kapsamında ekspertiz ücreti
banka tarafından karşılanmaktadır" cümlesi `masraf_durumu` ÜRETMİYORDU;
şartnamenin o cümleden beklediği iki hücre ("Ekspertiz ücretsiz" /
"Ekspertiz ücreti banka tarafından karşılanıyor") boş kalıyordu ve tablo
21 hücrenin 16'sını dolduruyordu.

Açık çıkarım katmanındaydı ve `TestBBankasiMasrafMuafiyeti` onu adıyla
ölçüyordu. Aynı gün kapandı: kural muafiyet ifadesini tanımaya başladı, test
kırmızıya döndü, beklentiler güncellendi. Tek çıkarım düzeltmesi İKİ hücreyi
birden kapattı — çünkü avantaj kolonu muafiyeti `AVANTAJ_MUAFIYET_ALANLARI`
üzerinden zaten kaynak olarak okuyordu. Tablo artık **18/21**, yani
şartnamenin kendi doluluğuyla birebir aynı.

O sınıf şimdi kapanmış davranışın nöbetçisi: muafiyet yeniden kaybolursa
düşer.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.comparison.compare import (
    AVANTAJ_ALANLARI,
    AVANTAJ_MUAFIYET_ALANLARI,
    OLCULEN_SUTUNLAR,
    SARTNAME_SUTUNLARI,
    SUTUN_AVANTAJ_CAKISAN,
    avantaj_hucresi,
    tablo_dolulugu,
    tablo_satirlari,
)

TUR = "Konut Finansmanı"

#: Şartname s.11 — üç kampanya metni, BİREBİR.
SARTNAME_METINLERI: tuple[tuple[str, str, str], ...] = (
    ("a-bankasi", "A Bankası",
     "Yeni ev sahibi olmak isteyen müşterilerimize özel %1,89 kâr payı oranı "
     "ile 120 aya kadar konut finansmanı fırsatı sunulmaktadır. Kampanya "
     "kapsamında 50.000 TL'ye kadar dosya masrafı alınmamaktadır. Kampanya "
     "31 Aralık 2026 tarihine kadar geçerlidir."),
    ("b-bankasi", "B Bankası",
     "Konut finansmanında avantajlı ödeme seçenekleri. %1,95 kâr payı oranı "
     "ile 120 ay vadeye kadar finansman imkânı sunulmaktadır. Kampanya "
     "kapsamında ekspertiz ücreti banka tarafından karşılanmaktadır."),
    ("c-bankasi", "C Bankası",
     "Yeni konut alımlarına özel %1,87 kâr payı oranı ile 96 ay vadeli konut "
     "finansmanı fırsatı. Kampanya kapsamında 5.000 TL değerinde alışveriş "
     "çeki verilmektedir."),
)

#: Şartname s.12 tablosunun KANONİK karşılığı. `...` = "bu hücre boş kalmalı"
#: DEĞİL; aşağıda her hücre açıkça yazılıdır ve `None` "Belirtilmemiş"tir.
BEKLENEN: dict[str, dict[str, object]] = {
    "A Bankası": {
        "bank": "A Bankası",
        "campaign_type": TUR,
        "kar_payi_orani": 1.89,          # s.12: %1,89
        "vade_ay": 120,                  # s.12: 120 ay
        "masraf_durumu": {"has_fee": False, "amount": 0.0},   # "Dosya masrafı yok"
        "kampanya_suresi": "2026-12-31",  # s.12: 31 Aralık 2026
    },
    "B Bankası": {
        "bank": "B Bankası",
        "campaign_type": TUR,
        "kar_payi_orani": 1.95,
        "vade_ay": 120,
        # s.12: "Ekspertiz ücretsiz". 2026-08-16'da çıkarım katmanı muafiyet
        # ifadesini tanımaya başladı ve `muaf_ucret` ile HANGİ ücretin muaf
        # olduğunu da söylüyor — şartnamenin hücresi de tam bunu yazıyor.
        "masraf_durumu": {"has_fee": False, "amount": 0.0,
                          "muaf_ucret": "ekspertiz"},
        "kampanya_suresi": None,         # s.12: Belirtilmemiş
    },
    "C Bankası": {
        "bank": "C Bankası",
        "campaign_type": TUR,
        "kar_payi_orani": 1.87,
        "vade_ay": 96,
        "masraf_durumu": None,           # s.12: Masraf belirtilmemiş
        "kampanya_suresi": None,         # s.12: Belirtilmemiş
    },
}

#: Kampanya Avantajı hücresinin hangi ÇIKARIM ALANINDAN gelmesi beklendiği.
#: Şartnamenin yeniden yazımı değil, o yeniden yazımın DAYANAĞI ölçülür.
BEKLENEN_AVANTAJ: dict[str, tuple[str | None, object]] = {
    # s.12: "50.000 TL'ye kadar masraf alınmıyor" -> masraf MUAFİYETİ
    "A Bankası": ("masraf_durumu", {"has_fee": False, "amount": 0.0}),
    # s.12: "Ekspertiz ücreti banka tarafından karşılanıyor" -> muafiyet
    "B Bankası": ("masraf_durumu", {"has_fee": False, "amount": 0.0,
                                    "muaf_ucret": "ekspertiz"}),
    # s.12: "5.000 TL alışveriş çeki" -> ödül miktarı
    "C Bankası": ("odul_miktari", {"value": 5000.0, "currency": "TRY"}),
}


def _kampanyalar() -> list[dict]:
    """Üç şartname metnini çıkarımdan geçirip tablo girdisine çevirir."""
    from src.extraction.reconcile import build_campaign

    out = []
    for i, (slug, ad, metin) in enumerate(SARTNAME_METINLERI, start=1):
        c = build_campaign(metin, bank_slug=slug, campaign_type=TUR)
        out.append({
            "bank": slug, "bank_name": ad, "campaign_id": i,
            "campaign_type": c.campaign_type, "campaign_status": None,
            "fields": {
                f.field_name: {
                    "canonical_value": f.canonical_value,
                    "raw_value": f.raw_value,
                    "confidence": f.confidence,
                    "extractor": f.extractor.value,
                    "source_span": f.source_span,
                    "span_start": f.span_start,
                    "span_end": f.span_end,
                }
                for f in c.fields
            },
        })
    return out


class SartnameTablosuHucreHucre(unittest.TestCase):
    """s.11 metinleri girdi, s.12 tablosu beklenen çıktı."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.satirlar = tablo_satirlari(_kampanyalar())
        cls.satir = {s.bank_name: s for s in cls.satirlar}

    def test_uc_banka_uc_satir(self) -> None:
        self.assertEqual([s.bank_name for s in self.satirlar],
                         ["A Bankası", "B Bankası", "C Bankası"])

    def test_her_satir_TEK_kampanyadan(self) -> None:
        """Banka içi birleştirme yok — satır var olmayan ürün icat etmez."""
        for s in self.satirlar:
            with self.subTest(banka=s.bank_name):
                self.assertIsNotNone(s.campaign_id)
                self.assertEqual(s.other_count, 0)

    def test_kolon_sozlesmesi_sartname_basliklariyla_AYNI(self) -> None:
        self.assertEqual([b for _a, b, _f in SARTNAME_SUTUNLARI],
                         ["Banka", "Ürün Türü", "Kâr Payı Oranı", "Vade",
                          "Kampanya Avantajı", "Masraf Durumu",
                          "Kampanya Süresi"])

    def test_kanonik_hucreler_HUCRE_HUCRE(self) -> None:
        for banka, beklenen in BEKLENEN.items():
            satir = self.satir[banka]
            for sutun, deger in beklenen.items():
                with self.subTest(banka=banka, sutun=sutun):
                    self.assertEqual(satir.cells[sutun].value, deger)

    def test_bos_hucreler_BOS_isaretli(self) -> None:
        """Boş hücre `bos=True` döner; arayüz «Belirtilmemiş» basar."""
        for banka, beklenen in BEKLENEN.items():
            for sutun, deger in beklenen.items():
                with self.subTest(banka=banka, sutun=sutun):
                    self.assertEqual(self.satir[banka].cells[sutun].bos,
                                     deger is None)

    def test_dolu_hucreler_KANITINI_tasiyor(self) -> None:
        """Denetlenemeyen bir hücre, tabloda bir iddia olmaya yetmez."""
        for banka in BEKLENEN:
            for sutun in OLCULEN_SUTUNLAR:
                hucre = self.satir[banka].cells[sutun]
                if hucre.bos or sutun == "kampanya_avantaji":
                    continue
                with self.subTest(banka=banka, sutun=sutun):
                    self.assertTrue(hucre.raw_value,
                                    "ham ifade yok — kanıtsız hücre")
                    self.assertIsNotNone(hucre.confidence)
                    self.assertIsNotNone(hucre.extractor)

    def test_kampanya_avantaji_DOGRU_ALANDAN_geliyor(self) -> None:
        for banka, (alan, deger) in BEKLENEN_AVANTAJ.items():
            hucre = self.satir[banka].cells["kampanya_avantaji"]
            with self.subTest(banka=banka):
                if alan is None:
                    self.assertEqual(hucre.parcalar, [])
                    self.assertTrue(hucre.bos)
                    continue
                self.assertEqual([p.field_name for p in hucre.parcalar], [alan])
                self.assertEqual(hucre.parcalar[0].value, deger)

    def test_kampanya_avantaji_SERBEST_METIN_degil(self) -> None:
        """Hücrenin kendi değeri yoktur; yalnız span'li parçalar taşır."""
        for banka in BEKLENEN_AVANTAJ:
            hucre = self.satir[banka].cells["kampanya_avantaji"]
            with self.subTest(banka=banka):
                self.assertIsNone(hucre.value,
                                  "birleşik kolon kendi metnini ÜRETMEZ")
                for p in hucre.parcalar:
                    self.assertTrue(p.raw_value, "parça kanıtsız olamaz")
                    self.assertIn(p.field_name,
                                  AVANTAJ_ALANLARI + AVANTAJ_MUAFIYET_ALANLARI)

    def test_sartname_dolulugu(self) -> None:
        """s.12'de 21 hücrenin 3'ü boş; bizde de 3'ü — TAM ÖRTÜŞME.

        Sayı ELLE yazılmıyor, `tablo_dolulugu()` ile ölçülüyor. 2026-08-16
        sabahı bu sayı 16/21 idi; çıkarım katmanı ekspertiz muafiyetini
        tanıyınca B Bankası'nın iki hücresi birden doldu ve tablo şartnameyle
        aynı doluluğa oturdu. Boş kalan üç hücrenin üçü de şartnamede de boş:
        B ve C'nin kampanya süresi, C'nin masraf durumu.
        """
        d = tablo_dolulugu(self.satirlar)
        self.assertEqual(d["satir"], 3)
        self.assertEqual(d["tum_hucre"], 21, "3 satır × 7 kolon (s.12 ile aynı)")
        self.assertEqual(d["tum_dolu"], 18, "s.12 ile aynı: 21 hücrenin 3'ü boş")
        self.assertEqual(d["hucre"], 15, "türetilmiş iki kolon sayaca girmez")
        self.assertEqual(d["dolu"], 12)
        self.assertEqual(
            {s: v["dolu"] for s, v in d["sutun_basina"].items()},
            {"kar_payi_orani": 3, "vade_ay": 3, "kampanya_avantaji": 3,
             "masraf_durumu": 2, "kampanya_suresi": 1})


class TestBBankasiMasrafMuafiyeti(unittest.TestCase):
    """KAPANMIŞ AÇIĞIN nöbetçisi — B Bankası'nın iki hücresi.

    Şartname B Bankası için iki hücre bekliyor ve ikisi de TEK cümleden
    çıkıyor: "Kampanya kapsamında ekspertiz ücreti banka tarafından
    karşılanmaktadır." → "Ekspertiz ücretsiz" (Masraf Durumu) ve "Ekspertiz
    ücreti banka tarafından karşılanıyor" (Kampanya Avantajı).

    2026-08-16 sabahı çıkarım bu muafiyeti TANIMIYORDU ve iki hücre de boştu;
    burası açığı adıyla ölçen bir nöbetçiydi. Açık aynı gün kapandı (çıkarım
    katmanı `muaf_ucret` ile hangi ücretin muaf olduğunu da söylüyor) ve test
    yönünü değiştirdi: artık kapanmış davranışı KİLİTLER.

    Tek çıkarım düzeltmesinin iki hücreyi birden doldurması tesadüf değil:
    avantaj kolonu muafiyeti `AVANTAJ_MUAFIYET_ALANLARI` üzerinden zaten
    kaynak olarak okuyordu, yani kıyas tarafı hazır bekliyordu.
    """

    def setUp(self) -> None:
        from src.extraction.reconcile import build_campaign

        _slug, _ad, metin = SARTNAME_METINLERI[1]
        self.kampanya = build_campaign(metin, bank_slug="b-bankasi",
                                       campaign_type=TUR)

    def test_cikarim_ekspertiz_muafiyetini_TANIYOR(self) -> None:
        alan = self.kampanya.get("masraf_durumu")
        self.assertIsNotNone(alan, "ekspertiz muafiyeti yeniden kayboldu")
        self.assertIs(alan.canonical_value.get("has_fee"), False)
        self.assertIn("ekspertiz", (alan.raw_value or "").lower())

    def test_ayni_cumle_IKI_hucreyi_birden_dolduruyor(self) -> None:
        satir = tablo_satirlari([{
            "bank": "b-bankasi", "bank_name": "B Bankası", "campaign_id": 1,
            "campaign_type": TUR, "campaign_status": None,
            "fields": {f.field_name: {"canonical_value": f.canonical_value,
                                      "raw_value": f.raw_value,
                                      "confidence": f.confidence,
                                      "extractor": f.extractor.value}
                       for f in self.kampanya.fields},
        }])[0]
        self.assertFalse(satir.cells["masraf_durumu"].bos)
        self.assertEqual(
            [p.field_name for p in satir.cells["kampanya_avantaji"].parcalar],
            ["masraf_durumu"])

    def test_muafiyet_kurali_alan_ADINDAN_bagimsiz(self) -> None:
        """Kıyas tarafı `muaf_ucret` alanını bilmek zorunda DEĞİL.

        Kural yalnız `has_fee` bayrağına bakar; çıkarım katmanı sözlüğe yeni
        anahtar eklediğinde (bugün `muaf_ucret` eklendi) kıyas kodunun
        değişmesi gerekmez.
        """
        hucre = avantaj_hucresi({"masraf_durumu": {
            "canonical_value": {"has_fee": False},
            "raw_value": "ekspertiz ücreti banka tarafından karşılanmaktadır",
            "confidence": 0.9, "extractor": "rule"}})
        self.assertEqual([p.field_name for p in hucre.parcalar],
                         ["masraf_durumu"])
        self.assertFalse(hucre.bos)


class TestAvantajBirlestirmeKurali(unittest.TestCase):
    """"Kampanya Avantajı" nasıl derleniyor — kural ve sınırları."""

    def _alan(self, deger, ham="x"):
        return {"canonical_value": deger, "raw_value": ham,
                "confidence": 0.9, "extractor": "rule"}


    def test_dogrudan_fayda_alanlari_ONCELIK_SIRASIYLA(self) -> None:
        hucre = avantaj_hucresi({
            "indirim_orani": self._alan(10.0),
            "odul_miktari": self._alan({"value": 500.0, "currency": "TRY"}),
            "alisveris_puani": self._alan({"kind": "points", "value": 750.0}),
        })
        self.assertEqual([p.field_name for p in hucre.parcalar],
                         ["odul_miktari", "alisveris_puani", "indirim_orani"])

    def test_muafiyet_yalniz_dogrudan_fayda_YOKKEN(self) -> None:
        """Masraf ayrı bir kolon; iki hücrede aynı çıkarımı basmayız."""
        hucre = avantaj_hucresi({
            "odul_miktari": self._alan({"value": 500.0, "currency": "TRY"}),
            "masraf_durumu": self._alan({"has_fee": False, "amount": 0.0}),
        })
        self.assertEqual([p.field_name for p in hucre.parcalar],
                         ["odul_miktari"])

    def test_VAR_OLAN_ucret_avantaj_DEGILDIR(self) -> None:
        for deger in ({"has_fee": True, "amount": 750.0},
                      {"has_fee": True, "amount": None},
                      {"value": 3000.0, "currency": "TRY"}):
            with self.subTest(deger=deger):
                hucre = avantaj_hucresi({"masraf_durumu": self._alan(deger),
                                         "tahsis_ucreti": self._alan(deger)})
                self.assertTrue(hucre.bos)

    def test_CELISKILI_kayit_avantaj_SAYILMAZ(self) -> None:
        """«Ücret var ve sıfır» — korpusta ölçülen çelişki (Vakıf, konut).

        `has_fee` bayrağı kazanır; çelişkili bir çıkarımı olumlu bir iddiaya
        çevirmektense hücre boş kalır.
        """
        hucre = avantaj_hucresi({
            "masraf_durumu": self._alan({"has_fee": True, "amount": 0.0})})
        self.assertTrue(hucre.bos)

    def test_bayraksiz_SIFIR_ucret_muafiyettir(self) -> None:
        """`tahsis_ucreti` para biçimlidir; 0 TL orada çelişki taşımaz."""
        hucre = avantaj_hucresi({
            "tahsis_ucreti": self._alan({"value": 0.0, "currency": "TRY"})})
        self.assertEqual([p.field_name for p in hucre.parcalar],
                         ["tahsis_ucreti"])

    def test_kampanya_kosullari_KAYNAK_DEGIL(self) -> None:
        """Kısıtı avantaj kolonuna basmak anlamını tersine çevirirdi."""
        hucre = avantaj_hucresi({
            "kampanya_kosullari": self._alan(
                ["Müşteri olma aşamasında \"Davet Kodu\" alanına "
                 "\"KTOD2026\" kodunun yazılması gerekmektedir."]),
        })
        self.assertTrue(hucre.bos)
        self.assertNotIn("kampanya_kosullari",
                         AVANTAJ_ALANLARI + AVANTAJ_MUAFIYET_ALANLARI)

    def test_hicbiri_yoksa_hucre_BOS(self) -> None:
        self.assertTrue(avantaj_hucresi({}).bos)

    def test_kolonu_TEKRAR_EDEN_parca_isaretlenir(self) -> None:
        """`masraf_durumu` hem avantaj kaynağı hem tablo kolonu — çakışır.

        Arayüz bu işareti görünce bankanın kendi ifadesini basar; işaret
        olmazsa hücre yanındaki kolonu kelimesi kelimesine tekrar ederdi.
        """
        hucre = avantaj_hucresi({
            "masraf_durumu": self._alan({"has_fee": False}, "Ücretsiz")})
        self.assertEqual(hucre.parcalar[0].sutun, SUTUN_AVANTAJ_CAKISAN)

    def test_kolon_OLMAYAN_kaynak_isaretlenmez(self) -> None:
        """`tahsis_ucreti` tabloda kolon değil; tekrar da yok."""
        hucre = avantaj_hucresi({
            "tahsis_ucreti": self._alan({"value": 0.0, "currency": "TRY"})})
        self.assertEqual(hucre.parcalar[0].sutun, "kampanya_avantaji")

    def test_dogrudan_fayda_parcalari_ISARETSIZ(self) -> None:
        """Ödül/puan/indirim hiçbir kolonu tekrar etmiyor — dokunulmuyor."""
        hucre = avantaj_hucresi({
            "odul_miktari": self._alan({"value": 500.0, "currency": "TRY"}),
            "indirim_orani": self._alan(10.0),
        })
        for p in hucre.parcalar:
            with self.subTest(alan=p.field_name):
                self.assertEqual(p.sutun, "kampanya_avantaji")

    def test_isaret_hucreyi_BOSALTMAZ(self) -> None:
        """Doluluk düşmemeli: işaret yalnız GÖSTERİMİ değiştirir."""
        hucre = avantaj_hucresi({
            "masraf_durumu": self._alan({"has_fee": False}, "Ücretsiz")})
        self.assertFalse(hucre.bos)
        self.assertIsNotNone(hucre.parcalar[0].raw_value)


class TestTemsilciSecimi(unittest.TestCase):
    """Bankanın hangi kampanyası satırı temsil eder."""

    def _kampanya(self, cid, **alanlar):
        return {"bank": "x", "bank_name": "X", "campaign_id": cid,
                "campaign_type": TUR,
                "campaign_status": alanlar.pop("status", None),
                "fields": {k: {"canonical_value": v, "raw_value": "h",
                               "confidence": 0.9, "extractor": "rule"}
                           for k, v in alanlar.items()}}

    def test_EN_COK_HUCRE_dolduran_kazanir(self) -> None:
        satirlar = tablo_satirlari([
            self._kampanya(1, kar_payi_orani=2.0),
            self._kampanya(2, kar_payi_orani=3.0, vade_ay=60,
                           kampanya_suresi="2026-01-01"),
        ])
        self.assertEqual(len(satirlar), 1)
        self.assertEqual(satirlar[0].campaign_id, 2)
        self.assertEqual(satirlar[0].other_count, 1, "diğeri SAYILIR")

    def test_suresi_dolmus_kampanya_TEMSIL_ETMEZ(self) -> None:
        """Daha dolu olsa bile: kapanmış kampanya ürünü temsil etmez."""
        satirlar = tablo_satirlari([
            self._kampanya(1, kar_payi_orani=2.0),
            self._kampanya(2, status="expired", kar_payi_orani=3.0,
                           vade_ay=60, kampanya_suresi="2026-01-01"),
        ])
        self.assertEqual(satirlar[0].campaign_id, 1)

    def test_esitlikte_sira_KARARLI(self) -> None:
        a = [self._kampanya(7, kar_payi_orani=2.0),
             self._kampanya(3, kar_payi_orani=2.0)]
        self.assertEqual(tablo_satirlari(a)[0].campaign_id, 3)
        self.assertEqual(tablo_satirlari(list(reversed(a)))[0].campaign_id, 3)

    def test_ayni_bankanin_farkli_TURLERI_ayri_satir(self) -> None:
        satirlar = tablo_satirlari([
            self._kampanya(1, kar_payi_orani=2.0),
            {**self._kampanya(2, kar_payi_orani=3.0),
             "campaign_type": "Taşıt Finansmanı"},
        ])
        self.assertEqual(len(satirlar), 2)


class TestKapsamTablodaDaGecerli(unittest.TestCase):
    """Alanı hiç olmayan banka tablodan DÜŞMEZ (1. turun kapsam kararı)."""

    def test_kapsam_satiri_tum_hucreleri_bos_olarak_gelir(self) -> None:
        satirlar = tablo_satirlari(
            [],
            kapsam=[{"bank": "ziraat-katilim", "bank_name": "Ziraat Katılım",
                     "campaign_type": TUR}],
        )
        self.assertEqual(len(satirlar), 1)
        s = satirlar[0]
        self.assertIsNone(s.campaign_id)
        self.assertEqual(s.cells["bank"].value, "Ziraat Katılım")
        self.assertEqual(s.cells["campaign_type"].value, TUR)
        for sutun in OLCULEN_SUTUNLAR:
            with self.subTest(sutun=sutun):
                self.assertTrue(s.cells[sutun].bos)

    def test_doluluk_kapsam_satirini_SAYAR(self) -> None:
        """Boş satır paydaya girer; girmezse oran gerçekten yüksek görünür."""
        d = tablo_dolulugu(tablo_satirlari(
            _kampanyalar(),
            kapsam=[{"bank": "z", "bank_name": "Z Katılım",
                     "campaign_type": TUR}]))
        self.assertEqual(d["satir"], 4)
        self.assertEqual(d["hucre"], 20)


class TestUrunTablosuUcu(unittest.TestCase):
    """`GET /urun-tablosu` — uçtan uca, şartname metinleriyle."""

    def setUp(self) -> None:
        try:
            import fastapi  # noqa: F401
        except (ImportError, RuntimeError) as e:  # pragma: no cover
            self.skipTest(f"fastapi/testclient yok: {e}")
        from src.db.repository import Repository
        from src.extraction.reconcile import build_campaign

        self._tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self._tmp.name) / "sartname.db")
        repo = Repository(self.path)
        for slug, ad, metin in SARTNAME_METINLERI:
            repo.upsert_bank(name=ad, slug=slug)
            repo.insert_campaign(build_campaign(metin, bank_slug=slug,
                                                campaign_type=TUR))
        repo.close()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _tablo(self) -> dict:
        from fastapi.testclient import TestClient

        from src.api import main as api_main
        onceki = api_main.DB_PATH
        api_main.DB_PATH = self.path
        try:
            app = api_main.build_app()
        finally:
            api_main.DB_PATH = onceki
        r = TestClient(app).get("/urun-tablosu", params={"type": TUR})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_yanit_sartname_tablosunu_verir(self) -> None:
        d = self._tablo()
        self.assertEqual([c["label"] for c in d["columns"]],
                         ["Banka", "Ürün Türü", "Kâr Payı Oranı", "Vade",
                          "Kampanya Avantajı", "Masraf Durumu",
                          "Kampanya Süresi"])
        self.assertEqual([r["bank_name"] for r in d["rows"]],
                         ["A Bankası", "B Bankası", "C Bankası"])
        for satir in d["rows"]:
            beklenen = BEKLENEN[satir["bank_name"]]
            for sutun, deger in beklenen.items():
                with self.subTest(banka=satir["bank_name"], sutun=sutun):
                    self.assertEqual(satir["cells"][sutun]["value"], deger)

    def test_doluluk_yanitta_ve_CALISMA_ANINDA(self) -> None:
        d = self._tablo()["doluluk"]
        self.assertEqual((d["satir"], d["hucre"], d["dolu"]), (3, 15, 12))
        self.assertEqual((d["tum_hucre"], d["tum_dolu"]), (21, 18))

    def test_turetilmis_kolonlar_sayaca_GIRMEZ(self) -> None:
        d = self._tablo()
        olculur = {c["key"] for c in d["columns"] if c["olculur"]}
        self.assertEqual(olculur, set(OLCULEN_SUTUNLAR))
        self.assertNotIn("bank", olculur)
        self.assertNotIn("campaign_type", olculur)


if __name__ == "__main__":
    unittest.main()
