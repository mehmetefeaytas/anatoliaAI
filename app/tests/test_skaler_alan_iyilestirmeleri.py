"""Skaler alanların precision/recall temizliği — ölçülmüş her düzeltmenin kapısı.

İlgili: ../src/extraction/rules/extract.py (`extract_vade`, `_islenmis_ornek`,
        `_oran_tablosu_c`, `_TUTAR_KOLON_RE`, `_ODUL_DISI_RE`,
        `_IADE_TRIGGER_RE`, `extract_all`),
        ../data/gold/ANNOTATION_GUIDE.md §4 (`vade_ay`, `alisveris_puani`,
        `odul_miktari`, `masraf_durumu` kapsam kuralı),
        ../docs/rapor/liste-alanlari-iyilestirme.md (ölçüm defteri)

## Neden bu dosya var

gold.v2'de (48 kayıt, kural katmanı, strict) yedi skaler alan F1 1,00'ın
altındaydı ve kayıpların TAMAMI tek tek teşhis edildi. Bu dosya her
düzeltmenin ürettiği davranışı kilitler; gerekçeler ve alternatif hipotezlerin
ölçümü `extract.py` içindeki ilgili blokların başında yazılı.

Ölçülen etki (kural / strict / all):

    vade_ay          0,545 -> 1,000
    kar_payi_orani   0,800 -> 1,000
    finansman_tutari 0,857 -> 1,000
    alisveris_puani  0,667 -> 0,933
    odul_miktari     0,615 -> 0,727
    yapısal mikro    0,744 -> 0,823   ·  halüsinasyon 18 -> 15

Sayılar burada TEKRAR ÖLÇÜLMEZ (gold koşumu eval'in işi); bu dosya
davranışın kendisini tutar, böylece bir gerileme sessizce geçmez.
"""

from __future__ import annotations

import unittest

from src.extraction.rules.extract import (
    extract_alisveris_puani,
    extract_all,
    extract_odul_miktari,
    extract_vade,
    parse_rate_table,
)


def _alan(metin: str, ad: str):
    for f in extract_all(metin):
        if f.field_name == ad:
            return f
    return None


class TestVadeYuklemEki(unittest.TestCase):
    """"azami vade 10 YILDIR" — yüklem eki değeri düşürmemeli."""

    METIN = ("Hak sahiplerine kullandırılacak kâr destekli konut finansmanı "
             "için azami vade 10 yıldır. Bireysel işyeri finansmanı için ise "
             "7 yıldır.")

    def test_yuklem_ekli_vade_okunur(self) -> None:
        f = extract_vade(self.METIN)
        self.assertIsNotNone(f)
        self.assertEqual(f.canonical_value, 120)

    def test_daha_uzak_ikinci_vade_secilmez(self) -> None:
        """'vade' sözcüğüne yakınlık ölçütü korunuyor (7 yıl = 84 seçilmemeli)."""
        self.assertNotEqual(extract_vade(self.METIN).canonical_value, 84)


class TestIslenmisOrnekCumlesi(unittest.TestCase):
    """Örnek cümlesindeki sayı ürünün değeri değildir — İKİ koşullu kapı."""

    def test_sayisal_ornek_REDDEDILIR(self) -> None:
        metin = ("Sadece gelecek bir yıl içerisinde vadesi dolacak "
                 "borçlarınızı giriniz. Örneğin 10 yıl vadeli 180.000 TL ev "
                 "borcu olan kimse gelecek bir yıl içerisinde 18.000 TL borç "
                 "ödeyecekse borç olarak 180.000 TL değil 18.000 TL'yi girer.")
        f = extract_vade(metin)
        self.assertNotEqual(
            getattr(f, "canonical_value", None), 120,
            "zekât örneğindeki '10 yıl vadeli' ürün vadesi sanıldı")

    def test_tutarsiz_ornek_urun_beyani_KORUNUR(self) -> None:
        """Kapı gevşek yazılsa bu kayıt ölürdü — ölçüm 2:1'den 4:0'a taşındı."""
        metin = ("Örneğin: Kuveyt Türk Çeyiz Hesabı, minimum 3 yıl vade ile "
                 "ve sadece TL cinsinden açılır.")
        f = extract_vade(metin)
        self.assertIsNotNone(f, "örnek işareti ürün beyanını da öldürdü")
        self.assertEqual(f.canonical_value, 36)


class TestOranTablosuBicimC(unittest.TestCase):
    """Yüzde İŞARETSİZ oran tablosu (BİÇİM C) ve yapısal kapıları."""

    LEASING = ("Kampanyalı oranlarımız 12 ile 60 ay arası kullanacağınız "
               "leasing finansmanlarında geçerlidir. "
               "Vade TL Kar Oranı USD Kar Oranı EUR Kar Oranı "
               "12 Ay 4.15 0.83 0.79 24 Ay 3.90 0.83 0.79 "
               "36 Ay 3.81 0.84 0.79 48 Ay 3.81 0.90 0.79 "
               "60 Ay 3.81 0.90 0.79")

    def test_yuzdesiz_tablo_ayristirilir(self) -> None:
        satirlar = parse_rate_table(self.LEASING)
        self.assertEqual([r.vade_ay for r in satirlar], [12, 24, 36, 48, 60])
        self.assertEqual(satirlar[0].kar_payi, 4.15)

    def test_kar_payi_ARALIK_olarak_uretilir(self) -> None:
        f = _alan(self.LEASING, "kar_payi_orani")
        self.assertIsNotNone(f)
        self.assertEqual(f.canonical_value, {"min": 3.81, "max": 4.15})

    def test_ilk_satir_DEGIL_en_uzun_vade(self) -> None:
        """Tablo hücresi tablonun tamamını temsil etmez."""
        f = _alan(self.LEASING, "vade_ay")
        self.assertIsNotNone(f)
        self.assertEqual(f.canonical_value, 60)

    def test_iki_satir_TABLO_SAYILMAZ(self) -> None:
        """Hesaplama aracı widget'ı iki satır üretiyordu — asgari 3 satır."""
        metin = "Vade Kâr Oranı 1 Ay 1.93 12 Ay 1.93"
        self.assertEqual(parse_rate_table(metin), [])

    def test_azalan_vade_TABLO_SAYILMAZ(self) -> None:
        """Düz metinden devşirilen satırlar sıralı değildir."""
        metin = ("48 ay vadeye kadar tüm vadelerde uygun kâr oranıyla taşıt "
                 "finansmanı! Vade Kâr Oranı 36 ay 1.20 24 ay 1.20 12 ay 1.20")
        self.assertEqual(parse_rate_table(metin), [])


