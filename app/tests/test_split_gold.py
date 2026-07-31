"""`scripts/split_gold.py` testleri — dev/test bölme ve dondurma protokolü.

Bu testler bir *istatistiksel dürüstlük* mekanizmasını koruyor. Yedi model kolu
(kural-only, Qwen3-8B, Trendyol-8B, GLiNER, NuExtract, BERTurk, LoRA) aynı gold
set üzerinde yarışacak. Kol seçimi test verisine bakılarak yapılırsa seçim
yanlılığı oluşur ve raporlanan sayı gerçek genelleme performansı olmaz.

Bu yüzden aşağıdaki değişmezler test altında:
  - Bölme deterministik (aynı gold + seed = aynı sha256)
  - Her zor-vaka kategorisi HER İKİ bölmede temsil edilir
  - Nadir alanlar tek tarafa yığılmaz
  - Dondurulmuş bölmenin üzerine kazara yazılamaz
  - Kurcalama sha256 ile yakalanır
  - Test bölmesine her erişim kalıcı kayda geçer
"""

from __future__ import annotations

import contextlib
import io
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.split_gold import (  # noqa: E402
    ERISIM_KAYDI_ADI,
    MANIFEST_ADI,
    NADIR_ALANLAR,
    bol,
    dogrula,
    erisim_kaydet,
    main,
    sha256_dosya,
)

HARD_TAGS = ("terminoloji", "format-varyant", "eksik-bilgi",
             "celiskili", "kosullu-aralik", "tr-ortografi")
BANKALAR = ["kuveyt-turk", "albaraka", "turkiye-finans", "ziraat-katilim",
            "vakif-katilim", "emlak-katilim", "tom-katilim", "adil-katilim"]
TURLER = ["Finansman", "Ihtiyac Finansmani", "Konut Finansmani",
          "Tasit Finansmani", "Kart", "Alisveris Puani", "Yeni Musteri",
          "Yatirim Urunu"]


@contextlib.contextmanager
def sessiz():
    """Betiğin ilerleme çıktısını yutar — CI logları okunabilir kalsın.

    Betik bilinçli olarak konuşkan (jüriye gösterilen bir denge tablosu
    basıyor); testte bunu görmek istemiyoruz, yalnızca çıkış kodları ve
    üretilen dosyalar önemli.
    """
    yakala = io.StringIO()
    with contextlib.redirect_stdout(yakala), contextlib.redirect_stderr(yakala):
        yield yakala


def sentetik_gold(n: int = 250, seed: int = 7) -> list[dict]:
    """Gerçek gold'un şema ve seyreklik karakterini taklit eden kayıtlar.

    Nadir alan oranları korpus ölçümünden geliyor: 849 belgede `kar_payi_orani`
    54 belgede vardı, `tahsis_ucreti` daha da seyrek.
    """
    rng = random.Random(seed)
    kayitlar = []
    for i in range(n):
        n_hard = rng.choices([0, 1, 2], [0.60, 0.32, 0.08])[0]
        fields: dict = {}
        if rng.random() < 0.22:
            fields["kar_payi_orani"] = round(rng.uniform(1.5, 3.5), 2)
        if rng.random() < 0.18:
            fields["tahsis_ucreti"] = {"value": rng.choice([0, 500, 1500]),
                                       "currency": "TRY"}
        if rng.random() < 0.55:
            fields["vade_ay"] = rng.choice([12, 24, 36, 120])
        kayitlar.append({
            "id": f"doc-{i:04d}",
            "text": f"ornek metin {i}",
            "fields": fields,
            "absent_fields": rng.sample(
                ["odul_miktari", "indirim_orani", "alisveris_puani"],
                k=rng.randint(0, 2)),
            "hard_tags": rng.sample(HARD_TAGS, k=n_hard),
            "bank_slug": rng.choice(BANKALAR),
            "campaign_type": rng.choice(TURLER),
        })
    return kayitlar


