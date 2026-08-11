"""Sıralama, çıkarımın KENDİ güven skorunu yok sayamaz.

İlgili: ../src/comparison/compare.py (`ASGARI_GUVEN`, `rank`, `rank_advantageous`)
        ../src/chatbot/structured.py (elenen değerin gerekçesiyle görünmesi)
        ../src/api/main.py (`/compare`, `/scoring`, `/advantageous`)

## Bu testin varlık sebebi

Çıkarıcı her alana bir `confidence` yazıyordu ve sıralama o sayıya HİÇ
bakmıyordu. Sistem kendi belirsizliğini ölçüyor, sonra sıralama adımında
çöpe atıyordu. Tarayıcıda görülen sonuç:

    "Yeni müşterilere verilen araba finansman tutarı ne kadar?"
        Vakıf Katılım:  400000 TRY
        Dünya Katılım:       0 TRY      <- YANLIŞ

Kanıt penceresi sebebi söylüyordu:

    "…Belirleyeceğim Aylık Taksit Tutarı 0 TL Ödenecek Toplam Tutar 0 TL
      Aylık Kâr Oranı %0 Ödeme Planı Hemen Başvur…"

Bu, DOLDURULMAMIŞ bir hesaplama aracının varsayılan değeridir; ürünün
finansman tutarı değildir. Çıkarıcı onu zaten 0,40 güvenle işaretlemişti.
Kusur çıkarımda değil, sıralamadaydı.

## Neden bu kapı gerekli — düzeltme notu yetmez

Aynı ilke bu depoda daha önce iki kez "bir yolda doğru, diğerinde eskimiş"
hâlde bulundu (`masraf_durumu` sıfır sayımı, aralık ucu seçimi). Güven kapısı
da iki yolda yaşıyor: tek alanlı `rank()` ve bileşik `rank_advantageous()`.
Bu dosya ikisinin de kapıyı GERÇEKTEN uyguladığını ve eşiğin altında kalan
değerin SİLİNMEDİĞİNİ, gerekçesiyle görünür kaldığını kilitler.

## Eşik neden 0,65 — ölçüm

`data/gold/gold.v2.json`'un 48 belgesi `data/demo.db` ile birebir eşleşiyor.
Sayısal alanlar altın değerle karşılaştırıldığında:

    güven          doğru   yanlış   aşırı-üretim   doğruluk
    0,45–0,55        0       2           5            %0
    0,72–0,85       11       2           6           %58

Eşiğin altındaki 7 çıkarımın 7'si de hatalı ve hepsi belgenin kampanya
olmayan bölümlerinden geliyor (çerez metni, ücret tarifesi, hesap açılış
asgarisi). Korpus dağılımı da aynı yerden ayrılıyor: güven değerleri
{0,15…0,55} ve {0,65…0,95} diye iki kümede toplanıyor, arada kayıt yok.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot import structured
from src.comparison.compare import (
    ASGARI_GUVEN,
    rank,
    rank_advantageous,
)

#: Ekranda görülen gerçek vaka: hesaplama aracının doldurulmamış varsayılanı.
ARAC_PENCERESI = ("ndim Belirleyeceğim Aylık Taksit Tutarı 0 TL Ödenecek "
                  "Toplam Tutar 0 TL Aylık Kâr Or")


def _satir(bank, deger, guven, *, tur="Taşıt Finansmanı", cid=1, span=""):
    return {"bank": bank, "bank_name": bank, "canonical_value": deger,
            "confidence": guven, "source_span": span, "campaign_id": cid,
            "campaign_type": tur}


class TestGuvenKapisiTekAlan(unittest.TestCase):
    """`rank()` — eşiğin altındaki değer sıralamaya girmez ama GÖRÜNÜR."""

    def test_esik_altindaki_sifir_siralamanin_tepesine_cikmaz(self):
        """Bildirilen kusurun ta kendisi: 0 TL "en düşük" olamaz."""
        rows = [
            _satir("vakif", {"value": 400000.0, "currency": "TRY"}, 0.85),
            _satir("dunya", {"value": 0.0, "currency": "TRY"}, 0.40,
                   span=ARAC_PENCERESI),
        ]
        ranked = rank(rows, "finansman_tutari")
        kiyaslanabilir = [x for x in ranked if x.comparable]
        self.assertEqual(["vakif"], [x.bank for x in kiyaslanabilir],
                         "düşük güvenli 0 TL hâlâ kıyaslanabilir sayılıyor")

    def test_elenen_deger_SILINMEZ_gerekcesiyle_kalir(self):
        """Zayıf değeri silmek de bir tür saklamadır.

        Satır listede kalmalı, değeri okunabilmeli ve notu NEDEN elendiğini
        söylemeli — "veri yok" ile "veri güvenilmez" aynı şey değildir.
        """
        rows = [_satir("dunya", {"value": 0.0, "currency": "TRY"}, 0.40,
                       span=ARAC_PENCERESI)]
        (satir,) = rank(rows, "finansman_tutari")
        self.assertFalse(satir.comparable)
        self.assertEqual({"value": 0.0, "currency": "TRY"}, satir.value,
                         "değer düşürülmüş — bilgi gizlenemez")
        self.assertIn("düşük çıkarım güveni", satir.note or "")
        # Ölçülen güven ve eşik metinde geçmeli: kullanıcı kapalı bir kutuyla
        # değil, sayıyla karşılaşmalı.
        self.assertIn("0,40", satir.note or "")
        self.assertIn("0,65", satir.note or "")

    def test_esigin_ustundeki_deger_dokunulmadan_gecer(self):
        rows = [_satir("vakif", {"value": 400000.0, "currency": "TRY"}, 0.85)]
        (satir,) = rank(rows, "finansman_tutari")
        self.assertTrue(satir.comparable)
        self.assertIsNone(satir.note)

    def test_esik_degerinin_kendisi_GECER(self):
        """Sınır dahildir: 0,65 "düşük" değildir."""
        rows = [_satir("a", {"value": 1000.0, "currency": "TRY"},
                       ASGARI_GUVEN)]
        (satir,) = rank(rows, "finansman_tutari")
        self.assertTrue(satir.comparable)

    def test_guven_bilinmiyorsa_kapi_ATESLENMEZ(self):
        """"Bilinmiyor" ile "düşük" aynı şey değildir.

        Güven taşımayan çağıranlar (eski sözlükler, testler) aynen çalışmalı;
        olmayan bir belirsizlik iddia edilmemeli.
        """
        rows = [{"bank": "a", "bank_name": "A",
                 "canonical_value": {"value": 1000.0, "currency": "TRY"},
                 "source_span": ""}]
        (satir,) = rank(rows, "finansman_tutari")
        self.assertTrue(satir.comparable)
        self.assertIsNone(satir.note)

    def test_asil_kiyaslanamama_nedeni_guvenle_GIZLENMEZ(self):
        """Aralık zaten kıyaslanamaz; notu güvenle değiştirmek bilgi kaybıdır."""
        rows = [_satir("a", {"min": 12.0, "max": 120.0}, 0.40)]
        (satir,) = rank(rows, "vade_ay")
        self.assertFalse(satir.comparable)
        self.assertIn("aralık", satir.note or "")


class TestMesruSifirlarKorunur(unittest.TestCase):
    """Çözüm "sıfırı ele" DEĞİLDİR — korpustaki sıfırların çoğu gerçektir."""

    def test_masrafsiz_sifiri_kiyasta_kalir(self):
        """`masraf_durumu` 0 = "masrafsız"; kılavuz bunu ZORUNLU kılıyor."""
        rows = [_satir("a", {"has_fee": False, "amount": 0}, 0.95)]
        (satir,) = rank(rows, "masraf_durumu")
        self.assertTrue(satir.comparable,
                        "masrafsız kampanya kıyas dışı bırakıldı")
        self.assertEqual(0.0, satir.sort_key)

    def test_gercek_sifir_kar_payi_kampanyasi_kiyasta_kalir(self):
        """"%0 kâr payıyla" gerçek bir üründür, bilgi eksikliği değil."""
        rows = [_satir("a", 0.0, 0.95)]
        (satir,) = rank(rows, "kar_payi_orani")
        self.assertTrue(satir.comparable)

    def test_tahsis_ucreti_sifiri_kiyasta_kalir(self):
        rows = [_satir("a", {"value": 0.0, "currency": "TRY"}, 0.95)]
        (satir,) = rank(rows, "tahsis_ucreti")
        self.assertTrue(satir.comparable)


class TestGuvenKapisiBilesikSkor(unittest.TestCase):
    """`rank_advantageous()` aynı eşiği aynı gerekçeyle uygular.

    İki yüzeyin aynı değeri biri kıyaslanabilir biri değil sayması, bu depoda
    beş kez pahalıya mal olmuş "aynı karar iki yerde" hatasının bileşik
    skordaki karşılığı olurdu.
    """

    def _kampanyalar(self, guven):
        return [
            {"bank": "a", "bank_name": "A", "campaign_id": 1,
             "campaign_type": "Taşıt Finansmanı",
             "fields": {"kar_payi_orani": 1.89, "vade_ay": 36},
             "field_confidence": {"kar_payi_orani": 0.95, "vade_ay": 0.95}},
            {"bank": "b", "bank_name": "B", "campaign_id": 2,
             "campaign_type": "Taşıt Finansmanı",
             "fields": {"kar_payi_orani": 0.01, "vade_ay": 36},
             "field_confidence": {"kar_payi_orani": guven, "vade_ay": 0.95}},
        ]

    def test_dusuk_guvenli_alan_skorlanmaz(self):
        skorlar = rank_advantageous(self._kampanyalar(0.20))
        b = next(s for s in skorlar if s.bank == "b")
        bilesen = next(c for c in b.components
                       if c.field_name == "kar_payi_orani")
        self.assertIsNone(bilesen.normalized,
                          "eşik altındaki alan skora girdi")
        self.assertIn("düşük çıkarım güveni", bilesen.note or "")

    def test_dusuk_guvenli_alan_kampanyayi_CEZALANDIRMAZ(self):
        """Skorlanmayan alan "sıfır puan" değildir; kapsamayı düşürür."""
        skorlar = rank_advantageous(self._kampanyalar(0.20))
        b = next(s for s in skorlar if s.bank == "b")
        bilesen = next(c for c in b.components
                       if c.field_name == "kar_payi_orani")
        self.assertEqual(0.0, bilesen.contribution)
        self.assertLess(b.coverage, 1.0, "kapsama düşmedi")

    def test_yuksek_guvenli_ayni_deger_skoru_TEPEYE_tasir(self):
        """Kontrol grubu: fark yalnız güvenden gelmeli, değerden değil."""
        skorlar = rank_advantageous(self._kampanyalar(0.95))
        self.assertEqual("b", skorlar[0].bank,
                         "yüksek güvenli en iyi oran tepeye çıkmadı")

    def test_guven_verilmezse_kapi_ATESLENMEZ(self):
        satirlar = [dict(r) for r in self._kampanyalar(0.20)]
        for r in satirlar:
            r.pop("field_confidence")
        skorlar = rank_advantageous(satirlar)
        b = next(s for s in skorlar if s.bank == "b")
        bilesen = next(c for c in b.components
                       if c.field_name == "kar_payi_orani")
        self.assertIsNotNone(bilesen.normalized)


class TestSohbetteGerekceGORUNUR(unittest.TestCase):
    """Elenen değer chatbot cevabında da "yok" gibi görünmemeli."""

    def test_liste_satirinda_gerekce_basilir(self):
        rows = [
            _satir("vakif", {"value": 400000.0, "currency": "TRY"}, 0.85),
            _satir("dunya", {"value": 0.0, "currency": "TRY"}, 0.40,
                   span=ARAC_PENCERESI),
        ]
        ranked = rank(rows, "finansman_tutari")
        metin = structured._phrase_list("finansman_tutari", ranked, {})
        # Birim `TRY` değil `TL`: kullanıcıya dönük metinde para birimi Türkçe
        # yazılır (bkz. structured._tr_para). Testin iddiası değişmedi —
        # elenen değerin cevapta GÖRÜNMESİ.
        self.assertIn("0 TL", metin, "elenen değer cevaptan silinmiş")
        self.assertIn("düşük çıkarım güveni", metin)

    def test_hicbir_satir_kiyaslanamazsa_SEBEP_yazilir(self):
        """"Veri bulunamadı" tek başına yanıltıcıdır — veri VAR."""
        rows = [_satir("dunya", {"value": 0.0, "currency": "TRY"}, 0.40,
                       span=ARAC_PENCERESI)]
        ranked = rank(rows, "finansman_tutari")
        metin = structured._kiyaslanamaz_metni("finansman_tutari", ranked)
        self.assertIn("düşük çıkarım güveni", metin)
        self.assertIn("kıyas dışı", metin)

    def test_aile_kazanani_yoksa_SEBEP_ve_DEGER_yazilir(self):
        """Aile satırı "kıyaslanabilir veri yok" deyip susmamalı."""
        rows = [_satir("kuveyt", 60.0, 0.45, tur="Alışveriş Puanı")]
        ranked = rank(rows, "vade_ay")
        metin = structured._phrase_superlative_by_type(
            "vade_ay", "lowest", [("Alışveriş Puanı", None, ranked)])
        self.assertIn("60 ay", metin, "elenen değer görünmüyor")
        self.assertIn("düşük çıkarım güveni", metin)


class TestKorpusOlcumu(unittest.TestCase):
    """Eşiğin korpustaki etkisi — sayı değişirse test söyler.

    Bu sınıf `data/demo.db` yoksa atlanır: demo veri tabanı depoda tutulmuyor
    ve testin varlığı ona bağlı olmamalı.
    """

    DB = Path(__file__).resolve().parents[1] / "data" / "demo.db"

    def setUp(self):
        if not self.DB.exists():
            self.skipTest("data/demo.db yok")
        import sqlite3
        self.conn = sqlite3.connect(f"file:{self.DB}?mode=ro", uri=True)
        self.addCleanup(self.conn.close)

    def _sifirlar(self, alan):
        """Bir alanın sıfır değerli kayıtlarının güvenleri."""
        import json
        out = []
        for cv, guven in self.conn.execute(
                "SELECT canonical_value, confidence FROM extracted_fields "
                "WHERE field_name=?", (alan,)):
            v = json.loads(cv)
            if isinstance(v, dict):
                if "has_fee" in v:
                    sayi = 0.0 if v.get("has_fee") is False else v.get("amount")
                else:
                    sayi = next((v[k] for k in ("value", "amount", "rate", "min")
                                 if v.get(k) is not None), None)
            else:
                sayi = v if isinstance(v, (int, float)) else None
            if sayi == 0:
                out.append(guven)
        return out

    def test_masrafsiz_sifirlarinin_HICBIRI_elenmez(self):
        """543 "masrafsız" kaydı eşikten etkilenmemeli."""
        guvenler = self._sifirlar("masraf_durumu")
        self.assertGreater(len(guvenler), 400, "korpus beklenenden küçük")
        self.assertEqual([], [g for g in guvenler if g < ASGARI_GUVEN],
                         "meşru 'masrafsız' kayıtları kıyas dışı kaldı")

    def test_hesaplama_araci_sifirlarinin_TAMAMI_elenir(self):
        """`finansman_tutari` sıfırları hesaplama aracı varsayılanıdır."""
        guvenler = self._sifirlar("finansman_tutari")
        self.assertGreater(len(guvenler), 0)
        self.assertEqual([], [g for g in guvenler if g >= ASGARI_GUVEN],
                         "hesaplama aracı varsayılanı kıyasta kaldı")

    def test_gercek_yuzde_sifir_kampanyalari_korunur(self):
        for alan in ("kar_payi_orani", "tahsis_ucreti"):
            with self.subTest(alan=alan):
                self.assertEqual(
                    [], [g for g in self._sifirlar(alan) if g < ASGARI_GUVEN],
                    f"{alan} gerçek %0 kayıtları elendi")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
