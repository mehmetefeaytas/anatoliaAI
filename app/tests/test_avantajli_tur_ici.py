"""§5.7 "En Avantajlı Kampanya" — tür içi sıralama testleri.

## Neden tür içinde

Şartnamenin kendi çalışılmış örneği (s.12–13) **aynı ürünü** karşılaştırıyor:
A, B ve C Bankası'nın **konut finansmanı** kampanyaları, tek tabloda.
Türler arası karşılaştırma istenmiyor.

Ölçülmüş gerekçe (849 belge, 495 skorlanabilir kampanya):

    Kart               114 kampanya —  3'ünde kâr payı
    İhtiyaç Finansmanı 104 kampanya —  5'inde
    Alışveriş Puanı     13 kampanya —  0'ında
    Konut Finansmanı    72 kampanya — 11'inde

Kampanyaların yalnızca **%9,5'inde** kâr payı var. Türler arası tek listede
kâr payına hangi ağırlık verilirse verilsin %90 için yeniden dağıtılır.
Dahası bir kredi kartı kampanyasıyla bir konut finansmanı birbirinin
alternatifi değildir — "hangisi daha avantajlı" iyi tanımlı bir soru değil.

`CLAUDE.md` §17 ("yalnızca aynı birime normalize alanlar kıyaslanır")
kuralının ürün ailesi düzeyine uygulanmış hâli.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.comparison.compare import (  # noqa: E402
    BILINMEYEN_TUR,
    MIN_GROUP_SIZE,
    best_advantageous_by_type,
    rank_advantageous_by_type,
)


def _satir(banka: str, tur: str | None, cid: int, **alanlar) -> dict:
    return {"bank": banka, "bank_name": banka, "campaign_id": cid,
            "campaign_type": tur, "fields": alanlar}


def _konut(n: int = 4) -> list[dict]:
    """Aynı türde, oranları farklı kampanyalar."""
    return [_satir(f"banka{i}", "Konut Finansmanı", i,
                   kar_payi_orani=1.80 + i * 0.10,
                   vade_ay=120 - i * 12,
                   masraf_durumu={"has_fee": False, "amount": 0.0})
            for i in range(n)]


def _kart(n: int = 4) -> list[dict]:
    """Kâr payı OLMAYAN tür — gerçek korpustaki kart kampanyaları gibi."""
    return [_satir(f"banka{i}", "Kart", 100 + i,
                   odul_miktari={"value": 1000 + i * 500, "currency": "TRY"},
                   masraf_durumu={"has_fee": False, "amount": 0.0})
            for i in range(n)]


class TestGruplama(unittest.TestCase):

    def test_turler_ayri_gruplanir(self) -> None:
        sonuc = rank_advantageous_by_type(_konut() + _kart())
        self.assertIn("Konut Finansmanı", sonuc)
        self.assertIn("Kart", sonuc)
        self.assertEqual(sonuc["Konut Finansmanı"]["count"], 4)
        self.assertEqual(sonuc["Kart"]["count"], 4)

    def test_bir_grubun_uyeleri_baska_gruba_sizmaz(self) -> None:
        sonuc = rank_advantageous_by_type(_konut() + _kart())
        konut_id = {c.campaign_id for c in sonuc["Konut Finansmanı"]["ranked"]}
        kart_id = {c.campaign_id for c in sonuc["Kart"]["ranked"]}
        self.assertEqual(konut_id & kart_id, set(), "gruplar arası sızıntı")

    def test_turu_olmayan_kampanya_ayri_gruba_dusser(self) -> None:
        sonuc = rank_advantageous_by_type(_konut() + [
            _satir("x", None, 900, kar_payi_orani=2.0),
            _satir("y", None, 901, kar_payi_orani=2.5),
            _satir("z", None, 902, kar_payi_orani=3.0),
        ])
        self.assertIn(BILINMEYEN_TUR, sonuc)
        self.assertEqual(sonuc[BILINMEYEN_TUR]["count"], 3)

    def test_bos_girdi(self) -> None:
        self.assertEqual(rank_advantageous_by_type([]), {})


class TestNormalizasyonGrupIcinde(unittest.TestCase):
    """En kritik değişmez: bir tür başka türün dağılımından etkilenmemeli."""

    def test_baska_tur_eklemek_siralamayi_degistirmez(self) -> None:
        yalniz = rank_advantageous_by_type(_konut())
        karisik = rank_advantageous_by_type(_konut() + _kart(10))

        a = [(c.campaign_id, c.score)
             for c in yalniz["Konut Finansmanı"]["ranked"]]
        b = [(c.campaign_id, c.score)
             for c in karisik["Konut Finansmanı"]["ranked"]]
        self.assertEqual(a, b,
                         "kart kampanyaları eklenince konut skorları değişti — "
                         "normalizasyon grup içinde koşmuyor")

    def test_en_iyi_kendi_grubunda_belirlenir(self) -> None:
        """Konut'ta en düşük oran kazanmalı (kâr payında düşük iyidir)."""
        sonuc = rank_advantageous_by_type(_konut() + _kart())
        kazanan = next(c for c in sonuc["Konut Finansmanı"]["ranked"]
                       if c.comparable)
        self.assertEqual(kazanan.campaign_id, 0, "en düşük oranlı kazanmadı")


