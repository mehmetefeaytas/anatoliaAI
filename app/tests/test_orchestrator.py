"""Çok-ajanlı orkestrasyon — yetki asimetrisi ve fail-closed testleri.

İlgili: ../src/extraction/llm/orchestrator.py, ../src/extraction/llm/agents.py,
        ../src/extraction/reconcile.py, ../eval/predictors.py

Buradaki testlerin tamamı tek bir değişmezi koruyor:

    ajanlar ÖNERİR · hakem yalnız REDDEDER · reddedilen alan kural değerine düşer
    => orkestrasyonun EN KÖTÜ hâli kural-only'dir.

Bu keyfi bir tercih değil. Ablasyon hibrit kolun kuraldan daha kötü olduğunu
ölçtü (mikro-F1 0,612 -> 0,575, halüsinasyon 0,102 -> 0,163). LLM'in yazma
yetkisi olduğu sürece o regresyon tekrarlanabilir; yetki alınınca yapısal
olarak tekrarlanamaz. Bu dosya "yetki alınmış mı" sorusunu sabitliyor.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.llm import agents as A
from src.extraction.llm.extractor import LLMExtractionError
from src.extraction.llm.orchestrator import LLMOrchestrator

METIN = ("Konut finansmanında kâr payı oranı %2,05'ten başlıyor. "
         "Kampanya 01.08.2026 - 30.09.2026 tarihleri arasında geçerlidir. "
         "Yeni müşterilerimize tahsis ücreti alınmamaktadır.")


class SahteIstemci:
    """`generate_json` arayüzünü taklit eder; rolü şemadan ayırt eder."""

    def __init__(self, sayisal=None, baglamsal=None, hakem=None,
                 hakem_patlat=False, rol_patlat=None):
        self.sayisal = sayisal if sayisal is not None else {
            "kar_payi_orani": {"value": 2.05, "confidence": 0.9,
                               "source_span": "kâr payı oranı %2,05"}}
        self.baglamsal = baglamsal if baglamsal is not None else {
            "hedef_kitle": {"value": ["yeni_musteri"], "confidence": 0.8,
                            "source_span": "Yeni müşterilerimize"}}
        self.hakem = hakem
        self.hakem_patlat = hakem_patlat
        self.rol_patlat = rol_patlat        # "sayisal" | "baglamsal" | None
        self.cagrilar: list[str] = []
        self.sistemler: list[str] = []

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        self.sistemler.append(system)
        if "kararlar" in (schema.get("properties") or {}):
            self.cagrilar.append("hakem")
            if self.hakem_patlat:
                raise RuntimeError("hakem servisi kapalı")
            if self.hakem is not None:
                return self.hakem
            return {"kararlar": []}          # karar yok -> hepsi kabul
        istenen = set((schema.get("properties") or {}))
        if istenen & set(A.ROL_SAYISAL.alanlar):
            self.cagrilar.append("sayisal")
            if self.rol_patlat == "sayisal":
                raise RuntimeError("sayısal ajan çöktü")
            return dict(self.sayisal)
        self.cagrilar.append("baglamsal")
        if self.rol_patlat == "baglamsal":
            raise RuntimeError("bağlamsal ajan çöktü")
        return dict(self.baglamsal)


def _orc(**kw) -> tuple[LLMOrchestrator, SahteIstemci]:
    istemci_kw = {k: kw.pop(k) for k in
                  ("sayisal", "baglamsal", "hakem", "hakem_patlat", "rol_patlat")
                  if k in kw}
    c = SahteIstemci(**istemci_kw)
    return LLMOrchestrator(c, **kw), c


class TestRolAyrimi(unittest.TestCase):
    def test_her_rol_kendi_alanlariyla_cagrilir(self) -> None:
        orc, c = _orc()
        orc.extract(METIN)
        self.assertEqual(sorted(set(c.cagrilar) - {"hakem"}),
                         ["baglamsal", "sayisal"])

    def test_alan_kumeleri_ortusmez(self) -> None:
        """Aynı alanı iki ajan çıkarırsa hangisinin kazandığı belirsizleşir."""
        self.assertEqual(
            set(A.ROL_SAYISAL.alanlar) & set(A.ROL_BAGLAMSAL.alanlar), set())

    def test_roller_12_alani_TAM_kapsar(self) -> None:
        from src.extraction.llm.schema import EXTRACTION_FIELDS
        birlesim: set[str] = set()
        for r in A.ROLLER:
            birlesim |= set(r.alanlar)
        self.assertEqual(birlesim, set(EXTRACTION_FIELDS),
                         "bir alan hiçbir ajana ait değil — sessizce düşer")

    def test_rol_disi_alan_gecmez(self) -> None:
        """Sayısal ajan koşul üretirse şema ihlalidir, çıktıya sızmamalı."""
        orc, _ = _orc(sayisal={
            "kar_payi_orani": {"value": 2.05, "confidence": 0.9,
                               "source_span": "kâr payı oranı %2,05"},
            "kampanya_kosullari": {"value": ["uydurma"], "confidence": 0.9,
                                   "source_span": "Yeni müşterilerimize"}})
        adlar = [f.field_name for f in orc.extract(METIN)]
        self.assertIn("kar_payi_orani", adlar)
        self.assertEqual(adlar.count("kampanya_kosullari"), 0)

    def test_bir_rolun_cokmesi_digerini_dusurmez(self) -> None:
        orc, _ = _orc(rol_patlat="sayisal")
        adlar = [f.field_name for f in orc.extract(METIN)]
        self.assertEqual(adlar, ["hedef_kitle"])
        self.assertIn("sayisal", orc.last_report.rol_hatasi)


class TestKanitKapisi(unittest.TestCase):
    """Mekanik kapı LLM'den ÖNCE — consensus.py'deki ile aynı ilke."""

    def test_metinde_olmayan_alinti_dusurulur(self) -> None:
        orc, _ = _orc(sayisal={
            "kar_payi_orani": {"value": 1.11, "confidence": 0.99,
                               "source_span": "bu cümle metinde hiç yok"}})
        adlar = [f.field_name for f in orc.extract(METIN)]
        self.assertNotIn("kar_payi_orani", adlar)
        self.assertEqual(orc.last_report.kanit_kapisi_red, 1)

    def test_alintisiz_oneri_dusurulur(self) -> None:
        orc, _ = _orc(sayisal={
            "kar_payi_orani": {"value": 1.11, "confidence": 0.99,
                               "source_span": None}})
        self.assertNotIn("kar_payi_orani",
                         [f.field_name for f in orc.extract(METIN)])

    def test_kapi_LLM_cagrilmadan_calisir(self) -> None:
        """Hakem, kapıdan geçen kalmadıysa hiç çağrılmamalı — boşuna token."""
        orc, c = _orc(sayisal={"kar_payi_orani": {
                          "value": 1.11, "confidence": 0.9,
                          "source_span": "metinde yok"}},
                      baglamsal={})
        orc.extract(METIN)
        self.assertNotIn("hakem", c.cagrilar)

    def test_kapi_kapatilabilir_olcum_icin(self) -> None:
        orc, _ = _orc(kanit_kapisi=False, judge=False, sayisal={
            "kar_payi_orani": {"value": 1.11, "confidence": 0.9,
                               "source_span": "metinde yok"}})
        self.assertIn("kar_payi_orani",
                      [f.field_name for f in orc.extract(METIN)])


class TestKalemKapisi(unittest.TestCase):
    """Ücret alanında komşu kalem karışması — HAKEMİN KAÇIRDIĞI vaka.

    Ölçüldü: hakem beş kontrol vakasının dördünü doğru bildi ama "Taşıt Rehin
    Tesis Ücreti 350,92 TL" alıntısını `tahsis_ucreti` için KABUL etti. Aynı
    karışma ücret çapraz denetiminde de ölçülmüştü. Sistematik ve bilinen bir
    hata mekanik kapıyla kapatılır; hakem prompt'unu bu vakaya göre yamalamak
    ölçüm kümesine aşırı uydurma olurdu.
    """

    METIN_UCRET = ("Taşıt Rehin Tesis Ücreti 350,92 TL'dir. "
                   "Tahsis ücreti alınmaz; rehin ücreti ayrıca tahsil edilir.")

    def _orc_ucret(self, span: str):
        return _orc(judge=False, baglamsal={}, sayisal={
            "tahsis_ucreti": {"value": 350.92, "confidence": 0.9,
                              "source_span": span}})

    def test_komsu_kalem_dusurulur(self) -> None:
        orc, _ = self._orc_ucret("Taşıt Rehin Tesis Ücreti 350,92 TL")
        adlar = [f.field_name for f in orc.extract(self.METIN_UCRET)]
        self.assertNotIn("tahsis_ucreti", adlar)
        self.assertEqual(orc.last_report.kalem_kapisi_red, 1)

    def test_kendi_etiketi_varsa_DUSURULMEZ(self) -> None:
        """Kapı dar olmalı: 'Tahsis ücreti alınmaz; rehin ücreti...' meşrudur."""
        orc, _ = self._orc_ucret(
            "Tahsis ücreti alınmaz; rehin ücreti ayrıca tahsil edilir")
        self.assertIn("tahsis_ucreti",
                      [f.field_name for f in orc.extract(self.METIN_UCRET)])

    def test_ucret_disi_alan_etkilenmez(self) -> None:
        orc, _ = _orc(judge=False, baglamsal={}, sayisal={
            "vade_ay": {"value": 36, "confidence": 0.9,
                        "source_span": "Taşıt Rehin Tesis Ücreti 350,92 TL"}})
        self.assertIn("vade_ay",
                      [f.field_name for f in orc.extract(self.METIN_UCRET)])


class TestHakemYalnizReddeder(unittest.TestCase):
    def test_red_alani_dusurur(self) -> None:
        orc, _ = _orc(hakem={"kararlar": [
            {"alan": "kar_payi_orani", "kabul": False, "gerekce": "yanlış kalem"}]})
        adlar = [f.field_name for f in orc.extract(METIN)]
        self.assertNotIn("kar_payi_orani", adlar)
        self.assertIn("hedef_kitle", adlar)
        self.assertEqual(orc.last_report.hakem_red, 1)

    def test_hakem_YENI_alan_EKLEYEMEZ(self) -> None:
        """Hakem 'kabul' dediği ama ajanların önermediği alan yazamaz."""
        orc, _ = _orc(hakem={"kararlar": [
            {"alan": "vade_ay", "kabul": True, "gerekce": "ben ekledim"}]})
        self.assertNotIn("vade_ay", [f.field_name for f in orc.extract(METIN)])

    def test_hakem_DEGER_degistiremez(self) -> None:
        orc, _ = _orc(hakem={"kararlar": [
            {"alan": "kar_payi_orani", "kabul": True, "gerekce": "aslında 9.99"}]})
        alan = next(f for f in orc.extract(METIN)
                    if f.field_name == "kar_payi_orani")
        self.assertEqual(alan.canonical_value, 2.05)

    def test_karar_verilmeyen_alan_KABUL(self) -> None:
        """Aksi halde model bir alanı ATLAYARAK sessizce düşürebilirdi."""
        orc, _ = _orc(hakem={"kararlar": []})
        self.assertEqual(len(orc.extract(METIN)), 2)

    def test_hakem_kapatilabilir_olcum_icin(self) -> None:
        orc, c = _orc(judge=False)
        orc.extract(METIN)
        self.assertNotIn("hakem", c.cagrilar)


class TestHakemCokerseFailClosedVeGURULTULU(unittest.TestCase):
    """Sessiz düşüş, ablasyonda 'orkestra' satırını 'kural'a çevirirdi."""

    def test_tum_oneriler_duser(self) -> None:
        orc, _ = _orc(hakem_patlat=True)
        self.assertEqual(orc.extract(METIN), [])

    def test_hata_RAPORLANIR(self) -> None:
        orc, _ = _orc(hakem_patlat=True)
        orc.extract(METIN)
        self.assertIsNotNone(orc.last_report.hakem_hata)
        self.assertEqual(orc.stats["hakem_hata"], 1)

    def test_kati_modda_YUKSELIR(self) -> None:
        orc, _ = _orc(hakem_patlat=True, strict=True)
        with self.assertRaises(LLMExtractionError):
            orc.extract(METIN)


class TestTerimKartiEnjeksiyonu(unittest.TestCase):
    def test_kart_sistem_promptuna_girer(self) -> None:
        orc, c = _orc()
        orc.extract(METIN)
        self.assertTrue(any("DEĞİLDİR" in s for s in c.sistemler))

    def test_kart_BELGEYE_ozel(self) -> None:
        """Sözlük 76.200 karakter; bağlam penceresi ~25.000. Sabit enjeksiyon
        imkânsız, üstelik Ollama taşmayı BAŞTAN kırpıp sistem prompt'unu yok
        ediyor."""
        orc, c = _orc()
        orc.extract("Sukuk ihracı ve kira sertifikası getirisi hakkında.")
        birlesik = "\n".join(c.sistemler)
        self.assertIn("Sukuk", birlesik)
        self.assertNotIn("Tekâfül", birlesik)

    def test_kart_kapatilabilir_olcum_icin(self) -> None:
        """Ö1 ablasyonu: kart enjeksiyonunun katkısı ancak kapatılabilirse
        ölçülebilir."""
        orc, c = _orc(terim_karti=False)
        orc.extract(METIN)
        self.assertFalse(any("Bu metinde geçen katılım finansı terimleri" in s
                             for s in c.sistemler))

    def test_rol_yonergesi_promptta(self) -> None:
        orc, c = _orc()
        orc.extract(METIN)
        birlesik = "\n".join(c.sistemler)
        self.assertIn("SAYISAL ALAN UZMANI", birlesik)
        self.assertIn("KOŞUL VE BAĞLAM UZMANI", birlesik)

    def test_prompt_baglam_penceresine_sigar(self) -> None:
        """OLLAMA_NUM_CTX=8192 token ~ 25.000 karakter; belge de aynı pencerede."""
        kur = A.sistem_kurucu(A.ROL_SAYISAL)
        self.assertLess(len(kur(METIN)), 12000)


class TestArayuzUyumu(unittest.TestCase):
    def test_LLMExtractor_arayuzunu_karsilar(self) -> None:
        """Arayüz uyumu `.available`/`.extract` ile BİTMİYOR.

        `summary()` eksikti ve 30 dakikalık ölçüm koşusu tam rapor
        yazılırken AttributeError ile çöktü — sayılar hesaplanmıştı ama
        diske hiç yazılmadı.
        """
        from src.extraction.llm.extractor import LLMExtractor
        orc, _ = _orc()
        for ad in ("available", "extract", "summary", "reset_stats",
                   "structured_mode", "stats"):
            self.assertTrue(hasattr(orc, ad), f"eksik: {ad}")
        eksik = {k for k in LLMExtractor(None).summary()} - set(orc.summary())
        self.assertEqual(eksik, set(), f"summary() sözleşmesi eksik: {eksik}")
        self.assertTrue(orc.available)

    def test_summary_orkestrasyon_ayrintisini_tasir(self) -> None:
        orc, _ = _orc()
        orc.extract(METIN)
        s = orc.summary()
        self.assertTrue(s["orkestrasyon"])
        self.assertEqual(sorted(s["roller"]), ["baglamsal", "sayisal"])
        self.assertIn("sayisal", s["ajan_sayaclari"])

    def test_istemcisiz_bos_doner(self) -> None:
        self.assertEqual(LLMOrchestrator(None).extract(METIN), [])
        self.assertFalse(LLMOrchestrator(None).available)

    def test_reconcile_ile_calisir(self) -> None:
        from src.extraction.reconcile import reconcile
        orc, _ = _orc()
        self.assertTrue(reconcile(METIN, llm=orc))

    def test_EN_KOTU_HAL_kural_only(self) -> None:
        """Değişmezin kendisi: orkestrasyon hiçbir şey geçirmese bile sonuç
        kural katmanının çıktısıdır — asla ondan kötü değil."""
        from src.extraction.reconcile import reconcile
        orc, _ = _orc(hakem_patlat=True)
        kural = {f.field_name for f in reconcile(METIN, llm=None)}
        orkestra = {f.field_name for f in reconcile(METIN, llm=orc)}
        self.assertTrue(kural <= orkestra, "kural alanı orkestrasyonda kayboldu")

    def test_missing_filtresi_uygulanir(self) -> None:
        orc, c = _orc()
        orc.extract(METIN, ["hedef_kitle"])
        self.assertNotIn("sayisal", c.cagrilar)


class TestOlcumKolu(unittest.TestCase):
    def test_konfigler_tanimli(self) -> None:
        from eval.predictors import (
            CONFIG_NAMES,
            CONFIG_ORKESTRA,
            CONFIG_ORKESTRA_HAKEMSIZ,
        )
        self.assertIn(CONFIG_ORKESTRA, CONFIG_NAMES)
        self.assertIn(CONFIG_ORKESTRA_HAKEMSIZ, CONFIG_NAMES)

    def test_varsayilan_hala_kural_degil_orkestra(self) -> None:
        """K3 kararı: orkestrasyon ölçümü geçmeden varsayılan OLAMAZ."""
        from eval.predictors import CONFIG_ORKESTRA, DEFAULT_CONFIG
        self.assertNotEqual(DEFAULT_CONFIG, CONFIG_ORKESTRA)

    def test_rapor_ozeti_sayilari_tasir(self) -> None:
        from src.extraction.llm.orchestrator import rapor_ozeti
        orc, _ = _orc()
        orc.extract(METIN)
        self.assertIn("gecen=2", rapor_ozeti(orc))


if __name__ == "__main__":
    unittest.main()
