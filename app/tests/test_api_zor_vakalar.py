"""Zor vaka tezgâhı: gerçek korpus metni, altın referans, tek doğruluk tanımı.

İlgili: ../src/api/zor_vaka.py, ../src/api/main.py (`GET /zor-vakalar`,
        `POST /extract`), ../web/app/components/ExtractLive.tsx
        ../eval/matchers.py, ../scripts/gold_schema.py

## Bu testlerin varlık sebebi

"Canlı Çıkarım" ekranı bir geliştirici formuydu: dört ADET ELLE YAZILMIŞ örnek
metin ve karşılaştırılacak hiçbir referans. Kendi yazdığın metinden kendi
çıkardığın değer hiçbir şeyin kanıtı değildir. Ekran artık altın kümenin ZOR
işaretli belgeleriyle çalışıyor ve model çıktısını altın değerle yan yana
çiziyor.

Buradaki kapılar üç geri adımı engeller:

1. **Ekranın yeniden uydurma metinlere dönmesi.** Kaynak düzeyinde denetlenir:
   bileşen vaka listesini sunucudan okumak ZORUNDA.
2. **Doğruluk tanımının ikizlenmesi.** Eşleşme kararı ölçüm koşusunun
   kullandığı eşleştiricilerden gelmeli; arayüzde ikinci bir "doğru" tanımı
   yazılırsa jüriye gösterilen tablo ile rapordaki F1 sessizce ayrışır.
3. **Uydurmanın uyuşmazlık içinde kaybolması.** Altın küme "bu belgede bu alan
   YOK" dediği yerde üretilen değer ayrı bir durumdur (`fabricated`) ve ayrı
   sayılır — projenin merkezindeki iddia tam olarak o sayıyla ayakta durur.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.gold_schema import HARD_TAGS
from src.api import zor_vaka
from src.db.repository import Repository
from src.extraction.llm.schema import EXTRACTION_FIELDS
from tests._ortam_gereksinimleri import arayuz_gerekir

KOK = Path(__file__).resolve().parents[1]

try:  # pragma: no cover - ortama bağlı
    import httpx  # noqa: F401
    from fastapi.testclient import TestClient  # noqa: F401
    HAS_API = True
except ModuleNotFoundError:  # pragma: no cover
    HAS_API = False

requires_api = unittest.skipUnless(
    HAS_API, "fastapi/httpx yok — zor vaka uç testleri atlanıyor")

#: Alan etiketleri testte SABİT değil, sunucunun kullandığı sözlükten gelir.
ETIKETLER = {ad: ad for ad in EXTRACTION_FIELDS}


def _kayit(**degisiklik):
    """Elle kurulmuş tek bir altın kayıt — karşılaştırma semantiği için."""
    temel = {
        "id": "test--vaka",
        "bank_slug": "ornek-katilim",
        "source_url": "https://ornek-katilim.test/kampanya",
        "campaign_type": "Konut Finansmanı",
        "hard_tags": ["kosullu_aralik"],
        "hard": True,
        "text": "Kâr payı oranı %1,99 - %2,49 arasındadır.",
        "fields": {"kar_payi_orani": {"min": 1.99, "max": 2.49}},
        "field_spans": {"kar_payi_orani": "%1,99 - %2,49"},
        "absent_fields": ["tahsis_ucreti"],
        "unclear_fields": ["masraf_durumu"],
        "notes": {},
    }
    temel.update(degisiklik)
    return temel


class TestTaksonomi(unittest.TestCase):
    """Etiket sözlüğü ile taksonomi AYRIŞAMAZ."""

    def test_her_zor_etiketin_turkce_karsiligi_var(self) -> None:
        for etiket in HARD_TAGS:
            self.assertIn(etiket, zor_vaka.ETIKET_ADLARI,
                          f"{etiket} için ekranda gösterilecek ad yok")
            ad, aciklama = zor_vaka.ETIKET_ADLARI[etiket]
            self.assertTrue(ad.strip() and aciklama.strip())

    def test_uydurulmus_etiket_yok(self) -> None:
        """Sözlükte taksonomide olmayan bir etiket bulunmamalı."""
        for etiket in zor_vaka.ETIKET_ADLARI:
            self.assertIn(etiket, HARD_TAGS)

    def test_etiket_sirasi_taksonomiden_gelir(self) -> None:
        """Sayıma göre sıralanırsa çipler her tazelemede yer değiştirirdi."""
        ozet = zor_vaka.etiket_ozeti()
        self.assertEqual([e["etiket"] for e in ozet][:len(HARD_TAGS)],
                         list(HARD_TAGS))


class TestAltinKume(unittest.TestCase):
    """Servis edilen küme gerçekten ZOR ve gerçekten korpustan."""

    def setUp(self) -> None:
        self.liste = zor_vaka.liste(ETIKETLER, {})

    def test_kaynak_okunuyor(self) -> None:
        self.assertTrue(self.liste["kaynak_var"])
        self.assertGreater(self.liste["zor_belge"], 0)

    def test_yalniz_zor_belgeler(self) -> None:
        for v in self.liste["vakalar"]:
            self.assertTrue(v["zor_etiketler"],
                            f"{v['id']} zor etiketi olmadan listeye girmiş")

    def test_metin_ve_kaynak_zinciri_tasiniyor(self) -> None:
        """Her vaka metnini ve kaynak adresini taşımak ZORUNDA.

        Metin olmadan çıkarım koşturulamaz; kaynak adresi olmadan jüri
        belgenin gerçekten korpustan geldiğini denetleyemez.
        """
        for v in self.liste["vakalar"]:
            self.assertTrue(v["metin"].strip(), f"{v['id']} metinsiz")
            self.assertEqual(v["metin_uzunlugu"], len(v["metin"]))
            self.assertTrue((v["kaynak_adresi"] or "").startswith("http"))

    def test_etiket_sayilari_vakalarla_tutarli(self) -> None:
        for e in self.liste["etiketler"]:
            gercek = sum(1 for v in self.liste["vakalar"]
                         if e["etiket"] in v["zor_etiketler"])
            self.assertEqual(e["adet"], gercek, f"{e['etiket']} sayacı yanlış")

    def test_kayip_dosya_SAHTE_LISTE_URETMEZ(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            yok = str(Path(d) / "olmayan.json")
            bos = zor_vaka.liste(ETIKETLER, {}, yol=yok)
        self.assertFalse(bos["kaynak_var"])
        self.assertEqual(bos["vakalar"], [])


class TestKarsilastirma(unittest.TestCase):
    """Durum kararları — ölçüm koşusunun eşleştiricileriyle aynı semantik."""

    def _kiyas(self, model, **degisiklik):
        return zor_vaka.karsilastir(_kayit(**degisiklik), model, ETIKETLER,
                                    list(EXTRACTION_FIELDS), metin_ayni=True)

    def _durum(self, sonuc, alan):
        return next(f["status"] for f in sonuc["fields"] if f["field"] == alan)

    def test_her_alan_TAM_OLARAK_bir_kez(self) -> None:
        s = self._kiyas({})
        adlar = [f["field"] for f in s["fields"]]
        self.assertEqual(adlar, list(EXTRACTION_FIELDS))
        self.assertEqual(sum(s["summary"].values()), len(EXTRACTION_FIELDS))

    def test_birebir_eslesme(self) -> None:
        s = self._kiyas({"kar_payi_orani": {"min": 1.99, "max": 2.49}})
        self.assertEqual(self._durum(s, "kar_payi_orani"), "match")

    def test_aralik_ici_skaler_ESDEGER_sayilir(self) -> None:
        """Aralıktan tek uç çıkarmak, hiçbir şey çıkarmamaktan farklıdır.

        Katı modda hata, gevşek modda kısmi kredi — ikisi arasındaki fark
        ekranda `esdeger` olarak görünür ve "kaç hata biçim hatası"
        sorusunun cevabıdır.
        """
        s = self._kiyas({"kar_payi_orani": 1.99})
        self.assertEqual(self._durum(s, "kar_payi_orani"), "equivalent")

    def test_gercek_uyusmazlik(self) -> None:
        s = self._kiyas({"kar_payi_orani": 4.5})
        self.assertEqual(self._durum(s, "kar_payi_orani"), "mismatch")
        gerekce = next(f["reason"] for f in s["fields"]
                       if f["field"] == "kar_payi_orani")
        self.assertTrue(gerekce.strip(), "uyuşmazlık gerekçesiz kalamaz")

    def test_model_bulamadi(self) -> None:
        self.assertEqual(self._durum(self._kiyas({}), "kar_payi_orani"),
                         "missed")

    def test_UYDURMA_ayri_bir_durumdur(self) -> None:
        """Altın küme "kontrol ettim, YOK" dediği alanda üretilen değer."""
        s = self._kiyas({"tahsis_ucreti": {"value": 750.0, "currency": "TRY"}})
        self.assertEqual(self._durum(s, "tahsis_ucreti"), "fabricated")
        self.assertEqual(s["summary"]["fabricated"], 1)
        self.assertEqual(s["summary"]["mismatch"], 0,
                         "uydurma, uyuşmazlık sayacına karışmamalı")

    def test_dogru_bosluk(self) -> None:
        self.assertEqual(self._durum(self._kiyas({}), "tahsis_ucreti"),
                         "correct_absence")

    def test_belirsiz_alan_OLCUM_DISI(self) -> None:
        s = self._kiyas({"masraf_durumu": {"has_fee": False, "amount": None}})
        self.assertEqual(self._durum(s, "masraf_durumu"), "unclear")

    def test_degerlendirilmemis_alan_UYUSMAZLIK_DEGIL(self) -> None:
        """Referans olmayan yerde doğru/yanlış denmez.

        `vade_ay` ne `fields` ne `absent_fields` içinde: anotatör oraya hiç
        bakmamış. Model orada bir değer üretse de üretmese de bu bir hata
        değildir; boş hücreyi uyuşmazlık gibi göstermek olmayan bir hata icat
        etmek olurdu.
        """
        for model in ({}, {"vade_ay": 120}):
            with self.subTest(model=model):
                self.assertEqual(self._durum(self._kiyas(model), "vade_ay"),
                                 "out_of_scope")

    def test_altin_deger_ve_dayanagi_tasiniyor(self) -> None:
        satir = next(f for f in self._kiyas({})["fields"]
                     if f["field"] == "kar_payi_orani")
        self.assertEqual(satir["gold_value"], {"min": 1.99, "max": 2.49})
        self.assertEqual(satir["gold_span"], "%1,99 - %2,49")
        self.assertTrue(satir["gold_present"])


@requires_api
class TestUclar(unittest.TestCase):
    """HTTP yüzeyi — sözleşme ve geriye uyumluluk."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        Repository(str(Path(self._tmp.name) / "t.db")).close()
        self._eski = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(Path(self._tmp.name) / "t.db")
        self.c = self._istemci()

    def tearDown(self) -> None:
        if self._eski is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = self._eski
        self._tmp.cleanup()

    def _istemci(self):
        import importlib

        from fastapi.testclient import TestClient

        from src.api import main as M
        importlib.reload(M)
        return TestClient(M.build_app())

    def test_liste_ucu(self) -> None:
        y = self.c.get("/zor-vakalar")
        self.assertEqual(y.status_code, 200)
        veri = y.json()
        self.assertTrue(veri["kaynak_var"])
        self.assertEqual(len(veri["vakalar"]), veri["zor_belge"])
        self.assertLessEqual(veri["zor_belge"], veri["toplam_belge"])

    def test_extract_gold_id_OLMADAN_eskisi_gibi(self) -> None:
        """Serbest metin yolu bozulmamalı — `gold` yalnızca `null` eklenir."""
        y = self.c.post("/extract", json={"text": "Kâr payı oranı %2,05."})
        self.assertEqual(y.status_code, 200)
        veri = y.json()
        self.assertIsNone(veri["gold"])
        for anahtar in ("fields", "missing_fields", "contradictions", "text"):
            self.assertIn(anahtar, veri)

    def test_extract_gold_id_ILE_karsilastirma_doner(self) -> None:
        vaka = self.c.get("/zor-vakalar").json()["vakalar"][0]
        y = self.c.post("/extract", json={"text": vaka["metin"],
                                          "bank": vaka["banka"],
                                          "gold_id": vaka["id"]})
        self.assertEqual(y.status_code, 200)
        gold = y.json()["gold"]
        self.assertEqual(gold["id"], vaka["id"])
        self.assertTrue(gold["text_matches"])
        self.assertEqual(len(gold["fields"]), len(EXTRACTION_FIELDS))
        self.assertEqual(sum(gold["summary"].values()), len(EXTRACTION_FIELDS))

    def test_degistirilmis_metin_ISARETLENIR(self) -> None:
        """Metin elle değiştirildiğinde ölçüm artık aynı belgenin değildir."""
        vaka = self.c.get("/zor-vakalar").json()["vakalar"][0]
        y = self.c.post("/extract", json={"text": vaka["metin"] + " Ek cümle.",
                                          "gold_id": vaka["id"]})
        self.assertFalse(y.json()["gold"]["text_matches"])

    def test_bilinmeyen_gold_id_CIKARIMI_COPE_ATMAZ(self) -> None:
        y = self.c.post("/extract", json={"text": "Kâr payı oranı %2,05.",
                                          "gold_id": "boyle-bir-vaka-yok"})
        self.assertEqual(y.status_code, 200)
        self.assertIsNone(y.json()["gold"])
        self.assertTrue(y.json()["fields"], "çıkarım yine de koşmalıydı")