class TestTabloTutarKolonu(unittest.TestCase):
    """Tablo başlığında tutar kolonu adı geçiyorsa tutar oradan okunur."""

    TOGG = ("Maksimum 48 aya varan vade imkânı sunar. "
            "Araç Modeli Vade (Ay) Kredi Tutarı Aylık Kar Oranı "
            "T10F V2 12 800.000 0,00% T10F V2 48 1.700.000 2,99% "
            "T10X V2 12 600.000 0,00% T10X V2 48 1.700.000 2,99%")

    def test_en_yuksek_tutar_alinir(self) -> None:
        f = _alan(self.TOGG, "finansman_tutari")
        self.assertIsNotNone(f)
        self.assertEqual(f.canonical_value,
                         {"value": 1700000.0, "currency": "TRY"})

    def test_kolon_adi_YOKSA_tutar_uretilmez(self) -> None:
        """`_TAHSIS_KOLON_RE` ile aynı disiplin: başlıkta adı yoksa yoktur."""
        metin = ("Vade Kâr Oranı 12 Ay 1,50% 24 Ay 1,40% 36 Ay 1,30% "
                 "48 Ay 1,20%")
        self.assertTrue(all(r.tutar is None for r in parse_rate_table(metin)))

    def test_tablo_tutari_YEDEKTIR(self) -> None:
        """Tekil çıkarıcı konuşuyorsa tabloya bakılmaz."""
        metin = ("Finansman tutarı 250.000 TL'dir. " + self.TOGG)
        f = _alan(metin, "finansman_tutari")
        self.assertEqual(f.canonical_value,
                         {"value": 250000.0, "currency": "TRY"})


class TestMarkaPuaniOdulDegil(unittest.TestCase):
    """ParafPara TL cinsinden sadakat puanıdır -> `alisveris_puani`."""

    PARAFPARA = ("Kampanya kapsamında yapılacak 10.000 TL ve üzeri ilk "
                 "alışverişe 1.000 TL ParafPara verilecektir. Bir müşteri "
                 "kampanyadan bir defa yararlanabilir ve en fazla 1.000 TL "
                 "ParafPara kazanabilir.")

    def test_parafpara_odul_miktari_URETMEZ(self) -> None:
        self.assertIsNone(extract_odul_miktari(self.PARAFPARA))

    def test_parafpara_alisveris_puani_URETIR(self) -> None:
        f = extract_alisveris_puani(self.PARAFPARA)
        self.assertIsNotNone(f)
        self.assertEqual(f.canonical_value, {"kind": "points", "value": 1000.0})

    def test_gercek_hediye_odulu_KORUNUR(self) -> None:
        """Liste dar: marka puanı olmayan ödül düşmemeli."""
        f = extract_odul_miktari("Yeni müşterilere 500 TL hediye verilecektir.")
        self.assertIsNotNone(f)
        self.assertEqual(f.canonical_value,
                         {"value": 500.0, "currency": "TRY"})


class TestNakitIadeOrani(unittest.TestCase):
    """Nakit iade ORANI `alisveris_puani`dır; `iade ücreti` bir masraftır."""

    def test_nakit_iade_orani_okunur(self) -> None:
        f = extract_alisveris_puani(
            "A101'de her alışverişte %3'e varan nakit iade!")
        self.assertIsNotNone(f)
        self.assertEqual(f.canonical_value, {"kind": "rate", "value": 3.0})

    def test_ciplak_iade_orani_okunur(self) -> None:
        f = extract_alisveris_puani(
            "Hadi Black Kredi Kartı ile yapılan Pegasus harcamalarında "
            "%50'ye varan iade kazanılabilir.")
        self.assertIsNotNone(f)
        self.assertEqual(f.canonical_value, {"kind": "rate", "value": 50.0})

    def test_iade_UCRETI_tetiklemez(self) -> None:
        """Ücret tarifesindeki "Çek İade Ücreti 0%" ödül değildir."""
        f = extract_alisveris_puani(
            "Çek Düzeltme İşlemi Ücreti Çek İade Ücreti 0% 0% 0%")
        self.assertIsNone(f)

    def test_iade_capasi_ADET_bicimini_ACMAZ(self) -> None:
        """"iptal/iade" cümlesindeki TL tutarı puan sanılmamalı."""
        f = extract_alisveris_puani(
            "1.000 TL ve üzeri alışverişin iptal/iade edilmesi durumunda "
            "kampanyadan yararlanılamaz.")
        self.assertIsNone(f)

    def test_mil_puan_olarak_okunur(self) -> None:
        f = extract_alisveris_puani(
            "10.000 TL ve üzeri ilk harcamasına tek seferde 8.000 Mil hediye")
        self.assertIsNotNone(f)
        self.assertEqual(f.canonical_value, {"kind": "points", "value": 8000.0})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
