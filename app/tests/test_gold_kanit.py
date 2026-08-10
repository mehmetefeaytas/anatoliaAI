"""Kanıt (`field_spans`) sözleşmesi — iki gold hattının aynı kapıya bağlı olması.

İlgili: scripts/gold_schema.py (kapının tanımı)
        scripts/build_gold.py (v1 hattı — kanıtı ÜRETİR)
        scripts/merge_gold_v2.py (v2 hattı — kanıtı ŞART KOŞAR)

## Bu dosyanın varlık sebebi

Ölçüldü (2026-08-10): `merge_gold_v2` her alan için `field_spans` alıntısı
şart koşuyordu ama `GoldRecord` bu anahtarı tanımlamıyor, `build_gold` onu
üretmiyordu. gold.v2'nin 112/112 alanı kanıtlıyken gold.v1'in **0/65**'i
kanıtlıydı. İki hat aynı sözleşmeye tabi görünüyor, biri sözleşmeden habersiz
çalışıyordu.

Buradaki testler o ayrışmanın geri gelmesini engeller: kapının tek tanımı
olduğunu, `build_gold`ın kanıt ürettiğini ve **kanıt uydurmadığını** kilitler.
Sonuncusu en önemlisi — kapıyı memnun etmenin ucuz yolu her alana bir alıntı
yazmaktır; testler bunun yapılMADIĞINI ispatlar.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.build_gold import build, kanit_alintisi
from scripts.gold_schema import (
    GoldRecord,
    fabrication_errors,
    load_gold,
    record_from_dict,
    span_supports,
    uncovered_fields,
    validate_gold,
    write_gold,
)

METIN = (
    "Konut Finansmanı kampanyası. Kâr payı oranı %1,89 ile 120 aya varan "
    "vade imkânı. Kampanya 31.12.2026 tarihine kadar geçerlidir."
)


def _doc(**kwargs) -> dict:
    """Ön-anotasyon belgesi — `preannotations.json` docs[] biçimi."""
    temel = {
        "id": "banka--kampanya",
        "bank_slug": "banka",
        "source_url": "https://ornek.test/kampanya",
        "content_hash": "h1",
        "text": METIN,
        "campaign_type": "Konut Finansmanı",
        "fields": {},
    }
    temel.update(kwargs)
    return temel


def _payload(deger, ham: str, **kwargs) -> dict:
    """Tek alanın ön-anotasyon yükü; offset'ler metinden hesaplanır."""
    start = METIN.find(ham)
    assert start >= 0, f"test kurgusu bozuk: {ham!r} metinde yok"
    end = start + len(ham)
    yuk = {
        "value": deger,
        "raw_value": ham,
        "confidence": 0.9,
        "confidence_source": "rule_heuristic",
        "extractor": "rule",
        "source_span": METIN[max(0, start - 40):min(len(METIN), end + 40)],
        "span_start": start,
        "span_end": end,
        "span_verified": True,
    }
    yuk.update(kwargs)
    return yuk


class SpanSupportsTest(unittest.TestCase):
    """Kanıtın TEK tanımı: alıntı belgede birebir geçiyor mu?"""

    def test_birebir_gecen_alinti_kabul(self):
        self.assertTrue(span_supports(METIN, "Kâr payı oranı %1,89"))

    def test_bosluk_gurultusu_affedilir(self):
        # Anotatör kopyalarken satır sonu/çift boşluk kaybedebilir; bu
        # kopyalama gürültüsüdür, uydurma değil.
        self.assertTrue(span_supports(METIN, "Kâr payı\n\noranı   %1,89"))

    def test_buyuk_kucuk_harf_katlanmaz(self):
        # Katlansaydı "yaklaşık aynı şeyi diyor" savunmasına kapı açılırdı;
        # kapının varlık sebebi tam olarak o savunmayı reddetmektir.
        self.assertFalse(span_supports(METIN, "KÂR PAYI ORANI %1,89"))

    def test_metinde_olmayan_alinti_reddedilir(self):
        self.assertFalse(span_supports(METIN, "Kâr payı oranı %2,49"))

    def test_bos_alinti_kanit_degildir(self):
        for bos in ("", "   ", None, 42):
            self.assertFalse(span_supports(METIN, bos), bos)


