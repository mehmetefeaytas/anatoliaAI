"""İnsan ikinci-etiketleyici turu — körleme, artımlı kayıt, kappa uyumu.

İlgili: scripts/ikinci_etiketleyici.py (`insan`, `_alan_sor`, `kappa`)
        data/gold/review/INSAN-TURU-TALIMAT.md (insana verilecek talimat)
        data/gold/review/_kappa-ikinci-tur.md (κ=0,700, jüri kısmi kredi
        gerekçesi: ikinci etiketleyici insan değil bir LLM'di)

## Bu dosyanın varlık sebebi

Jüri κ=0,700 ölçümünü doğruladı ama kısmi kredi verdi: ikinci etiketleyici
model-model uyumu ölçüyordu, gold'un İNSAN yargısıyla tutarlılığını
KANITLAMIYORDU. Çözüm insan bir ikinci etiketleyici turu eklemek; ama bu
turun kendisi üç şeyi BOZARSA ölçüm yine anlamsız olur:

  1. Körleme delinirse (insan gold değerini ya da LLM kararını görürse) κ
     kendi kendini onaylayan bir sayı üretir — tam olarak jürinin
     eleştirdiği kusurun insan versiyonu.
  2. Seçilen 16 kayıt LLM turuyla AYNI olmazsa iki κ karşılaştırılamaz.
  3. Artımlı kaydetme veri kaybederse (yarıda kesilince cevaplanmış alanlar
     silinirse) insan turu LLM turundan daha pahalı ama daha kırılgan olur.

Bu testler üçünü de kilitler; ayrıca `kappa` alt komutunun insan JSONL'ini
reddetmediğini (görev maddesi 4) ispatlar.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import ikinci_etiketleyici as ie
from scripts.gold_schema import GoldRecord
from src.extraction.llm.schema import EXTRACTION_FIELDS

GOLD_SIZINTI = "SIZINTI-BU-METINDE-GECMEYEN-GOLD-DEGERI"
LLM_SIZINTI = "SIZINTI-LLM-KARARI"


def _fake_kayit(id_="fake-doc-01", text="Kampanya metni: tahsis ücreti 500 TL.",
                 **overrides):
    kwargs = dict(
        id=id_, text=text,
        fields={"kar_payi_orani": GOLD_SIZINTI},
        absent_fields=["finansman_tutari"],
        annotators=["M1"],
    )
    kwargs.update(overrides)
    return GoldRecord(**kwargs)


class TestKorleme(unittest.TestCase):
    """`_alan_sor` / `insan()` gold'u ya da LLM kararını GÖSTERMEMELİ."""

    def test_alan_sor_gold_veya_llm_parametresi_almiyor(self):
        """Yapısal garanti: fonksiyon imzasında gold/llm alma yolu bile yok."""
        import inspect
        params = set(inspect.signature(ie._alan_sor).parameters)
        self.assertEqual(params, {"alan", "girdi_fn", "yaz_fn"},
                          "_alan_sor yalnız alan adı + I/O fonksiyonları "
                          "almalı; gold/llm parametresi eklenmesi körlemeyi "
                          "yapısal olarak kırar.")

    def test_insan_turu_gold_degerini_ekrana_basmiyor(self):
        """Tam bir insan() koşumunda gold değeri hiçbir çıktı satırında yok."""
        tmp = Path(tempfile.mkdtemp())
        kayit = _fake_kayit()
        cevaplar = iter(["yok"] * len(EXTRACTION_FIELDS))
        basilanlar: list[str] = []
        rc = ie.insan(
            kayitlar=[kayit],
            cikti_yolu=tmp / "insan.jsonl",
            ilerleme_yolu=tmp / "ilerleme.json",
            girdi_fn=lambda: next(cevaplar),
            yaz_fn=lambda *a: basilanlar.append(" ".join(str(x) for x in a)),
        )
        self.assertEqual(rc, 0)
        tum_cikti = "\n".join(basilanlar)
        self.assertNotIn(GOLD_SIZINTI, tum_cikti,
                          "gold değeri insan turunda ekrana sızdı — körleme "
                          "kırıldı, κ artık anlamsız.")

    def test_insan_turu_llm_dosyasini_hic_okumuyor(self):
        """insan() ikinci-tur-llm.jsonl'i açmaz; LLM kararı asla görülmez."""
        tmp = Path(tempfile.mkdtemp())
        # Aynı id'yle sahte bir LLM çıktısı koy — insan() bunu OKUMAMALI.
        llm_ciktisi = tmp / "ikinci-tur-llm.jsonl"
        llm_ciktisi.write_text(json.dumps({
            "id": "fake-doc-01", "fields": {"kar_payi_orani": LLM_SIZINTI},
        }) + "\n", encoding="utf-8")

        eski_cikti = ie.CIKTI
        try:
            ie.CIKTI = llm_ciktisi   # insan() bu sabiti KULLANMAMALI
            kayit = _fake_kayit()
            cevaplar = iter(["yok"] * len(EXTRACTION_FIELDS))
            basilanlar: list[str] = []
            ie.insan(
                kayitlar=[kayit],
                cikti_yolu=tmp / "insan.jsonl",
                ilerleme_yolu=tmp / "ilerleme.json",
                girdi_fn=lambda: next(cevaplar),
                yaz_fn=lambda *a: basilanlar.append(" ".join(str(x) for x in a)),
            )
        finally:
            ie.CIKTI = eski_cikti
        self.assertNotIn(LLM_SIZINTI, "\n".join(basilanlar))


