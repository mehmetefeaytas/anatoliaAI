"""D1 — kampanya süresi: başlangıç ve bitiş BİRLİKTE çıkarılır.

Mentörlük toplantısında tespit edilen çıkarım hatası (aksiyon planı §5.1-D1):
kural katmanı "ya sadece başlangıç ya sadece bitiş" tarihini alıyordu.

## Ölçüm (2026-08-07, `data/raw` altındaki 1759 belge)

    kampanya_suresi üreten belge            : 942
    başlangıç-bitiş ÇİFTİ içeren belge      : 492
      bunlardan BAŞLANGICI alan (HATA)      : 442   (%90)

Yani çift tarih yazan her 10 belgenin 9'unda, "geçerlilik bitiş tarihi"
alanına kampanyanın BAŞLADIĞI gün yazılıyordu. Bu sessiz bir hata: dashboard
süresi dolmuş bir kampanyayı hâlâ geçerli, yeni başlamış bir kampanyayı da
"birazdan bitiyor" gösterir. Düzeltmeden sonra aynı ölçüm **0** verdi.

Gold (20 belge, `--config kural --matcher tolerant`):
    kampanya_suresi  F1 0.308 -> 0.667   (TP 2->4, FP 5->2, FN 4->2, uydurma 1->0)

Buradaki her metin gerçek korpustan alınmıştır; dosya adı ilgili testte yazar.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules.extract import (
    extract_kampanya_suresi,
    kampanya_tarih_araligi,
)


def _tarih(metin: str):
    f = extract_kampanya_suresi(metin)
    return None if f is None else f.canonical_value


class TestAralikBitisiKazanir(unittest.TestCase):
    """Açık başlangıç-bitiş çiftinde BİTİŞ tarihi kanoniktir."""

    def test_nokta_ayirici_tarih_araligi(self) -> None:
        """`albaraka--detay-vade-farksiz-kampanyasi` — gold 2026-12-31.

        Eskiden 2026-01-01 (başlangıç) dönüyordu; gold'da FP+FN sayılıyordu.
        """
        metin = ("Anasayfa Kampanyalar Kampanya Başlangıç ve Bitiş "
                 "01.01.2026 - 31.12.2026 Müşteri Ol")
        self.assertEqual(_tarih(metin), "2026-12-31")

    def test_ay_adli_tarih_araligi(self) -> None:
        """`kuveyt-turk--kampanya-arsivi-business-plus-...` — gold 2023-08-31."""
        metin = "Kampanya Tarihleri 1.07.2023 - 31.08.2023 Kampanya Süresi Doldu!"
        self.assertEqual(_tarih(metin), "2023-08-31")

    def test_ayirici_bosluksuz_olabilir(self) -> None:
        """`albaraka/live/ayricalik-boynerde-1000-tl-indirim-81` biçimi.

        Korpusta ayıraç etrafında boşluk garanti değil: "27.02.2026-30.07.2026".
        """
        metin = "Kampanya 27.02.2026-30.07.2026 tarihleri arasında geçerlidir."
        self.assertEqual(_tarih(metin), "2026-07-30")

    def test_uzun_tire_ve_ay_adi(self) -> None:
        """`albaraka/live/ayricalik-yurt-disi-duty-free-...` — en-dash ayıraç."""
        metin = ("Kredi Kartlarınız ile 25 Nisan 2025 – 30 Eylül 2026 "
                 "tarihleri arasında geçerlidir.")
        self.assertEqual(_tarih(metin), "2026-09-30")

    def test_gun_gun_araligi_ay_paylasir(self) -> None:
        """"1-31 Temmuz 2026" — başlangıç yalnız GÜN olarak yazılır.

        `turkiye-emlak-katilim--kampanya-market-alisverislerinize-1500-tl-parafpara`
        belgesinden; gold 2026-07-31. Bu biçim ayrı ele alınmazsa başlangıç
        günü hiç görülmez ve aralık kurgusu kaçar.
        """
        metin = "Kampanya Koşulları Kampanya 1-31 Temmuz 2026 tarihleri arasında geçerlidir."
        self.assertEqual(_tarih(metin), "2026-07-31")
        aralik = kampanya_tarih_araligi(metin)
        self.assertEqual(aralik["baslangic"], "2026-07-01")
        self.assertEqual(aralik["bitis"], "2026-07-31")


class TestIkisiBirlikteCikar(unittest.TestCase):
    """`kampanya_tarih_araligi` iki tarihi de döndürür; alan bitişi taşır."""

    def test_aralik_her_iki_tarihi_verir(self) -> None:
        metin = "Kampanya 01.01.2026 - 31.12.2026 tarihlerinde geçerlidir."
        self.assertEqual(kampanya_tarih_araligi(metin),
                         {"baslangic": "2026-01-01", "bitis": "2026-12-31",
                          "span": (9, 32)})

    def test_ham_deger_araligin_tamamini_kapsar(self) -> None:
        """`raw_value` tek tarihi değil ARALIĞIN TAMAMINI göstermeli.

        Açıklanabilirlik: dashboard "2026-12-31" değerinin kaynağını
        vurgularken kullanıcıya çıkarımın iki tarihi birlikte gördüğünü
        göstermeli. Span doğrulaması (`verify_span`) da bitişik dilim ister.
        """
        metin = "Kampanya 01.01.2026 - 31.12.2026 tarihlerinde geçerlidir."
        f = extract_kampanya_suresi(metin)
        self.assertEqual(f.raw_value, "01.01.2026 - 31.12.2026")
        self.assertTrue(f.verify_span(metin))


class TestEksikTarafUydurulmaz(unittest.TestCase):
    """CLAUDE.md §19 — bilgi yoksa null. Diğer tarih TAHMİN EDİLMEZ."""

    def test_yalniz_baslangic_varsa_alan_uretilmez(self) -> None:
        """Sadece başlangıç bilinen kampanyanın bitişi uydurulmaz.

        Anotasyon kılavuzu da bu durumu `unclear` sayıyor
        (`data/gold/ANNOTATION_GUIDE.md` §kampanya_suresi sınır vakası).
        Başlangıcı bitiş sanmak, süresi belirsiz bir kampanyaya sahte bir
        son tarih uydurmaktır.
        """
        metin = "Kampanya 1 Mayıs 2026 tarihinden itibaren başlamaktadır."
        self.assertIsNone(extract_kampanya_suresi(metin))
        self.assertEqual(kampanya_tarih_araligi(metin),
                         {"baslangic": "2026-05-01", "bitis": None, "span": (9, 21)})

    def test_yalniz_bitis_varsa_baslangic_bos_kalir(self) -> None:
        metin = "Kampanya 31.12.2026 tarihine kadar geçerlidir."
        self.assertEqual(_tarih(metin), "2026-12-31")
        self.assertIsNone(kampanya_tarih_araligi(metin)["baslangic"])


class TestTarihGorunumluGurultu(unittest.TestCase):
    """Tarih gibi görünen ama kampanya tarihi OLMAYAN ifadeler."""

    def test_kanun_atfi_kampanya_tarihi_degildir(self) -> None:
        """`turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` — gold `absent`.

        Ölçülen halüsinasyon: "konutun 22/11/2001 tarihli ve 4721 sayılı Türk
        Medeni Kanununun..." ifadesinden 2001-11-22 üretiliyordu. Türk hukuk
        metinlerinin sabit atıf kalıbı "<tarih> tarihli ve <no> sayılı"dır.
        """
        metin = ("Bireysel müşterilerimizin, konut tadilatı kapsamında konutun "
                 "22/11/2001 tarihli ve 4721 sayılı Türk Medeni Kanununun ilgili "
                 "maddeleri uyarınca kullanabileceği finansmandır.")
        self.assertIsNone(extract_kampanya_suresi(metin))

    def test_ay_adi_olmayan_sozcuk_tarih_yapmaz(self) -> None:
        """Eski desen herhangi bir sözcüğü ay sanıyordu ve İLK adayda pes ediyordu.

        `pat.search` + `normalize_date is None -> return None` kombinasyonu,
        sahte bir adayın belgedeki GERÇEK tarihi tamamen gölgelemesine yol
        açıyordu.
        """
        metin = ("Ürün 12 taksit 2026 kampanyası kapsamındadır. "
                 "Kampanya 31.12.2026 tarihine kadar geçerlidir.")
        self.assertEqual(_tarih(metin), "2026-12-31")

    def test_takvimde_olmayan_tarih_kabul_edilmez(self) -> None:
        """31 Haziran yoktur; tahmin edilmez (bkz. `normalize._iso`)."""
        self.assertIsNone(extract_kampanya_suresi(
            "Kampanya 31.06.2026 tarihine kadar geçerlidir."))


if __name__ == "__main__":
    unittest.main()
