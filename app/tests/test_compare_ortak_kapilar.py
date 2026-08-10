"""`/compare` sunum kurallarını KENDİ gövdesinde yeniden yazmıyor.

İlgili: ../src/api/main.py (`/compare`)
        ../src/comparison/compare.py (`yon_zorla`, `tekil_banka_urun`)
        ../src/chatbot/structured.py (aynı iki kapıyı çağıran ikinci yüzey)
        ./test_chatbot_kiyas_paritesi.py (davranış paritesi)

## Bu testin varlık sebebi

İki sunum kuralı — "istenen sıralama yönü" ve "banka × ürün ailesi başına tek
satır" — bir süre İKİ yerde yaşadı: `/compare` ucunun gövdesinde ve chatbot'un
yapısal yolunda. Ayrışınca tarayıcıda görüldü: aynı banka ve aynı değer 232
satır boyunca tekrarlandı. Bu, depoda "aynı karar iki yerde" hatasının
beşinci tekrarıydı.

Kural artık `comparison/compare.py` içinde tek yerde. Yanındaki parite testi
davranışın ayrışmadığını kilitler — ama tek başına YETMEZ: uca geri konan bir
kopya, ilk gün aynı sonucu üretir ve parite testi hiçbir şey söylemez.
Ayrışma ancak ikisinden biri güncellenince, yani en geç fark edildiği anda
görünür.

Bu dosya o boşluğu kapatır: uç noktanın ortak kapıları GERÇEKTEN çağırdığı
davranışsal olarak kanıtlanır (fonksiyon yerine sayaç konur ve çağrıldığı
görülür). Kopya geri konursa sayaç sıfır kalır ve test düşer.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_KOK = Path(__file__).resolve().parents[1]
if str(_KOK) not in sys.path:
    sys.path.insert(0, str(_KOK))

from src.api import main as api_main
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign


def _fastapi_var() -> bool:
    try:
        from fastapi.testclient import TestClient  # noqa: F401
    except Exception:
        return False
    return True


@unittest.skipUnless(_fastapi_var(), "fastapi kurulu değil")
class TestUcNoktaOrtakKapilariCagiriyor(unittest.TestCase):
    ALAN = "kar_payi_orani"

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self._tmp.name) / "api.db")
        repo = Repository(self.path)
        # Aynı bankanın aynı ailede iki kampanyası: tekilleştirme olmadan
        # tabloda iki satır kalır, olduğunda bir satır + other_count=1.
        for slug, oran, tur in (
            ("kuveyt-turk", "1,89", "Konut Finansmanı"),
            ("kuveyt-turk", "2,49", "Konut Finansmanı"),
            ("albaraka", "2,95", "Konut Finansmanı"),
        ):
            repo.insert_campaign(build_campaign(
                f"Finansmanda kâr payı oranı %{oran}, 36 ay vade.",
                bank_slug=slug, campaign_type=tur))
        repo.close()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _client(self):
        from fastapi.testclient import TestClient

        onceki = api_main.DB_PATH
        api_main.DB_PATH = self.path
        try:
            return TestClient(api_main.build_app())
        finally:
            api_main.DB_PATH = onceki

    def test_tekil_banka_urun_gercekten_cagriliyor(self) -> None:
        client = self._client()
        cagri = {"n": 0}
        gercek = api_main.tekil_banka_urun

        def sayan(ranked):
            cagri["n"] += 1
            return gercek(ranked)

        api_main.tekil_banka_urun = sayan
        try:
            r = client.get("/compare", params={"field": self.ALAN,
                                               "per_bank": "best"})
        finally:
            api_main.tekil_banka_urun = gercek
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(
            cagri["n"], 1,
            "/compare tekilleştirmeyi ortak kapıdan geçirmiyor — kural uca "
            "geri kopyalanmış olabilir")

    def test_yon_zorla_gercekten_cagriliyor(self) -> None:
        client = self._client()
        cagri = {"n": 0}
        gercek = api_main.yon_zorla

        def sayan(ranked, field_name, intent):
            cagri["n"] += 1
            return gercek(ranked, field_name, intent)

        api_main.yon_zorla = sayan
        try:
            r = client.get("/compare", params={"field": self.ALAN,
                                               "intent": "highest"})
        finally:
            api_main.yon_zorla = gercek
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(
            cagri["n"], 1,
            "/compare sıralama yönünü ortak kapıdan geçirmiyor")

    def test_other_count_ortak_kapidan_geliyor(self) -> None:
        """Sayı uçta yeniden hesaplanmıyor: kapı ne derse o basılıyor."""
        client = self._client()
        gercek = api_main.tekil_banka_urun

        def isaretli(ranked):
            from dataclasses import replace
            return [replace(x, other_count=99) for x in gercek(ranked)]

        api_main.tekil_banka_urun = isaretli
        try:
            satirlar = client.get(
                "/compare", params={"field": self.ALAN,
                                    "per_bank": "best"}).json()
        finally:
            api_main.tekil_banka_urun = gercek
        self.assertTrue(satirlar)
        self.assertTrue(all(s["other_count"] == 99 for s in satirlar),
                        [s["other_count"] for s in satirlar])

    def test_per_bank_all_yolunda_tekillestirme_KOSMAZ(self) -> None:
        """`all` eski davranıştır: hiçbir satır elenmez, other_count 0'dır."""
        client = self._client()
        satirlar = client.get("/compare",
                              params={"field": self.ALAN,
                                      "per_bank": "all"}).json()
        kt = [s for s in satirlar if s["bank"] == "kuveyt-turk"]
        self.assertEqual(len(kt), 2, satirlar)
        self.assertTrue(all(s["other_count"] == 0 for s in satirlar))


if __name__ == "__main__":
    unittest.main()