class TestKayitSecimi(unittest.TestCase):
    """LLM turu ile insan turu AYNI 16 kaydı seçmeli — yeni rastgelelik yok."""

    def _kayitlar(self, n_per_block=4, bloklar=("M1", "M2", "M3", "M4")):
        out = []
        for etiketleyici in bloklar:
            for i in range(6):
                out.append(GoldRecord(
                    id=f"{etiketleyici}-{i:02d}", text=f"metin {etiketleyici}-{i}",
                    annotators=[etiketleyici],
                ))
        return out

    def test_insan_sec_ile_aynı_fonksiyonu_kullanir(self):
        kayitlar = self._kayitlar()
        beklenen = {k.id for k in ie.sec(kayitlar)}

        cagrilar = {}
        orijinal_sec = ie.sec

        def casus(kayitlar_arg):
            sonuc = orijinal_sec(kayitlar_arg)
            cagrilar["secilen"] = {k.id for k in sonuc}
            return sonuc

        tmp = Path(tempfile.mkdtemp())
        ie.sec = casus
        try:
            cevaplar = iter(["yok"] * (len(kayitlar) * len(EXTRACTION_FIELDS)))
            ie.insan(
                kayitlar=kayitlar,
                cikti_yolu=tmp / "insan.jsonl",
                ilerleme_yolu=tmp / "ilerleme.json",
                girdi_fn=lambda: next(cevaplar),
                yaz_fn=lambda *a: None,
            )
        finally:
            ie.sec = orijinal_sec

        self.assertEqual(cagrilar.get("secilen"), beklenen,
                          "insan() farklı bir seçim mantığı kullanıyor; LLM "
                          "turuyla aynı kayıtlar üzerinde κ kıyaslanamaz.")


