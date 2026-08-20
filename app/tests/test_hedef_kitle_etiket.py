"""`hedef_kitle` — segment sinyali CÜMLEDE aranır, menüde değil.

İlgili: ../src/extraction/rules/extract.py (`extract_hedef_kitle`,
        `_gezinme_seridi`, `_EVRENSELLIK_RE`),
        ../data/gold/ANNOTATION_GUIDE.md §4 `hedef_kitle` + §4.13/2,
        ../docs/rapor/liste-alanlari-iyilestirme.md (ölçüm defteri)

## Neden bu dosya var — kök neden ve ürün yüzeyindeki etki

Alan gold.v2'de kalem düzeyinde F1 **0,364** (tp 6 · fp 10 · fn 11), ikili
düzeyde **0,286** ile en zayıf ikinci alandı. Kalem kalem sayım iki ayrı kök
neden gösterdi ve ikisi ters yönde çalışıyordu:

**(1) Yanlış pozitiflerin yarısı GEZİNME ŞERİDİNDEN geliyordu.** Eski çıkarıcı
deseni belgenin TAMAMINDA `re.search` yapıyordu, yani üst menüde, ürün
listesinde ya da komşu kampanya başlığında geçen bir sözcük bu kampanyanın
hedef kitlesi sayılıyordu:

    "… Bireysel Emeklilik Sistemi Sigortacılık Hizmetleri …"  -> belirli_segment
    "… Kredi Kartı Kampanyaları Maaş Ödemesi Kampanyaları …"  -> maas_musterisi
    "Anonim ve Limited Şirketler … Serbest Meslek Sahipleri"  -> belirli_segment
    "Worldcard Kampanyaları Yeni Müşterilerimize Özel …"      -> yeni + mevcut

Hiçbiri cümle değil; hepsi HTML menüsünün metne inmiş hâli. Ürün yüzeyinde
sonucu şuydu: bir hayat sigortası ürün sayfası dashboard'da "emekli
müşterilere özel" diye etiketleniyordu — yani filtre "emeklilere uygun
kampanyalar" sorgusuna ALAKASIZ belge döndürüyordu.

**(2) Kaçırılan 11 etiketin 6'sı SÖZLÜK EKSİĞİydi.** Kılavuz §4.13/2 kişi
niteliğini segment sayıyor ("Emekli müşterilerimize"), ama sözlükte meslek
adı, kulüp/kademe üyeliği ve "seçili müşteri" aileleri hiç yoktu:

    "… ilk defa bankamızdan alan eczacı müşterilerimize"      (meslek)
    "Hadi Gold üyesi olmalısın"                               (üyelik)
    "… limitini artıran seçili müşteriler için geçerlidir"    (seçili)

İki kapı ayrı ayrı kilitlenir; biri kaldırılırsa öteki hatayı tek başına
yakalayamaz:

  KAPI 1  Segment sinyali gezinme şeridinde ya da "herkes" bağlamında
          geçiyorsa etiket ÜRETİLMEZ (kesinlik).
  KAPI 2  Kişi niteliğinin üç ailesi tanınır (geri çağırma).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules.extract import _gezinme_seridi, extract_hedef_kitle

GECERLI_ETIKETLER = frozenset({
    "yeni_musteri", "mevcut_musteri", "maas_musterisi", "belirli_segment"})


def _etiketler(metin: str) -> list[str]:
    f = extract_hedef_kitle(metin)
    return list(f.canonical_value) if f else []


# --------------------------------------------------------------------------- #
# KAPI 1 — gezinme şeridi ve evrensellik
# --------------------------------------------------------------------------- #
class TestGezinmeSeridiEtiketUretmez(unittest.TestCase):
    """Her karşı-örnek gold.v2'de ölçülmüş bir yanlış pozitiftir."""

    def test_ust_menu_urun_adi_segment_degil(self) -> None:
        """"Bireysel Emeklilik" bir ÜRÜN adı; menüde geçiyor."""
        metin = ("Albaraka Mobil Mobil Bankacılık Aç Kredi Hayat Sigortası "
                 "Anasayfa Bireysel Sigorta ve Emeklilik Hayat ve Ferdi Kaza "
                 "Sigortası Kredi Hayat Sigortası Güvenceli Hayat Sigortası")
        self.assertEqual(_etiketler(metin), [])

    def test_menu_kategorisi_maas_musterisi_uretmez(self) -> None:
        metin = ("Müşteri Ol Kampanyalar Dijital Bankacılık Kampanyaları "
                 "Kredi Kartı Kampanyaları Maaş Ödemesi Kampanyaları Yatırım "
                 "Kampanyaları Sigorta Kampanyaları Finansman Kampanyaları")
        self.assertEqual(_etiketler(metin), [])

    def test_komsu_kampanya_basligi_etiket_uretmez(self) -> None:
        """Kampanya LİSTESİ sayfası — başlıklar başka kampanyalara ait."""
        metin = ("Özel Bankacılık Bireysel Business World Kampanyaları Geçmiş "
                 "Kampanyalar Worldcard Kampanyaları Yeni Müşterilerimize Özel "
                 "Vade Farksız Destek")
        self.assertEqual(_etiketler(metin), [])

    def test_tuzel_kisi_listesi_segment_degil(self) -> None:
        metin = ("Anonim ve Limited Şirketler Şahıs Firmaları Kolektif "
                 "Şirketler Serbest Meslek Sahipleri Ortak Girişimler")
        self.assertEqual(_etiketler(metin), [])

    def test_gezinme_seridi_olcutu_CUMLEYE_dokunmaz(self) -> None:
        """Ölçüt iki koşulu birlikte arar; normal cümle şerit sayılmaz."""
        self.assertFalse(_gezinme_seridi(
            "Kampanyadan tüzel ve şahıs firmasına sahip eczaneler "
            "faydalanabilir."))
        self.assertFalse(_gezinme_seridi("Emekli müşterilerimize özeldir."))
        self.assertTrue(_gezinme_seridi(
            "Kredi Kartları Banka Kartları Yatırım Hizmetleri Bireysel "
            "Emeklilik Sistemi Sigortacılık Hizmetleri"))

    def test_herkes_baglami_segment_degil(self) -> None:
        """Kılavuz §4: kapsayıcılık retoriği kısıt DEĞİLDİR."""
        metin = ("Girişimcilerden KOBİ'lere, yatırımcılardan öğrencilere "
                 "herkesin ve her kesimin finansal ihtiyaçlarını karşılamaya "
                 "çalışıyoruz.")
        self.assertEqual(_etiketler(metin), [])

    def test_negasyon_hala_etiket_uretmiyor(self) -> None:
        """Kılavuz §4 NEGASYON — olumsuzlanan segment etiketlenmez."""
        self.assertEqual(
            _etiketler("Yeni müşteri olmayanlar için geçerli değildir."), [])


