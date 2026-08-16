"""Kâr payı oranı: BOZUK HESAPLAMA ARACI penceresi reddedilir, gerçek %0 durur.

İlgili: src/extraction/rules/extract.py
        (`_SIFIR_TUTAR_RE`, `_ARAC_HATASI_RE`, `_bozuk_hesaplama_araci`)

## Bu testin varlık sebebi

Banka sitelerindeki finansman hesaplama araçları JavaScript ile doldurulur.
Scrape anında servis cevap vermediğinde widget BAŞLANGIÇ durumunda donuyor ve
HTML'e şu iskelet düşüyordu:

    "… Service unavailable ! Kâr Oranını Kendim Belirleyeceğim
     Aylık Taksit Tutarı 0 TL Ödenecek Toplam Tutar 0 TL Aylık Kâr Oranı % 0"

Buradaki "% 0" bir kampanya değil, DOLDURULMAMIŞ bir form alanıdır. Kural yine
de etiket + değer görüp `kar_payi_orani = 0.0` üretiyor, üstelik `%` işaretli
olduğu için makullük bandına da takılmadan `0.95` güvenle tabloya giriyordu.

ÖLÇÜLDÜ (2026-08-16, `data/demo.db`, 70 `kar_payi_orani` kaydı): 15 kayıt
sıfır değerliydi, **7'si** bu bozuk widget'tan geliyordu. Demonun manşet
sorusu ("en düşük kâr payı hangi bankada?") bu alanı sıralıyor ve sıfır her
zaman tepede çıkıyor — hata sessiz değil VİTRİNDEYDİ.

## Testin iki yönü

Kapı iki yönden de bağlanmalı, yoksa düzeltme yeni bir hata olur:

    REDDET  — pencerede sıfır tutar / araç hata metni var (sayfa boş yüklendi)
    TUT     — gerçek %0 promosyonu; pencerede tutar ve vade DOLU

Ayrım BANKA ADINDAN DEĞİL pencerenin kendisinden kurulur; aşağıdaki tüm
metinler korpustan birebir alınmıştır.
"""

from __future__ import annotations

import logging
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.extraction.rules.extract import extract_kar_payi


def _oran(text: str):
    field = extract_kar_payi(text)
    return field.canonical_value if field else None


# --------------------------------------------------------------------------- #
# Korpustan birebir alınmış bozuk widget iskeletleri (7 kaydın 4 tekil sayfası)
# --------------------------------------------------------------------------- #
_ISKELET = (
    "İhtiyaç Finansmanı için hesaplamanız Kar oranı limitler dışında ! "
    "Lütfen kontrol edip tekrar deneyiniz. Service unavailable ! "
    "Kâr Oranını Kendim Belirleyeceğim Aylık Taksit Tutarı 0 TL "
    "Ödenecek Toplam Tutar 0 TL Aylık Kâr Oranı % 0 Ödeme Planı "
)


class BozukHesaplamaAraciREDDEDILIR(unittest.TestCase):
    """demo.db'deki 7 sahte %0 kaydının tamamı bu sınıftan geliyordu."""

    def test_arac_finansmani_sayfasi(self):
        """dunya-katilim/arac-finansmani (korpusta 2 kopya)."""
        self.assertIsNone(_oran(
            "Müşterilerine bütçelerine en uygun ödeme planlarını oluşturma "
            "imkânı tanır. Finansal Hesaplama *12 yaşa kadar olan "
            "otomobillerde ikinci el araç finansmanı sağlanmaktadır. "
            + _ISKELET
            + "Gerekli Belgeler Taşıt finansmanı başvurularında talep edilen "
              "belgeler, başvuru sahibinin statüsüne göre belirtilmiştir."))

    def test_cevre_dostu_arac_sayfasi(self):
        """dunya-katilim/cevre-dostu-arac-finansmani (korpusta 2 kopya)."""
        self.assertIsNone(_oran(
            "Böylece hem çevreyi koruyan bir tercih yapabilir hem de "
            "bütçenizi rahatlatan bir çözüme kolayca ulaşabilirsiniz. "
            "Hesaplama Aracı Finansal Hesaplama "
            + _ISKELET
            + "Çevre Dostu Araç Finansmanının Özellikleri Nelerdir?"))

    def test_ihtiyac_finansmani_sayfasi(self):
        """dunya-katilim/ihtiyac-finansmani (korpusta 2 kopya)."""
        self.assertIsNone(_oran(
            "* Tahsis ücreti müşteriden peşin olarak tahsil edilecektir. "
            "Ödenecek toplam tutar finansman tahsis ücretini "
            "içermemektedir. Bu tablo bilgi amaçlıdır. "
            + _ISKELET
            + "Başvuru Şartları 18 yaşını doldurmuş olmak."))

    def test_konut_finansmani_sayfasi(self):
        """dunya-katilim/konut-finansmani (korpusta 1 kopya)."""
        self.assertIsNone(_oran(
            "Dünya Katılım Bankası A.Ş.'ni hiçbir şekilde taahhüt altına "
            "sokmaz. " + _ISKELET
            + "Konut Finansmanı Özellikleri Nedir Sıfır ve 2. El konutlar "
              "için fonlama yapılabilmektedir."))


