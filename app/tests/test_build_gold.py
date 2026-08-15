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
from scripts.gold_schema import (
    CAMPAIGN_TYPE_KEY,
    PROTOCOL_COLUMN,
    PROTOCOL_V2,
    SKIPPED_DECISION,
)
from scripts.hakemlik_uygula import DAMGA as HAKEMLIK_DAMGASI
from scripts.sema_onarimi_uygula import DAMGA as SEMA_ONARIMI_DAMGASI


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


def _kayit(**alanlar_ve_notlar: str):
    """Tek belgelik `_assemble` koşusu -> üretilen GoldRecord.

    `alanlar_ve_notlar`: alan adı -> o hücrenin `note`'u. Değer hep aynı;
    ölçülen şey NOT'un bayrağa etkisi.
    """
    doc_id = "albaraka--ornek"
    docs = {doc_id: {"id": doc_id, "text": "36 ay vade", "fields": {}}}
    decisions = {
        (doc_id, alan): [("A", "value", 36, not_)]
        for alan, not_ in alanlar_ve_notlar.items()
    }
    records, _, _ = build_gold._assemble(docs, decisions, {doc_id: ["A"]})
    return records[0]


class HakemlikDamgasiAdjudicatedYazar(unittest.TestCase):
    """`adjudicated` gerçeği söylemeli — 2026-08-15'e kadar HİÇ set edilmiyordu.

    `gold.round1.json`'un 134/134 kaydı "hakemlik yapılmadı" diyordu; oysa
    round1'de 41 uyuşmazlık üçüncü bir gözden geçmişti ve izi `notes`ta
    duruyordu. Bayrak o izden okunur.
    """

    def test_damga_tek_dogruluk_kaynagindan_gelir(self) -> None:
        """Sabit KOPYALANMAZ, damgayı yazan betiklerden içe aktarılır.

        Kopya bir sabit ayrışırsa bayrak sessizce yanlış olur ve kimse fark
        etmez — bu depoda ölçülmüş bir hata sınıfı (bkz. `report_iaa` başlığı).
        """
        self.assertEqual(
            build_gold.hakemlik_damgalari(),
            (HAKEMLIK_DAMGASI, SEMA_ONARIMI_DAMGASI))

    def test_hakemlik_damgali_hucre_adjudicated_yapar(self) -> None:
        record = _kayit(vade_ay=f"{HAKEMLIK_DAMGASI} B->A (kor hakem onayi)")
        self.assertTrue(record.adjudicated)

    def test_sema_onarimi_damgasi_da_adjudicated_yapar(self) -> None:
        record = _kayit(vade_ay=f"{SEMA_ONARIMI_DAMGASI} taksonomi disi deger")
        self.assertTrue(record.adjudicated)

    def test_damgasiz_kayit_adjudicated_DEGIL(self) -> None:
        """Varsayılan `False` bir iddiadır ve doğru olmak zorundadır."""
        record = _kayit(vade_ay="anotatör notu, damga yok")
        self.assertFalse(record.adjudicated)

    def test_bos_notlu_kayit_adjudicated_DEGIL(self) -> None:
        record = _kayit(vade_ay="")
        self.assertFalse(record.adjudicated)

    def test_tek_damgali_hucre_kaydin_tamamini_isaretler(self) -> None:
        """Bayrak KAYIT düzeyindedir: bir hücre yetiyor, hepsi gerekmiyor."""
        record = _kayit(
            vade_ay="",
            taksit_sayisi=f"{HAKEMLIK_DAMGASI} A->B (kor hakem onayi)",
        )
        self.assertTrue(record.adjudicated)

    def test_campaign_type_hucresindeki_damga_da_sayilir(self) -> None:
        """`campaign_type` en kalabalık uyuşmazlık alanıydı (n=47, 17 uyuşmazlık).

        O hücre `_assemble`'da `pop`lanıyor ve notu hiçbir yere yazılmıyor;
        bayrak popdan sonra hesaplanırsa oradaki hakemlik görünmez olur.
        """
        doc_id = "albaraka--ornek"
        docs = {doc_id: {"id": doc_id, "text": "36 ay vade", "fields": {}}}
        decisions = {
            (doc_id, CAMPAIGN_TYPE_KEY): [
                ("A", "value", "Konut Finansmanı",
                 f"{HAKEMLIK_DAMGASI} B->A (kor hakem onayi)")],
            (doc_id, "vade_ay"): [("A", "value", 36, "")],
        }
        records, _, _ = build_gold._assemble(docs, decisions, {doc_id: ["A"]})
        self.assertTrue(records[0].adjudicated)


class DamgaKismiEslesmeyleTetiklenmez(unittest.TestCase):
    """Çıplak alt-dize araması `#hakemlik-round10`'u da yakalardı."""

    def test_uzun_tur_numarasi_eslesmez(self) -> None:
        self.assertFalse(
            build_gold.hakemlik_damgali(f"{HAKEMLIK_DAMGASI}0 baska bir tur"))

    def test_damganin_uzatilmis_hali_eslesmez(self) -> None:
        self.assertFalse(
            build_gold.hakemlik_damgali(f"{SEMA_ONARIMI_DAMGASI}-taslak"))
        self.assertFalse(
            build_gold.hakemlik_damgali(f"{HAKEMLIK_DAMGASI}_eski"))

    def test_baska_etiketin_ortasina_dusen_dize_eslesmez(self) -> None:
        self.assertFalse(
            build_gold.hakemlik_damgali(f"#on{HAKEMLIK_DAMGASI}"))

    def test_kismi_eslesme_kayda_adjudicated_YAZMAZ(self) -> None:
        record = _kayit(vade_ay=f"{HAKEMLIK_DAMGASI}0 baska bir tur")
        self.assertFalse(record.adjudicated)

    def test_gercek_damga_metnin_icinde_de_yakalanir(self) -> None:
        """Damga notun başına da sonuna da düşebilir (`onceki_not | damga`)."""
        self.assertTrue(
            build_gold.hakemlik_damgali(f"anotatör notu | {HAKEMLIK_DAMGASI}"))
        self.assertTrue(
            build_gold.hakemlik_damgali(f"{HAKEMLIK_DAMGASI} B->A · ek not"))


if __name__ == "__main__":
    unittest.main()