class TestArtimliKayit(unittest.TestCase):
    """Yarıda kesilen bir kayıt cevaplanmış alanlarını KAYBETMEMELİ."""

    def test_kesinti_sonrasi_devam_eder_ve_tamamlar(self):
        tmp = Path(tempfile.mkdtemp())
        cikti = tmp / "insan.jsonl"
        ilerleme = tmp / "ilerleme.json"
        kayit = _fake_kayit()

        class Kesme(Exception):
            pass

        # Yalnız ilk 3 alanı cevapla, sonra "kullanıcı çıktı" simülasyonu.
        ilk_cevaplar = iter(["yok", "yok", "yok"])

        def kesilen_girdi():
            try:
                return next(ilk_cevaplar)
            except StopIteration:
                raise Kesme() from None

        with self.assertRaises(Kesme):
            ie.insan(kayitlar=[kayit], cikti_yolu=cikti, ilerleme_yolu=ilerleme,
                      girdi_fn=kesilen_girdi, yaz_fn=lambda *a: None)

        # Kayıt henüz TAMAMLANMADI -> çıktıda satır olmamalı.
        self.assertEqual(ie._tamamlanan_kayit_idleri(cikti), set())
        # Ama cevaplanan 3 alan ilerleme dosyasında KALICI olmalı.
        ilerleme_verisi = json.loads(ilerleme.read_text(encoding="utf-8"))
        self.assertEqual(len(ilerleme_verisi[kayit.id]), 3)

        # Devam: kalan alanları cevapla.
        kalan = len(EXTRACTION_FIELDS) - 3
        sonraki_cevaplar = iter(["yok"] * kalan)
        rc = ie.insan(kayitlar=[kayit], cikti_yolu=cikti, ilerleme_yolu=ilerleme,
                       girdi_fn=lambda: next(sonraki_cevaplar),
                       yaz_fn=lambda *a: None)
        self.assertEqual(rc, 0)

        # Şimdi tamamlanmış olmalı ve ilerleme temizlenmiş olmalı.
        self.assertEqual(ie._tamamlanan_kayit_idleri(cikti), {kayit.id})
        self.assertEqual(json.loads(ilerleme.read_text(encoding="utf-8")), {})

    def test_tamamlanan_kayit_tekrar_sorulmaz(self):
        """`insan()` ikinci kez çağrılınca bitmiş kaydı YENİDEN sormamalı."""
        tmp = Path(tempfile.mkdtemp())
        cikti = tmp / "insan.jsonl"
        ilerleme = tmp / "ilerleme.json"
        kayit = _fake_kayit()
        cevaplar = iter(["yok"] * len(EXTRACTION_FIELDS))
        ie.insan(kayitlar=[kayit], cikti_yolu=cikti, ilerleme_yolu=ilerleme,
                  girdi_fn=lambda: next(cevaplar), yaz_fn=lambda *a: None)

        def patlayan_girdi():
            raise AssertionError("tamamlanmış kayıt için tekrar soru sorulmamalı")

        rc = ie.insan(kayitlar=[kayit], cikti_yolu=cikti, ilerleme_yolu=ilerleme,
                       girdi_fn=patlayan_girdi, yaz_fn=lambda *a: None)
        self.assertEqual(rc, 0)

    def test_bastan_bayragi_cikti_ve_ilerlemeyi_temizler(self):
        tmp = Path(tempfile.mkdtemp())
        cikti = tmp / "insan.jsonl"
        ilerleme = tmp / "ilerleme.json"
        cikti.write_text('{"id": "eski"}\n', encoding="utf-8")
        ilerleme.write_text('{"eski": {}}', encoding="utf-8")

        kayit = _fake_kayit()
        cevaplar = iter(["yok"] * len(EXTRACTION_FIELDS))
        ie.insan(kayitlar=[kayit], cikti_yolu=cikti, ilerleme_yolu=ilerleme,
                  girdi_fn=lambda: next(cevaplar), yaz_fn=lambda *a: None,
                  bastan=True)
        idler = ie._tamamlanan_kayit_idleri(cikti)
        self.assertEqual(idler, {kayit.id})
        self.assertNotIn("eski", idler)


class TestAlanSorGirdiIslenmesi(unittest.TestCase):
    """`_alan_sor` — "yok", hatalı biçim ve çoklu-giriş davranışı."""

    def test_yok_absent_uretir(self):
        dolu, deger = ie._alan_sor("vade_ay", girdi_fn=iter(["yok"]).__next__,
                                    yaz_fn=lambda *a: None)
        self.assertFalse(dolu)
        self.assertIsNone(deger)

    def test_gecersiz_deger_tekrar_sorulur(self):
        girdiler = iter(["tamamen-anlamsiz-metin", "120"])
        uyarilar = []
        dolu, deger = ie._alan_sor(
            "vade_ay", girdi_fn=lambda: next(girdiler),
            yaz_fn=lambda *a: uyarilar.append(" ".join(map(str, a))))
        self.assertTrue(dolu)
        self.assertEqual(deger, 120)
        self.assertTrue(any("HATA" in u for u in uyarilar),
                         "geçersiz girdi sonrası HATA mesajı basılmalı.")

    def test_liste_alani_coklu_girisi_topluyor(self):
        girdiler = iter(["İlk koşul cümlesi", "İkinci koşul cümlesi", ""])
        dolu, deger = ie._alan_sor("kampanya_kosullari",
                                    girdi_fn=lambda: next(girdiler),
                                    yaz_fn=lambda *a: None)
        self.assertTrue(dolu)
        self.assertEqual(deger, ["İlk koşul cümlesi", "İkinci koşul cümlesi"])

    def test_tum_alanlar_icin_yardim_metni_var(self):
        for alan in EXTRACTION_FIELDS:
            self.assertIn(alan, ie.FIELD_YARDIM,
                           f"{alan} için FIELD_YARDIM eksik.")


