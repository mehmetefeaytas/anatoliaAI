"""`build_gold.resolve_decision` — `ok` kararının değeri NEREDEN okunur.

İlgili: ../scripts/build_gold.py
        ../scripts/onanotasyon_tazele.py   (bayatlığın kaynağı)
        ../scripts/lint_review_csv.py      (`--pre` bayatlık uyarısı)

## Neden bu testler — ölçülmüş hata

2026-08-15'e kadar `resolve_decision`, `verdict=ok` satırında değeri
ön-anotasyon havuzundan (`--pre`) okuyordu. CSV'nin `model_value` sütunu
"yalnızca ekran kopyası" sayılıyordu.

Ama CSV'ler 8–9 Ağustos'ta `onanotasyon_tazele.py` ile BUGÜNKÜ çıkarıcıya
yenilendi; `preannotations.v2.json` 4 Ağustos'tan kalmıştı. İkisi 59 hücrede
ayrıştı (A 18 · B 19 · C 1 · D 21):

  - 42 tarih sürüklemesi: CSV `2026-12-31` (bitiş), havuz `2026-01-01` (başlangıç)
  - 14 `kar_payi_orani`: CSV **boş**, havuz `50.0` / `30.0` / `5.0`
    (hepsi kâr PAYLAŞIM oranı — kılavuz §4.13/6 `absent` der)

Yani gold'a, anotatörün ekranda hiç görmediği değerler girdi. En zararlısı
"onaylanmış yokluk": anotatör boş hücreyi `ok` ile onaylamış ("kontrol ettim,
yok"), gold ise bir DEĞER yazmış — halüsinasyon ölçümünü tersine çeviren
bir hata.

`ok` "ekranda okuduğum değer doğru" demektir. Bu dosya, değerin kaynağının
bir daha havuza kaymamasını çitler.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import build_gold
from scripts.gold_schema import PROTOCOL_COLUMN, PROTOCOL_V2, SKIPPED_DECISION


def _satir(**kwargs) -> dict:
    """Tek inceleme satırı. Varsayılan: `ok`, CSV'de taze bir değer var."""
    row = {
        "doc_id": "albaraka--ornek", "bank": "albaraka", "field": "vade_ay",
        "model_value": "36", "model_conf": "0.95",
        "confidence_source": "rule", "disagreement": "", "snippet": "36 ay vade",
        "gold_value": "", "verdict": "ok", "note": "",
        PROTOCOL_COLUMN: PROTOCOL_V2,
        "_line": 2, "_file": "test.csv",
    }
    row.update(kwargs)
    return row


class OkKarariCSVdenOkunur(unittest.TestCase):
    def test_ok_karari_CSV_model_value_kullanir_havuzu_DEGIL(self) -> None:
        """K5'in çekirdeği: CSV taze, havuz bayat -> CSV kazanır.

        `resolve_decision` artık havuzu HİÇ görmüyor; imzasında da yok. Bu
        test imza değişikliğini de çitler: birisi havuzu geri parametre olarak
        eklerse çağrı burada patlar.
        """
        kind, value = build_gold.resolve_decision(_satir(model_value="36"))
        self.assertEqual(kind, "value")
        self.assertEqual(value, 36)

    def test_ok_ve_CSV_bos_ise_absent_uretir(self) -> None:
        """"Kontrol ettim, YOK" bir karardır ve gold'da `absent` olmalıdır.

        Round1'de 18 hücre böyleydi; havuzdan okunduğu için gold'a DEĞER
        girmişti ve halüsinasyon ölçümü bozuluyordu.
        """
        kind, value = build_gold.resolve_decision(_satir(model_value=""))
        self.assertEqual(
            kind, "absent",
            "anotatör boş hücreyi onayladı; gold'a değer giremez")
        self.assertIsNone(value)

    def test_ok_karari_kanonik_olmayan_CSV_degerinde_BuildError(self) -> None:
        """`fix` kolundaki kapının ikizi — sessiz bozulmaya kapı bırakılmaz."""
        with self.assertRaises(build_gold.BuildError):
            build_gold.resolve_decision(_satir(model_value="otuz alti ay"))

    def test_fix_karari_CSV_model_valueyi_YOKSAYAR(self) -> None:
        """`fix`te yazılan gold_value kazanır; model değeri değil."""
        kind, value = build_gold.resolve_decision(
            _satir(verdict="fix", model_value="36", gold_value="24"))
        self.assertEqual((kind, value), ("value", 24))

    def test_v2_bos_verdict_CSV_dolu_olsa_bile_golda_YAZMAZ(self) -> None:
        """Değer kaynağının değişmesi v2 protokolünü delmemeli.

        `ok` artık CSV'yi okuyor; boş `verdict` de "CSV'yi onayladı" diye
        yorumlanırsa kılavuzun §3.1 ile kaldırdığı çapalama geri gelir.
        """
        kind, value = build_gold.resolve_decision(
            _satir(verdict="", model_value="36"))
        self.assertEqual(kind, SKIPPED_DECISION)
        self.assertIsNone(value)


if __name__ == "__main__":
    unittest.main()
