"""Türkçe büyük/küçük harf katlama regresyon testleri.

İlgili: ../../sorun/farkli-ifade-bicimleri.md
        ../../decisions/zor-anlama-vakalari-merkezi.md
        docs/08-problemler-ve-cozumler.md (H1)

Python'un `str.lower()` metodu Türkçe için hatalıdır:
    'TAŞIT'.lower()   -> 'taşit'    (I → i, olması gereken ı)
    'ÜCRETSİZ'.lower() -> 'ücretsi̇z' (İ → i + U+0307 birleşen nokta)

Banka sitelerindeki başlıklar büyük harflidir. Bu hata üretimde:
  - sınıflandırmayı tamamen kaçırıyordu (TAŞIT FİNANSMANI -> None)
  - masraf negasyonunun İŞARETİNİ TERS ÇEVİRİYORDU
    (ÜCRETSİZ -> has_fee=True, yani "masrafsız" metni "masraf var" okunuyordu)

Bu testler o hataların geri gelmesini engeller.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot.router import route
from src.extraction.ner.classifier import RuleHintClassifier
from src.normalization.normalize import (
    normalize_date,
    normalize_fee_status,
    normalize_money,
    normalize_term_months,
)
from src.preprocessing.clean import tr_fold, tr_fold_ascii


class TestTrFold(unittest.TestCase):
    """Katlama primitiflerinin kendisi."""

    def test_problem_harfleri(self):
        self.assertEqual(tr_fold("TAŞIT"), "taşıt")
        self.assertEqual(tr_fold("İHTİYAÇ"), "ihtiyaç")
        self.assertEqual(tr_fold("IŞIK"), "ışık")

    def test_stdlib_lower_bozuk_oldugu_icin_farkli(self):
        # Bu testin amacı: düz .lower()'a geri dönülürse kırmak.
        self.assertNotEqual("TAŞIT".lower(), tr_fold("TAŞIT"))
        self.assertNotEqual("İHTİYAÇ".lower(), tr_fold("İHTİYAÇ"))

    def test_uzunluk_korunur_offset_guvenli(self):
        # extract.py source_span offset'leri katlanmış metin üzerinden
        # hesaplanıyor; uzunluk değişirse span'ler kayar.
        for s in ["İLK 6 AY ÖDEMESİZ", "TAŞIT FİNANSMANI 120 AYA KADAR VADE",
                  "1.500,00₺ TAHSİS ÜCRETİ", "IIIİİİ"]:
            self.assertEqual(len(s), len(tr_fold(s)), f"offset kayması: {s!r}")

    def test_ascii_katlama_varyantlari_birlestirir(self):
        self.assertEqual(tr_fold_ascii("Kâr Payı Oranı"),
                         tr_fold_ascii("KAR PAYI ORANI"))
        self.assertEqual(tr_fold_ascii("Taşıt"), tr_fold_ascii("TASIT"))

    def test_bos_girdi(self):
        self.assertEqual(tr_fold(""), "")
        self.assertEqual(tr_fold_ascii(""), "")
        self.assertEqual(tr_fold(None), "")


class TestSiniflandirmaAllCaps(unittest.TestCase):
    """H1: ALL-CAPS başlıklar sınıflandırılabilmeli."""

    def setUp(self):
        self.clf = RuleHintClassifier()

    def test_uc_yazim_bicimi_ayni_sinifi_verir(self):
        for text in ["TAŞIT FİNANSMANI KAMPANYASI",
                     "Taşıt finansmanı kampanyası",
                     "tasit finansmani kampanyasi"]:
            label, conf = self.clf.classify(text)
            self.assertEqual(label, "Taşıt Finansmanı", f"kaçırıldı: {text!r}")
            self.assertGreater(conf, 0.0)

    def test_diger_siniflar_all_caps(self):
        cases = [
            ("KONUT FİNANSMANI FIRSATI", "Konut Finansmanı"),
            ("İHTİYAÇ FİNANSMANI", "İhtiyaç Finansmanı"),
            ("ALIŞVERİŞ PUANI KAZAN", "Alışveriş Puanı"),
            ("YENİ MÜŞTERİYE ÖZEL", "Yeni Müşteri"),
        ]
        for text, expected in cases:
            self.assertEqual(self.clf.classify(text)[0], expected, text)

    def test_ipucu_yoksa_uydurmaz(self):
        self.assertEqual(self.clf.classify("Merhaba dünya"), (None, 0.0))

    def test_varyant_mukerrer_sayilmaz(self):
        # TYPE_HINTS hem 'taşıt' hem 'tasit' içeriyor; katlama sonrası ikisi
        # aynı dizeye düşer ve tek kez sayılmalı (güven skoru şişmemeli).
        _, conf = self.clf.classify("taşıt")
        self.assertLessEqual(conf, 0.7)


class TestNormalizasyonAllCaps(unittest.TestCase):
    """H1'in en tehlikeli sonucu: masraf negasyonunun işaretinin ters dönmesi."""

    def test_ucretsiz_all_caps_masrafsiz_demektir(self):
        # REGRESYON: bu daha önce {'has_fee': True} döndürüyordu.
        for text in ["ÜCRETSİZ", "Ücretsiz", "ücretsiz"]:
            self.assertEqual(normalize_fee_status(text),
                             {"has_fee": False, "amount": 0.0}, text)

    def test_tahsis_ucreti_yok_all_caps(self):
        self.assertEqual(normalize_fee_status("TAHSİS ÜCRETİ YOK"),
                         {"has_fee": False, "amount": 0.0})

    def test_pozitif_ucret_hala_dogru(self):
        self.assertEqual(normalize_fee_status("tahsis ücreti 500 TL"),
                         {"has_fee": True, "amount": 500.0})

    def test_masraf_gecmiyorsa_none(self):
        self.assertIsNone(normalize_fee_status("hava güzel"))

    def test_para_all_caps(self):
        for text in ["500 TÜRK LİRASI", "500 Türk Lirası", "500 TL", "500₺"]:
            got = normalize_money(text)
            self.assertEqual(got, {"value": 500.0, "currency": "TRY"}, text)

    def test_tarih_all_caps(self):
        self.assertEqual(normalize_date("31 ARALIK 2026"), "2026-12-31")
        self.assertEqual(normalize_date("1 ŞUBAT 2026"), "2026-02-01")
        self.assertEqual(normalize_date("15 KASIM 2026"), "2026-11-15")

    def test_vade_all_caps(self):
        self.assertEqual(normalize_term_months("12 AY"), 12)
        self.assertEqual(normalize_term_months("1 YIL"), 12)


class TestRouterAllCaps(unittest.TestCase):
    """Kullanıcı soruyu büyük harf veya diakritiksiz yazabilir."""

    def test_ayni_soru_uc_bicimde_ayni_yonlendirme(self):
        routes = [route(q) for q in [
            "Hangi bankada en düşük kâr payı var?",
            "EN DÜŞÜK KÂR PAYI HANGİ BANKADA?",
            "en dusuk kar payi hangi bankada",
        ]]
        for r in routes:
            self.assertEqual(r.handler, "structured")
            self.assertEqual(r.field, "kar_payi_orani")
            self.assertEqual(r.intent, "lowest")

    def test_kampanya_turu_filtresi_all_caps(self):
        self.assertEqual(
            route("TAŞIT KAMPANYASI KOŞULLARI").filters.get("campaign_type"),
            "Taşıt Finansmanı",
        )


if __name__ == "__main__":
    unittest.main()
