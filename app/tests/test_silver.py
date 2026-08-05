"""Gümüş etiket hattı testleri.

İlgili: ../src/extraction/silver/

## Neden bu testler

Bu hat, bir sınıflandırıcıyı eğitecek etiket üretiyor. Yanlış etiket kalıcı
hata öğretir ve hatanın kaynağı sonradan bulunamaz. Üç mekanizma test-çitiyle
korunuyor:

1. **Kanıt kapısı deterministiktir.** Etiket uydurulabilir, alıntı
   uydurulamaz — uydurulmuş alıntı belgede bulunmaz ve kayıt düşer. Bu kapı
   LLM'in kendi beyanına bakmaz, o yüzden en güvenilir savunma.
2. **Denetleyici lastik damga olamaz.** İki LLM oyu ayrışırsa kayıt insana
   gider. Ayrışmanın gümüşe geçmesi, iki oyu tek oya indirir.
3. **Kural katmanının veto hakkı yok.** `RuleHintClassifier` ölçülmüş hata
   taşıyor (sözcük sınırı düzeltmesinden önce korpusun %48'ini sahte Konut
   Finansmanı yapıyordu); yalnızca güveni yükseltebilir.
4. **Denetleyici, kanıtın bulunduğu metni görebilmeli.** Prompt kırpması
   gövdeyi keserse denetleyici doğru alıntıyı "belgede yok" sanar; iki oy
   ölçülemez biçimde kaybolur. Ölçüm: ürün sayfalarında gövde 18.000.
   karakterde başlıyordu (bkz. `src/extraction/silver/prompts.py`).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.silver import (
    CONF_HIGH,
    CONF_MEDIUM,
    MAX_PROMPT_CHARS,
    STATUS_QUEUE,
    STATUS_REJECT,
    STATUS_SILVER,
    LabelProposal,
    VerifyVerdict,
    class_balance_warnings,
    decide,
    evidence_is_verbatim,
    labeler_user_prompt,
    score_against_gold,
    summarize,
    verifier_user_prompt,
)
from src.extraction.silver.consensus import (
    R_EVIDENCE_WEAK,
    R_LABELS_DIVERGE,
    R_LLM_AGREE,
    R_NO_EVIDENCE,
    R_TAXONOMY,
    R_UNANIMOUS,
    R_UNVERIFIED,
)

METIN = ("Akbank Konut Kredisi ile hayalinizdeki eve kavuşun. "
         "120 aya kadar vade ve uygun faiz oranı avantajı sizi bekliyor.")


def _p(label, evidence, doc_id="akbank--konut", conf=0.9):
    return LabelProposal(doc_id=doc_id, label=label, evidence=evidence,
                         confidence=conf, labeler="opus-5")


def _v(own_label, supports=True, doc_id="akbank--konut"):
    return VerifyVerdict(doc_id=doc_id, own_label=own_label,
                         evidence_supports=supports, reason="", verifier="opus-5")


class TestKanitKapisi(unittest.TestCase):
    def test_birebir_alinti_gecer(self):
        self.assertTrue(evidence_is_verbatim(METIN, "Akbank Konut Kredisi ile"))

    def test_bosluk_ve_kasa_toleransli(self):
        self.assertTrue(evidence_is_verbatim(
            METIN, "akbank   konut\nkredisi ile"))

    def test_uydurulmus_alinti_reddedilir(self):
        self.assertFalse(evidence_is_verbatim(
            METIN, "kâr payı oranı %1,89 olarak uygulanır"))

    def test_cok_kisa_alinti_kanit_sayilmaz(self):
        """'TL' her belgede geçer; kısa alıntı hiçbir şey kanıtlamaz."""
        self.assertFalse(evidence_is_verbatim(METIN, "eve"))

    def test_bos_alinti(self):
        self.assertFalse(evidence_is_verbatim(METIN, ""))


class TestUzlasma(unittest.TestCase):
    def test_uc_oy_ayni_yuksek_guven(self):
        # kural katmanı da Konut Finansmanı diyor
        r = decide(METIN, _p("Konut Finansmanı", "Akbank Konut Kredisi ile"),
                   _v("Konut Finansmanı"), "Konut Finansmanı")
        self.assertEqual(r.status, STATUS_SILVER)
        self.assertEqual(r.confidence, CONF_HIGH)
        self.assertEqual(r.reason, R_UNANIMOUS)

    def test_iki_llm_ayni_kural_ayri_orta_guven(self):
        """Kural katmanı veto edemez — yalnız güveni düşürür."""
        r = decide(METIN, _p("Konut Finansmanı", "Akbank Konut Kredisi ile"),
                   _v("Konut Finansmanı"), "Finansman")
        self.assertEqual(r.status, STATUS_SILVER)
        self.assertEqual(r.confidence, CONF_MEDIUM)
        self.assertEqual(r.reason, R_LLM_AGREE)

    def test_kural_sessizse_de_gumus_uretilir(self):
        r = decide(METIN, _p("Konut Finansmanı", "Akbank Konut Kredisi ile"),
                   _v("Konut Finansmanı"), None)
        self.assertEqual(r.status, STATUS_SILVER)
        self.assertEqual(r.confidence, CONF_MEDIUM)

    def test_llm_ayrisirsa_insana_gider(self):
        r = decide(METIN, _p("Konut Finansmanı", "Akbank Konut Kredisi ile"),
                   _v("Finansman"), "Konut Finansmanı")
        self.assertEqual(r.status, STATUS_QUEUE)
        self.assertEqual(r.reason, R_LABELS_DIVERGE)

    def test_denetleyici_kaniti_yetersiz_bulursa_kuyruk(self):
        r = decide(METIN, _p("Konut Finansmanı", "120 aya kadar vade"),
                   _v("Konut Finansmanı", supports=False), "Konut Finansmanı")
        self.assertEqual(r.status, STATUS_QUEUE)
        self.assertEqual(r.reason, R_EVIDENCE_WEAK)

    def test_denetlenmemis_kayit_gumus_olmaz(self):
        """Tek oy, oy değildir."""
        r = decide(METIN, _p("Konut Finansmanı", "Akbank Konut Kredisi ile"),
                   None, "Konut Finansmanı")
        self.assertEqual(r.status, STATUS_QUEUE)
        self.assertEqual(r.reason, R_UNVERIFIED)


class TestMekanikKapilarOnceCalisir(unittest.TestCase):
    """Taksonomi ve kanıt kapıları, LLM oylarından ÖNCE."""

    def test_taksonomi_disi_etiket_her_sey_uyusa_bile_reddedilir(self):
        r = decide(METIN, _p("Konut Kredisi", "Akbank Konut Kredisi ile"),
                   _v("Konut Kredisi"), "Konut Kredisi")
        self.assertEqual(r.status, STATUS_REJECT)
        self.assertEqual(r.reason, R_TAXONOMY)
        self.assertIsNone(r.label)

    def test_uydurulmus_kanit_her_sey_uyusa_bile_reddedilir(self):
        r = decide(METIN, _p("Konut Finansmanı", "kâr payı oranı %1,89'dur"),
                   _v("Konut Finansmanı"), "Konut Finansmanı")
        self.assertEqual(r.status, STATUS_REJECT)
        self.assertEqual(r.reason, R_NO_EVIDENCE)
        self.assertIsNone(r.label, "reddedilen kayıt etiket taşımamalı")

    def test_null_etiket_reddedilir(self):
        r = decide(METIN, _p(None, ""), _v(None), None)
        self.assertEqual(r.status, STATUS_REJECT)
        self.assertEqual(r.reason, R_TAXONOMY)


class TestSozlesme(unittest.TestCase):
    def test_eksik_alan_sessizce_gecmez(self):
        with self.assertRaises(ValueError):
            LabelProposal.from_json({"doc_id": "x", "label": "Kart"})

    def test_denetleyici_karar_vermek_zorunda(self):
        """evidence_supports eksikse sessizce onay sayılamaz."""
        with self.assertRaises(ValueError) as ctx:
            VerifyVerdict.from_json({"doc_id": "x", "own_label": "Kart"})
        self.assertIn("evidence_supports", str(ctx.exception))

    def test_null_etiket_okunabilir(self):
        p = LabelProposal.from_json(
            {"doc_id": "x", "label": None, "evidence": "", "confidence": 0.0})
        self.assertIsNone(p.label)


class TestRapor(unittest.TestCase):
    def _kayitlar(self):
        return [
            decide(METIN, _p("Konut Finansmanı", "Akbank Konut Kredisi ile"),
                   _v("Konut Finansmanı"), "Konut Finansmanı"),
            decide(METIN, _p("Konut Finansmanı", "Akbank Konut Kredisi ile",
                             doc_id="b--x"),
                   _v("Finansman", doc_id="b--x"), "Konut Finansmanı"),
            decide(METIN, _p("Konut Kredisi", "Akbank Konut Kredisi ile",
                             doc_id="c--x"), _v("Kart", doc_id="c--x"), None),
        ]

    def test_ozet_sayimlari(self):
        o = summarize(self._kayitlar())
        self.assertEqual(o["toplam"], 3)
        self.assertEqual(o["durum"][STATUS_SILVER], 1)
        self.assertEqual(o["durum"][STATUS_QUEUE], 1)
        self.assertEqual(o["durum"][STATUS_REJECT], 1)
        self.assertEqual(o["sinif_dagilimi"], {"Konut Finansmanı": 1})

    def test_eksik_siniflar_sessiz_kalmaz(self):
        uyarilar = class_balance_warnings(self._kayitlar(), min_per_class=20)
        self.assertTrue(any("Kart" in u for u in uyarilar))
        self.assertTrue(any("Konut Finansmanı: 1/20" in u for u in uyarilar))


class TestPromptKirpmasi(unittest.TestCase):
    """Kırpma penceresi, ürün sayfalarının ölçülmüş gövde konumunu kapsamalı.

    Bu sınıf sessiz bir başarısızlığı çitliyor: `decide` kanıtı TAM metinde
    arar, denetleyici ise KIRPILMIŞ metinde. Pencere gövdeden önce kapanırsa
    doğru alıntı mekanik kapıdan geçer ama denetleyici onu göremez ve kayıt
    haksız yere kuyruğa düşer.
    """

    # Yapı Kredi ürün sayfalarının ölçülen gövde konumu ~18.000; en uzak
    # gerekçe alıntısı 18.321. karakterde çıktı.
    OLCULEN_GOVDE_KONUMU = 18321

    def _uzun_belge(self) -> tuple[str, str]:
        gurultu = "Şube ve ATM'ler Ürün ve Hizmet Ücretleri Menu " * 500
        govde = "Yapı Kredi Taşıt Kredisi ile hayalinizdeki araca kavuşun."
        return gurultu[:self.OLCULEN_GOVDE_KONUMU] + " " + govde, govde

    def test_pencere_olculen_govde_konumunu_kapsar(self):
        self.assertGreater(MAX_PROMPT_CHARS, self.OLCULEN_GOVDE_KONUMU,
                           "pencere ölçülen gövde konumundan küçük olamaz")

    def test_etiketleyici_govdeyi_gorur(self):
        metin, govde = self._uzun_belge()
        self.assertIn(govde, labeler_user_prompt("yapi-kredi--x", metin))

    def test_denetleyici_de_ayni_govdeyi_gorur(self):
        """Denetleyicinin penceresi etiketleyiciden dar olamaz."""
        metin, govde = self._uzun_belge()
        prompt = verifier_user_prompt("yapi-kredi--x", metin,
                                      "Taşıt Finansmanı", govde)
        self.assertIn(govde, prompt)

    def test_kirpma_hala_isaretlenir(self):
        """Pencere büyüdü diye kırpma bilgisi kaybolmamalı."""
        cok_uzun = "x" * (MAX_PROMPT_CHARS + 1)
        self.assertIn("metin kırpıldı", labeler_user_prompt("a--b", cok_uzun))
        self.assertNotIn("metin kırpıldı", labeler_user_prompt("a--b", "kısa"))


class TestGoldPuanlama(unittest.TestCase):
    def test_ortusme_olculur(self):
        kayitlar = [
            decide(METIN, _p("Konut Finansmanı", "Akbank Konut Kredisi ile"),
                   _v("Konut Finansmanı"), "Konut Finansmanı"),
            decide(METIN, _p("Kart", "120 aya kadar vade ve uygun",
                             doc_id="b--x"), _v("Kart", doc_id="b--x"), "Kart"),
        ]
        s = score_against_gold(kayitlar, {"akbank--konut": "Konut Finansmanı",
                                          "b--x": "Finansman"})
        self.assertEqual(s["gumus_olarak_puanlanan"], 2)
        self.assertEqual(s["ortusen"], 1)
        self.assertEqual(s["ortusme_orani"], 0.5)
        self.assertEqual(len(s["uyusmazliklar"]), 1)
        self.assertEqual(s["uyusmazliklar"][0]["gold"], "Finansman")

    def test_gold_kesisimi_yoksa_oran_none(self):
        """Kapsam yoksa oran uydurulmaz."""
        kayitlar = [decide(METIN, _p("Konut Finansmanı",
                                     "Akbank Konut Kredisi ile"),
                           _v("Konut Finansmanı"), None)]
        s = score_against_gold(kayitlar, {})
        self.assertIsNone(s["ortusme_orani"])
        self.assertEqual(s["gold_kesisimi"], 0)

    def test_kuyruktaki_kayit_puanlanmaz(self):
        """Yalnız gümüş kayıtlar ölçülür; kuyruk henüz karar değil."""
        kayitlar = [decide(METIN, _p("Konut Finansmanı",
                                     "Akbank Konut Kredisi ile"),
                           _v("Finansman"), None)]
        s = score_against_gold(kayitlar, {"akbank--konut": "Konut Finansmanı"})
        self.assertEqual(s["gumus_olarak_puanlanan"], 0)
        self.assertEqual(s["gold_kesisimi"], 1)


class TestKapsamSessizKalmaz(unittest.TestCase):
    """`merge` önerisi OLMAYAN belgeyi sessizce dışarıda bırakmamalı.

    Ölçülmüş boşluk: korpusun 724 belgesine karşı 608 öneri vardı, yani 116
    belge gümüş kümenin dışındaydı ve `merge` bunu hiç bildirmiyordu. Sessiz
    kırpma "korpusun tamamı etiketlendi" gibi okunur; okunmayan belge
    ölçülmemiş belgedir.
    """

    def _korpus(self, kok, belgeler):
        for ad, metin in belgeler.items():
            p = kok / "banka" / f"{ad}.txt"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(metin, encoding="utf-8")

    def _kos(self, belgeler, onerilen):
        import argparse
        import json as _json
        import tempfile
        from pathlib import Path

        from scripts.build_silver import cmd_merge

        with tempfile.TemporaryDirectory() as td:
            kok = Path(td)
            self._korpus(kok / "docs", belgeler)
            prop = kok / "proposals.jsonl"
            prop.write_text("\n".join(_json.dumps(
                {"doc_id": f"banka--{d}", "label": "Konut Finansmanı",
                 "evidence": belgeler[d][:30], "confidence": 0.9,
                 "labeler": "t"}, ensure_ascii=False) for d in onerilen),
                encoding="utf-8")
            out = kok / "out"
            kod = cmd_merge(argparse.Namespace(
                docs=str(kok / "docs"), proposals=str(prop),
                verdicts=None, out_dir=str(out)))
            rapor = _json.loads((out / "silver_report.json")
                                .read_text(encoding="utf-8"))
            return kod, rapor

    METINLER = {
        "a": "Konut Finansmanı kampanyası, kâr payı oranı %1,89.",
        "b": "Taşıt Finansmanı kampanyası, kâr payı oranı %2,45.",
    }

    def test_eksik_oneri_rapora_yazilir(self):
        kod, rapor = self._kos(self.METINLER, ["a"])
        self.assertEqual(kod, 0, "eksik öneri HATA değil, uyarıdır")
        self.assertEqual(rapor["kapsam"]["korpus_belge"], 2)
        self.assertEqual(rapor["kapsam"]["onerisi_olan"], 1)
        self.assertEqual(rapor["kapsam"]["onerisi_olmayan"], 1)
        self.assertEqual(rapor["kapsam"]["oran"], 0.5)

    def test_tam_kapsamda_bosluk_bildirilmez(self):
        _kod, rapor = self._kos(self.METINLER, ["a", "b"])
        self.assertEqual(rapor["kapsam"]["onerisi_olmayan"], 0)
        self.assertEqual(rapor["kapsam"]["oran"], 1.0)


if __name__ == "__main__":
    unittest.main()
