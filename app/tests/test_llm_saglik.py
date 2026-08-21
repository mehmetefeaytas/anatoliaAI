"""LLM sağlık günlüğü ve kanıt kapısı testleri — ağsız, GPU'suz.

İlgili: ../src/extraction/llm/extractor.py
        ../docs/rapor/llm-uretim-devreye-alma.md
        CLAUDE.md §21 (halüsinasyon yasağı)

## Neden bu dosya var

İki iddia iki jüri turu boyunca yalnız bir rapor tablosu satırıydı:

1. "384/384 temiz LLM çağrısı" — sayaçlar koşum bitince bellekle birlikte
   kaybolduğu için denetlenemiyordu. Artık her çağrı bir JSONL satırıdır ve
   bu testler o satırın ŞEKLİNİ (hangi anahtarlar, hangi değerler) sözleşme
   olarak dondurur. Anahtar adı sessizce değişirse rapor okunamaz hâle
   gelirdi.
2. "değer uydurmuyoruz" — kanıt kapısı, alıntısı kaynak metinde BİREBİR
   bulunmayan değeri düşürür. Testler kapının hem kestiğini hem de kanıtlı
   değeri kesMEdiğini gösterir; ikincisi olmadan kapı "her şeyi at" ile
   ayırt edilemez.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.llm.extractor import (
    SAGLIK_LOG_VARSAYILAN,
    LLMExtractionError,
    LLMExtractor,
    _saglik_log_yolu,
)

# Metin ve model çıktısı: `36 ay` alıntısı metinde GEÇER (kanıtlı),
# `%1,89` alıntısı GEÇMEZ (model kendi cümlesini yazdı -> kanıtsız).
TEXT = "İhtiyaç finansmanında 36 ay vade imkânı."

CIKTI = {
    "vade_ay": {"value": 36, "confidence": 0.9, "source_span": "36 ay"},
    "kar_payi_orani": {"value": 1.89, "confidence": 0.8,
                       "source_span": "kâr payı oranı %1,89"},
}


class SahteIstemci:
    """`generate_json` sözleşmesini karşılayan en küçük istemci."""

    model = "sahte-model"

    def __init__(self, cikti: dict | None = None):
        self.cikti = CIKTI if cikti is None else cikti
        self.cagri = 0

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        self.cagri += 1
        return self.cikti


class PatlayanIstemci:
    model = "patlayan-model"

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        raise RuntimeError("baglanti reddedildi")


class TestKanitKapisi(unittest.TestCase):

    def test_kapali_iken_kanitsiz_deger_gecer(self):
        """Varsayılan davranış (kapı kapalı) değişmemiş olmalı."""
        ex = LLMExtractor(SahteIstemci(), require_evidence=False,
                          saglik_log="")
        adlar = {f.field_name for f in ex.extract(TEXT)}
        self.assertEqual(adlar, {"vade_ay", "kar_payi_orani"})
        self.assertEqual(ex.stats["kanit_reddi"], 0)

    def test_acik_iken_yalniz_kanitsiz_deger_dusuruluyor(self):
        ex = LLMExtractor(SahteIstemci(), require_evidence=True,
                          saglik_log="")
        alanlar = ex.extract(TEXT)
        self.assertEqual([f.field_name for f in alanlar], ["vade_ay"])
        # Kapı DAR olmalı: kanıtlı değer kesilmedi, sayaç yalnız 1 artmalı.
        self.assertEqual(ex.stats["kanit_reddi"], 1)
        self.assertIsNotNone(alanlar[0].span_start)

    def test_ortam_degiskeni_kapiyi_acar(self):
        with mock.patch.dict(os.environ, {"LLM_KANIT_ZORUNLU": "1"},
                             clear=False):
            ex = LLMExtractor(SahteIstemci(), saglik_log="")
        self.assertTrue(ex.require_evidence)

    def test_kanit_reddi_cagri_sonucunda_gorunur(self):
        ex = LLMExtractor(SahteIstemci(), require_evidence=True,
                          saglik_log="")
        sonuc = ex.call(TEXT)
        self.assertTrue(sonuc.ok)
        self.assertEqual(sonuc.kanit_reddi, 1)


class TestSaglikGunlugu(unittest.TestCase):

    def _oku(self, yol: Path) -> list[dict]:
        return [json.loads(s) for s in
                yol.read_text(encoding="utf-8").splitlines() if s.strip()]

    def test_her_cagri_bir_satir_yazar(self):
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "alt" / "llm-sagligi.jsonl"
            ex = LLMExtractor(SahteIstemci(), saglik_log=str(yol))
            ex.extract(TEXT)
            ex.extract(TEXT)
            satirlar = self._oku(yol)
        self.assertEqual(len(satirlar), 2)

    def test_satir_denetim_icin_gereken_alanlari_tasir(self):
        """Rapor bu anahtarları okuyor — adları sözleşmedir."""
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "llm-sagligi.jsonl"
            ex = LLMExtractor(SahteIstemci(), require_evidence=True,
                              saglik_log=str(yol))
            with mock.patch.dict(os.environ, {"LLM_KOSUM": "birim-test"},
                                 clear=False):
                ex.extract(TEXT, ["vade_ay", "kar_payi_orani"])
            kayit = self._oku(yol)[0]
        for anahtar in ("ts", "kosum", "model", "client", "structured_mode",
                        "num_predict", "kanit_zorunlu", "rol",
                        "istenen_alanlar", "metin_uzunlugu", "istem_uzunlugu",
                        "sure_ms", "sema_gecti", "sebep", "onarim",
                        "uretilen_alan", "kanit_reddi"):
            self.assertIn(anahtar, kayit, anahtar)
        self.assertEqual(kayit["kosum"], "birim-test")
        self.assertEqual(kayit["model"], "sahte-model")
        self.assertTrue(kayit["sema_gecti"])
        self.assertIsNone(kayit["sebep"])
        self.assertEqual(kayit["uretilen_alan"], 1)
        self.assertEqual(kayit["kanit_reddi"], 1)
        self.assertEqual(kayit["metin_uzunlugu"], len(TEXT))

    def test_basarisiz_cagri_da_yazilir_ve_sebebi_tasir(self):
        """Sessiz hata yutmanın sonu: HATA da bir satırdır."""
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "llm-sagligi.jsonl"
            ex = LLMExtractor(PatlayanIstemci(), strict=False,
                              saglik_log=str(yol))
            self.assertEqual(ex.extract(TEXT), [])
            kayit = self._oku(yol)[0]
        self.assertFalse(kayit["sema_gecti"])
        self.assertIn("baglanti reddedildi", kayit["sebep"])

    def test_yazilamayan_gunluk_cikarimi_dusurmez(self):
        """Denetim artefaktı, denetlenen işi bozmamalı."""
        with tempfile.TemporaryDirectory() as d:
            # Dosya yerine DİZİN: `open(..., "a")` OSError yükseltir.
            yol = Path(d) / "engel"
            yol.mkdir()
            ex = LLMExtractor(SahteIstemci(), saglik_log=str(yol))
            self.assertEqual(len(ex.extract(TEXT)), 2)


class TestGunlukYolu(unittest.TestCase):

    def test_backend_bosken_gunluk_kapali(self):
        """Sahte istemcilerle koşan birim testleri artefaktı kirletmemeli."""
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(_saglik_log_yolu(None))

    def test_backend_varken_varsayilan_yol(self):
        with mock.patch.dict(os.environ, {"LLM_BACKEND": "ollama"},
                             clear=True):
            self.assertEqual(_saglik_log_yolu(None),
                             Path(SAGLIK_LOG_VARSAYILAN))

    def test_ortam_degiskeni_yolu_ezer(self):
        with mock.patch.dict(os.environ,
                             {"LLM_BACKEND": "ollama",
                              "LLM_SAGLIK_LOG": "/tmp/x.jsonl"}, clear=True):
            self.assertEqual(_saglik_log_yolu(None), Path("/tmp/x.jsonl"))

    def test_kapatma_degerleri(self):
        with mock.patch.dict(os.environ,
                             {"LLM_BACKEND": "ollama",
                              "LLM_SAGLIK_LOG": "0"}, clear=True):
            self.assertIsNone(_saglik_log_yolu(None))
        self.assertIsNone(_saglik_log_yolu(""))


if __name__ == "__main__":
    unittest.main()


class TestYanitOnbellegi(unittest.TestCase):
    """Önbellek: ölçüm koşumunu yeniden başlatılabilir kılar, iddiayı ŞİŞİRMEZ."""

    def test_ikinci_cagri_istemciye_gitmez(self):
        with tempfile.TemporaryDirectory() as d:
            c = SahteIstemci()
            ex1 = LLMExtractor(c, saglik_log="", onbellek=d)
            ex1.extract(TEXT)
            self.assertEqual(c.cagri, 1)
            # AYNI istem, YENİ çıkarıcı (süreç ölüp yeniden başlamış gibi).
            c2 = SahteIstemci()
            ex2 = LLMExtractor(c2, saglik_log="", onbellek=d)
            alanlar = ex2.extract(TEXT)
        self.assertEqual(c2.cagri, 0, "önbellek isabeti istemciye gitmemeli")
        self.assertEqual(len(alanlar), 2, "önbellekten gelen yanıt da alan üretmeli")
        # `calls` "kaç çıkarım isteği geldi"yi sayar; önbellek isabeti de bir
        # istektir ve oraya girer. Künye "kaç tanesi GERÇEKTEN modele gitti"yi
        # AYRICA yayımlar — bu ayrım olmadan `calls: N, ok: N` satırı N gerçek
        # çağrı gibi okunurdu.
        self.assertEqual(ex2.stats["cache_hit"], 1)
        self.assertEqual(ex2.stats["calls"], 1)
        self.assertEqual(ex2.summary()["gercek_cagri"], 0)
        self.assertEqual(ex1.summary()["gercek_cagri"], 1)

    def test_onbellek_isabeti_gunluge_ISARETLENIR(self):
        """"384/384 temiz çağrı" iddiası önbellekle şişirilemesin."""
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "llm-sagligi.jsonl"
            onb = Path(d) / "onb"
            LLMExtractor(SahteIstemci(), saglik_log=str(log),
                         onbellek=str(onb)).extract(TEXT)
            LLMExtractor(SahteIstemci(), saglik_log=str(log),
                         onbellek=str(onb)).extract(TEXT)
            kayitlar = [json.loads(s) for s in
                        log.read_text(encoding="utf-8").splitlines() if s.strip()]
        self.assertEqual([k["onbellek"] for k in kayitlar], [False, True])

    def test_istem_degisirse_anahtar_degisir(self):
        """Bayat yanıt yeni bir yapılandırmaya sızmamalı."""
        with tempfile.TemporaryDirectory() as d:
            c = SahteIstemci()
            LLMExtractor(c, saglik_log="", onbellek=d).extract(TEXT)
            # Farklı çıktı bütçesi -> farklı anahtar -> gerçek çağrı.
            LLMExtractor(c, saglik_log="", onbellek=d,
                         num_predict=999).extract(TEXT)
        self.assertEqual(c.cagri, 2)

    def test_varsayilan_kapali(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(LLMExtractor(SahteIstemci()).onbellek)

    def test_bozuk_onbellek_dosyasi_cikarimi_dusurmez(self):
        with tempfile.TemporaryDirectory() as d:
            c = SahteIstemci()
            ex = LLMExtractor(c, saglik_log="", onbellek=d)
            ex.extract(TEXT)
            for yol in Path(d).glob("*.json"):
                yol.write_text("{bozuk", encoding="utf-8")
            ex2 = LLMExtractor(c, saglik_log="", onbellek=d)
            self.assertEqual(len(ex2.extract(TEXT)), 2)


class TestAlanBasinaKip(unittest.TestCase):
    """Sorgu granülaritesi: eksik alan başına AYRI çağrı (`LLM_ALAN_BASINA`)."""

    def test_varsayilan_coklu_alan_tek_cagri(self):
        c = SahteIstemci()
        ex = LLMExtractor(c, saglik_log="")
        ex.extract(TEXT, ["vade_ay", "kar_payi_orani"])
        self.assertFalse(ex.alan_basina)
        self.assertEqual(c.cagri, 1)

    def test_alan_basina_kipinde_alan_sayisi_kadar_cagri(self):
        c = SahteIstemci()
        ex = LLMExtractor(c, saglik_log="", alan_basina=True)
        ex.extract(TEXT, ["vade_ay", "kar_payi_orani", "tahsis_ucreti"])
        self.assertEqual(c.cagri, 3)
        self.assertEqual(ex.stats["calls"], 3)

    def test_ortam_degiskeni_kipi_acar(self):
        with mock.patch.dict(os.environ, {"LLM_ALAN_BASINA": "1"}, clear=False):
            self.assertTrue(LLMExtractor(SahteIstemci(), saglik_log="").alan_basina)

    def test_tek_alan_istemi_daraltilmis_talimat_tasir(self):
        """İki kol arasındaki tek fark granülarite olmalı — few-shot AYNI kalır."""
        ex = LLMExtractor(SahteIstemci(), saglik_log="")
        tek = ex._build_user_prompt(TEXT, ["vade_ay"])
        cok = ex._build_user_prompt(TEXT, ["vade_ay", "kar_payi_orani"])
        self.assertIn("YALNIZ bu tek alanı değerlendir", tek)
        self.assertIn("'vade_ay'", tek)
        self.assertNotIn("YALNIZ bu tek alanı", cok)
        self.assertIn("Listedeki HER alan için", cok)
        # few-shot gövdesi iki kolda da aynı olmalı
        self.assertEqual(tek.split("Şu alanları çıkar")[0],
                         cok.split("Şu alanları çıkar")[0])

    def test_hosgoruluda_bir_alanin_hatasi_otekileri_dusurmez(self):
        class Kismi:
            model = "kismi"
            def __init__(self): self.n = 0
            def generate_json(self, system, user, schema):
                self.n += 1
                if self.n == 1:
                    raise RuntimeError("ilk alan patladi")
                return {"vade_ay": {"value": 36, "confidence": 0.9,
                                    "source_span": "36 ay"}}
        ex = LLMExtractor(Kismi(), strict=False, saglik_log="", alan_basina=True)
        alanlar = ex.extract(TEXT, ["kar_payi_orani", "vade_ay"])
        self.assertEqual([f.field_name for f in alanlar], ["vade_ay"])

    def test_katida_ilk_hata_yukseltilir(self):
        """Katı modda ilk alanın hatası koşumu DURDURUR.

        İstisna tipi ÖZGÜL olarak beklenir: `assertRaises(Exception)` yazılsa
        test kör kalırdı — kod tamamen başka bir sebeple (ör. isim hatası)
        patladığında da geçerdi ve "katı mod çalışıyor" iddiası doğrulanmamış
        olurdu. Mesajın hangi alanda patladığını taşıdığı da doğrulanır.
        """
        ex = LLMExtractor(PatlayanIstemci(), strict=True, saglik_log="",
                          alan_basina=True)
        with self.assertRaises(LLMExtractionError) as ctx:
            ex.extract(TEXT, ["vade_ay", "kar_payi_orani"])
        self.assertIn("alan=vade_ay", str(ctx.exception))
        self.assertIn("baglanti reddedildi", str(ctx.exception))

    def test_kunye_granulariteyi_tasir(self):
        ex = LLMExtractor(SahteIstemci(), saglik_log="", alan_basina=True)
        self.assertTrue(ex.summary()["alan_basina"])
