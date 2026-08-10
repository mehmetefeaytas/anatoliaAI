"""Süresi dolmuş kampanya sıralamaya GİRMEZ ama tablodan da SİLİNMEZ.

İlgili: ../src/comparison/compare.py (`_durum_notu`, `rank`, `rank_advantageous`)
        ../src/db/base.py (`suresi_dolmus_mu`)
        ../src/pipeline.py (`collect_corpus` → `insert_campaign`)
        ../docs/rapor/suresi-dolmus-damgasi.md §5 (kapatılan boşluk)

## Bu testin varlık sebebi

`docs/rapor/suresi-dolmus-damgasi.md` korpustaki 458 belgeyi
`campaign_status: expired` ile işaretledi ve aynı raporun §5'i boşluğu açıkça
yazdı: *"Kıyas motoru bu alanı henüz OKUMUYOR."* Damga diskte duruyordu,
sıralama onu görmüyordu; kapanmış bir kampanyanın oranı hâlâ metinde yazılı
olduğu ve çıkarıcı onu yüksek güvenle bulduğu için, kapanmış kampanyalar
sıralamanın TEPESİNDE oturuyordu — bugün başvurulabilecek en iyi teklifin
üstünde.

Bu dosya iki şeyi birden kilitler, çünkü ikisinden yalnız biri doğruysa
düzeltme bozuktur:

1. Süresi dolmuş satır **sıralamaya girmez** (`comparable=False`).
2. Süresi dolmuş satır **listede kalır** ve gerekçesi görünür. Satırı düşürmek
   bilgiyi saklamak olurdu: kullanıcıya "bu bankada böyle bir kampanya yok"
   demek, oysa kampanya var — süresi dolmuş.

Üçüncü bir kapı da burada: **damgasız satır etkilenmez.** `None` "geçerli"
demek değil "bilinmiyor" demektir ve korpusun 1316 belgesi damgasızdır;
bunları elemek ölçülmemiş bir bilgi iddia etmek olurdu (CLAUDE.md §19).
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_KOK = Path(__file__).resolve().parents[1]
if str(_KOK) not in sys.path:
    sys.path.insert(0, str(_KOK))

from src.comparison.compare import (
    ASGARI_GUVEN,
    rank,
    rank_advantageous,
    tekil_banka_urun,
)
from src.db.base import (
    KAMPANYA_DURUMU_AKTIF,
    KAMPANYA_DURUMU_SURESI_DOLMUS,
    suresi_dolmus_mu,
)
from src.db.repository import Repository
from src.schemas import Campaign, ExtractedField, Extractor

ALAN = "kar_payi_orani"


def _satir(bank: str, deger: float, durum: str | None,
           guven: float = 0.95) -> dict:
    return {"bank": bank, "bank_name": bank.title(), "canonical_value": deger,
            "source_span": f"{bank} kanıtı", "campaign_id": hash(bank) % 9973,
            "campaign_type": "Konut Finansmanı", "confidence": guven,
            "campaign_status": durum}


class TestDurumYardimcisi(unittest.TestCase):
    """`suresi_dolmus_mu()` yalnız KESİN damgaya `True` der."""

    def test_yalniz_expired_true(self) -> None:
        self.assertTrue(suresi_dolmus_mu(KAMPANYA_DURUMU_SURESI_DOLMUS))

    def test_bilinmeyen_ve_aktif_false(self) -> None:
        # `None` = damgasız. Korpusun %74'ü bu durumda; `True` dönseydi kıyas
        # tablosu neredeyse tamamen boşalırdı.
        for durum in (None, KAMPANYA_DURUMU_AKTIF, "", "EXPIRED", "dolmus"):
            with self.subTest(durum=durum):
                self.assertFalse(suresi_dolmus_mu(durum))


class TestTekAlanliSiralama(unittest.TestCase):
    def test_suresi_dolmus_siralamaya_girmez(self) -> None:
        # Dolmuş kampanya SAYISAL OLARAK en iyisi: %1,00 diğer ikisini de
        # yener. Kapı çalışmazsa sıranın tepesinde o durur.
        rows = [
            _satir("dolmus", 1.00, KAMPANYA_DURUMU_SURESI_DOLMUS),
            _satir("acik-a", 2.50, None),
            _satir("acik-b", 3.10, KAMPANYA_DURUMU_AKTIF),
        ]
        siralama = rank(rows, ALAN)

        kiyaslanabilir = [x for x in siralama if x.comparable]
        self.assertEqual([x.bank for x in kiyaslanabilir], ["acik-a", "acik-b"])
        self.assertEqual(siralama[0].bank, "acik-a",
                         "kapanmış kampanya sıralamanın tepesinde kaldı")

    def test_satir_SILINMEZ_gerekcesiyle_kalir(self) -> None:
        rows = [_satir("dolmus", 1.00, KAMPANYA_DURUMU_SURESI_DOLMUS),
                _satir("acik", 2.50, None)]
        siralama = rank(rows, ALAN)

        self.assertEqual(len(siralama), 2, "satır listeden düşürülmüş")
        dolmus = next(x for x in siralama if x.bank == "dolmus")
        self.assertFalse(dolmus.comparable)
        self.assertIsNotNone(dolmus.note)
        self.assertIn("süresi dolmuş", dolmus.note)
        # Değer GÖRÜNÜR kalır — "veri yok" ile karıştırılmamalı.
        self.assertEqual(dolmus.value, 1.00)
        # Rozet nottan AYRI alandan okunur.
        self.assertEqual(dolmus.campaign_status, KAMPANYA_DURUMU_SURESI_DOLMUS)

    def test_damgasiz_satir_etkilenmez(self) -> None:
        siralama = rank([_satir("a", 1.0, None), _satir("b", 2.0, None)], ALAN)
        self.assertTrue(all(x.comparable for x in siralama))
        self.assertTrue(all(x.campaign_status is None for x in siralama))

    def test_sure_kapisi_guven_kapisinin_ONUNDE(self) -> None:
        """İkisi de ateşlenirse gösterilen gerekçe süredir.

        Düşük güven bir ÖLÇÜM kusurudur; süresi dolmuşluk ürünün kendisiyle
        ilgili bir gerçektir. Kullanıcıya tek not gösteriliyorsa daha temel
        olan eleme sebebi yazmalıdır.
        """
        rows = [_satir("d", 1.0, KAMPANYA_DURUMU_SURESI_DOLMUS,
                       guven=ASGARI_GUVEN - 0.2)]
        (satir,) = rank(rows, ALAN)
        self.assertFalse(satir.comparable)
        self.assertIn("süresi dolmuş", satir.note)

    def test_asil_neden_gizlenmez(self) -> None:
        """Zaten kıyaslanamayan satırın notu süreyle EZİLMEZ.

        Aralık, süre kapısından önce gelen ve kendi başına yeterli bir
        gerekçedir; üstüne yazmak asıl nedeni gizlerdi. Güven kapısındaki
        aynı kural.
        """
        rows = [{**_satir("d", 0.0, KAMPANYA_DURUMU_SURESI_DOLMUS),
                 "canonical_value": {"min": 1.5, "max": 2.5}}]
        (satir,) = rank(rows, ALAN)
        self.assertFalse(satir.comparable)
        self.assertIn("aralık", satir.note)
        # Rozet yine de doğru: iki bilgi tek dizeye sıkıştırılmıyor.
        self.assertEqual(satir.campaign_status, KAMPANYA_DURUMU_SURESI_DOLMUS)

    def test_tekillestirme_acik_kampanyayi_tercih_eder(self) -> None:
        """Aynı bankanın açık ve kapalı kampanyası varsa açık olan temsil eder.

        `tekil_banka_urun()` ayrı bir "en iyiyi seç" mantığı yazmaz, sıranın
        ilk satırını alır — kapı çalışıyorsa kapanmış satır zaten arkadadır.
        """
        rows = [_satir("banka", 1.00, KAMPANYA_DURUMU_SURESI_DOLMUS),
                _satir("banka", 2.50, None)]
        # `_satir` kampanya kimliğini bankadan türetiyor; ikisi ayrı olmalı.
        rows[0]["campaign_id"] = 1
        rows[1]["campaign_id"] = 2
        (tek,) = tekil_banka_urun(rank(rows, ALAN))
        self.assertTrue(tek.comparable)
        self.assertEqual(tek.value, 2.50)


class TestBilesikSkor(unittest.TestCase):
    """`rank_advantageous` tek alanlı yolla AYNI kapıyı uygular."""

    def _kampanya(self, bank: str, oran: float, durum: str | None) -> dict:
        return {"bank": bank, "bank_name": bank.title(), "campaign_id": bank,
                "campaign_type": "Konut Finansmanı",
                "fields": {"kar_payi_orani": oran, "vade_ay": 120,
                           "masraf_durumu": {"has_fee": False}},
                "field_confidence": {"kar_payi_orani": 0.95, "vade_ay": 0.95,
                                     "masraf_durumu": 0.95},
                "campaign_status": durum}

    def test_dolmus_kampanya_kiyaslanabilir_degil(self) -> None:
        skorlar = rank_advantageous([
            self._kampanya("dolmus", 1.00, KAMPANYA_DURUMU_SURESI_DOLMUS),
            self._kampanya("acik-a", 2.50, None),
            self._kampanya("acik-b", 3.10, None),
        ])
        dolmus = next(c for c in skorlar if c.bank == "dolmus")
        self.assertFalse(dolmus.comparable)
        self.assertIn("süresi dolmuş", dolmus.note or "")
        self.assertEqual(dolmus.campaign_status, KAMPANYA_DURUMU_SURESI_DOLMUS)
        # Kıyaslanamayanlar SONA alınır — gizlenmez.
        self.assertEqual(skorlar[-1].bank, "dolmus")
        self.assertTrue(skorlar[0].comparable)

    def test_not_olcum_kusuru_gibi_okunmaz(self) -> None:
        """Tüm alanları düşen kampanya "ölçülebilen ölçüt yok" DEMEZ.

        O metin çıkarımın başarısızlığını anlatır; buradaki sebep başkadır ve
        yanlış gerekçe göstermek, doğru gerekçeyi gizlemekle aynı kusurdur.
        """
        (skor,) = rank_advantageous(
            [self._kampanya("tek", 1.0, KAMPANYA_DURUMU_SURESI_DOLMUS)])
        self.assertIn("süresi dolmuş", skor.note or "")


class TestKorpustanDBye(unittest.TestCase):
    """`.meta.json` → `campaigns.campaign_status` → `query_fields` zinciri.

    Damga diskte doğru ama DB'ye taşınmıyorsa kıyas kapısı hiç ateşlenmez —
    kusurun 10 Ağu 2026'ya kadarki tam hâli buydu. Zincir uçtan uca ölçülür.
    """

    def _korpus_yaz(self, kok: Path, slug: str, ad: str, metin: str,
                    durum: str | None) -> None:
        d = kok / slug / "live"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{ad}.txt").write_text(metin, encoding="utf-8")
        meta = {"source_url": f"https://ornek.test/{slug}/{ad}",
                "scraped_at": "2026-08-10T00:00:00+00:00"}
        if durum is not None:
            meta["campaign_status"] = durum
        (d / f"{ad}.txt.meta.json").write_text(
            json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    def test_sidecar_damgasi_query_fields_e_ulasir(self) -> None:
        from src.pipeline import MODE_CORPUS, run_pipeline

        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            raw = kok / "raw"
            self._korpus_yaz(raw, "ornek-banka", "kapali",
                             "Kampanya kâr payı oranı %1,00'dır.",
                             KAMPANYA_DURUMU_SURESI_DOLMUS)
            self._korpus_yaz(raw, "ornek-banka", "acik",
                             "Kampanya kâr payı oranı %2,50'dir.", None)
            banks = kok / "banks.yaml"
            banks.write_text(
                "banks:\n  - name: Örnek Banka\n    slug: ornek-banka\n"
                "    website_url: https://ornek.test\n", encoding="utf-8")

            repo = Repository(str(kok / "t.db"))
            try:
                run_pipeline(repo, str(banks), raw_dir=str(raw),
                             mode=MODE_CORPUS)
                durumlar = {c["source_url"].rsplit("/", 1)[-1]:
                            c.get("campaign_status")
                            for c in repo.all_campaigns()}
                self.assertEqual(durumlar.get("kapali"),
                                 KAMPANYA_DURUMU_SURESI_DOLMUS)
                self.assertIsNone(durumlar.get("acik"),
                                  "damgasız belgeye durum UYDURULDU")

                satirlar = repo.query_fields(ALAN)
                self.assertTrue(satirlar, "korpustan hiç oran çıkmadı")
                self.assertIn("campaign_status", satirlar[0],
                              "sütun query_fields çıktısına taşınmıyor")
            finally:
                repo.close()

    def test_insert_campaign_durumu_yazar_ve_okur(self) -> None:
        """Depo sözleşmesinin kendisi — pipeline'dan bağımsız."""
        repo = Repository(":memory:")
        try:
            c = Campaign(
                bank_slug="x", raw_text="Kâr payı oranı %1,00", source_url="u",
                campaign_type="Konut Finansmanı",
                fields=[ExtractedField(
                    field_name=ALAN, raw_value="%1,00", canonical_value=1.0,
                    confidence=0.95, source_span="Kâr payı oranı %1,00",
                    extractor=Extractor.RULE)])
            cid = repo.insert_campaign(
                c, clean_text="Kâr payı oranı %1,00",
                campaign_status=KAMPANYA_DURUMU_SURESI_DOLMUS)
            self.assertEqual(
                repo.campaign_text(cid)["campaign_status"],
                KAMPANYA_DURUMU_SURESI_DOLMUS)
            (satir,) = repo.query_fields(ALAN)
            self.assertEqual(satir["campaign_status"],
                             KAMPANYA_DURUMU_SURESI_DOLMUS)
            # Ve kıyas motoru bunu görüyor.
            (siralanmis,) = rank([satir], ALAN)
            self.assertFalse(siralanmis.comparable)
        finally:
            repo.close()

    def test_durum_verilmezse_NULL_kalir(self) -> None:
        """Varsayılan uydurulmaz: damgasız kampanya damgasız kalır."""
        repo = Repository(":memory:")
        try:
            c = Campaign(bank_slug="x", raw_text="metin", source_url="u",
                         campaign_type=None, fields=[])
            cid = repo.insert_campaign(c, clean_text="metin")
            self.assertIsNone(repo.campaign_text(cid)["campaign_status"])
        finally:
            repo.close()


if __name__ == "__main__":
    unittest.main()
