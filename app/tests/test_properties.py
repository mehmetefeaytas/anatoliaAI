"""Değişmez (invariant) testleri — etiketsiz hata avı.

İlgili: ../eval/properties.py
        docs/10-degerlendirme.md

Örnek tabanlı testler ("şu girdi → şu çıktı") yalnızca aklımıza gelen vakaları
korur. Değişmez testleri ise HER girdi için doğru olması gereken özellikleri
zorlar ve **gold etiketi gerektirmez** — girdinin anlamını değiştirmeyen bir
dönüşüm çıktıyı değiştiriyorsa, doğru cevabı bilmeye gerek olmadan ortada bir
hata olduğu kesindir.

Bugüne kadar elle bulunan beş hatanın dördü bu değişmezlerle otomatik
yakalanırdı (bkz. eval/properties.py başlığı).

Buradaki son sınıf (`TestDenetleyiciCalisiyorMu`) bir META testtir: her zaman
geçen bir denetleyici işe yaramaz, o yüzden kasıtlı bozuk bir çıkarıcıda
ihlal ürettiği doğrulanır.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.properties import (
    check_irrelevant_insertion,
    check_orthographic_invariance,
    check_sentence_order_invariance,
    check_span_integrity,
    run,
)
from src.normalization.normalize import normalize_term_months
from src.preprocessing.clean import normalize_text

# Gerçekçi kampanya metinleri — 8 kampanya türünü ve zor vakaları kapsar.
KORPUS: dict[str, str] = {
    "konut": (
        "Konut finansmanında kâr payı oranı %1,89 ile 120 aya kadar vade. "
        "Tahsis ücreti 1.500,00 TL. Kampanya 31.12.2026 tarihine kadar geçerlidir."
    ),
    "tasit": (
        "Taşıt finansmanı kâr payı oranı %1,99 - %2,49 arasında, 48 ay vade. "
        "İlk 3 ay ödemesiz. Emeklilere özel."
    ),
    "ihtiyac": (
        "İhtiyaç finansmanında ilk 6 ay masrafsız, 36 ay vade imkânı. "
        "Maaş müşterilerimize özel. "
        "Başvuru için asgari 6 ay çalışma şartı gerekmektedir."
    ),
    "kart": (
        "YENİ MÜŞTERİLERE ÖZEL KREDİ KARTI KAMPANYASI. Kartınızla yapacağınız "
        "alışverişlerde %5 puan iadesi ve 1.000 TL hediye çeki kazanın. "
        "Market alışverişlerinde %20 indirim fırsatı. Yıllık kart ücreti alınmaz."
    ),
    "celiski": (
        "Bu kampanya masrafsızdır. Ancak tahsis ücreti 500 TL olarak tahsil edilir."
    ),
    "celiski_ters": (
        "Tahsis ücreti 500 TL olarak tahsil edilir. Bu kampanya masrafsızdır."
    ),
    "yatirim": (
        "Katılma hesabınıza özel getiri oranı %42,50 yıllık. "
        "Asgari 50.000 TL bakiye şartı aranmaktadır."
    ),
    "bilgisiz": (
        "Şubelerimiz hafta içi hizmet vermektedir. Detaylı bilgi için bize ulaşın."
    ),
}


class TestDegismezlerKorpusta(unittest.TestCase):
    """Tüm korpus tüm değişmezlerden geçmeli."""

    def test_tum_degismezler_gecer(self):
        rep = run(KORPUS)
        self.assertTrue(
            rep.passed,
            "değişmez ihlali:\n" + "\n".join(
                f"  [{v.prop}] {v.doc_id}/{v.field_name}: "
                f"{v.before!r} -> {v.after!r}"
                for v in rep.violations
            ),
        )

    def test_span_butunlugu(self):
        for name, text in KORPUS.items():
            self.assertEqual(check_span_integrity(text, name), [], name)

    def test_ortografik_degismezlik(self):
        for name, text in KORPUS.items():
            self.assertEqual(check_orthographic_invariance(text, name), [], name)

    def test_alakasiz_ekleme(self):
        for name, text in KORPUS.items():
            self.assertEqual(check_irrelevant_insertion(text, name), [], name)

    def test_cumle_sirasi(self):
        for name, text in KORPUS.items():
            self.assertEqual(check_sentence_order_invariance(text, name), [], name)


class TestSafDegismezler(unittest.TestCase):
    """Normalizasyon katmanının cebirsel özellikleri."""

    def test_birim_denkligi(self):
        # "1 yıl" ile "12 ay" aynı kanonik değeri vermeli
        self.assertEqual(normalize_term_months("1 yıl"),
                         normalize_term_months("12 ay"))
        self.assertEqual(normalize_term_months("2 yıl"),
                         normalize_term_months("24 ay"))

    def test_normalize_text_idempotent(self):
        for text in KORPUS.values():
            once = normalize_text(text)
            self.assertEqual(normalize_text(once), once)


class TestDenetleyiciCalisiyorMu(unittest.TestCase):
    """META: her zaman geçen bir denetleyici işe yaramaz.

    Kasıtlı olarak TR-yanlış küçük harf kullanan bir ortamda denetleyicinin
    gerçekten ihlal ürettiği doğrulanır. Bu test geçmezse, yukarıdaki
    '0 ihlal' sonuçları anlamsızdır.
    """

    def test_bozuk_tr_katlama_ihlal_uretir(self):
        import src.preprocessing.clean as clean_mod

        orig_fold, orig_ascii = clean_mod.tr_fold, clean_mod.tr_fold_ascii
        try:
            # H1 hatasını geri getir: TR-yanlış düz lower()
            clean_mod.tr_fold = lambda s: (s or "").lower()
            clean_mod.tr_fold_ascii = lambda s: (s or "").lower()

            # Modülleri yeniden yükle ki bozuk katlamayı kullansınlar
            for mod in [m for m in list(sys.modules)
                        if m.startswith(("src.", "eval."))
                        and m != "src.preprocessing.clean"]:
                sys.modules.pop(mod, None)

            from eval.properties import run as broken_run
            rep = broken_run({
                "ucretsiz": "Kredi kartı yıllık ücreti ücretsizdir. "
                            "Tahsis ücreti 500 TL.",
            })
            self.assertFalse(
                rep.passed,
                "denetleyici bilinen H1 hatasını YAKALAYAMADI — "
                "diğer '0 ihlal' sonuçları güvenilmez",
            )
        finally:
            clean_mod.tr_fold, clean_mod.tr_fold_ascii = orig_fold, orig_ascii
            for mod in [m for m in list(sys.modules)
                        if m.startswith(("src.", "eval."))
                        and m != "src.preprocessing.clean"]:
                sys.modules.pop(mod, None)


if __name__ == "__main__":
    unittest.main()