class HerIkiIsaretTekBasinaYETER(unittest.TestCase):
    """Kapının iki bacağı bağımsızdır; birinin kaçırdığını diğeri tutmalı."""

    def test_yalniz_sifir_tutar(self):
        """Hata metni olmadan da sıfırlanmış tutarlar tek başına delildir."""
        self.assertIsNone(_oran(
            "Finansal Hesaplama Aylık Taksit Tutarı 0 TL "
            "Ödenecek Toplam Tutar 0 TL Aylık Kâr Oranı % 0 Ödeme Planı"))

    def test_yalniz_arac_hata_metni(self):
        """Sıfır tutar bloğu olmadan da hata metni tek başına delildir."""
        self.assertIsNone(_oran(
            "Finansal Hesaplama Service unavailable ! "
            "Kâr Oranını Kendim Belirleyeceğim Aylık Kâr Oranı % 0"))

    def test_ondalikli_sifir_tutar(self):
        """Widget bazı sayfalarda '0,00 TL' basıyor — aynı boş durum."""
        self.assertIsNone(_oran(
            "Aylık Taksit Tutarı 0,00 TL Ödenecek Toplam Tutar 0,00 TL "
            "Aylık Kâr Oranı % 0"))


class GercekSifirPromosyonuTUTULUR(unittest.TestCase):
    """Bu testin KALBİ: gerçek %0 kampanyaları kesilmemeli.

    Hepsinde ortak olan şey — pencerede tutar (ve çoğunda vade) DOLU.
    """

    def test_albaraka_vade_farksiz_kampanyasi(self):
        """demo.db id=2051 — tutar dolu (40.000 TL)."""
        self.assertEqual(_oran(
            "Kâr payı yok. Beklemek yok. 140.000 TL'ye kadar vade farksız "
            "destek Albaraka'da! Şimdi Albaraka Mobil'den müşteri olanlar, "
            "%0 kâr payı ile 40.000 TL'ye kadar Pratik Finansman Kart "
            "(İhtiyaç Finansmanı) kullanabiliyor."), 0.0)

    def test_turkiye_finans_emekliler_kampanyasi(self):
        """demo.db id=2344 — tutar (50.000 TL) VE vade (3 ay) dolu."""
        self.assertEqual(_oran(
            "50.000 TL'ye Kadar Kâr Paysız İhtiyaç Finansmanı kampanyası "
            "ile Mobilden Türkiye Finanslı olarak %0 kâr payı oranı ve "
            "3 ay vadeli olarak 50.000 TL'ye kadar İhtiyaç Finansmanı "
            "başvurusu yapma avantajından faydalanabilirsiniz."), 0.0)

    def test_turkiye_finans_dijital_bankacilik(self):
        """demo.db id=2339 — tutar dolu (50.000 TL)."""
        self.assertEqual(_oran(
            "Mobilden Türkiye Finanslı Ol, Kâr Paysız 50.000 TL'ye Varan "
            "İhtiyaç Finansmanını Kaçırma! Şimdi mobilden Türkiye Finanslı "
            "olanlar %0 kar payı ile 50.000 TL'ye varan İhtiyaç "
            "Finansmanından yararlanıyor."), 0.0)

    def test_kuveyt_turk_api_market(self):
        """demo.db id=1502 — ortak (LCW) adı geçen gerçek %0 beyanı."""
        self.assertEqual(_oran(
            "Yapı, ortağa bağlı olarak değişiklik gösterebilir. LCW'de "
            "%0 kar payıyla kullanılmak üzere finansman API'ları açıktır."),
            0.0)

    def test_emlak_katilim_ucret_tablosu_TUTAR_KOLONU(self):
        """demo.db id=4036 — en dar regresyon: pencerede '0 TL' VAR ama meşru.

        "0 TL" burada ücret tablosunun *Tutar* kolonudur, sıfırlanmış bir
        hesaplama çıktısı değil. Kapı sıfırı yalnız ETİKETİNE BİTİŞİK
        aradığı için bu kayıt korunur. Çıplak "0 TL" aransaydı düşerdi.
        """
        self.assertEqual(_oran(
            "Banka, Akdi Kâr Payı'nı ve Gecikme Cezası'nı azami oranları "
            "geçmemek şartıyla arttırmaya yetkilidir. "
            "Adı Oranı Tutar Tahsilat Periyodu Açıklama "
            "Aylık Akdi Kâr Payı Oranı %0 0 TL Ekstre Dönemlerinde Asgari "
            "ödeme tutarı ve üzerinde ödeme yapılması halinde ödeme "
            "yapacağınız güne kadar uygulanacak kâr payı oranıdır."), 0.0)

    def test_emlak_katilim_temel_bankacilik_formu(self):
        """demo.db id=4051 — ücret listesinde '0 TL' var, oran yine meşru."""
        self.assertEqual(_oran(
            "Emlak Katılım Paraf Troy Kart Ücreti Şube 0 TL Kredi kartı "
            "ürününün sunduğu hizmetler doğrultusunda alınan yıllık "
            "ücrettir. 04.11.2024 Akdi Kâr Payı Oranı Şube %0 Kredi "
            "kartının asgari ödeme tutarının ödendiği durumda ekstre "
            "borcunun ödenmeyen kısmına yansıtılan orandır."), 0.0)