@arayuz_gerekir
class TestEkranUydurmaMetne_DONMEZ(unittest.TestCase):
    """`ExtractLive` vakalarını SUNUCUDAN okumalı, kendi içinde tutmamalı."""

    def setUp(self) -> None:
        self.kaynak = (KOK / "web" / "app" / "components"
                       / "ExtractLive.tsx").read_text(encoding="utf-8")

    def test_vaka_listesi_sunucudan(self) -> None:
        self.assertIn("zorVakalar", self.kaynak,
                      "vaka listesi sunucudan okunmalı")

    def test_elle_yazilmis_ornek_metin_YOK(self) -> None:
        """Eski dört örnek metin geri gelirse ekran yine referanssız olur."""
        for iz in ("SAMPLES", "Konut Finansmanı Kampanyası.",
                   "Hayalinizdeki eve kavuşun"):
            self.assertNotIn(iz, self.kaynak)

    def test_altin_bosluk_ACIKCA_yazilir(self) -> None:
        """Boş bir hücre uyuşmazlık gibi okunur; sebebi yazılmak zorunda."""
        self.assertIn("altında yok", self.kaynak)

    def test_karsilastirma_karari_EKRANDA_HESAPLANMAZ(self) -> None:
        """Doğruluk tanımı tek yerde yaşar: ölçüm koşusunun eşleştiricileri.

        Ekranda ikinci bir eşitlik karşılaştırması yazılırsa jüriye gösterilen
        tablo ile rapordaki metrik sessizce ayrışabilir.
        """
        for yasak in ("JSON.stringify(gold", "=== g.gold_value",
                      "gold_value ==="):
            self.assertNotIn(yasak, self.kaynak)
        self.assertIn("status", self.kaynak,
                      "karar sunucudan gelen `status` alanından okunmalı")


if __name__ == "__main__":
    unittest.main()
