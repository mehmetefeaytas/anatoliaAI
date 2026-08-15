"""`.xlsx` -> inceleme CSV taşıması — üreteç sütunları KORUNUR, satır kümesi kilitli.

İlgili: ../scripts/xlsx_to_review_csv.py, ../scripts/protokol_yukselt.py
        ../data/gold/review/_atama.md (κ için satır kümesi sabittir)

Bu dosyanın koruduğu üç şey:

1. **Üreteç sütunlarına dokunulmaz.** Excel `model_conf` `0.70`'i `0.7` yapar;
   o değer `.xlsx`'ten değil CSV'den okunmalıdır. Aksi hâlde ön-anotasyonun
   güven skoru sessizce değişir ve `build_gold` başka bir şey ölçer.
2. **Satır kümesi ayrışırsa taşıma YAPILMAZ.** Anotatör Excel'de satır siler
   ya da eklerse dört dosya artık aynı birimleri taşımaz ve Fleiss κ hizasız
   çıkar — üstelik sessizce.
3. **Eşleme sıraya değil `(doc_id, field)`'a dayanır.** Anotatör sıralama
   yapmış olabilir; kararı doğru satıra düşürmek zorundayız.
"""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import xlsx_to_review_csv as X
from scripts.to_review_csv import CSV_DELIMITER, CSV_ENCODING

BASLIK = ["doc_id", "bank", "field", "model_value", "model_conf",
          "confidence_source", "disagreement", "snippet", "gold_value",
          "verdict", "note"]