class SemaTest(unittest.TestCase):
    """`field_spans` şemanın birinci sınıf alanı — gidiş-dönüş ve doğrulama."""

    def test_gidis_donus_korunur(self):
        kayit = GoldRecord(id="d1", text=METIN, fields={"vade_ay": 120},
                           field_spans={"vade_ay": "120 aya varan"})
        geri = record_from_dict(kayit.to_dict())
        self.assertEqual(geri.field_spans, {"vade_ay": "120 aya varan"})

    def test_kanitsiz_kayit_bos_sozluk_yazar(self):
        # Anahtarın sessizce yok olması kapının kör kalmasının ta kendisiydi;
        # boş sözlük "kanıt yok" diye BAĞIRAN bir bildirimdir.
        kayit = GoldRecord(id="d1", text=METIN, fields={"vade_ay": 120})
        self.assertEqual(kayit.to_dict()["field_spans"], {})

    def test_degeri_olmayan_alanin_kaniti_reddedilir(self):
        # Yokluğun/belirsizliğin alıntısı olmaz; olsaydı `uncovered_fields`
        # onu hiç denetlemez, "kanıt sayısı" sahte biçimde şişerdi.
        kayit = GoldRecord(id="d1", text=METIN,
                           absent_fields=["odul_miktari"],
                           field_spans={"odul_miktari": "Kâr payı oranı"})
        hatalar = kayit.validate()
        self.assertTrue(any("field_spans içinde ama fields içinde değil" in h
                            for h in hatalar), hatalar)

    def test_bos_alinti_sema_hatasi(self):
        kayit = GoldRecord(id="d1", text=METIN, fields={"vade_ay": 120},
                           field_spans={"vade_ay": "  "})
        self.assertTrue(any("boş olmayan metin olmalı" in h
                            for h in kayit.validate()))


class KapiAyrimiTest(unittest.TestCase):
    """Uydurma (ispatlanmış kusur) ile kanıtsızlık (bilgi yokluğu) ayrı şeyler."""

    def test_uydurma_yakalanir(self):
        kayit = GoldRecord(id="d1", text=METIN, fields={"kar_payi_orani": 2.49},
                           field_spans={"kar_payi_orani": "Kâr payı oranı %2,49"})
        self.assertEqual(len(fabrication_errors([kayit])), 1)
        # Alıntı VAR, dolayısıyla kanıtsız değil — ayrı kusur sınıfı.
        self.assertEqual(uncovered_fields([kayit]), [])

    def test_kanitsizlik_uydurma_sayilmaz(self):
        kayit = GoldRecord(id="d1", text=METIN, fields={"vade_ay": 120})
        self.assertEqual(fabrication_errors([kayit]), [])
        self.assertEqual(uncovered_fields([kayit]), [("d1", "vade_ay")])

    def test_temiz_kayit_iki_kapidan_da_gecer(self):
        kayit = GoldRecord(id="d1", text=METIN, fields={"vade_ay": 120},
                           field_spans={"vade_ay": "120 aya varan"})
        self.assertEqual(fabrication_errors([kayit]), [])
        self.assertEqual(uncovered_fields([kayit]), [])
        self.assertEqual(validate_gold([kayit]), [])


class KanitAlintisiTest(unittest.TestCase):
    """`build_gold` kanıtı NEREDEN alır — ve nerede almayı REDDEDER."""

    def test_onaylanan_model_degeri_kanit_uretir(self):
        doc = _doc(fields={"vade_ay": _payload(120, "120 aya varan")})
        alinti = kanit_alintisi(doc, "vade_ay", 120)
        self.assertIsNotNone(alinti)
        self.assertIn("120 aya varan", alinti)
        self.assertTrue(span_supports(METIN, alinti))

    def test_duzeltilen_deger_kanit_URETMEZ(self):
        # Bu testin düşmesi, betiğin YANLIŞ değerin konumunu DÜZELTİLMİŞ
        # değerin kanıtı diye yazdığı anlamına gelir. Kapıyı kandırmak budur.
        doc = _doc(fields={"vade_ay": _payload(24, "120 aya varan")})
        self.assertIsNone(kanit_alintisi(doc, "vade_ay", 120))

    def test_modelin_uretmedigi_alan_kanitsiz(self):
        doc = _doc(fields={})
        self.assertIsNone(kanit_alintisi(doc, "vade_ay", 120))

    def test_kaymis_offset_kanit_saylimaz(self):
        # `text[start:end] != raw_value`: gösterilen yer ile raporlanan değer
        # uyuşmuyor. Böyle bir konum provenance değil, gürültüdür.
        yuk = _payload(120, "120 aya varan")
        yuk["span_start"] = 0
        yuk["span_end"] = 5
        self.assertIsNone(kanit_alintisi(_doc(fields={"vade_ay": yuk}), "vade_ay", 120))

    def test_degeri_icermeyen_pencere_kanit_sayilmaz(self):
        # Değeri göstermeyen bir pencere, o değerin kanıtı değil; belgeden
        # rastgele bir cümledir.
        yuk = _payload(120, "120 aya varan")
        yuk["source_span"] = "Konut Finansmanı kampanyası."
        self.assertIsNone(kanit_alintisi(_doc(fields={"vade_ay": yuk}), "vade_ay", 120))

    def test_metinde_gecmeyen_pencere_kanit_sayilmaz(self):
        yuk = _payload(120, "120 aya varan")
        yuk["source_span"] = "uydurma pencere 120 aya varan uydurma"
        self.assertIsNone(kanit_alintisi(_doc(fields={"vade_ay": yuk}), "vade_ay", 120))


