"""Kıyasın iki adil-kıyas kapısı: **kapsam** ve **oran bazı**.

İlgili: ../src/comparison/compare.py (`rank`, `_kapsam_eksikleri`, `_baz_notu`,
                                     `delta_between`, `rank_advantageous`)
        ../src/api/main.py (`/compare` — `_kiyas_kapsami`)
        CLAUDE.md §6 (aylık vs. yıllık baz), §17 (adil kıyas), §21 (uydurma yok)

## Kapsam kapısı — neden test edilir

Şartnamenin beklenen çıktı tablosu (s.11–12) üç bankalı bir konut finansmanı
tablosudur ve B ile C bankalarının bazı hücreleri boştur ("Belirtilmemiş",
"Masraf belirtilmemiş"). Satırlar eksik alana rağmen DURUYOR. Sistem ise alanı
olmayan bankayı tablodan tamamen düşürüyordu.

Kök neden ölçüldü (2026-08-16, `data/demo.db`): `rank()` DEĞİL. `rank()` satırı
olan hiçbir bankayı düşürmez, `comparable=False` işaretler. Kayıp bir adım önce,
`repo.query_fields(field)` adımında oluyor — o alanda `extracted_fields` satırı
olmayan banka sorguya hiç girmiyor. `/compare?field=kar_payi_orani&type=Konut
Finansmanı` sekiz bankanın altısını döndürüyordu; Ziraat Katılım (46 konut
kampanyası) ve Adil Katılım sessizce düşüyordu.

## Baz kapısı — neden test edilir

`delta_between()` ve `rank()` iki oranı yalnız SAYI olarak görüyordu: aylık
%1,89 ile yıllık %24,0 aynı eksende sıralanıyordu. Kapı, bazın veriye girdiği
gün sessizce yanlış sıralanmaması içindir; bilinmeyen bazda ateşlenmez ve
yıllık→aylık ÇEVİRİ yapmaz (türetilmiş sayı, uydurma sıralamanın hesap
makinesiyle yapılmış hâli olurdu).
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.comparison.compare import (
    ELEME_ALAN_YOK,
    ELEME_ORAN_BAZI,
    ELEME_SURESI_DOLMUS,
    KANONIK_ORAN_BAZI,
    NOT_ALAN_YOK,
    RANK_KAPI_ALANLARI,
    best,
    delta_between,
    eleme_sebebi,
    oran_bazi_dogrula,
    rank,
    rank_advantageous,
    tekil_banka_urun,
    turlere_ayir,
    yon_zorla,
)

ALAN = "kar_payi_orani"


def satir(bank: str, deger, tur: str = "Konut Finansmanı", **ek) -> dict:
    """`rank()` girdisi — kapı alanlarının tamamı taşınır."""
    temel = {
        "bank": bank,
        "bank_name": bank.title(),
        "canonical_value": deger,
        "source_span": f"kâr payı oranı %{deger} ile.",
        "campaign_id": abs(hash((bank, str(deger), tur))) % 10_000,
        "campaign_type": tur,
        "confidence": 0.95,
        "campaign_status": None,
        "raw_value": None,
        "oran_bazi": None,
    }
    temel.update(ek)
    return temel


def kapsam_ogesi(bank: str, tur: str = "Konut Finansmanı") -> dict:
    return {"bank": bank, "bank_name": bank.title(), "campaign_type": tur}


# =========================================================================== #
# MADDE 1 — kapsam kapısı
# =========================================================================== #


class TestKapsamKapisi(unittest.TestCase):
    def test_kapsam_verilmezse_davranis_AYNEN_eskisi(self) -> None:
        """Kapsam isteğe bağlıdır; geçirmeyen çağıranlar etkilenmez."""
        rows = [satir("kuveyt-turk", 1.89)]
        self.assertEqual(len(rank(rows, ALAN)), 1)
        self.assertEqual(len(rank(rows, ALAN, kapsam=None)), 1)

    def test_alani_OLMAYAN_banka_kapsamsiz_YOK_OLUYOR(self) -> None:
        """Kusurun kendisi: satırı olmayan banka çıktıda hiç görünmüyor.

        Bu test düzeltmeyi değil, düzeltmenin SEBEBİNİ kilitler. Kapsam
        mekanizması bir gün sessizce devre dışı kalırsa buradaki iddia hâlâ
        doğru olur ve bir alttaki test düşer.
        """
        ranked = rank([satir("kuveyt-turk", 1.89)], ALAN)
        self.assertEqual([x.bank for x in ranked], ["kuveyt-turk"])

    def test_kapsamdaki_her_banka_GORUNUR(self) -> None:
        ranked = rank(
            [satir("kuveyt-turk", 1.89)],
            ALAN,
            kapsam=[kapsam_ogesi("kuveyt-turk"), kapsam_ogesi("ziraat-katilim")],
        )
        self.assertEqual(sorted(x.bank for x in ranked),
                         ["kuveyt-turk", "ziraat-katilim"])

    def test_eksik_banka_belirtilmemis_olarak_ve_KIYAS_DISI_gelir(self) -> None:
        ranked = rank([satir("kuveyt-turk", 1.89)], ALAN,
                      kapsam=[kapsam_ogesi("ziraat-katilim")])
        eksik = next(x for x in ranked if x.bank == "ziraat-katilim")
        self.assertIsNone(eksik.value, "değer UYDURULMAZ — null kalır")
        self.assertIsNone(eksik.sort_key)
        self.assertFalse(eksik.comparable)
        self.assertEqual(eksik.note, NOT_ALAN_YOK)
        self.assertEqual(eleme_sebebi(eksik.note), ELEME_ALAN_YOK)
        self.assertEqual(eksik.campaign_type, "Konut Finansmanı")
        self.assertIsNone(eksik.campaign_id, "kaynak belgesi YOKTUR")

    def test_eksik_banka_SIRALAMAYA_girmez(self) -> None:
        """Değeri olmayan satır ne tepede ne de sıranın içinde durur."""
        rows = [satir("kuveyt-turk", 1.89), satir("albaraka", 2.95)]
        ranked = rank(rows, ALAN, kapsam=[kapsam_ogesi("ziraat-katilim")])
        self.assertEqual([x.bank for x in ranked][:2],
                         ["kuveyt-turk", "albaraka"])
        self.assertEqual(ranked[-1].bank, "ziraat-katilim")
        en_iyi = best(rows + [], ALAN)
        self.assertIsNotNone(en_iyi)
        self.assertEqual(en_iyi.bank, "kuveyt-turk")

    def test_kapsam_satirlari_ELENEN_satirlarin_ARKASINDA_durur(self) -> None:
        """Ölçülmüş bir boşluk, hiç ölçülmemiş bir alanın ÖNÜNDE gelir."""
        rows = [satir("albaraka", {"min": 3.85, "max": 3.95})]
        ranked = rank(rows, ALAN, kapsam=[kapsam_ogesi("ziraat-katilim")])
        self.assertEqual([x.bank for x in ranked],
                         ["albaraka", "ziraat-katilim"])

    def test_anahtar_banka_DEGIL_banka_x_tur(self) -> None:
        """Konutta oranı olan banka, taşıtta da olduğu varsayılmaz."""
        rows = [satir("kuveyt-turk", 1.89, "Konut Finansmanı")]
        kapsam = [kapsam_ogesi("kuveyt-turk", "Konut Finansmanı"),
                  kapsam_ogesi("kuveyt-turk", "Taşıt Finansmanı")]
        ranked = rank(rows, ALAN, kapsam=kapsam)
        cift = {(x.bank, x.campaign_type): x for x in ranked}
        self.assertEqual(len(cift), 2)
        self.assertTrue(cift[("kuveyt-turk", "Konut Finansmanı")].comparable)
        self.assertEqual(cift[("kuveyt-turk", "Taşıt Finansmanı")].note,
                         NOT_ALAN_YOK)

    def test_ayni_kapsam_ogesi_iki_kez_TEK_satir_uretir(self) -> None:
        ranked = rank([], ALAN,
                      kapsam=[kapsam_ogesi("ziraat-katilim"),
                              kapsam_ogesi("ziraat-katilim")])
        self.assertEqual(len(ranked), 1)

    def test_sira_KARARLIDIR(self) -> None:
        """Sıralama anahtarı olmayan satırlar çağrıdan çağrıya oynamaz."""
        kapsam = [kapsam_ogesi("ziraat-katilim"), kapsam_ogesi("adil-katilim"),
                  kapsam_ogesi("hayat-finans")]
        bir = [x.bank for x in rank([], ALAN, kapsam=kapsam)]
        iki = [x.bank for x in rank([], ALAN, kapsam=list(reversed(kapsam)))]
        self.assertEqual(bir, iki)
        self.assertEqual(bir, ["adil-katilim", "hayat-finans", "ziraat-katilim"])

    def test_yon_zorla_kapsam_satirini_ONE_almaz(self) -> None:
        rows = [satir("kuveyt-turk", 1.89), satir("albaraka", 2.95)]
        ranked = rank(rows, ALAN, kapsam=[kapsam_ogesi("ziraat-katilim")])
        for niyet in ("lowest", "highest"):
            with self.subTest(niyet=niyet):
                self.assertEqual(yon_zorla(ranked, ALAN, niyet)[-1].bank,
                                 "ziraat-katilim")

    def test_tekillestirme_ve_gruplama_kapsam_satirini_korur(self) -> None:
        rows = [satir("kuveyt-turk", 1.89), satir("kuveyt-turk", 2.49)]
        ranked = rank(rows, ALAN, kapsam=[kapsam_ogesi("ziraat-katilim")])
        tekil = tekil_banka_urun(ranked)
        eksik = next(x for x in tekil if x.bank == "ziraat-katilim")
        self.assertEqual(eksik.other_count, 0,
                         "temsil ettiği başka kampanya yok")
        gruplar = dict(turlere_ayir(tekil))
        self.assertEqual(
            sorted(x.bank for x in gruplar["Konut Finansmanı"]),
            ["kuveyt-turk", "ziraat-katilim"])


class TestKapsamUcu(unittest.TestCase):
    """`/compare` gerçekten kapsam satırı döndürüyor mu (uçtan uca)."""

    def setUp(self) -> None:
        try:
            import fastapi  # noqa: F401
        except (ImportError, RuntimeError) as e:  # pragma: no cover
            self.skipTest(f"fastapi/testclient yok: {e}")
        from src.db.repository import Repository
        from src.extraction.reconcile import build_campaign

        self._tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self._tmp.name) / "api.db")
        repo = Repository(self.path)
        # Kuveyt Türk konutta oran ilan ediyor; Ziraat Katılım'ın konut
        # kampanyası VAR ama metninde oran yok — ölçülen demo.db kalıbı.
        repo.insert_campaign(build_campaign(
            "Konut finansmanında kâr payı oranı %1,89, 120 ay vade.",
            bank_slug="kuveyt-turk", campaign_type="Konut Finansmanı"))
        repo.insert_campaign(build_campaign(
            "Konut finansmanında dosya masrafı yok, başvuru şubelerimizden.",
            bank_slug="ziraat-katilim", campaign_type="Konut Finansmanı"))
        repo.close()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _compare(self) -> list[dict]:
        from fastapi.testclient import TestClient

        from src.api import main as api_main
        onceki = api_main.DB_PATH
        api_main.DB_PATH = self.path
        try:
            app = api_main.build_app()
        finally:
            api_main.DB_PATH = onceki
        r = TestClient(app).get("/compare", params={
            "field": ALAN, "type": "Konut Finansmanı"})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_alani_olmayan_banka_YANITTA_durur(self) -> None:
        rows = self._compare()
        self.assertEqual(sorted(r["bank"] for r in rows),
                         ["kuveyt-turk", "ziraat-katilim"])

    def test_kapsam_satirinin_SEMASI_digerleriyle_ayni(self) -> None:
        """Arayüz tek bir satır biçimi bilir; kapsam satırı ondan sapmaz."""
        rows = self._compare()
        dolu = next(r for r in rows if r["bank"] == "kuveyt-turk")
        bos = next(r for r in rows if r["bank"] == "ziraat-katilim")
        self.assertEqual(set(dolu), set(bos))

    def test_kapsam_satiri_deger_UYDURMAZ(self) -> None:
        bos = next(r for r in self._compare() if r["bank"] == "ziraat-katilim")
        self.assertIsNone(bos["value"])
        self.assertIsNone(bos["sort_key"])
        self.assertIsNone(bos["rank"])
        self.assertIsNone(bos["campaign_id"])
        self.assertFalse(bos["comparable"])
        self.assertEqual(bos["note"], NOT_ALAN_YOK)
        self.assertEqual(bos["campaign_type"], "Konut Finansmanı")


class TestKapsamGercekKorpus(unittest.TestCase):
    """Ölçülen kusurun kendisi: demo korpusunda Ziraat Katılım geri geldi mi."""

    DB = _ROOT / "data" / "demo.db"

    def setUp(self) -> None:
        if not self.DB.exists():  # pragma: no cover - ortama bağlı
            self.skipTest("data/demo.db yok")
        from src.db.repository import Repository
        self.repo = Repository(str(self.DB))

    def tearDown(self) -> None:
        self.repo.close()

    def _kapsam(self, tur: str) -> list[dict]:
        gorulen: dict[tuple, dict] = {}
        for c in self.repo.all_campaigns(govde=False):
            if c.get("belge_turu") == "sozlesme" or c.get("campaign_type") != tur:
                continue
            gorulen.setdefault((c["bank"], tur), {
                "bank": c["bank"], "bank_name": c["bank_name"],
                "campaign_type": tur})
        return list(gorulen.values())

    def test_ziraat_katilim_konut_kiyasinda_GORUNUR(self) -> None:
        tur = "Konut Finansmanı"
        rows = [r for r in self.repo.query_fields(ALAN)
                if r.get("campaign_type") == tur]
        kapsam = self._kapsam(tur)

        eski = {x.bank for x in rank(rows, ALAN)}
        self.assertNotIn("ziraat-katilim", eski,
                         "ölçülen kusur değişmiş olabilir — testi yeniden ölç")

        yeni = tekil_banka_urun(rank(rows, ALAN, kapsam=kapsam))
        self.assertIn("ziraat-katilim", {x.bank for x in yeni})
        z = next(x for x in yeni if x.bank == "ziraat-katilim")
        self.assertIsNone(z.value)
        self.assertEqual(eleme_sebebi(z.note), ELEME_ALAN_YOK)
        # Kapsamdaki HER banka görünür — biri bile düşmez.
        self.assertEqual({k["bank"] for k in kapsam}, {x.bank for x in yeni})


# =========================================================================== #
# MADDE 2 — oran bazı kapısı
# =========================================================================== #


class TestOranBaziDogrulama(unittest.TestCase):
    def test_gecerli_degerler(self) -> None:
        self.assertEqual(oran_bazi_dogrula("aylik"), "aylik")
        self.assertEqual(oran_bazi_dogrula("yillik"), "yillik")

    def test_taninmayan_deger_NONE_olur(self) -> None:
        for deger in (None, "", "aylık", "monthly", "YILLIK", 12, True):
            with self.subTest(deger=deger):
                self.assertIsNone(oran_bazi_dogrula(deger))

    def test_kanonik_baz_yalniz_oran_alaninda_tanimli(self) -> None:
        self.assertEqual(KANONIK_ORAN_BAZI["kar_payi_orani"], "aylik")
        self.assertNotIn("vade_ay", KANONIK_ORAN_BAZI)
        self.assertNotIn("finansman_tutari", KANONIK_ORAN_BAZI)


class TestBazKapisi(unittest.TestCase):
    def test_yillik_oran_KIYAS_DISI(self) -> None:
        ranked = rank([satir("a-bank", 24.0, oran_bazi="yillik")], ALAN)
        x = ranked[0]
        self.assertFalse(x.comparable)
        self.assertEqual(eleme_sebebi(x.note), ELEME_ORAN_BAZI)
        self.assertIn("yıllık", x.note)
        self.assertIn("doğrudan kıyaslanamaz", x.note)

    def test_yillik_oranin_DEGERI_CEVRILMEZ_ve_gorunur_kalir(self) -> None:
        """24,0 → 2,0 diye bir sayı ÜRETİLMEZ; değer olduğu gibi görünür."""
        x = rank([satir("a-bank", 24.0, oran_bazi="yillik")], ALAN)[0]
        self.assertEqual(x.value, 24.0)
        self.assertEqual(x.oran_bazi, "yillik")

    def test_aylik_oran_kiyaslanabilir_kalir(self) -> None:
        x = rank([satir("a-bank", 1.89, oran_bazi="aylik")], ALAN)[0]
        self.assertTrue(x.comparable)
        self.assertIsNone(x.note)
        self.assertEqual(x.oran_bazi, "aylik")

    def test_baz_BILINMIYORSA_kapi_atesleneMEZ(self) -> None:
        """Ölçülmemiş bazı "aylık" saymak da, elemek de bir iddia olurdu."""
        for deger in (None, "bilinmiyor"):
            with self.subTest(deger=deger):
                x = rank([satir("a-bank", 1.89, oran_bazi=deger)], ALAN)[0]
                self.assertTrue(x.comparable)
                self.assertIsNone(x.oran_bazi)

    def test_kanonik_bazi_olmayan_ALANDA_kapi_calismaz(self) -> None:
        """`vade_ay`da "yıllık" etiketi bir kıyas engeli değildir."""
        x = rank([satir("a-bank", 120, oran_bazi="yillik")], "vade_ay")[0]
        self.assertTrue(x.comparable)

    def test_yillik_satir_aylik_satirin_ONUNE_GECMEZ(self) -> None:
        rows = [satir("yillik-bank", 24.0, oran_bazi="yillik"),
                satir("aylik-bank", 1.89, oran_bazi="aylik")]
        ranked = rank(rows, ALAN)
        self.assertEqual(ranked[0].bank, "aylik-bank")
        self.assertEqual(best(rows, ALAN).bank, "aylik-bank")

    def test_suresi_dolmusluk_baz_notunun_ONUNDE(self) -> None:
        """En temel eleme sebebi gösterilir: ürün artık verilmiyor."""
        x = rank([satir("a-bank", 24.0, oran_bazi="yillik",
                        campaign_status="expired")], ALAN)[0]
        self.assertEqual(eleme_sebebi(x.note), ELEME_SURESI_DOLMUS)
        self.assertEqual(x.oran_bazi, "yillik", "rozet verisi yine de taşınır")

    def test_kapi_alani_cagiranlara_DUYURULUR(self) -> None:
        """Alan taşınmazsa kapı sessizce kapanır — parite kapısı bunu tutar."""
        self.assertIn("oran_bazi", RANK_KAPI_ALANLARI)


class TestDeltaBaz(unittest.TestCase):
    def test_farkli_BILINEN_bazlar_kiyaslanamaz(self) -> None:
        self.assertEqual(
            delta_between(ALAN, 1.89, 24.0, "aylik", "yillik"),
            ("kiyaslanamaz", None, None))
        self.assertEqual(
            delta_between(ALAN, 24.0, 1.89, "yillik", "aylik"),
            ("kiyaslanamaz", None, None))

    def test_ayni_baz_normal_hesaplanir(self) -> None:
        kind, mutlak, _ = delta_between(ALAN, 1.89, 2.49, "aylik", "aylik")
        self.assertEqual(kind, "daha_iyi")
        self.assertAlmostEqual(mutlak, 0.60)

    def test_baz_verilmezse_ESKI_davranis(self) -> None:
        self.assertEqual(delta_between(ALAN, 1.89, 2.49),
                         delta_between(ALAN, 1.89, 2.49, None, None))
        self.assertEqual(delta_between(ALAN, 1.89, 2.49)[0], "daha_iyi")

    def test_tek_taraf_biliniyorsa_digeri_VARSAYILMAZ(self) -> None:
        """Bilinmeyen bazı "farklı" saymak da bir iddia olurdu."""
        self.assertEqual(delta_between(ALAN, 1.89, 2.49, "aylik", None)[0],
                         "daha_iyi")
        self.assertEqual(delta_between(ALAN, 1.89, 2.49, None, "yillik")[0],
                         "daha_iyi")

    def test_kapi_ALAN_BAGIMSIZDIR_rank_kapisindan_genis(self) -> None:
        """İki taraf farklı birim ilan ettiyse alan ne olursa olsun reddedilir.

        `rank()`in kapısı alan başına kanonik bir baz okur (`KANONIK_ORAN_BAZI`)
        ve bu sözlükte olmayan alanda hiç çalışmaz. `delta_between()` daha
        geniştir ve bilerek öyledir: burada ölçülen tek şey ÇAĞIRANIN iki taraf
        için farklı birim bildirmiş olmasıdır. Bu bildirime rağmen fark üretmek
        hiçbir alanda doğru olmaz; reddetmek ise hiçbir alanda yanlış olmaz.
        """
        kind, mutlak, goreli = delta_between("vade_ay", 120.0, 36.0,
                                             "aylik", "yillik")
        self.assertEqual((kind, mutlak, goreli), ("kiyaslanamaz", None, None))


class TestBilesikSkordaBaz(unittest.TestCase):
    """`rank_advantageous()` tek alanlı `rank()` ile AYNI kararı verir."""

    def _rows(self, baz):
        return [
            {"bank": "a", "campaign_id": 1,
             "fields": {ALAN: 2.0, "vade_ay": 120},
             "field_oran_bazi": {ALAN: baz}},
            {"bank": "b", "campaign_id": 2,
             "fields": {ALAN: 3.0, "vade_ay": 60}},
            {"bank": "c", "campaign_id": 3,
             "fields": {ALAN: 4.0, "vade_ay": 36}},
        ]

    def _bilesen(self, skorlar, bank, alan):
        c = next(s for s in skorlar if s.bank == bank)
        return next(x for x in c.components if x.field_name == alan)

    def test_yillik_alan_SKORLANMAZ_ve_gerekce_tasinir(self) -> None:
        skorlar = rank_advantageous(self._rows("yillik"))
        oran = self._bilesen(skorlar, "a", ALAN)
        self.assertIsNone(oran.normalized)
        self.assertEqual(oran.contribution, 0.0)
        self.assertIn("farklı oran bazı", oran.note)

    def test_yillik_alan_kampanyanin_DIGER_alanlarini_dusurmez(self) -> None:
        """Baz tek bir oranın özelliğidir, kampanyanın değil."""
        vade = self._bilesen(rank_advantageous(self._rows("yillik")), "a",
                             "vade_ay")
        self.assertIsNotNone(vade.normalized)

    def test_aylik_ve_bos_baz_skoru_DEGISTIRMEZ(self) -> None:
        temel = rank_advantageous(self._rows(None))
        for baz in ("aylik", None, "bilinmiyor"):
            with self.subTest(baz=baz):
                self.assertEqual(
                    [(s.bank, s.score) for s in rank_advantageous(self._rows(baz))],
                    [(s.bank, s.score) for s in temel])

    def test_field_oran_bazi_hic_verilmezse_calisir(self) -> None:
        rows = [{"bank": "a", "campaign_id": 1, "fields": {ALAN: 2.0}},
                {"bank": "b", "campaign_id": 2, "fields": {ALAN: 3.0}},
                {"bank": "c", "campaign_id": 3, "fields": {ALAN: 4.0}}]
        self.assertEqual([s.bank for s in rank_advantageous(rows)],
                         ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main()
