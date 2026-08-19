"""Katalog router'ı — bağımsız kurulabilirlik ve taşıma regresyonları.

İlgili: ../src/api/routers/katalog.py · ../docs/rapor/api-bolme-plani.md

## Neden bu dosya var

`api/main.py` kademeli olarak bölünüyor ve katalog uçları ilk taşınan grup.
Bu testler taşımanın ASIL KAZANCINI kilitler: uçlar artık `build_app()`
kurmadan, gerçek depo/config olmadan sınanabiliyor. Önceden `/banks` otorite
süzmesini test etmek `config/banks.yaml` okumayı gerektiriyordu; şimdi sahte
bir `otorite_sluglari` yeterli.

İkinci amaç bir regresyon kapısı: taşıma sırasında `Response` fonksiyon içine
import edilmişti ve `GET /campaigns` her istekte **422** döndürdü. Sebep
`from __future__ import annotations` — tip anotasyonları dizeye dönüşüyor ve
FastAPI onları modül global'lerinden çözüyor; import fonksiyon içinde kalınca
`response: Response` çözülemiyor ve FastAPI onu bir QUERY parametresi sanıyor.
Aynı tuzak `api/main.py`'de bir kez yaşanmış ve orada yorumla işaretlenmiş;
taşıma onu birebir tekrarladı. Kapı 3 burada duruyor ki üçüncü kez olmasın.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover
    TestClient = None

from src.api.routers import katalog


class _SahteDepo:
    """`repo` sözleşmesinin yalnız katalog uçlarının kullandığı yüzü."""

    backend = "sahte"

    def __init__(self, banks=None, campaigns=None):
        self._banks = banks or []
        self._campaigns = campaigns or []
        self.son_cagri: dict = {}

    def all_banks(self):
        return list(self._banks)

    def all_campaigns(self, **kw):
        self.son_cagri = kw
        return list(self._campaigns)


class _SahteLlm:
    available = False


def _istemci(repo=None, *, otorite=frozenset()):
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(katalog.router_kur(
        repo or _SahteDepo(), _SahteLlm(),
        otorite_sluglari=lambda: otorite,
        scoring_direction=lambda f: ("lower_is_better", "Küçük daha iyi"),
    ))
    return TestClient(app)


@unittest.skipIf(TestClient is None, "fastapi kurulu değil")
class TestBagimsizKurulabilirlik(unittest.TestCase):
    """KAPI 1 — router `build_app()` olmadan, sahte bağımlılıklarla kurulur."""

    def test_router_alti_uc_tasiyor(self) -> None:
        r = katalog.router_kur(
            _SahteDepo(), _SahteLlm(),
            otorite_sluglari=lambda: frozenset(),
            scoring_direction=lambda f: ("unranked", "-"))
        yollar = {q.path for q in r.routes}
        self.assertEqual(yollar, {"/health", "/banks", "/campaigns",
                                  "/search", "/stats", "/fields"})

    def test_health_depo_arka_ucunu_bildirir(self) -> None:
        """`backend` alanı bilinçli açığa çıkarılıyor; sahte depo da görünmeli."""
        c = _istemci()
        y = c.get("/health").json()
        self.assertEqual(y["backend"], "sahte")
        self.assertFalse(y["llm"])


@unittest.skipIf(TestClient is None, "fastapi kurulu değil")
class TestOtoriteSuzmesi(unittest.TestCase):
    """KAPI 2 — otorite kaynağı süzmesi, config dosyasına DOKUNMADAN sınanır."""

    BANKALAR = [{"slug": "kuveyt-turk", "name": "Kuveyt Türk"},
                {"slug": "tkbb", "name": "TKBB"}]

    def test_otorite_kaynagi_varsayilan_olarak_suzulur(self) -> None:
        c = _istemci(_SahteDepo(banks=self.BANKALAR), otorite=frozenset({"tkbb"}))
        sluglar = [b["slug"] for b in c.get("/banks").json()]
        self.assertEqual(sluglar, ["kuveyt-turk"])

    def test_bayrakla_tam_liste_gelir(self) -> None:
        """Süzme GİZLEME DEĞİLDİR — denetlenebilir kalmalı."""
        c = _istemci(_SahteDepo(banks=self.BANKALAR), otorite=frozenset({"tkbb"}))
        sluglar = [b["slug"] for b in
                   c.get("/banks?otorite_kaynaklari_dahil=true").json()]
        self.assertEqual(sluglar, ["kuveyt-turk", "tkbb"])


@unittest.skipIf(TestClient is None, "fastapi kurulu değil")
class TestTasimaRegresyonlari(unittest.TestCase):
    """KAPI 3 — taşıma sırasında bir kez kırılan davranışlar."""

    def test_campaigns_422_dondurmez(self) -> None:
        """`Response` modül global'inde olmazsa FastAPI onu query sanar."""
        c = _istemci(_SahteDepo(campaigns=[{"id": 1, "bank": "x"}]))
        y = c.get("/campaigns")
        self.assertEqual(y.status_code, 200, y.text[:200])

    def test_toplam_kayit_basligi_sayfalamadan_bagimsiz(self) -> None:
        kayitlar = [{"id": i} for i in range(5)]
        c = _istemci(_SahteDepo(campaigns=kayitlar))
        y = c.get("/campaigns?limit=2")
        self.assertEqual(y.status_code, 200)
        self.assertEqual(y.headers["X-Toplam-Kayit"], "5")
        self.assertEqual(len(y.json()), 2)

    def test_negatif_sayfalama_400(self) -> None:
        c = _istemci(_SahteDepo())
        self.assertEqual(c.get("/campaigns?offset=-1").status_code, 400)

    def test_fields_etiket_ve_yon_dondurur(self) -> None:
        """`/fields` üç kaynağı birleştiriyor: şema, etiket sözlüğü, sıralama."""
        c = _istemci()
        y = c.get("/fields").json()
        self.assertTrue(y)
        ilk = y[0]
        self.assertEqual(set(ilk), {"field", "label", "direction",
                                    "direction_label", "comparable_field"})
        etiketler = {x["field"]: x["label"] for x in y}
        self.assertEqual(etiketler["kar_payi_orani"], "Kâr Payı Oranı")


if __name__ == "__main__":
    unittest.main()