class TestBolme(unittest.TestCase):
    """Bölmenin matematiksel özellikleri."""

    def setUp(self) -> None:
        self.kayitlar = sentetik_gold(250)

    def test_boyutlar_hedef_orana_oturur(self) -> None:
        dev, test, tani = bol(self.kayitlar, test_orani=0.60, seed=42)
        self.assertEqual(len(dev) + len(test), 250)
        self.assertEqual(len(test), 150)
        self.assertEqual(len(dev), 100)
        self.assertAlmostEqual(tani["test_orani_gercek"], 0.60, places=2)

    def test_kayit_kaybi_veya_cogalmasi_yok(self) -> None:
        """Her kayıt tam olarak bir bölmede olmalı — ne kayıp ne kopya."""
        dev, test, _ = bol(self.kayitlar, seed=42)
        dev_ids = [k["id"] for k in dev]
        test_ids = [k["id"] for k in test]
        self.assertEqual(len(dev_ids), len(set(dev_ids)), "dev'de kopya var")
        self.assertEqual(len(test_ids), len(set(test_ids)), "test'te kopya var")
        self.assertEqual(set(dev_ids) & set(test_ids), set(),
                         "aynı kayıt iki bölmede — SIZINTI")
        self.assertEqual(set(dev_ids) | set(test_ids),
                         {k["id"] for k in self.kayitlar}, "kayıt kayboldu")

    def test_deterministik(self) -> None:
        """Aynı gold + aynı seed = birebir aynı bölme."""
        d1, t1, _ = bol(self.kayitlar, seed=42)
        d2, t2, _ = bol(self.kayitlar, seed=42)
        self.assertEqual([k["id"] for k in d1], [k["id"] for k in d2])
        self.assertEqual([k["id"] for k in t1], [k["id"] for k in t2])

    def test_farkli_seed_farkli_bolme(self) -> None:
        """Seed gerçekten etkili olmalı — aksi halde katmanlama sahte."""
        _, t1, _ = bol(self.kayitlar, seed=42)
        _, t2, _ = bol(self.kayitlar, seed=1234)
        self.assertNotEqual([k["id"] for k in t1], [k["id"] for k in t2])

    def test_her_zor_vaka_kategorisi_iki_bolmede_de_var(self) -> None:
        """En kritik değişmez: bir kategori tek tarafa düşerse o kategoride
        metrik raporlayamayız ve ablasyonun 'hibrit NEREDE kazandı' iddiası
        çöker."""
        dev, test, _ = bol(self.kayitlar, seed=42)

        def etiketler(kayitlar: list[dict]) -> set[str]:
            return {e for k in kayitlar for e in k.get("hard_tags", [])}

        dev_e, test_e = etiketler(dev), etiketler(test)
        tumu = etiketler(self.kayitlar)
        for etiket in tumu:
            self.assertIn(etiket, dev_e, f"{etiket} dev'de yok")
            self.assertIn(etiket, test_e, f"{etiket} test'te yok")

    def test_nadir_alanlar_tek_tarafa_yigilmaz(self) -> None:
        dev, test, _ = bol(self.kayitlar, seed=42)
        for alan in NADIR_ALANLAR:
            d = sum(1 for k in dev if alan in k.get("fields", {}))
            t = sum(1 for k in test if alan in k.get("fields", {}))
            self.assertGreater(d, 0, f"{alan} dev'de hiç yok")
            self.assertGreater(t, 0, f"{alan} test'te hiç yok")

    def test_tum_bankalar_test_bolmesinde_temsil_edilir(self) -> None:
        _, test, _ = bol(self.kayitlar, seed=42)
        self.assertGreaterEqual(
            len({k["bank_slug"] for k in test}), 7,
            "test bölmesinde bankaların çoğu temsil edilmeli")

    def test_bos_gold_hata_verir(self) -> None:
        with self.assertRaises(ValueError):
            bol([], seed=42)

    def test_gecersiz_oran_hata_verir(self) -> None:
        for oran in (0.0, 1.0, -0.2, 1.5):
            with self.assertRaises(ValueError):
                bol(self.kayitlar, test_orani=oran, seed=42)

    def test_kucuk_gold_ile_de_calisir(self) -> None:
        """3 kayıtlık `gold.sample.json` ile de çökmemeli."""
        dev, test, _ = bol(sentetik_gold(3), test_orani=0.60, seed=42)
        self.assertEqual(len(dev) + len(test), 3)


