"""«Özet yok» iki ayrı şeydir ve depo ikisini AYIRT ETMEK ZORUNDA.

İlgili: ../src/db/repository.py (`set_ozet`, `set_ozet_sebep`)
        ../src/summarize/toplu.py (`sayim`, `calistir`)
        ../src/summarize/ozet.py (`kalici_sebep`)
        ../web/app/components/SummaryCoverage.tsx (ekrandaki cümle)

## Bu testin varlık sebebi

Ekrandaki kapsam cümlesi şuydu:

    Kalan 23 belgede ÖZETLENECEK İÇERİK YOK: sayfanın tamamı çerçeve metni.

Bu cümle yazıldığı gün doğruydu — 1751 belge özetlenmiş, kalan 23'ü denenmiş ve
içerikleri çıkmamıştı. Ama `campaigns.ozet` sütunu tek başına yalnız "özet var
mı" sorusunu cevaplayabiliyor; "neden yok" sorusunu cevaplayamıyor. Yani
tazeleme yeni bir belge indirdiği ve o belge DB'ye girdiği anda aynı cümle
**yeni belge için de** kurulacaktı: henüz denenmemiş bir belgeye "içeriği yok"
demek, ölçülmemiş bir iddiayı ölçülmüş gibi sunmaktır.

`ozet_sebep` sütunu bu ayrımı taşır. Testler üç şeyi kapıda tutar:

1. Sebep yazılıp geri okunuyor ve kovalar KESİŞMİYOR.
2. Dolu bir özet yazmak sebebi TEMİZLİYOR — "özet var" ile "şu sebeple yok"
   aynı satırda birlikte duramaz.
3. `kalici_atla` yalnız belgenin KENDİSİNE ait sebebi eler; koşuya ait
   sebepli belgeler tekrar denenir.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.repository import Repository
from src.schemas import Campaign
from src.summarize.ozet import (
    SEBEP_METIN_BOS,
    SEBEP_YABANCI_ALFABE,
    kalici_sebep,
)
from src.summarize.toplu import hedef_kampanyalar, sayim


def _depo() -> Repository:
    repo = Repository(":memory:")
    repo.upsert_bank("Örnek Katılım", "ornek")
    return repo


def _kampanya(repo: Repository, metin: str) -> int:
    return repo.insert_campaign(
        Campaign(bank_slug="ornek", raw_text=metin,
                 source_url=f"https://ornek.test/{metin[:8]}"))


class TestSebepYazimi(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = _depo()
        self.a = _kampanya(self.repo, "A belgesi metni")
        self.b = _kampanya(self.repo, "B belgesi metni")
        self.c = _kampanya(self.repo, "C belgesi metni")

    def tearDown(self) -> None:
        self.repo.close()

    def _kayit(self, cid: int) -> dict:
        return next(c for c in self.repo.all_campaigns() if c["id"] == cid)

    def test_sebep_yazilip_geri_okunuyor(self) -> None:
        self.repo.set_ozet_sebep({self.a: SEBEP_METIN_BOS})
        self.assertEqual(self._kayit(self.a)["ozet_sebep"], SEBEP_METIN_BOS)

    def test_dolu_ozet_sebebi_TEMIZLER(self) -> None:
        """Kusurun kendisi: özet gelince eski sebep kalsaydı çelişki kalıcı olurdu.

        Aynı belge iki kovada birden sayılırdı: hem "özetli" hem "içerik yok".
        """
        self.repo.set_ozet_sebep({self.a: SEBEP_METIN_BOS})
        self.repo.set_ozet({self.a: "Bu belge konut finansmanını anlatıyor."})
        kayit = self._kayit(self.a)
        self.assertTrue(kayit["ozet"])
        self.assertIsNone(kayit["ozet_sebep"],
                          "dolu özet yazıldığında sebep TEMİZLENMELİ")

    def test_ozeti_silmek_sebebi_ELLEMEZ(self) -> None:
        """Ters yön: özeti `None`'a çeken tarafın gerekçesi kendisine aittir."""
        self.repo.set_ozet({self.a: "geçici özet"})
        self.repo.set_ozet_sebep({self.a: SEBEP_YABANCI_ALFABE})
        self.repo.set_ozet({self.a: None})
        self.assertEqual(self._kayit(self.a)["ozet_sebep"], SEBEP_YABANCI_ALFABE)

    def test_kovalar_KESISMEZ_ve_toplami_korpusa_esit(self) -> None:
        self.repo.set_ozet({self.a: "özet"})
        self.repo.set_ozet_sebep({self.b: SEBEP_METIN_BOS})
        # c: hiç denenmedi
        s = sayim(self.repo)
        self.assertEqual(s["ozetli"], 1)
        self.assertEqual(s["icerik_yok"], 1)
        self.assertEqual(s["basarisiz"], 0)
        self.assertEqual(s["denenmemis"], 1)
        self.assertEqual(
            s["ozetli"] + s["icerik_yok"] + s["basarisiz"] + s["denenmemis"],
            s["toplam"], "kovalar kesişmemeli ve toplamı korpusa eşit olmalı")

    def test_hedef_denenmemis_arti_tekrar_denenebilir(self) -> None:
        """Düğmenin yazdığı sayı, gerçekten işlenecek belge sayısı olmalı."""
        self.repo.set_ozet({self.a: "özet"})
        self.repo.set_ozet_sebep({self.b: SEBEP_METIN_BOS})
        self.repo.set_ozet_sebep({self.c: SEBEP_YABANCI_ALFABE})
        s = sayim(self.repo)
        # b kalıcı (hedefte yok), c tekrar denenebilir + hiç kimse denenmemiş
        self.assertEqual(s["hedef"], 1)
        hedefler, _ = hedef_kampanyalar(self.repo, kapsam="hepsi", devam=True,
                                        limit=None, kalici_atla=True)
        self.assertEqual([h["id"] for h in hedefler], [self.c],
                         "kalıcı sebepli belge hedeften düşmeli, koşuya ait "
                         "sebepli belge DÜŞMEMELİ")

    def test_kalici_atla_kapaliyken_hepsi_hedefte(self) -> None:
        """CLI'ın bugünkü davranışı korunur (geri uyum)."""
        self.repo.set_ozet_sebep({self.b: SEBEP_METIN_BOS})
        hedefler, _ = hedef_kampanyalar(self.repo, kapsam="hepsi", devam=True,
                                        limit=None, kalici_atla=False)
        self.assertEqual(len(hedefler), 3)


class TestSebepSiniflandirmasi(unittest.TestCase):
    """Hangi sebep "belgenin kendisine ait" sayılıyor."""

    def test_metin_bos_KALICI(self) -> None:
        # Karar LLM'e hiç gitmeden verilir: katlanmış metin boş çıktı.
        self.assertTrue(kalici_sebep(SEBEP_METIN_BOS))

    def test_alfabe_kaymasi_kalici_DEGIL(self) -> None:
        # Model üretimin ortasında dil değiştirdi; aynı belge sonraki koşuda
        # düzgün özetlenebilir.
        self.assertFalse(kalici_sebep(SEBEP_YABANCI_ALFABE))

    def test_bilinmeyen_sebep_kalici_DEGIL(self) -> None:
        """Varsayılan taraf TEKRAR DENEME yönünde.

        Ters varsayım (bilinmeyeni kalıcı say) yeni bir sebep etiketi
        eklendiğinde o belgeleri sessizce kalıcı kayıp yapardı.
        """
        self.assertFalse(kalici_sebep("llm_hatasi: TimeoutError"))
        self.assertFalse(kalici_sebep(None))


if __name__ == "__main__":
    unittest.main()