class BuildGoldUctanUcaTest(unittest.TestCase):
    """CSV -> gold: kanıt gerçekten yazılıyor mu, uydurma sızıyor mu?"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dizin = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

        self.pre = self.dizin / "pre.json"
        self.pre.write_text(json.dumps({"docs": [_doc(fields={
            "vade_ay": _payload(120, "120 aya varan"),
            "kar_payi_orani": _payload(1.89, "%1,89"),
        })]}, ensure_ascii=False), encoding="utf-8")

    def _csv(self, satirlar: list[str]) -> str:
        yol = self.dizin / "round0_kalibrasyon_A.csv"
        basliklar = "doc_id;field;model_value;gold_value;verdict;note;protokol"
        yol.write_text("﻿" + "\n".join([basliklar, *satirlar]) + "\n",
                       encoding="utf-8")
        return str(yol)

    def test_ok_karari_kanit_yazar_fix_yazmaz(self):
        csv_yolu = self._csv([
            "banka--kampanya;vade_ay;120;;ok;;v2",
            "banka--kampanya;kar_payi_orani;1.89;%2,49;fix;;v2",
        ])
        sonuc = build(str(self.pre), [csv_yolu])
        self.assertEqual(sonuc["errors"], [])
        (kayit,) = sonuc["records"]

        self.assertEqual(kayit.fields["vade_ay"], 120)
        self.assertIn("vade_ay", kayit.field_spans)

        # Düzeltilmiş değer gold'a girer AMA kanıtsız girer ve bu görünür.
        self.assertEqual(kayit.fields["kar_payi_orani"], 2.49)
        self.assertNotIn("kar_payi_orani", kayit.field_spans)
        self.assertEqual(uncovered_fields([kayit]),
                         [("banka--kampanya", "kar_payi_orani")])

    def test_uretilen_kanit_uydurma_kapisindan_gecer(self):
        # v1 hattının çıktısı v2 kapısının UYDURMA testinden geçmeli.
        csv_yolu = self._csv([
            "banka--kampanya;vade_ay;120;;ok;;v2",
            "banka--kampanya;kar_payi_orani;1.89;;ok;;v2",
        ])
        sonuc = build(str(self.pre), [csv_yolu])
        kayitlar = sonuc["records"]
        self.assertEqual(fabrication_errors(kayitlar), [])
        self.assertEqual(uncovered_fields(kayitlar), [])
        self.assertEqual(validate_gold(kayitlar), [])

    def test_kanit_diskte_kalici(self):
        csv_yolu = self._csv(["banka--kampanya;vade_ay;120;;ok;;v2"])
        kayitlar = build(str(self.pre), [csv_yolu])["records"]
        hedef = self.dizin / "gold.json"
        write_gold(kayitlar, hedef)
        (geri,) = load_gold(hedef)
        self.assertIn("vade_ay", geri.field_spans)
        self.assertTrue(span_supports(geri.text, geri.field_spans["vade_ay"]))

    def test_absent_karari_kanit_uretmez(self):
        csv_yolu = self._csv(["banka--kampanya;vade_ay;120;;absent;;v2"])
        (kayit,) = build(str(self.pre), [csv_yolu])["records"]
        self.assertEqual(kayit.absent_fields, ["vade_ay"])
        self.assertEqual(kayit.field_spans, {})
        self.assertEqual(validate_gold([kayit]), [])


class DepodakiGoldTest(unittest.TestCase):
    """Depodaki gold dosyaları kapının HANGİ tarafında — sayıyla."""

    def test_gold_v2_kanit_tam_ve_uydurmasiz(self):
        yol = _ROOT / "data/gold/gold.v2.json"
        if not yol.is_file():
            self.skipTest("gold.v2.json yok")
        kayitlar = load_gold(yol)
        self.assertEqual(fabrication_errors(kayitlar), [])
        self.assertEqual(uncovered_fields(kayitlar), [])

    def test_gold_v1_uydurma_icermez(self):
        # gold.v1 kanıtsızdır (ölçüldü: 0/65) ama UYDURMA içermez. Test
        # kapsamı yeniden derlendikçe kanıtsızlığın azalmasını serbest
        # bırakır, uydurmanın girmesini yasaklar.
        yol = _ROOT / "data/gold/gold.v1.json"
        if not yol.is_file():
            self.skipTest("gold.v1.json yok")
        self.assertEqual(fabrication_errors(load_gold(yol)), [])


if __name__ == "__main__":
    unittest.main()