class SaglamHesaplamaAraciTUTULUR(unittest.TestCase):
    """Kapı widget DÜZENİNE değil, SIFIRLANMIŞ çıktıya bakar."""

    def test_dolu_tutarli_hesaplama_araci(self):
        """Aynı widget, veri DOLU — oran gerçektir ve tabloya girmeli."""
        self.assertEqual(_oran(
            "Finansal Hesaplama Aylık Taksit Tutarı 1.250,00 TL "
            "Ödenecek Toplam Tutar 45.000,00 TL Aylık Kâr Oranı %3,99 "
            "Ödeme Planı"), 3.99)

    def test_tom_katilim_gizli_hata_kutusu(self):
        """demo.db cid=1602 — kapının ilk sürümü bu GERÇEK kaydı düşürmüştü.

        Sayfada "Bir hata oluştu…" cümlesi var ama araç hesaplamış: taksit
        ve geri ödeme tutarları DOLU. Hata metni tek başına "veri yok"un
        kanıtı değil, yalnız şüphesidir; karar tutarlara bakar.
        """
        self.assertEqual(_oran(
            "Finansman Tutarı TL 5.000 TL 150.000 TL Vade Ay 1 Ay 36 Ay "
            "Hesapla Aylık Kâr Oranı: 3,99 % Taksit Tutarı: 1.981,98 TL "
            "Geri Ödenecek Tutar 11.891,83 TL Ödeme Planını Görüntüle "
            "Bir hata oluştu, lütfen tekrar deneyin veya ilgili sayfayı "
            "yenileyin."), 3.99)

    def test_dolu_tutar_hata_metnini_gecersizler(self):
        """Sağlamlık kanıtı, bozukluk şüphesini yener — kapı sırası budur."""
        self.assertEqual(_oran(
            "Service unavailable ! Aylık Taksit Tutarı 1.981,98 TL "
            "Aylık Kâr Oranı %2,49"), 2.49)

    def test_sifir_tutar_uzak_pencerede_bulasmaz(self):
        """Sıfır tutar bloğu ±240 karakterin dışındaysa değere bulaşmaz."""
        uzak = "Bu tablo bilgi amaçlıdır ve taahhüt niteliği taşımaz. " * 8
        self.assertEqual(_oran(
            "Aylık Taksit Tutarı 0 TL " + uzak
            + "Taşıt finansmanında %4,19 kar payı oranı ile sahip olun."),
            4.19)


class RetIzlenebilir(unittest.TestCase):
    """Sessiz eleme, sessiz uydurma kadar izlenemezdir (CLAUDE.md §19)."""

    def test_ret_gerekcesi_loglanir(self):
        with self.assertLogs(
                "src.extraction.rules.extract", level=logging.DEBUG) as kayit:
            self.assertIsNone(_oran(_ISKELET))
        birlesik = "\n".join(kayit.output)
        self.assertIn("bozuk hesaplama aracı", birlesik)
        self.assertIn("neden=", birlesik)


if __name__ == "__main__":
    unittest.main()
