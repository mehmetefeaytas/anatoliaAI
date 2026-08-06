"""D2 — tahsis ücreti: yüzdeli ifadeler ve hesap katmanı.

Mentörlük toplantısında tespit edilen çıkarım hatası (aksiyon planı §5.1-D2):
"yüzdeli ifadelerde hesaplama yapmıyor".

## Ölçüm (2026-08-07, `data/raw` altındaki 1759 belge)

    tahsis/dosya masrafı tetikleyicisi olan belge : 101
      ücreti ORAN olarak veren belge              :  62
        hiçbir değer üretilmeyen                  :  51
        oranı TL TUTARI sanan                     :   1   ("%0,25" -> 0,25 TL)

İkinci satır birincisinden tehlikeli: sessizce ~400 kat yanlış bir değer
üretiyor ve karşılaştırma tablosunda o bankayı en ucuz gösteriyordu.

Ayrıca ölçüldü: oran tablosu başlığında "Tahsis Ücreti"nden sonra gelen ilk
sayı komşu KOLONA aitti (kâr oranı %3,67 tahsis ücreti sanılıyordu) —
`_truncate_at_next_column` bu sınıfı kapatır.

## Neden taban bilinmiyorsa hesap YOK

Ölçülen alternatif — oranı `{"rate": X}` olarak yazmak — gold'da
`tahsis_ucreti` F1'ini 0.400'den 0.333'e düşürdü (2 belgede halüsinasyon):
anotasyon kılavuzu bu alanı PARA olarak tanımlıyor, çıplak oran o sözleşmeyi
taşımıyor. Uydurulmuş bir tabanla çarpmak ise doğrudan §19 ihlali olurdu.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules.extract import extract_all, extract_tahsis_ucreti
from src.normalization import normalize as N


class TestOranIfadesiAyristirma(unittest.TestCase):
    """`binde` ile `yüzde` arasında 10 kat fark vardır; karıştırılamaz."""

    def test_yuzde_isareti(self) -> None:
        self.assertEqual(N.parse_oran_ifadesi("%2,5"), 2.5)

    def test_yuzde_sonda(self) -> None:
        self.assertEqual(N.parse_oran_ifadesi("0,50%"), 0.5)

    def test_yuzde_sozcugu(self) -> None:
        self.assertEqual(N.parse_oran_ifadesi("yüzde 0.20'si"), 0.20)

    def test_binde_onda_bir_yuzdedir(self) -> None:
        """"binde 5" = ‰5 = %0,5. Yüzde sanılırsa ücret 10 kat şişer."""
        self.assertEqual(N.parse_oran_ifadesi("binde 5'i"), 0.5)

    def test_tutar_oran_degildir(self) -> None:
        self.assertIsNone(N.parse_oran_ifadesi("500 TL"))


class TestHesapFormulSaklar(unittest.TestCase):
    """Hesaplanan değer metinde geçmez; formül olmadan açıklanamaz."""

    def test_hesap_ve_formul(self) -> None:
        kanonik, formul = N.hesapla_oransal_ucret(2.5, 100000.0)
        self.assertEqual(kanonik, {"value": 2500.0, "currency": "TRY"})
        self.assertEqual(formul, "100.000 TL × %2,50 = 2.500 TL")

    def test_taban_yoksa_hesap_yok(self) -> None:
        """CLAUDE.md §19 — girdi bilinmiyorsa uydurulmaz."""
        self.assertIsNone(N.hesapla_oransal_ucret(2.5, None))

    def test_tr_sayi_bicimi(self) -> None:
        """Formül TR gösterimiyle yazılır; kanonik değer float kalır."""
        self.assertEqual(N.bicimle_tr_sayi(2500.0), "2.500")
        self.assertEqual(N.bicimle_tr_sayi(157.5), "157,50")


class TestOranTlSanilmaz(unittest.TestCase):
    """Ölçülen sessiz hata sınıfı: yüzde ifadesinin TL tutarı sanılması."""

    def test_yuzde_tl_tutari_uretmez(self) -> None:
        """`hayat-finans/products/urun-ve-hizmet-ucretleri` — %0,25 -> 0,25 TL.

        Cümlecikte "TL" geçtiği için para birimi denetimi geçiyor, ardından
        `normalize_money` ilk sayıyı (0,25) tutar sanıyordu.
        """
        metin = "Tahsis Ücreti TL %0,25 - - Limit yenilemelerinde ücret alınır"
        f = extract_tahsis_ucreti(metin)
        self.assertIsNone(f, "oran, taban bilinmeden TL tutarına çevrilmemeli")

    def test_komsu_kolon_tahsis_ucreti_degildir(self) -> None:
        """`turkiye-finans--tasit-finansmani` — kâr oranı kolonu okunuyordu.

        "Vade Kâr Oranı Tahsis Ücreti Aylık Toplam Maliyet ... 3 3,67% 0,50%"
        satırında tetikleyiciden sonraki ilk sayı KÂR ORANI kolonuna aittir.
        """
        metin = ("Vade Kâr Oranı Tahsis Ücreti Aylık Toplam Maliyet "
                 "Yıllık Toplam Maliyet 3 3,67% 0,50% 5,07% 81,11%")
        self.assertIsNone(extract_tahsis_ucreti(metin))


class TestTabanBilindiginde(unittest.TestCase):
    """Taban biliniyorsa HESAPLANIR ve formül `source_span`'e yazılır."""

    def test_bitisik_taban_ile_hesaplanir(self) -> None:
        metin = "Tahsis ücreti 100.000 TL'nin %2,5'i kadardır"
        f = extract_tahsis_ucreti(metin)
        self.assertEqual(f.canonical_value, {"value": 2500.0, "currency": "TRY"})
        self.assertIn("100.000 TL × %2,50 = 2.500 TL", f.source_span)

    def test_belge_duzeyi_taban_extract_all_ile_gelir(self) -> None:
        """Taban metinde ADLA yazılır ("finansman tutarının"), sayıyla değil.

        `extract_all` iki alanı birlikte gördüğü için bağı kurabilir;
        `extract_tahsis_ucreti` tek başına çağrıldığında tabanı bilmez ve
        (doğru davranış olarak) hesap yapmaz.
        """
        metin = ("Finansman tutarı 200.000 TL olarak kullandırılır. "
                 "Tahsis ücreti finansman tutarının binde 5'i oranındadır")
        alanlar = {f.field_name: f for f in extract_all(metin)}
        self.assertEqual(alanlar["tahsis_ucreti"].canonical_value,
                         {"value": 1000.0, "currency": "TRY"})
        self.assertIn("hesap:", alanlar["tahsis_ucreti"].source_span)

    def test_metin_tabani_adlandirmiyorsa_hesap_yok(self) -> None:
        """`tom-katilim--hesaplama-araclari` — taban HARCAMA, kaydırıcı sınırı değil.

        Belgede 150.000 TL'lik bir tutar var ama oranın tabanı o değil:
        "%0.5 tahsis ücreti yapılan harcama üzerine eklenir". Belge tutarıyla
        çarpmak 750 TL'lik uydurma bir ücret üretirdi.
        """
        metin = ("Hesaplama aracı ile 150.000 TL tutarında finansman "
                 "kullanabilirsiniz. Veresiye kredide %0.5 tahsis ücreti "
                 "yapılan harcama üzerine eklenir")
        alanlar = {f.field_name: f for f in extract_all(metin)}
        self.assertNotIn("tahsis_ucreti", alanlar)

    def test_makul_olmayan_taban_kullanilmaz(self) -> None:
        """Ücret tarifesi PDF'lerinde `extract_tutar` 0,27 TL gibi çöp döndürüyor.

        Bu tabanla çarpım **0 TL tahsis ücreti** üretiyordu — yani "ücretsiz"
        gibi görünen uydurma bir değer. 3 belgede ölçüldü; makullük bandı
        (`confidence.PLAUSIBLE_RANGES["finansman_tutari"]`) üçünü de eler.
        """
        metin = ("Kredi tutarı 2 TL üzerinden hesaplanır. Tahsis ücreti, "
                 "tahsis edilen veya yenilenen limitin yüzde 0.20'sidir")
        alanlar = {f.field_name: f for f in extract_all(metin)}
        self.assertNotIn("tahsis_ucreti", alanlar)


