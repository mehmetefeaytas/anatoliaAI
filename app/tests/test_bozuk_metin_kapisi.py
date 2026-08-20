"""Bozuk PDF metni kapısı — CI'ı kıran gerçek ihlalin testi.

İlgili: ../src/extraction/rules/_ortak.py (`bozuk_metin`)
        ../src/extraction/rules/kosullar.py (kapının uygulandığı iki nokta)

## Neden bu dosya var

21 Ağustos 2026'da jüri 3. turu `eval.properties` denetiminin HEAD'de **2
ihlal** verdiğini ve CI'ın dört commit'tir kırmızı olduğunu buldu. İhlal
GERÇEKTİ ve kökü veriydi: son PDF hasadında bir Albaraka sözleşmesinin metni,
gömülü yazı tipinin ToUnicode tablosu olmadığı için okunamaz çıkmıştı. Bu çöp
metin `kampanya_kosullari` kalemi olarak seçiliyor, kalem cümle sonu
noktalaması taşımadığı için P3 denetiminin eklediği alakasız cümle kaleme
YAPIŞIYOR ve "alakasız ekleme çıkarımı değiştirdi" ihlali doğuyordu.

İki şeyi birden koruyoruz:

1. **Ölçüt iki bozulma sınıfını da yakalar.** Mojibake (okunamaz) ve kerning
   parçalanması (okunabilir ama sözcük içi boşluklu). Aşağıdaki vakalar canlı
   korpustan alınmış GERÇEK örneklerdir, uydurma değil.
2. **Ölçüt gerçek koşulu ELEMEZ.** Ölçülen boşluğun (0,222 – 0,571) sağ
   tarafındaki en kötü gerçek kalem de burada; eşik ona dokunmamalı. Kapı
   fazla hevesli olursa 2.218 meşru kalemi çöpe atardı.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules._ortak import (_BOZUK_ASGARI_JETON,
                                         _BOZUK_UZUN_JETON_ORANI,
                                         bozuk_metin)
from src.extraction.rules.kosullar import extract_kampanya_kosullari

#: MOJİBAKE — ToUnicode tablosu olmayan gömülü yazı tipi. Canlı korpustan:
#: albaraka/docs/gecmis-tarihli-arac-kredisi-sozlesmesi-pdf.txt
MOJIBAKE = ("M$ 9GIHI A & & 9PPP1 # ,$ 1& 9 )! F /151 #M$ 9 / $ 9 9 9 - "
            "F /151 #@)M$9 &*#& ' 9 &/ 0 9 9 9")

#: İkinci mojibake örneği (ölçülen en düşük oran: 0,123'ün altındaki sınıf).
MOJIBAKE_2 = "9 5G 1 51=111N0>5102 -131:05=1:>01 ?1+/6431=10 ?1+/7.?1+/-205=1-21?11?-2."

#: KERNİNG PARÇALANMASI — okunabilir Türkçe, sözcük içi boşluklu.
#: Vakıf Katılım PDF'lerinden; metin çöp DEĞİL ama kalem olarak kullanılamaz.
KERNING = ("M ü ş t eri ö d e n ecek t u t arı Ba n k a n e z d i n d eki "
           "h esa b ı n a e n g eç ö d e r")
KERNING_2 = ("P o s t a, e - p o s t a, S M S gi b i g ü v e n li şi f r eleme "
             "içerm e y e n il e Ɵşim")

#: SAĞLAM kalemler. Sondaki iki tanesi ölçümde EN RİSKLİ olanlar:
#: - "10.000 TL ve üzeri…" ölçülen en düşük GERÇEK oran (0,571)
#: - "3 ay, 6 ay … vadeli" sayı jetonları sayılsaydı 0,25 çıkıp yanlışlıkla
#:   elenecekti; ölçüt sayıları saymadığı için 0,40 çıkıyor ve geçiyor.
SAGLAM = (
    "18 yaşını doldurmuş olmak ve kampanya süresi içinde başvuru yapmak gerekir",
    "Kampanyadan yalnızca yeni müşteriler bir kez yararlanabilir",
    "10.000 TL ve üzeri harcamalara 500 TL indirim verilir.",
    "3 ay, 6 ay (en fazla 180 gün) veya 12 ay (en fazla 365 gün) vadeli olarak açılabilir",
)


class TestOlcut(unittest.TestCase):
    def test_mojibake_yakalanir(self) -> None:
        for metin in (MOJIBAKE, MOJIBAKE_2):
            with self.subTest(metin=metin[:30]):
                self.assertTrue(bozuk_metin(metin))

    def test_kerning_parcalanmasi_yakalanir(self) -> None:
        for metin in (KERNING, KERNING_2):
            with self.subTest(metin=metin[:30]):
                self.assertTrue(bozuk_metin(metin))

    def test_saglam_kalem_elenmez(self) -> None:
        for metin in SAGLAM:
            with self.subTest(metin=metin[:40]):
                self.assertFalse(
                    bozuk_metin(metin),
                    "kapı fazla hevesli: meşru koşul eleniyor")

    def test_kisa_parcada_cekimser_kalir(self) -> None:
        """Ölçülemeyecek kadar kısa parçada karar verilmez.

        "6 Ay" gibi bir parçada oran istatistiği anlamsız. Kapı `False`
        döner — uydurma bir karar vermek yerine çekimser kalır.
        """
        for metin in ("6 Ay", "TL", "A B C", "%0 kâr payı"):
            with self.subTest(metin=metin):
                self.assertFalse(bozuk_metin(metin))

    def test_bos_girdi_patlamaz(self) -> None:
        self.assertFalse(bozuk_metin(""))
        self.assertFalse(bozuk_metin("   "))

    def test_harfsiz_uzun_dizi_bozuk_sayilir(self) -> None:
        """Yalnız sayıdan oluşan uzun dizi de kalem olamaz.

        Yoğunluk bacağı bunu yakalıyor ve bu DOĞRU sonuç: 23 karakterlik bir
        rakam dizisi "bozuk metin" olmasa da bir koşul cümlesi değildir.
        Testin ilk hâli `False` bekliyordu — o beklenti tek bacaklı ölçütün
        kalıntısıydı ve ölçüm ikinci bacağı gerektirdiğinde düzeltildi.
        """
        self.assertTrue(bozuk_metin("123 456 789 000 111 222"))

    def test_esik_olculen_bosluk_icinde(self) -> None:
        """Eşik, ölçülen boşluğun (0,222 – 0,571) İÇİNDE kalmalı.

        Boşluğun dışına taşan bir eşik ya bozuk kalemi geçirir ya meşru
        kalemi eler. Bu test eşiği dondurmuyor, boşlukta tutuyor.
        """
        self.assertGreater(_BOZUK_UZUN_JETON_ORANI, 0.222)
        self.assertLess(_BOZUK_UZUN_JETON_ORANI, 0.571)
        self.assertGreaterEqual(_BOZUK_ASGARI_JETON, 3)


class TestKosullaraBaglandi(unittest.TestCase):
    """Kapı `kosullar.py`de GERÇEKTEN uygulanıyor mu?

    Ölçüt doğru olup çağrılmazsa hiçbir şey değişmez — bu depoda beş kez
    olmuş bir hata (kural var, kapısı yok).
    """

    def test_bozuk_metinden_kosul_cikarilmaz(self) -> None:
        # Tetikleyici sözcük ("gerekir") EKLENEREK bozuk metnin süzgeçten
        # yalnız bozukluk ölçütüyle düştüğü garanti ediliyor.
        metin = f"Kampanya Koşulları {MOJIBAKE} gerekir"
        sonuc = extract_kampanya_kosullari(metin)
        if sonuc is not None:
            for kalem in sonuc.canonical_value:
                self.assertNotIn(
                    "9GIHI", kalem,
                    "okunamaz PDF metni koşul olarak sunuluyor")

    def test_saglam_kosul_hala_cikariliyor(self) -> None:
        metin = ("Kampanya Koşulları: 18 yaşını doldurmuş olmak ve kampanya "
                 "süresi içinde başvuru yapmak gerekir.")
        sonuc = extract_kampanya_kosullari(metin)
        self.assertIsNotNone(sonuc, "kapı meşru koşulu da elemiş")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