class TestKucukGrup(unittest.TestCase):
    """Az örnekli türde 'en avantajlı' iddiası bilgi taşımaz — ama gizlenmez."""

    def test_esik_altinda_siralama_yapilmaz(self) -> None:
        sonuc = rank_advantageous_by_type(_konut(MIN_GROUP_SIZE - 1))
        grup = sonuc["Konut Finansmanı"]
        self.assertEqual(grup["ranked"], [])
        self.assertIsNotNone(grup["note"], "sebep bildirilmedi")

    def test_kucuk_grup_gizlenmez(self) -> None:
        """Sayı raporlanmalı — sessizce düşürmek veriyi saklamaktır."""
        sonuc = rank_advantageous_by_type(_konut(2))
        self.assertEqual(sonuc["Konut Finansmanı"]["count"], 2)

    def test_esikte_siralama_yapilir(self) -> None:
        sonuc = rank_advantageous_by_type(_konut(MIN_GROUP_SIZE))
        self.assertTrue(sonuc["Konut Finansmanı"]["ranked"])


class TestTurBasinaEnIyi(unittest.TestCase):

    def test_her_tur_icin_bir_kazanan(self) -> None:
        en_iyi = best_advantageous_by_type(_konut() + _kart())
        self.assertEqual(set(en_iyi), {"Konut Finansmanı", "Kart"})
        for tur, c in en_iyi.items():
            with self.subTest(tur=tur):
                self.assertIsNotNone(c, f"{tur} için kazanan yok")
                self.assertTrue(c.comparable)

    def test_kucuk_grupta_kazanan_none(self) -> None:
        en_iyi = best_advantageous_by_type(_konut(2))
        self.assertIsNone(en_iyi["Konut Finansmanı"])


class TestGercekKorpusSekli(unittest.TestCase):
    """Korpusun gerçek şeklini taklit eder: türler farklı alanlara sahip."""

    def test_kar_payi_olmayan_tur_yine_de_siralanir(self) -> None:
        """Kart kampanyalarının %97'sinde kâr payı yok; ödülle sıralanmalı."""
        sonuc = rank_advantageous_by_type(_kart())
        kiyas = [c for c in sonuc["Kart"]["ranked"] if c.comparable]
        self.assertTrue(kiyas, "kâr payı olmayan tür hiç sıralanamadı")
        # Ödülde yüksek iyidir → en yüksek ödüllü kazanmalı
        self.assertEqual(kiyas[0].campaign_id, 103)

    def test_alan_eksikligi_sifir_puan_degildir(self) -> None:
        """Adil kıyas: eksik alan cezalandırılmaz, kapsama ayrı raporlanır."""
        satirlar = _konut(3) + [
            _satir("eksikli", "Konut Finansmanı", 50, kar_payi_orani=1.50)]
        sonuc = rank_advantageous_by_type(satirlar)
        eksikli = next(c for c in sonuc["Konut Finansmanı"]["ranked"]
                       if c.campaign_id == 50)
        self.assertLess(eksikli.coverage, 1.0, "kapsama tam görünüyor")
        if eksikli.score is not None:
            self.assertGreater(eksikli.score, 0.0,
                               "eksik alan sıfır puan gibi işlendi")


if __name__ == "__main__":
    unittest.main()