class TestMevcutDavranisKorunur(unittest.TestCase):
    """Tutar ve negasyon yolları değişmemeli (gold'da TP olan vakalar)."""

    def test_acik_tutar(self) -> None:
        f = extract_tahsis_ucreti("Tahsis ücreti 500 TL olarak alınır")
        self.assertEqual(f.canonical_value, {"value": 500.0, "currency": "TRY"})

    def test_binlik_ayirici_bozulmaz(self) -> None:
        f = extract_tahsis_ucreti("Dosya masrafı 1.500,00 TL")
        self.assertEqual(f.canonical_value["value"], 1500.0)

    def test_negasyon_sifirdir(self) -> None:
        """"alınmaz" = ücret SIFIR, "bilgi yok" değil."""
        f = extract_tahsis_ucreti("TAHSİS ÜCRETİ ALINMAZ")
        self.assertEqual(f.canonical_value, {"value": 0.0, "currency": "TRY"})

    def test_tutar_oncede_ise_para_okunur(self) -> None:
        """`turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani` — gold 30.000.

        Tablo satırında tutar oranın ÖNÜNDE gelir; sıra kuralı bu vakayı
        korur (yoksa 1,69% oran sanılıp gold TP'si kaybedilirdi).
        """
        metin = "Tahsis Ücreti 30.000,00 ₺ 12 Ay 1,69% 2.841,66 ₺ 157,50 ₺"
        f = extract_tahsis_ucreti(metin)
        self.assertEqual(f.canonical_value, {"value": 30000.0, "currency": "TRY"})


if __name__ == "__main__":
    unittest.main()
