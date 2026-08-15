"""Liste alanlarında güven skoru SEÇİM belirsizliğini de sayar.

İlgili: ../src/extraction/rules/extract.py (`kampanya_kosullari`, `hedef_kitle`)
        ../src/extraction/rules/confidence.py (`AMBIGUITY_PENALTY`)
        ../docs/rapor/oturum-2026-08-15-kanit-tazeligi.md

## Ölçülmüş gerekçe — ve bir varsayımın çürütülmesi

Plan, `extract.py`'deki **11 sabit `trigger_distance=0`**'ı bir kusur sayıp
"gerçek mesafeyle değiştir" diyordu. 2026-08-15'te tek tek okundu ve
varsayım **çürüdü**: çoğunda tetikleyici sözcük eşleşmenin kendi içindedir
(`"12 taksit"`, `"masrafsız"`, `"kâr payı %2,5"`), yani mesafe gerçekten
sıfırdır. Uydurma bir sabit değil, doğru bir olgu.

Gerçek kusur daha dardı ve başka bir yerdeydi: **liste alanlarında seçim
belirsizliği hiç sayılmıyordu.** `kampanya_kosullari` tek bir eşleşme değil,
koşul ipucu taşıyan N cümlenin SEÇİMİDİR; `hedef_kitle` N etiketin. N seçim
kararı, tek bir bitişik eşleşmeyle aynı kesinliği taşıyamaz.

Ölçüldü (gold.round1, n=134):

    kampanya_kosullari kalem düzeyi kesinlik : 0,556
    ilan edilen güven                        : 0,950

Düzeltmenin ölçülen bedeli ve kazancı:

    tam 0,95 skorlu alan payı : %57,2 -> %38,5
    ECE                       : 0,192 -> 0,188
    0,90+ bandı doğruluğu     : 0,571 -> 0,688
    mikro/makro/yapısal F1    : DEĞİŞMEDİ
    eşik altı karar sayısı    : 25 -> 25  (kullanıcıya görünen davranış AYNI)

Son satır kritik: `compare.ASGARI_GUVEN = 0,65` kullanıcıya görünen bir
kapıdır. Skor dağılımını değiştirip o kapının ne attığını da değiştirmek,
teslime 11 gün kala sessiz bir üretim davranışı değişikliği olurdu.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules import confidence as C
from src.extraction.rules.extract import extract_all


def _alan(metin: str, ad: str):
    for f in extract_all(metin):
        if f.field_name == ad:
            return f
    return None


class TestSecimBelirsizligiSayilir(unittest.TestCase):
    def test_GERCEK_korpusta_cok_kalemli_daha_dusuk_guvenli(self) -> None:
        """Sentetik metin çoklu seçim üretmiyor; gerçek belgeler üretiyor.

        Uydurma bir metin kurup "çoklu seçim" beklemek bu projede ölçülmüş
        bir hata sınıfıdır. Ölçüm gerçek korpusta yapılır: gold.round1'de
        27 belge tek kalem, 36 belge sekiz kalem üretiyor.
        """
        import json
        yol = Path(__file__).resolve().parents[1] / "data/gold/gold.round1.json"
        if not yol.exists():
            self.skipTest("gold.round1 yok")
        tek, cok = [], []
        for r in json.loads(yol.read_text(encoding="utf-8")):
            f = _alan(r["text"], "kampanya_kosullari")
            if f is None:
                continue
            (tek if len(f.canonical_value) == 1 else cok).append(f.confidence)
        self.assertTrue(tek and cok, "korpusta iki grup da bulunmalı")
        # Gruplar ÖRTÜŞÜR ve örtüşmeleri doğrudur: skoru belirsizlik dışında
        # başka etkenler de düşürür (makullük, gezinme bağlamı). Bu yüzden
        # "her çok kalemli, her tek kalemliden düşüktür" YANLIŞ bir iddia
        # olurdu. Denetlenen şey dar ve doğrulanabilir: çok kalemli hiçbir
        # seçim, bitişik tek eşleşmenin tavan skorunu taşıyamaz.
        self.assertLess(max(cok), 0.95,
                        "çok kalemli bir SEÇİM 0,95 taşıyor — belirsizlik "
                        "cezası uygulanmamış")
        self.assertLessEqual(sum(cok) / len(cok), sum(tek) / len(tek),
                             "ortalama güven, seçim sayısıyla artmamalı")

    def test_belirsizlik_cezasi_gercekten_uygulaniyor(self) -> None:
        """Ceza sabiti sıfırlanırsa bu testin koruduğu şey sessizce ölür."""
        tek, _ = C.score("kampanya_kosullari", ["a"], trigger_distance=0,
                         candidate_count=1)
        cok, _ = C.score("kampanya_kosullari", ["a", "b", "c"],
                         trigger_distance=0, candidate_count=3)
        self.assertLess(cok, tek)
        self.assertLess(C.AMBIGUITY_PENALTY, 0)


class TestBitisikSabitlerKALIR(unittest.TestCase):
    """NEGATİF TUZAK: doğru olan sabitler "düzeltilirse" kanıt zayıflar.

    Bu vakalarda tetikleyici sözcük eşleşmenin İÇİNDEDİR; mesafe gerçekten
    sıfırdır ve bunu `None` yapmak var olmayan bir kusuru "onarırdı".
    """

    def test_taksit_sayisi_bitisik_kalir(self) -> None:
        f = _alan("Alışverişlerinizde 12 taksit fırsatı sizi bekliyor.",
                  "taksit_sayisi")
        self.assertIsNotNone(f)
        self.assertGreaterEqual(f.confidence, 0.90,
                                "tetikleyici eşleşmenin içinde; bitişik kanıt")

    def test_masrafsiz_bitisik_kalir(self) -> None:
        f = _alan("Bu finansmanda dosya masrafı alınmaz.", "masraf_durumu")
        self.assertIsNotNone(f)
        self.assertGreaterEqual(f.confidence, 0.90)


class TestKorpusDegismezi(unittest.TestCase):
    """Sabit-0,95 kütlesi geri şişerse kalibrasyon iddiası yine çürür."""

    def test_tam_095_payi_yuzde_45in_altinda(self) -> None:
        import json
        yol = Path(__file__).resolve().parents[1] / "data/gold/gold.round1.json"
        if not yol.exists():
            self.skipTest("gold.round1 yok")
        kayitlar = json.loads(yol.read_text(encoding="utf-8"))
        toplam = sabit = 0
        for r in kayitlar:
            for f in extract_all(r["text"]):
                toplam += 1
                if abs(float(f.confidence) - 0.95) < 1e-9:
                    sabit += 1
        self.assertGreater(toplam, 0)
        pay = sabit / toplam
        self.assertLess(pay, 0.45,
                        f"tam 0,95 payı %{pay:.1%} — ölçülen 15 Ağustos "
                        f"değeri %38,5 idi, kütle geri şişmiş")


if __name__ == "__main__":
    unittest.main()
