"""LLM özeti — LLM kapalıysa ÜRETİLMEZ, sahte özet basılmaz.

İlgili: ../src/summarize/ozet.py, ../scripts/build_summaries.py
        ../eval/predictors.py (aynı ilke: ölçülmeyen şey ölçülmüş gibi
        raporlanmaz)

Bu dosyanın koruduğu iki ilke:

1. **Sahte özet yasağı.** LLM kapalıyken kural tabanlı bir "özet" (ilk N
   cümle) basmak, kullanıcının modelin ürettiğini sanacağı bir metni
   üretmektir. Doğru cevap `None` + sebep.
2. **Katlanmış metin.** Modele giden metin, panelde katlanan çerçeveyi
   İÇERMEZ. Ayrışsalardı özet ekranda görünmeyen bir cümleyi anlatabilirdi.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.summarize import ozet as O

BELGE = ("Konut finansmanında kâr payı oranı %2,05'ten başlıyor. "
         "Vade 120 aya kadar uzayabilir. "
         "6698 sayılı Kişisel Verilerin Korunması Kanunu uyarınca veri "
         "sorumlusu sıfatıyla hareket edilmektedir.")


class SahteIstemci:
    """`generate_json` çağrısını kaydeden sahte LLM istemcisi."""

    def __init__(self, cevap=None, hata: Exception | None = None):
        self.cevap = cevap if cevap is not None else {"ozet": "Kısa özet."}
        self.hata = hata
        self.cagrilar: list[tuple[str, str, dict]] = []

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        self.cagrilar.append((system, user, schema))
        if self.hata is not None:
            raise self.hata
        return self.cevap


class SahteLLM:
    def __init__(self, available: bool = True, client=None):
        self.available = available
        self.client = client if client is not None else SahteIstemci()


class TestLLMKapali(unittest.TestCase):
    """Kapalı LLM = özet YOK. Kural tabanlı yedek YASAK."""

    def test_available_false_ise_ozet_uretilmez(self) -> None:
        s = O.ozetle(BELGE, SahteLLM(available=False))
        self.assertIsNone(s.ozet)
        self.assertIsNone(s.kaynak)
        self.assertEqual(s.sebep, "llm_kapali")

    def test_istemci_yoksa_ozet_uretilmez(self) -> None:
        llm = SahteLLM(available=True)
        llm.client = None
        s = O.ozetle(BELGE, llm)
        self.assertIsNone(s.ozet)
        self.assertEqual(s.sebep, "llm_kapali")

    def test_llm_yerine_none_verilse_de_cokmez(self) -> None:
        s = O.ozetle(BELGE, None)
        self.assertIsNone(s.ozet)
        self.assertEqual(s.sebep, "llm_kapali")

    def test_metnin_ilk_cumlesi_ozet_diye_donmez(self) -> None:
        """Sessiz sahtekârlığın tam adı: metnin kendisini özet sanmak."""
        s = O.ozetle(BELGE, SahteLLM(available=False))
        self.assertIsNone(s.ozet)
        self.assertNotIn("Konut finansmanında", str(s.ozet))


class TestUretim(unittest.TestCase):
    def test_ozet_ve_kaynak_dolar(self) -> None:
        s = O.ozetle(BELGE, SahteLLM())
        self.assertEqual(s.ozet, "Kısa özet.")
        self.assertEqual(s.kaynak, O.OZET_KAYNAK_LLM)
        self.assertIsNone(s.sebep)
        self.assertTrue(s.uretildi)

    def test_bos_cikti_null_olur(self) -> None:
        """Model 'özetlenecek bir şey yok' derse boş kutu gösterilmez."""
        s = O.ozetle(BELGE, SahteLLM(client=SahteIstemci({"ozet": "   "})))
        self.assertIsNone(s.ozet)
        self.assertEqual(s.sebep, "bos_cikti")

    def test_llm_hatasi_yutulmaz_sebebe_yazilir(self) -> None:
        istemci = SahteIstemci(hata=RuntimeError("baglanti yok"))
        s = O.ozetle(BELGE, SahteLLM(client=istemci))
        self.assertIsNone(s.ozet)
        self.assertTrue(s.sebep.startswith("llm_hatasi"))

    def test_bos_metin(self) -> None:
        s = O.ozetle("   ", SahteLLM())
        self.assertIsNone(s.ozet)
        self.assertEqual(s.sebep, "metin_bos")

    def test_bosluklar_tek_satira_indirilir(self) -> None:
        istemci = SahteIstemci({"ozet": " İki  satır\nolan   özet. "})
        s = O.ozetle(BELGE, SahteLLM(client=istemci))
        self.assertEqual(s.ozet, "İki satır olan özet.")


class TestKatlanmisMetin(unittest.TestCase):
    """Modele giden metin, panelde katlanan çerçeveyi İÇERMEZ."""

    def test_cerceve_modele_gitmez(self) -> None:
        istemci = SahteIstemci()
        O.ozetle(BELGE, SahteLLM(client=istemci))
        _, user, _ = istemci.cagrilar[0]
        self.assertIn("kâr payı oranı", user)
        self.assertNotIn("Kişisel Verilerin Korunması", user)

    def test_katlanmis_metin_blocks_ile_ayni(self) -> None:
        from src.preprocessing.blocks import gorunur_metin
        self.assertEqual(O.katlanmis_metin(BELGE), gorunur_metin(BELGE))

    def test_uzun_girdi_kirpilir_ve_gorunur_kalir(self) -> None:
        uzun = ("Kâr payı oranı %2,05'tir. " * 800)
        istemci = SahteIstemci()
        s = O.ozetle(uzun, SahteLLM(client=istemci), maks_karakter=500)
        self.assertTrue(s.kirpildi, "kırpma sessiz kaldı")
        self.assertEqual(s.girdi_karakter, 500)
        _, user, _ = istemci.cagrilar[0]
        self.assertLess(len(user), 700)

    def test_sema_tek_alanli_ve_zorunlu(self) -> None:
        istemci = SahteIstemci()
        O.ozetle(BELGE, SahteLLM(client=istemci))
        _, _, schema = istemci.cagrilar[0]
        self.assertEqual(schema["required"], ["ozet"])
        self.assertEqual(set(schema["properties"]), {"ozet"})


class TestYonergeDisiplini(unittest.TestCase):
    """Yönerge halüsinasyonu ve konvansiyonel terimi açıkça yasaklamalı."""

    def test_uydurma_yasagi_yonergede(self) -> None:
        self.assertIn("EKLEME", O.SISTEM_PROMPT)
        self.assertIn("SADECE", O.SISTEM_PROMPT)

    def test_yonerge_yasak_kokleri_icermez(self) -> None:
        """Özet metinleri jargon kurallarına tabidir (scripts/jargon_lint)."""
        from src.preprocessing.clean import tr_fold_ascii
        katli = tr_fold_ascii(O.SISTEM_PROMPT)
        for kok in ("faiz", "mevduat"):
            self.assertNotIn(kok, katli, f"yönergede yasak kök: {kok}")


class TestOzetSonucuSozlesmesi(unittest.TestCase):
    def test_as_dict_api_alan_adlarini_kullanir(self) -> None:
        d = O.ozetle(BELGE, SahteLLM()).as_dict()
        self.assertEqual(d["ozet"], "Kısa özet.")
        self.assertEqual(d["ozet_kaynak"], "llm")

    def test_kaynak_tek_gecerli_deger(self) -> None:
        """Kural tabanlı bir kaynak YOKTUR — sabit tek değerdir."""
        self.assertEqual(O.OZET_KAYNAK_LLM, "llm")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