class TestDondurmaProtokolu(unittest.TestCase):
    """sha256 dondurma, üzerine yazma koruması, erişim kaydı."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.gold = self.tmp / "gold.json"
        self.gold.write_text(
            json.dumps(sentetik_gold(250), ensure_ascii=False),
            encoding="utf-8")
        self.out = self.tmp / "splits"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _bol(self, *ek: str) -> int:
        with sessiz():
            return main(["--gold", str(self.gold), "--out-dir", str(self.out), *ek])

    def _dogrula(self) -> int:
        with sessiz():
            return dogrula(self.out)

    def _erisim(self, gerekce: str) -> int:
        with sessiz():
            return erisim_kaydet(self.out, gerekce)

    def _bol_yol(self, gold_yolu: Path, *ek: str) -> int:
        """Farklı bir gold dosyasıyla böler — biçim ve hata yolları için."""
        with sessiz():
            return main(["--gold", str(gold_yolu), "--out-dir", str(self.out), *ek])

    def test_bolme_uretilir_ve_sha256_yazilir(self) -> None:
        self.assertEqual(self._bol(), 0)
        for ad in ("dev.json", "test.json"):
            self.assertTrue((self.out / ad).exists())
            self.assertTrue((self.out / f"{ad}.sha256").exists())
        self.assertTrue((self.out / MANIFEST_ADI).exists())
        self.assertTrue((self.out / ERISIM_KAYDI_ADI).exists(),
                        "erişim kaydı dosyası protokolün parçası")

    def test_manifest_sha256_gercek_dosyayla_uyusur(self) -> None:
        self._bol()
        manifest = json.loads((self.out / MANIFEST_ADI).read_text(encoding="utf-8"))
        for ad, beklenen in manifest["sha256"].items():
            self.assertEqual(sha256_dosya(self.out / ad), beklenen)

    def test_uzerine_yazma_engellenir(self) -> None:
        """Sızıntının en olası yolu: 'bir daha bölelim' deyip test setini
        değiştirmek. Varsayılan olarak engellenmeli."""
        self.assertEqual(self._bol(), 0)
        self.assertEqual(self._bol(), 3, "ikinci bölme --force olmadan geçti")

    def test_force_ile_uzerine_yazilabilir(self) -> None:
        self._bol()
        self.assertEqual(self._bol("--force"), 0)

    def test_dogrulama_bozulmamis_bolmede_gecer(self) -> None:
        self._bol()
        self.assertEqual(self._dogrula(), 0)

    def test_kurcalama_yakalanir(self) -> None:
        self._bol()
        (self.out / "test.json").write_text("[]", encoding="utf-8")
        self.assertEqual(self._dogrula(), 1, "kurcalanmış test bölmesi geçti")

    def test_kayip_bolme_yakalanir(self) -> None:
        self._bol()
        (self.out / "test.json").unlink()
        self.assertEqual(self._dogrula(), 1)

    def test_manifest_yoksa_dogrulama_hata_verir(self) -> None:
        """Bölme üretilmemişken --verify sessizce geçmemeli."""
        self.assertEqual(self._dogrula(), 2)

    def test_erisim_kaydi_birikimli(self) -> None:
        self._bol()
        self.assertEqual(self._erisim("nihai olcum"), 0)
        self.assertEqual(self._erisim("ikinci bakis"), 0)
        satirlar = [s for s in (self.out / ERISIM_KAYDI_ADI).read_text(
            encoding="utf-8").splitlines() if s.strip()]
        self.assertEqual(len(satirlar), 2)
        for satir in satirlar:
            girdi = json.loads(satir)
            self.assertIn("zaman", girdi)
            self.assertIn("git_sha", girdi)
            self.assertTrue(girdi["gerekce"].strip())

    def test_bos_gerekce_reddedilir(self) -> None:
        """Gerekçesiz erişim kaydı denetim izini işe yaramaz kılar."""
        self._bol()
        self.assertEqual(self._erisim("   "), 2)

    def test_gold_dosyasi_yoksa_hata(self) -> None:
        self.assertEqual(
            self._bol_yol(self.tmp / "yok.json"), 2)

    def test_sozluk_bicimindeki_gold_okunur(self) -> None:
        """`build_gold.py` ileride {records: [...]} yazarsa da çalışmalı."""
        sarili = self.tmp / "gold-dict.json"
        sarili.write_text(
            json.dumps({"schema_version": "1.0", "records": sentetik_gold(50)},
                       ensure_ascii=False), encoding="utf-8")
        self.assertEqual(self._bol_yol(sarili), 0)

    def test_tanimsiz_bicim_acik_hata_verir(self) -> None:
        """Tanınmayan gold biçimi sessizce boş bölme üretmemeli."""
        bozuk = self.tmp / "bozuk.json"
        bozuk.write_text(json.dumps({"baska": "sey"}), encoding="utf-8")
        with self.assertRaises(ValueError):
            self._bol_yol(bozuk)


if __name__ == "__main__":
    unittest.main()
