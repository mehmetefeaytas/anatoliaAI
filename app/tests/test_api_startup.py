"""API açılış davranışı — kalıcı DB'de tohumlama tekrarlanmamalı.

## Neden bu dosya var

`build_app()` açılışta demo verisini dolduruyordu (CLAUDE.md §11, önceden
doldurulmuş DB). Bu çağrı **koşulsuzdu**.

In-memory DB'de zararsız: her açılış sıfırdan başlar. Ama `DATABASE_PATH`
bir DOSYAYI gösterdiğinde her yeniden başlatma 3 kampanya daha ekliyordu:

    849 -> 852 -> 855 -> ...  sonsuza dek

Şemada UNIQUE kısıtı olmadığı için çift kayıtlar sessizce birikir;
karşılaştırma tablosunda aynı banka birden çok kez görünür ve sıralama
bozulur. Hiçbir şey çökmez — yalnızca sayılar yavaşça yanlışlaşır.

Bu, `scripts/build_demo_db.py` ile üretilen 849 belgelik kalıcı DB'ye
geçişin **ön koşuluydu**.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.repository import Repository

# Çekirdek paket SIFIR üçüncü parti bağımlılıkla koşar — bu, on-prem
# iddiasının bir parçası ve CI'daki `test` işi bilinçli olarak hiçbir şey
# kurmuyor. FastAPI yoksa bu dosya ATLANIR, başarısız OLMAZ; aksi halde
# bağımlılıksız koşuyu kırar ve mimari kısıtı görünmez biçimde bozardık.
try:  # pragma: no cover - ortama bağlı
    import fastapi  # noqa: F401
    FASTAPI_VAR = True
except ModuleNotFoundError:  # pragma: no cover
    FASTAPI_VAR = False


def _build_app_with_db(db_path: str):
    """`build_app()`'i verilen DB yoluyla, modül önbelleğini temizleyerek kurar.

    `DB_PATH` modül seviyesinde okunuyor, bu yüzden ortam değişkenini
    değiştirmek tek başına yetmez — modülün yeniden içe aktarılması gerek.
    """
    onceki = os.environ.get("DATABASE_PATH")
    os.environ["DATABASE_PATH"] = db_path
    try:
        for ad in [k for k in list(sys.modules) if k.startswith("src.")]:
            del sys.modules[ad]
        from src.api.main import build_app
        return build_app()
    finally:
        if onceki is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = onceki


@unittest.skipUnless(FASTAPI_VAR, "fastapi kurulu değil — API testi atlanıyor")
class TestKaliciDbTohumlama(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmp.name) / "demo.db")

    def tearDown(self) -> None:
        # Modül önbelleğini temiz bırak — sonraki testler etkilenmesin.
        for ad in [k for k in list(sys.modules) if k.startswith("src.")]:
            del sys.modules[ad]
        self._tmp.cleanup()

    def _kampanya_sayisi(self) -> int:
        repo = Repository(self.db)
        try:
            return repo.counts()["campaigns"]
        finally:
            repo.close()

    def test_yeniden_baslatma_kampanya_ciftlemez(self) -> None:
        """Asıl değişmez: üç açılış, aynı sayı."""
        _build_app_with_db(self.db)
        ilk = self._kampanya_sayisi()
        self.assertGreater(ilk, 0, "ilk açılış hiç veri doldurmadı")

        for tur in (2, 3):
            _build_app_with_db(self.db)
            with self.subTest(acilis=tur):
                self.assertEqual(
                    self._kampanya_sayisi(), ilk,
                    f"{tur}. açılışta kampanya sayısı değişti — tohumlama "
                    f"tekrarlandı ve kayıtlar çiftlendi")

    def test_dolu_db_tohumlanmaz(self) -> None:
        """Hazır doldurulmuş DB'ye fixture verisi EKLENMEMELİ.

        `build_demo_db.py` ile üretilen 849 belgelik korpusun üstüne 3
        sentetik fixture eklemek, gerçek korpusu kirletirdi.
        """
        from src.schemas import Campaign
        repo = Repository(self.db)
        repo.insert_campaign(
            Campaign(bank_slug="onceden-dolu", raw_text="hazır veri",
                     source_url="https://ornek.test/x", fields=[]),
            clean_text="hazır veri")
        onceki = repo.counts()["campaigns"]
        repo.close()

        _build_app_with_db(self.db)
        self.assertEqual(self._kampanya_sayisi(), onceki,
                         "dolu DB'ye fixture verisi eklendi")

    def test_bos_db_tohumlanir(self) -> None:
        """Koşul fazla sıkı olmamalı: boş DB gerçekten doldurulmalı."""
        self.assertEqual(self._kampanya_sayisi(), 0)
        _build_app_with_db(self.db)
        self.assertGreater(self._kampanya_sayisi(), 0,
                           "boş DB doldurulmadı — demo boş açılırdı")


if __name__ == "__main__":
    unittest.main()
