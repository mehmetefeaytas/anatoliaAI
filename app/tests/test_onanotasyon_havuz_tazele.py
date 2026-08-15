"""Havuz tazeleme — kanıt kazandırır, KARAR bozmaz.

İlgili: ../scripts/onanotasyon_havuz_tazele.py

Bu dosyanın koruduğu üç şey:

1. **Belge kümesi DEĞİŞMEZ.** `preannotate` havuzu yeniden örnekler ve korpus
   büyüdüyse aynı seed'le bile farklı belge kümesi verir; gold'un `doc_id`'leri
   havuzda bulunamayıp sessizce düşer. Bu araç örneklemeye hiç dokunmaz ve
   küme değişirse yazmayı reddeder.
2. **Birleştirir, üzerine yazmaz.** Bugünkü çıkarıcının artık üretmediği alan
   KORUNUR. Ölçüldü: düşürmek 13 kanıt kaybettiriyordu (kazanç 30'dan 17'ye
   iniyordu). Eski girdiyi tutmak uydurma değildir — `kanit_alintisi` her
   çağrıda span'i metne karşı yeniden doğrular.
3. **`campaign_type`e DOKUNMAZ.** Sınıflandırıcı çıktısıdır, kanıt türetiminde
   kullanılmaz; tazelemek yalnız risk ekler.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.onanotasyon_havuz_tazele import tazele

METIN = ("Kampanya Başlangıç ve Bitiş 01.01.2026 - 31.12.2026 tarihleri "
         "arasında geçerlidir. Tahsis ücreti 500 TL'dir.")


def _havuz(docs: list[dict]) -> Path:
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                      encoding="utf-8")
    json.dump({"schema_version": "1.0", "docs": docs}, tmp, ensure_ascii=False)
    tmp.close()
    return Path(tmp.name)


class BelgeKumesiKorunur(unittest.TestCase):
    def test_belge_sayisi_ve_kimlikleri_DEGISMEZ(self) -> None:
        yol = _havuz([{"id": "a", "text": METIN, "fields": {}},
                      {"id": "b", "text": METIN, "fields": {}}])
        tazele(yol)
        veri = json.loads(yol.read_text(encoding="utf-8"))
        self.assertEqual([d["id"] for d in veri["docs"]], ["a", "b"])

    def test_metinsiz_belge_atlanir_ama_DUSMEZ(self) -> None:
        yol = _havuz([{"id": "a", "text": "", "fields": {"vade_ay": {"value": 9}}}])
        tazele(yol)
        veri = json.loads(yol.read_text(encoding="utf-8"))
        self.assertEqual(len(veri["docs"]), 1)
        self.assertEqual(veri["docs"][0]["fields"]["vade_ay"]["value"], 9,
                         "metin yoksa alan olduğu gibi kalmalı")


class BirlestirmeUzerineYazmaDegil(unittest.TestCase):
    def test_bugun_URETILMEYEN_alan_KORUNUR(self) -> None:
        """Düşürmek ölçülmüş 13 kanıt kaybettiriyordu."""
        yol = _havuz([{"id": "a", "text": METIN, "fields": {
            "hayali_alan": {"value": 42, "raw_value": "42", "span_start": 0,
                            "span_end": 2, "source_span": "42"}}}])
        r = tazele(yol)
        veri = json.loads(yol.read_text(encoding="utf-8"))
        self.assertIn("hayali_alan", veri["docs"][0]["fields"])
        self.assertEqual(veri["docs"][0]["fields"]["hayali_alan"]["value"], 42)
        self.assertEqual(r["korunan_alan"], 1)

    def test_taze_deger_eskisini_EZER(self) -> None:
        yol = _havuz([{"id": "a", "text": METIN, "fields": {
            "kampanya_suresi": {"value": "2026-01-01", "raw_value": "eski",
                                "span_start": 0, "span_end": 4,
                                "source_span": "eski"}}}])
        r = tazele(yol)
        alan = json.loads(yol.read_text(encoding="utf-8"))["docs"][0]["fields"]
        self.assertEqual(alan["kampanya_suresi"]["value"], "2026-12-31",
                         "bayat başlangıç tarihi taze bitiş tarihiyle değişmeli")
        self.assertEqual(r["degisen_alan"], 1)

    def test_span_metinle_TUTARLI_yazilir(self) -> None:
        """Kanıt kapısının aradığı değişmez: `text[start:end] == raw_value`."""
        yol = _havuz([{"id": "a", "text": METIN, "fields": {}}])
        tazele(yol)
        alanlar = json.loads(yol.read_text(encoding="utf-8"))["docs"][0]["fields"]
        for ad, y in alanlar.items():
            s, e = y.get("span_start"), y.get("span_end")
            if isinstance(s, int) and isinstance(e, int):
                self.assertEqual(METIN[s:e], y["raw_value"], f"{ad} span kaymış")


class SiniflandiriciyaDokunulmaz(unittest.TestCase):
    def test_campaign_type_DEGISMEZ(self) -> None:
        yol = _havuz([{"id": "a", "text": METIN, "fields": {},
                       "campaign_type": "Kart",
                       "campaign_type_confidence": 0.42}])
        tazele(yol)
        d = json.loads(yol.read_text(encoding="utf-8"))["docs"][0]
        self.assertEqual(d["campaign_type"], "Kart")
        self.assertEqual(d["campaign_type_confidence"], 0.42)


class KuruKosu(unittest.TestCase):
    def test_kuru_kosuda_dosya_DEGISMEZ(self) -> None:
        yol = _havuz([{"id": "a", "text": METIN, "fields": {}}])
        once = yol.read_text(encoding="utf-8")
        r = tazele(yol, kuru=True)
        self.assertEqual(yol.read_text(encoding="utf-8"), once)
        self.assertIsNone(r["yedek"])


if __name__ == "__main__":
    unittest.main()
