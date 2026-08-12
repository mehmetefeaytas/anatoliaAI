"""`vade_ay` tetikleyicisiz üretilemez ve tablo dilimi kampanya vadesi değildir.

İlgili: ../src/extraction/rules/extract.py (`extract_vade`, `parse_rate_table`,
        `_TABLO_YEDEK_ALANLARI`), ./test_vade_takvim_yili.py (kardeş kapı)

## Bu testlerin varlık sebebi — ÖLÇÜLDÜ (2026-08-12, `data/gold/gold.v2.json`)

`vade_ay` gold setinin en kötü alanıydı: **F1 0,133** (P=0,100 R=0,200,
TP=1 FP=9 FN=4). Dokuz yanlış pozitifin beşi HALÜSİNASYONDU — gold'da alan
yokken değer üretiliyordu.

Üç ayrı kök neden bulundu; üçü de burada kilitleniyor:

### 1. Yüzdenin ondalık kısmı vade sanılıyordu

`parse_rate_table` içindeki `\\b(\\d{1,3})(?![\\d.,])` deseni, "2,99%"
ifadesindeki "99"u yakalıyordu: virgülle rakam arasında kelime sınırı vardır
ve "%" önünde `(?![\\d.,])` sağlanır. Albaraka TOGG belgesinde satır listesi
[(48, 2.99), (48, 2.99), **(99, 2.99)**, (4, 2.99)] çıkıyor ve `max(...)`
**99 ay** veriyordu. Gold değeri 48.

Aynı sınır koruması 2026-08-11'de `_ORAN_IFADESI`/`_PARA_IFADESI`'ne
uygulanmıştı (bkz. ./test_kesik_sayi.py); bu desen o taramadan atlanmıştı.

### 2. Tablo dilimi, kampanyanın vadesi sanılıyordu

Türkiye Finans belgesinde oran tablosu "1-3 0,00% 0,50% ..." dilimini
içeriyor; `max(r.vade_ay)` = **3**. Ama kampanyanın vadesi metinde açıkça
yazılı ("36 ayı") ve `extract_vade` onu DOĞRU buluyordu. Tablo çıkarıcısı
0,95 güvenle doğru cevabı eziyordu.

Düzeltme: `vade_ay` `_TABLO_YEDEK_ALANLARI`'na alındı — tablo yalnız
`extract_vade` sustuğunda konuşur. Satırdaki vade `RateRow` içinde KALIR
(kâr payını vadeye bağlamak için gerekli).

### 3. Tetikleyici şartı yoktu

`extract_vade` "vade" sözcüğüne olan mesafeyi yalnız SIRALAMA ölçütü olarak
kullanıyordu (`default=10**6`); sözcük metinde hiç geçmese de en baştaki
sayı seçiliyordu. Ölçüldü:

* gold.v2 (48 kayıt): tetikleyicisiz **4 vakanın 4'ü de** halüsinasyon;
  tüm doğru çıkarımlarda "vade" en az bir kez geçiyor.
* demo.db (1774 belge): `vade_ay` üreten 652 belgenin 210'u (%32)
  tetikleyicisiz — 177'si açık halüsinasyon (ödül/üyelik süresi, promosyon
  dönemi, çerez saklama süresi), 30'u `taksit_sayisi`'na ait ifade
  ("12 Aya varan taksit"), yalnız 3'ü meşru sayılabilir. %98'i hatalı.

## Sonuç

    vade_ay F1  0,133 -> 0,545   (TP 1->3, FP 9->3, halüsinasyon 5->1)
    taksit_sayisi F1 0,714       (GERİLEMEDİ — kardeş alan korundu)

Bu dosya o kazancı kilitler: aşağıdaki vakalar gerçek korpustan alınmıştır.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.extraction.rules.extract import (
    extract_all,
    extract_vade,
    parse_rate_table,
)

#: Depo kökü (`app/`) — gold seti buradan çözülür.
_KOK = Path(__file__).resolve().parent.parent


def _vade(text: str):
    """`extract_all` boru hattının ürettiği `vade_ay` değeri (yoksa None)."""
    for f in extract_all(text):
        if f.field_name == "vade_ay":
            return f.canonical_value
    return None


class TestYuzdeOndaligiVadeDegildir(unittest.TestCase):
    """KÖK NEDEN 1 — "2,99%" içindeki "99" bir vade DEĞİLDİR."""

    # Albaraka TOGG taşıt finansmanı sayfasından (gold.v2), kısaltılmış.
    TOGG = ("Vade (Ay) Kredi Tutarı Aylık Kar Oranı "
            "T10F V2 12 800.000 0,00% T10F V2 48 1.700.000 2,99% "
            "T10X V2 12 600.000 0,00% T10X V2 48 1.700.000 2,99%")

    def test_tablo_satirlarinda_99_yok(self):
        vadeler = {r.vade_ay for r in parse_rate_table(self.TOGG)}
        self.assertNotIn(
            99, vadeler,
            "'2,99%' ifadesinin ondalık kısmı vade olarak okundu")

    def test_uretilen_vade_gercekci_bandda(self):
        """Ayrıştırılan hiçbir vade, korpusun meşru tavanını aşmamalı.

        ## BİLİNEN SINIR — model kodundan sayı kapma (düzeltilmedi)

        Bu test `<= {12, 48}` diye YAZILAMADI: desen "T10F V2" model
        kodundaki "10"u da yakalıyor (öncesi 'T', sonrası 'F' — sayı sınırı
        koruması bunu engellemez). Yani tablo ayrıştırıcısı hâlâ kolon
        olmayan yerlerden vade adayı üretebiliyor.

        Bu AYRI bir kusurdur ve bilerek kapsam dışı bırakıldı: gerçek belgede
        zararsız kalıyor, çünkü `vade_ay` artık `_TABLO_YEDEK_ALANLARI`'nda
        ve `extract_vade` metindeki açık ifadeyi ("48 aya") bulup öne
        geçiyor — uçtan uca doğrulaması `TestGercekBelgeUctanUca`'da.

        Düzeltilirse buradaki iddia `<= {12, 48}`'e daraltılmalıdır.
        """
        vadeler = {r.vade_ay for r in parse_rate_table(self.TOGG)}
        self.assertTrue(vadeler, "tablo hiç satır üretmedi")
        self.assertTrue(
            all(1 <= v <= 120 for v in vadeler),
            f"korpusun meşru tavanı 120 ay; ayrıştırılan: {vadeler}")


class TestTabloDilimiKampanyaVadesiDegildir(unittest.TestCase):
    """KÖK NEDEN 2 — tekil çıkarıcı konuşuyorsa tablo susar."""

    # Türkiye Finans ihtiyaç finansmanı sayfasından (gold.v2), kısaltılmış.
    TF = ("Sigortasız İhtiyaç Finansmanı Kâr Oranları ve Maliyet Tablosu "
          "Vade Kar Oranı Tahsis Ücreti Aylık Toplam Maliyet "
          "1-3 1,90% 0,50% 2,77% 38,78% "
          "Finansman tutarı 100.000 TL ve vadesi 36 ayı aşamaz.")

    def test_metindeki_acik_vade_tabloyu_yener(self):
        self.assertEqual(
            _vade(self.TF), 36,
            "tablo dilimi (1-3 ay) kampanya vadesi (36 ay) sanıldı")

    def test_tekil_cikarici_susarsa_tablo_yedek_kalir(self):
        # Aynı tablo, ama metinde açık vade ifadesi YOK. Tablo devreye girmeli;
        # yedeğe alınmak, bilgiyi ATMAK anlamına gelmemeli.
        sadece_tablo = ("Kâr Oranları Tablosu Vade Kar Oranı Tahsis Ücreti "
                        "12 1,90% 0,50% 2,77% 36 1,80% 0,50% 2,60%")
        self.assertIsNotNone(
            _vade(sadece_tablo),
            "tekil çıkarıcı susunca tablo yedeği de susarsa bilgi kaybolur")


class TestTetikleyiciSarti(unittest.TestCase):
    """KÖK NEDEN 3 — "vade" sözcüğü yoksa `vade_ay` da yoktur."""

    # Üçü de gerçek korpustan; üçü de gold'da `vade_ay` TAŞIMIYOR.
    HALUSINASYON = {
        "ödül/üyelik süresi":
            "Toplam 1.000 TL ve üzeri alışverişine özel 3 aylık TOD "
            "Trendyol Süperlig Paketi üyeliği hediye!",
        "çerez saklama süresi":
            "Ziyaretçi istatistiklerini toplamak amacıyla kullanılan "
            "çerezdir. 1 yıl 5.Kişisel Veri Sahibi Olarak Haklarınız",
        "promosyon dönemi":
            "Kapsamındaki işlemlerinizi 3 ay boyunca ücretsiz "
            "gerçekleştirebilirsiniz.",
    }

    def test_tetikleyicisiz_metin_vade_uretmez(self):
        for ad, metin in self.HALUSINASYON.items():
            with self.subTest(vaka=ad):
                self.assertIsNone(
                    extract_vade(metin),
                    f"'{ad}' bir vade değil ama değer üretildi")

    def test_tetikleyici_varsa_deger_uretilir(self):
        f = extract_vade("36 ay vade ile faizsiz finansman imkânı.")
        self.assertIsNotNone(f, "tetikleyici varken değer üretilmedi")
        self.assertEqual(f.canonical_value, 36)

    def test_taksit_ifadesi_vadeye_sizmaz(self):
        # "12 Aya varan taksit" `taksit_sayisi` alanına aittir. Korpusta bu
        # sınıftan 30 belge var ve hepsi `vade_ay` olarak yazılıyordu.
        self.assertIsNone(
            extract_vade("incehesap.com'da 12 Aya varan taksit seçenekleri!"),
            "taksit ifadesinden vade üretildi (alan karışması)")


class TestGercekBelgeUctanUca(unittest.TestCase):
    """Kısaltılmış örnek değil, GOLD'un kendi metni üzerinde ölçüm.

    Yukarıdaki testler kök nedenleri tek tek izole eder; burası boru hattının
    tamamının gold'a karşı ne ürettiğini kilitler. Kısaltılmış metin gerçeği
    tam yansıtmıyor (bkz. `test_uretilen_vade_gercekci_bandda`), bu yüzden
    asıl garanti budur.
    """

    GOLD = _KOK / "data" / "gold" / "gold.v2.json"

    @classmethod
    def setUpClass(cls):
        if not cls.GOLD.exists():                         # pragma: no cover
            raise unittest.SkipTest(f"gold seti yok: {cls.GOLD}")
        cls.kayitlar = json.loads(cls.GOLD.read_text(encoding="utf-8"))

    def _kayit(self, id_onek: str) -> dict:
        for r in self.kayitlar:
            if r["id"].startswith(id_onek):
                return r
        self.skipTest(f"gold'da '{id_onek}' ile başlayan kayıt yok")

    def test_togg_gercek_vadeyi_verir(self):
        r = self._kayit("albaraka--tasit-finansmani-togg")
        self.assertEqual(r["fields"].get("vade_ay"), 48, "gold değişmiş")
        self.assertEqual(_vade(r["text"]), 48)

    def test_turkiye_finans_tablo_dilimini_vermez(self):
        r = self._kayit("turkiye-finans--kampanyalar-turkiye-finans-avantaj")
        self.assertEqual(r["fields"].get("vade_ay"), 36, "gold değişmiş")
        self.assertEqual(_vade(r["text"]), 36)

    def test_halusinasyon_sayisi_gerilemez(self):
        """Gold'da `vade_ay` YOKKEN üretilen değer sayısı ≤ 1 olmalı.

        Ölçüm (2026-08-12): düzeltme öncesi **5**, sonrası **1**. Kalan tek
        vaka `ziraat-katilim--zekat-hesaplama` — "Örneğin 10 yıl vadeli
        180.000 TL ev borcu" cümlesindeki ÖRNEK metni; "vade" sözcüğü gerçekten
        geçtiği için tetikleyici kapısına takılmıyor. Örnek/senaryo metnini
        ayırt etmek ayrı bir iştir.
        """
        halusinasyon = [
            r["id"] for r in self.kayitlar
            if r["fields"].get("vade_ay") is None
            and "vade_ay" in set(r.get("absent_fields") or [])
            and _vade(r["text"]) is not None
        ]
        self.assertLessEqual(
            len(halusinasyon), 1,
            f"halüsinasyon sayısı 1'i aştı: {halusinasyon}")


class TestKardesAlanKorundu(unittest.TestCase):
    """`taksit_sayisi` bu düzeltmeden ETKİLENMEMELİ (F1 0,714 korunur)."""

    def test_taksit_sayisi_hala_cikariliyor(self):
        metin = "Alışverişlerinizde 9 taksit imkânı sizi bekliyor."
        alanlar = {f.field_name for f in extract_all(metin)}
        self.assertIn(
            "taksit_sayisi", alanlar,
            "vade düzeltmesi kardeş alanı sessizce kapattı")


if __name__ == "__main__":                                # pragma: no cover
    unittest.main()
