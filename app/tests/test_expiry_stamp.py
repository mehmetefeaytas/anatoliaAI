"""Bitmişlik damgası testleri — yanlış pozitif kapıları + kanıt/tarih doğruluğu.

İlgili: ../src/scraping/expiry_stamp.py, ../src/extraction/rules/ihtar.py
        ../docs/rapor/suresi-dolmus-damgasi.md

## Neden bu testler

Bir belgeye "bu kampanya bitti" demek KARARDIR: belge arşive gider ya da kıyas
sıralamasından düşer. Yanlış karar canlı bir kampanyayı gizler. Ölçüldü
(2026-08-10): geniş desenin ürettiği 5 `suresi_dolmus` kararının 5'i de yanlış
pozitifti. Buradaki parçacıkların HEPSİ gerçek korpustan birebir alınmıştır —
uydurma örnek üzerinde geçen bir test bu kusuru yakalayamazdı.

Üç yanlış pozitif kaynağı ayrı ayrı kapıda tutulur:

1. **Menü bağlantısı** — Türkiye Finans'ın her sayfasında duran
   "… Diğer Kampanyalar Biten Kampanyalar Blog …" gezinti çubuğu.
2. **İhtar kalıbı** — "kampanyayı durdurma, sona erdirme … hakkını saklı tutar";
   "bitti"nin TAM TERSİ, bankanın bitirme HAKKINI anlatır.
3. **Kuyruk bloğu** — "Diğer Kampanyalar" başlığından sonraki damga BAŞKA bir
   kampanyaya aittir (Albaraka'nın kart listesi).

Ayrıca tarih UYDURULMAMALI: damgaya yapışık olmayan tarih okunmaz.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.scraping.expiry_stamp import find_expiry_stamp, has_expiry_stamp

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

# --------------------------------------------------------------------------- #
# KONTROL GRUBU — canlı olduğu kesin belgelerden birebir alıntılar.
# Hiçbiri damga SAYILMAMALI.
# --------------------------------------------------------------------------- #

#: turkiye-finans/live/bireysel-arsa-finansmani.txt — sayfa canlı bir ürün
#: sayfası; eşleşen tek şey gezinti menüsündeki bağlantı metni.
KONTROL_MENU = (
    "Kampanyaları Sigorta Kampanyaları Finansman Kampanyaları Ticari "
    "Kampanyalar Diğer Kampanyalar Biten Kampanyalar Blog Finansal Okuryazarlık "
    "IBAN Numarası Nedir?"
)

#: vakif-katilim/live/detay-dijitalden-musteri-ol-hisse-senedi-islemlerinde-…
KONTROL_IHTAR_VAKIF = (
    "panyaya dahil değildir. Vakıf Katılım Bankası AŞ önceden haber vermeksizin "
    "kampanyayı durdurma, sona erdirme, kampanya kapsamını ve koşullarını "
    "değiştirme hakkını saklı tutar. Tümünü Göster"
)

#: tom-katilim/live/kampanyalar-hadi-black-kredi-karti-ile-pegasus-…
KONTROL_IHTAR_TOM = (
    "kkını saklı tutar. TOM Bank ve Pegasus, kampanya koşullarını değiştirme "
    "ve/veya kampanyayı iptal etme ve sona erdirme hakkını saklı tutar. "
    "Kampanya koşulları, değişiklik tarihinden önce tamamlanmamış işlemler"
)

#: kuveyt-turk/live/finansman-kampanyalari-taksitlioda-yeni-musterilere-…
#: İhtarın `ihtar.IHTAR_RE`'nin görmediği bir çekimi ("sonlandırabilir");
#: bu vakayı ihtar vetosu değil, DAR DESEN eliyor.
KONTROL_IHTAR_KUVEYT = (
    "yapmaktadır. Kuveyt Türk, önceden haber vermeden kampanya koşullarında "
    "değişiklik yapabilir ya da kampanyayı sonlandırabilir. Kuveyt Türk "
    "Taksitlio Alışveriş Finansmanı hakkında daha fazla detaylı bilgi almak için"
)

#: albaraka/live/detay-bosch-harcamalarinizda-worlde-ozel-6-taksit-firsati.txt
#: Sayfanın KENDİ kampanyası (BOSCH) damgasız; damga alttaki "Diğer
#: Kampanyalar" kartında ve BAŞKA bir kampanyaya (Arçelik) ait.
KONTROL_KUYRUK_ALBARAKA = (
    "BOSCH Harcamalarınızda World'e Özel 6 Taksit Fırsatı! BOSCH "
    "harcamalarınızda 24 Haziran 2026 tarihine kadar World'e özel 6 taksit "
    "fırsatını kaçırmayın. Kampanya Başlangıç ve Bitiş Tarihi: Kampanya "
    "1 Mayıs 2026 – 24 Haziran 2026 tarihlerinde geçerlidir. Bankacılık "
    "Düzenleme ve Denetleme Kurulu'nun (BDDK) taksitlendirmeyi düzenleyen "
    "yönetmeliğine göre uygulanabilecek taksit sayısı değişiklik "
    "gösterebilmektedir. Diğer Kampanyalar Arçelik, Altus ve Beko "
    "Harcamalarınızda World'e Özel 9 Taksit Fırsatı! Arçelik, Altus ve Beko "
    "harcamalarınızda 15 Haziran 2026 tarihine kadar World'e özel 9 taksit "
    "fırsatını kaçırmayın. Bu kampanya sona ermiştir. Paylaş Facebook Twitter"
)

KONTROL_GRUBU = {
    "menü bağlantısı (turkiye-finans)": KONTROL_MENU,
    "ihtar cümlesi (vakif-katilim)": KONTROL_IHTAR_VAKIF,
    "ihtar cümlesi (tom-katilim)": KONTROL_IHTAR_TOM,
    "ihtar çekimi (kuveyt-turk)": KONTROL_IHTAR_KUVEYT,
    "kuyruk bloğu (albaraka)": KONTROL_KUYRUK_ALBARAKA,
}

# --------------------------------------------------------------------------- #
# DAMGALI GRUP — gerçekten bitmiş olduğu sayfada YAZAN belgelerden alıntılar.
# --------------------------------------------------------------------------- #

#: ziraat-katilim/live/kart-kampanyalari-jumboda-5-taksit.txt
DAMGA_ZIRAAT = (
    "yaz Eşya ve Ev Aletleri 17 Giyim ve Aksesuar Arşiv Jumbo'da 5 Taksit "
    "Kampanya 30-04-2026 Tarihinde Sona Ermiştir. Sektör: Mobilya ve "
    "Dekorasyon Ziraat"
)

#: vakif-katilim/live/detay-3-ay-ertelemeli-motosiklet-kampanyasi.txt
DAMGA_VAKIF = (
    " Kampanyalar 3 Ay Ertelemeli Motosiklet Kampanyası Kampanya Geçerlilik "
    "Tarihi Kampanya Süresi Dolmuştur Kampanya Detayları Hayalinizdeki "
    "Motosiklet Başka Bahara Kalmasın!"
)

#: dunya-katilim/live/kampanyalar-hepsiburada.txt — damga ihtar cümlesinin
#: HEMEN ARDINDAN geliyor; veto yönlü olmasaydı bu gerçek damga düşerdi.
DAMGA_DUNYA = (
    "Ş. kampanya koşullarının tamamında değişiklik yapma ve/veya kampanyayı "
    "durdurma hakkını saklı tutar. Paraf Kampanyaları Sona erdi Bitiş Tarihi: "
    "31 Temmuz 2026 Paylaş Diğer Kampanyalar Tüm site ziyaretçilerimizi"
)


class TestKontrolGrubu(unittest.TestCase):
    """Canlı olduğu kesin belgelerde desen ATEŞLEMEMELİ."""

    def test_hicbiri_damga_sayilmaz(self):
        for ad, metin in KONTROL_GRUBU.items():
            with self.subTest(kaynak=ad):
                bulgu = find_expiry_stamp(metin)
                self.assertIsNone(
                    bulgu,
                    f"{ad}: canlı belge bitmiş sayıldı — eşleşen "
                    f"«{bulgu.phrase if bulgu else ''}»")

    def test_ihtar_vetosu_yonlu(self):
        """İhtar ÖNCE gelirse damga vetolanmaz; SONRA gelirse vetolanır."""
        # Vakıf ihtarında "sona erdirme" ihtardan ÖNCE, "hakkını saklı tutar"
        # sonra → ihtar vetosu tam da bu yönü kapatmalı.
        self.assertFalse(has_expiry_stamp(KONTROL_IHTAR_VAKIF))
        # Dünya Katılım'da ihtar ÖNCE, gerçek damga SONRA → veto ETMEMELİ.
        self.assertTrue(has_expiry_stamp(DAMGA_DUNYA))


class TestDamgaliGrup(unittest.TestCase):
    """Sayfada açık damga varsa yakalanmalı ve kanıtı taşımalı."""

    def test_ziraat_damgasi_ve_tarihi(self):
        s = find_expiry_stamp(DAMGA_ZIRAAT)
        self.assertIsNotNone(s)
        self.assertEqual(s.phrase, "Tarihinde Sona Ermiştir")
        self.assertEqual(s.end_date, "2026-04-30")
        self.assertIn("30-04-2026", s.quote)

    def test_vakif_damgasi_tarihsiz(self):
        """Damga tarih taşımıyorsa tarih UYDURULMAZ."""
        s = find_expiry_stamp(DAMGA_VAKIF)
        self.assertIsNotNone(s)
        self.assertEqual(s.phrase, "Kampanya Süresi Dolmuştur")
        self.assertIsNone(s.end_date)

    def test_dunya_damgasi_ve_tarihi(self):
        s = find_expiry_stamp(DAMGA_DUNYA)
        self.assertIsNotNone(s)
        self.assertEqual(s.end_date, "2026-07-31")

    def test_yapisik_olmayan_tarih_okunmaz(self):
        """Damganın YANINDAKİ ama ona AİT OLMAYAN tarih bitiş sanılmamalı.

        Gerçek vaka (vakif-katilim, 3 belge): "Kampanya Süresi Dolmuştur
        Kampanya Detayları 15 Ekim 2024 - 31 Mayıs 2025 …" — yakınlıkla okuyan
        sürüm kampanyanın BAŞLANGIÇ tarihini bitiş sanıyordu.
        """
        metin = ("Kampanya Geçerlilik Tarihi Kampanya Süresi Dolmuştur "
                 "Kampanya Detayları 15 Ekim 2024 - 31 Mayıs 2025 tarihleri "
                 "arasında geçerlidir.")
        s = find_expiry_stamp(metin)
        self.assertIsNotNone(s)
        self.assertIsNone(s.end_date,
                          "damgaya yapışık olmayan tarih okunmamalı")


class TestKorpusRegresyonu(unittest.TestCase):
    """Gerçek `live/` korpusunun tamamında ölçülen davranışı kapıda tutar.

    `data/raw/*/live/*.txt` depoda izlenen dosyalardır (yalnız `.html`
    dışlanmıştır), dolayısıyla bu test temiz bir klonda da koşar.
    """

    #: Bu bankaların `live/` belgelerinde damga ÇIKMAMALI. Gerekçe ölçüme
    #: dayanır (docs/rapor/suresi-dolmus-damgasi.md): geniş desenin bu
    #: bankalarda bulduğu her eşleşme menü bağlantısı, ihtar kalıbı ya da
    #: kuyruk bloğundaki başka kampanyanın damgasıydı.
    KONTROL_BANKALAR = ("turkiye-finans", "kuveyt-turk", "hayat-finans",
                        "tom-katilim", "adil-katilim", "turkiye-emlak-katilim",
                        "albaraka")

    #: Korpusta gerçekten damga taşıyan bankalar ve ölçülen belge sayıları.
    #: Sayı değişirse ya desen bozulmuştur ya korpus yeniden hasat edilmiştir;
    #: ikinci durumda ölçüm tekrarlanıp bu sayılar ve rapor güncellenmelidir.
    DAMGALI_BANKALAR = {"ziraat-katilim": 102, "vakif-katilim": 81,
                        "dunya-katilim": 38}

    @classmethod
    def setUpClass(cls):
        if not RAW_DIR.is_dir():
            raise unittest.SkipTest("data/raw yok")
        cls.sayim: dict[str, int] = {}
        cls.belge: dict[str, int] = {}
        for path in sorted(RAW_DIR.glob("*/live/*.txt")):
            if path.name.endswith(".meta.json"):
                continue
            bank = path.parts[-3]
            cls.belge[bank] = cls.belge.get(bank, 0) + 1
            if has_expiry_stamp(path.read_text(encoding="utf-8",
                                               errors="replace")):
                cls.sayim[bank] = cls.sayim.get(bank, 0) + 1
        if not cls.belge:
            raise unittest.SkipTest("live/ korpusu boş")

    def test_kontrol_bankalarinda_sifir(self):
        for bank in self.KONTROL_BANKALAR:
            if bank not in self.belge:
                continue
            with self.subTest(banka=bank):
                self.assertEqual(
                    self.sayim.get(bank, 0), 0,
                    f"{bank}: canlı sayılan belgeler bitmiş işaretlendi")

    def test_damgali_bankalarda_olculen_sayi(self):
        for bank, beklenen in self.DAMGALI_BANKALAR.items():
            if bank not in self.belge:
                continue
            with self.subTest(banka=bank):
                self.assertEqual(self.sayim.get(bank, 0), beklenen)


if __name__ == "__main__":
    unittest.main()