# --------------------------------------------------------------------------- #
# KAPI 2 — kişi niteliğinin üç ailesi
# --------------------------------------------------------------------------- #
class TestKisiNiteligiTaninir(unittest.TestCase):
    """Kılavuz §4.13/2: kişi niteliği segmenttir, ürün/kanal kısıtı değildir."""

    def test_meslek_adi_belirli_segment(self) -> None:
        metin = ("250.000 TL tutarında hak ediş ödemesini ilk defa bankamızdan "
                 "alan eczacı müşterilerimize 8.000 Mil hediye.")
        self.assertIn("belirli_segment", _etiketler(metin))

    def test_uyelik_kademesi_belirli_segment(self) -> None:
        for metin in (
            "Kampanya'dan faydalanmak için Hadi Gold üyesi olmalısın.",
            "Çok Kazananlar Kulübü üyesi olan Hadi Black Kredi Kartı "
            "sahipleri yararlanabilir.",
        ):
            with self.subTest(metin=metin):
                self.assertIn("belirli_segment", _etiketler(metin))

    def test_secili_musteri_belirli_segment(self) -> None:
        metin = ("Kampanya 31 Temmuz'a kadar mevcut kredi kartı limitini "
                 "artıran seçili müşteriler için geçerlidir.")
        self.assertIn("belirli_segment", _etiketler(metin))

    def test_doktora_derecesi_meslek_SAYILMAZ(self) -> None:
        """Karşı-örnek: `doktor` lookahead'i olmadan "doktora" ateşliyordu.

        Danışma komitesi özgeçmiş sayfası kampanya değil; oradaki etiket
        tamamen uydurmaydı (gold: absent).
        """
        metin = ("Yüksek lisans ve doktora eğitimini Marmara Üniversitesi "
                 "İktisat Tarihi Anabilim Dalı'nda tamamladı.")
        self.assertEqual(_etiketler(metin), [])

    def test_urun_ve_kanal_kisiti_segment_DEGIL(self) -> None:
        """Kılavuz §4.13/2 — "Yalnız Paraf kartlar" KİM değil NE."""
        for metin in ("Kampanya yalnızca Paraf kartlar için geçerlidir.",
                      "Sadece mobil başvurularda geçerlidir."):
            with self.subTest(metin=metin):
                self.assertEqual(_etiketler(metin), [])


# --------------------------------------------------------------------------- #
# SÖZLEŞME — alan yalnız denetimli dört etiketi taşır
# --------------------------------------------------------------------------- #
class TestDenetimliDegerKumesi(unittest.TestCase):

    def test_uretilen_her_etiket_dort_etiketten_biridir(self) -> None:
        """Kılavuz §4: "Serbest metin yazılmaz"."""
        metin = ("Maaşını bankamızdan alan emekli müşterilerimize, ilk kez "
                 "müşteri olanlara ve mevcut müşterilerimize özel kampanya.")
        etiketler = _etiketler(metin)
        self.assertTrue(etiketler)
        self.assertTrue(set(etiketler) <= GECERLI_ETIKETLER,
                        f"denetim dışı etiket: {etiketler}")

    def test_etiketler_SIRALI_dondurulur(self) -> None:
        """Liste karşılaştırması sıraya duyarlı olmasın diye kanonik sıra."""
        metin = ("Maaş müşterilerimize ve ilk kez müşteri olanlara özel.")
        self.assertEqual(_etiketler(metin), sorted(_etiketler(metin)))

    def test_sinyal_yoksa_alan_URETILMEZ(self) -> None:
        """Halüsinasyon yasağı — "mevcut müşteri" varsayılanı YAPILMAZ."""
        self.assertIsNone(extract_hedef_kitle(
            "Kampanya 1-31 Temmuz 2026 tarihleri arasında geçerlidir."))

    def test_span_metne_izlenebilir(self) -> None:
        """Arama cümle cümle yapıldıktan sonra span BELGE ofseti olarak kalır.

        Regresyon riski gerçek: desen artık cümle diliminde arandığı için
        `m.span()` cümle-içi ofsettir; belge ofsetine çevrilmezse kaynak
        vurgulama (CLAUDE.md §18/1) yanlış yeri gösterir.
        """
        onek = "Bu sayfa bir kampanya sayfasıdır. "
        metin = onek + "Kampanya kapsamında emekli müşterilere özeldir."
        f = extract_hedef_kitle(metin)
        self.assertIsNotNone(f)
        self.assertIsNotNone(f.span_start)
        self.assertGreater(f.span_start, len(onek) - 1,
                           "span cümle-içi ofsette kalmış")
        self.assertEqual(metin[f.span_start:f.span_end].lower(), "emekli")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