def _xlsx_yaz(yol: Path, satirlar: list[list[str]]) -> None:
    """Minimal ama gerçek bir `.xlsx`: paylaşılan dizge tablosu + tek sayfa."""
    dizgeler: list[str] = []
    yer: dict[str, int] = {}

    def idx(s: str) -> int:
        if s not in yer:
            yer[s] = len(dizgeler)
            dizgeler.append(s)
        return yer[s]

    govde = []
    for r, satir in enumerate(satirlar, start=1):
        hucreler = []
        for c, deger in enumerate(satir):
            if deger == "":
                continue           # boş hücre yazılmaz (Excel de yazmaz)
            ad = chr(ord("A") + c) + str(r)
            hucreler.append(f'<c r="{ad}" t="s"><v>{idx(deger)}</v></c>')
        govde.append(f'<row r="{r}">{"".join(hucreler)}</row>')

    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    sheet = (f'<?xml version="1.0"?><worksheet xmlns="{ns}"><sheetData>'
             f'{"".join(govde)}</sheetData></worksheet>')
    ss_govde = "".join(f"<si><t>{s}</t></si>" for s in dizgeler)
    ss = (f'<?xml version="1.0"?><sst xmlns="{ns}" count="{len(dizgeler)}" '
          f'uniqueCount="{len(dizgeler)}">{ss_govde}</sst>')

    with zipfile.ZipFile(yol, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/sharedStrings.xml", ss)


def _csv_yaz(yol: Path, satirlar: list[dict]) -> None:
    with yol.open("w", encoding=CSV_ENCODING, newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=BASLIK, delimiter=CSV_DELIMITER,
                           lineterminator="\r\n")
        w.writeheader()
        w.writerows(satirlar)


def _csv_oku(yol: Path) -> list[dict]:
    with yol.open(encoding=CSV_ENCODING, newline="") as fh:
        return list(csv.DictReader(fh, delimiter=CSV_DELIMITER))


def _satir(doc: str, field: str, **ek) -> dict:
    temel = {"doc_id": doc, "bank": "test", "field": field,
             "model_value": "12", "model_conf": "0.70",
             "confidence_source": "rule", "disagreement": "",
             "snippet": "…metin…", "gold_value": "", "verdict": "", "note": ""}
    temel.update(ek)
    return temel


class _Temel(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)
        self.csv = self.d / "round0_X.csv"
        self.xlsx = self.d / "round0_X.xlsx"

    def tearDown(self) -> None:
        self._tmp.cleanup()


class TestUretecSutunlariKorunur(_Temel):
    def test_model_conf_EXCEL_BOZMASINA_RAGMEN_korunur(self) -> None:
        """Excel `0.70`'i `0.7` yapar; CSV'deki değer kalmalı."""
        _csv_yaz(self.csv, [_satir("d1", "vade_ay")])
        _xlsx_yaz(self.xlsx, [
            BASLIK,
            ["d1", "test", "vade_ay", "12", "0.7", "rule", "", "…metin…",
             "36", "fix", ""],
        ])
        X.tasi(self.xlsx, self.csv)
        satir = _csv_oku(self.csv)[0]
        self.assertEqual(satir["model_conf"], "0.70",
                         "üreteç sütunu `.xlsx`'ten YAZILMAMALI")
        self.assertEqual(satir["gold_value"], "36")
        self.assertEqual(satir["verdict"], "fix")

    def test_snippet_degistirilmez(self) -> None:
        _csv_yaz(self.csv, [_satir("d1", "vade_ay")])
        _xlsx_yaz(self.xlsx, [
            BASLIK,
            ["d1", "test", "vade_ay", "12", "0.7", "rule", "", "BOZULMUŞ",
             "", "ok", ""],
        ])
        X.tasi(self.xlsx, self.csv)
        self.assertEqual(_csv_oku(self.csv)[0]["snippet"], "…metin…")


class TestSatirKumesi(_Temel):
    def test_eksik_satir_TASIMAYI_DURDURUR(self) -> None:
        _csv_yaz(self.csv, [_satir("d1", "vade_ay"), _satir("d2", "vade_ay")])
        _xlsx_yaz(self.xlsx, [BASLIK,
                              ["d1", "test", "vade_ay", "12", "0.7", "rule",
                               "", "…", "36", "fix", ""]])
        rapor = X.tasi(self.xlsx, self.csv)
        self.assertEqual(rapor["xlsxte_olmayan"], [("d2", "vade_ay")])
        self.assertEqual(rapor["yazilan"], 0)
        self.assertEqual(_csv_oku(self.csv)[0]["verdict"], "",
                         "satır kümesi uyuşmuyorsa HİÇBİR şey yazılmamalı")

    def test_fazla_satir_TASIMAYI_DURDURUR(self) -> None:
        _csv_yaz(self.csv, [_satir("d1", "vade_ay")])
        _xlsx_yaz(self.xlsx, [
            BASLIK,
            ["d1", "test", "vade_ay", "12", "0.7", "rule", "", "…", "36", "fix", ""],
            ["dX", "test", "vade_ay", "12", "0.7", "rule", "", "…", "9", "fix", ""],
        ])
        rapor = X.tasi(self.xlsx, self.csv)
        self.assertEqual(rapor["csvde_olmayan"], [("dX", "vade_ay")])
        self.assertEqual(rapor["yazilan"], 0)

    def test_SIRA_degisse_de_dogru_satira_duser(self) -> None:
        """Anotatör Excel'de sıralamış olabilir; anahtar eşlemesi bunu taşır."""
        _csv_yaz(self.csv, [_satir("d1", "vade_ay"), _satir("d2", "kar_payi_orani")])
        _xlsx_yaz(self.xlsx, [
            BASLIK,   # ters sırada
            ["d2", "test", "kar_payi_orani", "12", "0.7", "rule", "", "…", "2.05", "fix", ""],
            ["d1", "test", "vade_ay", "12", "0.7", "rule", "", "…", "36", "fix", ""],
        ])
        X.tasi(self.xlsx, self.csv)
        satirlar = {(r["doc_id"], r["field"]): r for r in _csv_oku(self.csv)}
        self.assertEqual(satirlar[("d1", "vade_ay")]["gold_value"], "36")
        self.assertEqual(satirlar[("d2", "kar_payi_orani")]["gold_value"], "2.05")


class TestBosHucre(_Temel):
    def test_bos_hucre_DOLU_karari_EZMEZ(self) -> None:
        """Anotatör dokunmadıysa hedefteki karar korunur."""
        _csv_yaz(self.csv, [_satir("d1", "vade_ay", verdict="fix",
                                   gold_value="36")])
        _xlsx_yaz(self.xlsx, [BASLIK,
                              ["d1", "test", "vade_ay", "12", "0.7", "rule",
                               "", "…", "", "", ""]])
        X.tasi(self.xlsx, self.csv)
        satir = _csv_oku(self.csv)[0]
        self.assertEqual(satir["verdict"], "fix")
        self.assertEqual(satir["gold_value"], "36")

    def test_ustune_yazma_RAPORLANIR(self) -> None:
        """Sessiz üzerine yazma yok: farklı bir karar geldiyse görünür olur."""
        _csv_yaz(self.csv, [_satir("d1", "vade_ay", verdict="ok")])
        _xlsx_yaz(self.xlsx, [BASLIK,
                              ["d1", "test", "vade_ay", "12", "0.7", "rule",
                               "", "…", "", "absent", ""]])
        rapor = X.tasi(self.xlsx, self.csv)
        self.assertEqual(len(rapor["ustune_yazilan"]), 1)
        u = rapor["ustune_yazilan"][0]
        self.assertEqual((u["sutun"], u["eski"], u["yeni"]),
                         ("verdict", "ok", "absent"))


class TestKuruKosu(_Temel):
    def test_kuru_kosu_DOSYAYA_DOKUNMAZ(self) -> None:
        _csv_yaz(self.csv, [_satir("d1", "vade_ay")])
        _xlsx_yaz(self.xlsx, [BASLIK,
                              ["d1", "test", "vade_ay", "12", "0.7", "rule",
                               "", "…", "36", "fix", ""]])
        rapor = X.tasi(self.xlsx, self.csv, kuru=True)
        self.assertEqual(rapor["yazilan"], 1)      # ne olacağını söyler
        self.assertEqual(_csv_oku(self.csv)[0]["verdict"], "")   # ama yazmaz
        self.assertIsNone(rapor["yedek"])


class TestYedek(_Temel):
    def test_yazmadan_once_yedek_alinir(self) -> None:
        _csv_yaz(self.csv, [_satir("d1", "vade_ay")])
        _xlsx_yaz(self.xlsx, [BASLIK,
                              ["d1", "test", "vade_ay", "12", "0.7", "rule",
                               "", "…", "36", "fix", ""]])
        rapor = X.tasi(self.xlsx, self.csv)
        yedek = Path(rapor["yedek"])
        self.assertTrue(yedek.exists())
        self.assertEqual(_csv_oku(yedek)[0]["verdict"], "",
                         "yedek TAŞIMADAN ÖNCEKİ hâli tutmalı")

    def test_ikinci_kosu_yedegi_EZMEZ(self) -> None:
        _csv_yaz(self.csv, [_satir("d1", "vade_ay")])
        _xlsx_yaz(self.xlsx, [BASLIK,
                              ["d1", "test", "vade_ay", "12", "0.7", "rule",
                               "", "…", "36", "fix", ""]])
        ilk = Path(X.tasi(self.xlsx, self.csv)["yedek"])
        ikinci = Path(X.tasi(self.xlsx, self.csv)["yedek"])
        self.assertNotEqual(ilk, ikinci)
        self.assertTrue(ilk.exists() and ikinci.exists())


class TestBozukGirdi(_Temel):
    def test_eksik_sutun_ACIK_HATA(self) -> None:
        _csv_yaz(self.csv, [_satir("d1", "vade_ay")])
        _xlsx_yaz(self.xlsx, [["doc_id", "field"], ["d1", "vade_ay"]])
        with self.assertRaises(ValueError) as ctx:
            X.tasi(self.xlsx, self.csv)
        self.assertIn("eksik sütun", str(ctx.exception))

    def test_sutun_indeksi_cok_harfli(self) -> None:
        self.assertEqual(X._sutun_indeksi("A1"), 0)
        self.assertEqual(X._sutun_indeksi("Z9"), 25)
        self.assertEqual(X._sutun_indeksi("AA1"), 26)
        self.assertEqual(X._sutun_indeksi("AB12"), 27)


def _xlsx_tarihli_yaz(yol: Path, baslik: list[str], satirlar: list[list],
                      tarih_sutunlari: set[int]) -> None:
    """Belirtilen sütunları TARİH biçimli sayı hücresi olarak yazan `.xlsx`.

    Excel bir tarihi böyle saklar: değer bir seri numarasıdır, "bu bir tarihtir"
    bilgisi yalnız hücrenin stilinde durur.
    """
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    dizgeler: list[str] = []
    yer: dict[str, int] = {}

    def idx(s: str) -> int:
        if s not in yer:
            yer[s] = len(dizgeler)
            dizgeler.append(s)
        return yer[s]

    govde = []
    for r, satir in enumerate([baslik, *satirlar], start=1):
        hucreler = []
        for c, deger in enumerate(satir):
            if deger == "":
                continue
            ad = chr(ord("A") + c) + str(r)
            if r > 1 and c in tarih_sutunlari:
                # stil 1 -> cellXfs[1] -> numFmtId=14 (yerleşik tarih)
                hucreler.append(f'<c r="{ad}" s="1"><v>{deger}</v></c>')
            else:
                hucreler.append(f'<c r="{ad}" t="s"><v>{idx(str(deger))}</v></c>')
        govde.append(f'<row r="{r}">{"".join(hucreler)}</row>')

    sheet = (f'<?xml version="1.0"?><worksheet xmlns="{ns}"><sheetData>'
             f'{"".join(govde)}</sheetData></worksheet>')
    ss_govde = "".join(f"<si><t>{s}</t></si>" for s in dizgeler)
    ss = (f'<?xml version="1.0"?><sst xmlns="{ns}" count="{len(dizgeler)}" '
          f'uniqueCount="{len(dizgeler)}">{ss_govde}</sst>')
    styles = (f'<?xml version="1.0"?><styleSheet xmlns="{ns}"><cellXfs count="2">'
              f'<xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>')

    with zipfile.ZipFile(yol, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/sharedStrings.xml", ss)
        z.writestr("xl/styles.xml", styles)


class TestExcelSeriTarihi(_Temel):
    """Tarih hücresi seri numarası olarak taşınırsa gold sessizce bozulur.

    Ölçüldü (2026-08-15): `round1_B.xlsx`'te 17, `round1_main_D`'de 33
    `kampanya_suresi` hücresi `2026-12-31` yerine `46387` olarak taşınmıştı.
    Ayrıştırıcı sayıyı reddetmez — hata sessizdir.
    """

    def test_tarih_bicimli_hucre_ISO_tarihe_cevrilir(self) -> None:
        _csv_yaz(self.csv, [_satir("d1", "kampanya_suresi")])
        _xlsx_tarihli_yaz(
            self.xlsx, BASLIK,
            [["d1", "test", "kampanya_suresi", "12", "0.70", "rule", "",
              "…metin…", 46387, "fix", ""]],
            tarih_sutunlari={8},   # gold_value
        )
        X.tasi(self.xlsx, self.csv)
        self.assertEqual(_csv_oku(self.csv)[0]["gold_value"], "2026-12-31")

    def test_tarih_bicimsiz_sayi_OLDUGU_GIBI_kalir(self) -> None:
        """Biçimi tarih olmayan sayı çevrilmez — `finansman_tutari` 46203 olabilir."""
        _csv_yaz(self.csv, [_satir("d1", "finansman_tutari")])
        _xlsx_tarihli_yaz(
            self.xlsx, BASLIK,
            [["d1", "test", "finansman_tutari", "12", "0.70", "rule", "",
              "…metin…", 46203, "fix", ""]],
            tarih_sutunlari=set(),
        )
        X.tasi(self.xlsx, self.csv)
        self.assertEqual(_csv_oku(self.csv)[0]["gold_value"], "46203")


class TestCsvKaynak(_Temel):
    """Anotatör Excel'den CSV kaydettiğinde de yalnız KARAR sütunları taşınır.

    round1_A'da ölçüldü: BOM düştü ve `gold_value` ile `verdict` arasına adsız
    bir sütun girdi (12 -> 13 sütun). Dosyayı hedefin üzerine kopyalamak üreteç
    sütunlarını da değiştirirdi.
    """

    def test_adsiz_sutunlu_CSV_kararlari_dogru_sutuna_duser(self) -> None:
        _csv_yaz(self.csv, [_satir("d1", "vade_ay"), _satir("d2", "vade_ay")])
        kaynak = self.d / "round0_X_Etiketli.csv"
        # BOM yok + gold_value ile verdict arasında ADSIZ sütun
        bozuk = ["doc_id;bank;field;model_value;model_conf;confidence_source;"
                 "disagreement;snippet;gold_value;;verdict;note",
                 "d1;test;vade_ay;12;0.7;rule;;…metin…;36;;fix;dikkat",
                 "d2;test;vade_ay;12;0.7;rule;;…metin…;;;ok;"]
        kaynak.write_text("\r\n".join(bozuk) + "\r\n", encoding="utf-8")

        X.tasi(kaynak, self.csv)
        satirlar = {r["doc_id"]: r for r in _csv_oku(self.csv)}
        self.assertEqual(satirlar["d1"]["verdict"], "fix")
        self.assertEqual(satirlar["d1"]["gold_value"], "36")
        self.assertEqual(satirlar["d1"]["note"], "dikkat")
        self.assertEqual(satirlar["d2"]["verdict"], "ok")
        # Üreteç sütunu Excel'in bozduğu değerle DEĞİŞMEZ.
        self.assertEqual(satirlar["d1"]["model_conf"], "0.70")


class TestKismiTasima(_Temel):
    """`--kismi` yalnız κ'ya GİRMEYECEK dosyalar için kapıyı açar."""

    def _hizasiz_kur(self) -> None:
        _csv_yaz(self.csv, [_satir("d1", "vade_ay"), _satir("d2", "vade_ay")])
        _xlsx_yaz(self.xlsx, [
            BASLIK,
            ["d1", "test", "vade_ay", "12", "0.7", "rule", "", "…", "36", "fix", ""],
            # d9 hedefte YOK -> satır kümesi ayrışıyor
            ["d9", "test", "vade_ay", "12", "0.7", "rule", "", "…", "48", "fix", ""],
        ])

    def test_kismi_OLMADAN_tasima_yapilmaz(self) -> None:
        self._hizasiz_kur()
        rapor = X.tasi(self.xlsx, self.csv)
        self.assertTrue(rapor["csvde_olmayan"])
        self.assertEqual(rapor["yazilan"], 0)
        self.assertEqual(_csv_oku(self.csv)[0]["verdict"], "")

    def test_kismi_ILE_kesisim_tasinir_disarida_kalan_SAYILIR(self) -> None:
        self._hizasiz_kur()
        rapor = X.tasi(self.xlsx, self.csv, kismi=True)
        self.assertEqual(rapor["yazilan"], 1)
        self.assertEqual(rapor["disarida_kalan_dolu"], 1)
        satirlar = {r["doc_id"]: r for r in _csv_oku(self.csv)}
        self.assertEqual(satirlar["d1"]["gold_value"], "36")
        self.assertEqual(satirlar["d2"]["verdict"], "")


class TestGercekDosyalar(unittest.TestCase):
    """Ekipten gelen gerçek `.xlsx` dosyaları hâlâ okunabiliyor mu."""

    KAYNAK = Path(__file__).resolve().parents[1] / "data" / "gold" / "review"
    DOSYALAR = ("round0_kalibrasyon_B.xlsx", "round0_kalibrasyon_C.xlsx",
                "round0_kalibrasyon_D.csv.xlsx")

    def test_260_satir_okunur(self) -> None:
        for ad in self.DOSYALAR:
            yol = self.KAYNAK / ad
            if not yol.exists():
                self.skipTest(f"{ad} yok")
            with self.subTest(file=ad):
                kararlar = X.xlsx_kararlari(yol)
                self.assertEqual(len(kararlar), 260)


if __name__ == "__main__":
    unittest.main()