class TestCiktiBicimi(unittest.TestCase):
    """Yazılan JSONL, `kappa` alt komutunun beklediği biçime uymalı."""

    def test_insan_kimligi_dogru_yaziliyor(self):
        tmp = Path(tempfile.mkdtemp())
        cikti = tmp / "insan.jsonl"
        kayit = _fake_kayit(id_="d1")
        cevaplar = iter(["%1,89"] + ["yok"] * (len(EXTRACTION_FIELDS) - 1))
        ie.insan(kayitlar=[kayit], cikti_yolu=cikti,
                  ilerleme_yolu=tmp / "ilerleme.json",
                  girdi_fn=lambda: next(cevaplar), yaz_fn=lambda *a: None)
        satir = json.loads(cikti.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(satir["annotator"], ie.INSAN_ID)
        self.assertEqual(satir["model"], ie.INSAN_ID)
        self.assertEqual(satir["backend"], "insan")
        self.assertIsNone(satir["error"])
        self.assertEqual(satir["primary_human"], "M1")
        self.assertEqual(satir["fields"], {"kar_payi_orani": 1.89})


class TestKappaInsanDosyasiniKabulEder(unittest.TestCase):
    """Görev maddesi 4: mevcut model-tutarlılık kapısı insan dosyasını
    reddetmemeli. `kappa()` zaten hiçbir "model" alanına bakan bir kapı
    içermiyor (yalnız `kos()`nun kendi ekleme mantığında var, o da ayrı bir
    dosyaya -- ikinci-tur-llm.jsonl -- yazıyor); bu test bunu davranış
    düzeyinde kilitler."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.gold_yolu = self.tmp / "gold.json"
        self.gold_yolu.write_text(json.dumps([
            {"id": "d1", "text": "metin1", "fields": {"vade_ay": 36},
             "absent_fields": ["finansman_tutari"], "annotators": ["M1"]},
            {"id": "d2", "text": "metin2", "fields": {},
             "absent_fields": ["vade_ay", "finansman_tutari"],
             "annotators": ["M2"]},
        ]), encoding="utf-8")
        self._eski_gold = ie.GOLD
        ie.GOLD = self.gold_yolu

    def tearDown(self):
        ie.GOLD = self._eski_gold

    def _insan_ciktisi_yaz(self, yol: Path):
        satirlar = [
            {"id": "d1", "annotator": ie.INSAN_ID, "primary_human": "M1",
             "fields": {"vade_ay": 36}, "error": None, "latency_ms": 1000,
             "backend": "insan", "model": ie.INSAN_ID},
            {"id": "d2", "annotator": ie.INSAN_ID, "primary_human": "M2",
             "fields": {}, "error": None, "latency_ms": 900,
             "backend": "insan", "model": ie.INSAN_ID},
        ]
        with yol.open("w", encoding="utf-8") as f:
            for s in satirlar:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")

    def test_kappa_girdi_ile_insan_dosyasini_okur_ve_kabul_eder(self):
        insan_yolu = self.tmp / "ikinci-tur-insan.jsonl"
        self._insan_ciktisi_yaz(insan_yolu)
        rc = ie.kappa(argparse.Namespace(girdi=str(insan_yolu)))
        self.assertEqual(rc, 0)

    def test_kappa_ayri_rapor_dosyasina_yazar_llm_raporunu_ezmez(self):
        """`ie.RAPOR`ı (gerçek repo dosyası) hiç ELLEMEDEN izole test eder —
        paralel çalışan başka ajanlar aynı repoyu kullanıyor olabilir;
        gerçek dosyaya dokunmak bir yarış koşulu (race condition) riski
        taşır. Bunun yerine `ie.RAPOR`ı geçici olarak tmp bir yola çeviririz.
        """
        insan_yolu = self.tmp / "ikinci-tur-insan.jsonl"
        self._insan_ciktisi_yaz(insan_yolu)

        sahte_rapor = self.tmp / "_kappa-ikinci-tur.md"
        eski_rapor_icerigi = "DOKUNULMAMASI-GEREKEN-LLM-RAPORU"
        sahte_rapor.write_text(eski_rapor_icerigi, encoding="utf-8")

        eski_rapor = ie.RAPOR
        ie.RAPOR = sahte_rapor
        try:
            rc = ie.kappa(argparse.Namespace(girdi=str(insan_yolu)))
            self.assertEqual(rc, 0)
            insan_rapor = insan_yolu.parent / f"_kappa-{insan_yolu.stem}.md"
            self.assertTrue(insan_rapor.exists())
            self.assertIn("İNSANDIR", insan_rapor.read_text(encoding="utf-8"))
            self.assertEqual(sahte_rapor.read_text(encoding="utf-8"),
                              eski_rapor_icerigi,
                              "insan turu LLM'in κ raporunu ezdi.")
        finally:
            ie.RAPOR = eski_rapor

    def test_kappa_eksik_dosya_icin_2_dondurur(self):
        rc = ie.kappa(argparse.Namespace(girdi=str(self.tmp / "yok-boyle-dosya.jsonl")))
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
