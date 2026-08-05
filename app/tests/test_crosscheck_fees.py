"""Ücret çapraz kontrolü — beş kapının regresyon testleri.

İlgili: ../scripts/crosscheck_fees.py, ../docs/rapor/zor-vaka-kurleme.md,
        CLAUDE.md §18 yenilikçilik hedefi #2

Bu dosyadaki her sınıf, betiğin İLK KOŞUSUNDA gerçekten görülmüş bir yanlış
pozitifi çitliyor. Desenler gevşetilirse bu testler düşer — amaç tam bu.
Bu depoda gevşek desenin maliyeti iki kez ölçüldü: bir sezgisel 101 belgenin
87'sinde yanlış pozitif üretti, zor-vaka taramasının ilk desen kümesi
`celiskili`yi 476 belgede "buldu" (gerçek: 13).
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import crosscheck_fees as CF


def _korpus(kok: Path, yerlesim: dict[str, str]) -> None:
    """`{"banka/alt/dosya.txt": metin}` -> geçici korpus ağacı."""
    for yol, metin in yerlesim.items():
        p = kok / yol
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(metin, encoding="utf-8")


class TestSayiCozme(unittest.TestCase):
    """TR biçim belirsizliği: nokta hem binlik hem ondalık ayıraç olabilir."""

    def test_ondalik_nokta(self) -> None:
        self.assertAlmostEqual(CF._sayi_coz("%0.5"), 0.5)

    def test_ondalik_virgul(self) -> None:
        self.assertAlmostEqual(CF._sayi_coz("%0,5"), 0.5)

    def test_binlik_nokta(self) -> None:
        self.assertAlmostEqual(CF._sayi_coz("100.000TL"), 100000.0)

    def test_binlik_ve_ondalik_birlikte(self) -> None:
        self.assertAlmostEqual(CF._sayi_coz("1.500,00TL"), 1500.0)

    def test_sayisiz_girdi(self) -> None:
        self.assertIsNone(CF._sayi_coz("Dahil"))


class TestK4Makulluk(unittest.TestCase):
    """K4: tahsis ücreti düzenlenmiş bir kalem — sınır dışı değer reddedilir."""

    def test_bddk_ust_siniri_kabul(self) -> None:
        self.assertTrue(CF.makul_mu("%0,5"))
        self.assertTrue(CF.makul_mu("0.5%"))

    def test_kar_payi_orani_reddedilir(self) -> None:
        """ÖLÇÜLDÜ: Türkiye Finans ürün sayfasında etiketten sonraki ilk yüzde
        %4,09'du ve bu bir KÂR PAYI ORANI. Kapı olmadan rapor "banka %4,09
        tahsis ücreti ilan ediyor" diyordu."""
        self.assertFalse(CF.makul_mu("%4,09"))

    def test_finansman_tutari_reddedilir(self) -> None:
        """ÖLÇÜLDÜ: Vakıf Katılım taşıt oran tablosunda etiketten sonraki ilk
        sayı 100.000 TL — finansman tutarı kolonu, ücret değil."""
        self.assertFalse(CF.makul_mu("100.000TL"))

    def test_gercek_tl_ucreti_kabul(self) -> None:
        # 100.000 TL'nin %0,5'i = 500 TL; tarifede böyle ilan edilebiliyor.
        self.assertTrue(CF.makul_mu("500₺"))

    def test_sifir_reddedilir(self) -> None:
        # %0 bir ücret ilanı değil; `tutarli` yolu metinden anlaşılır.
        self.assertFalse(CF.makul_mu("%0"))


class TestK3BaskaKalem(unittest.TestCase):
    """K3: etiketle değer arasına başka bir ücret kalemi girmemeli."""

    def test_rehin_ucreti_tahsis_sanilmaz(self) -> None:
        """ÖLÇÜLDÜ: "Tahsis Ücreti % 0.5 ... Taşıt Rehin Tesis Ücreti 350.92 TL"
        dizisinde 350,92 tahsis ücreti sanılıyordu."""
        self.assertIsNone(CF._deger_bul("Taşıt Rehin Tesis Ücreti 350.92 TL"))

    def test_dogrudan_deger_gecer(self) -> None:
        self.assertEqual(CF._deger_bul(" Konut Finansmanı %0,5 Hariç"), "%0,5")

    def test_makul_olmayanin_ardindaki_makul_deger_bulunur(self) -> None:
        """İLK sayı değil, ilk MAKUL sayı alınır.

        Oran tablolarında etiketten sonra önce tutar kolonu geliyor:
        "... 100.000 TL 12 Ay ... 500 ₺" — doğru cevap 500 ₺.
        """
        self.assertEqual(CF._deger_bul("100.000 TL 12 Ay %3.50 500 ₺"), "500₺")

    def test_yuzde_TLye_tercih_edilir(self) -> None:
        self.assertEqual(CF._deger_bul("500 ₺ ... %0,5 idir"), "%0,5")


class TestK2HizmetMasrafsizligi(unittest.TestCase):
    """K2: "masrafsız bankacılık" finansman ücreti iddiası DEĞİLDİR."""

    def test_araya_sifat_girse_de_yakalanir(self) -> None:
        """ÖLÇÜLDÜ: Albaraka "masrafsız **bir** bankacılık sunuyoruz" yazıyor;
        bitişik desen bunu kaçırıp iddia sayıyordu."""
        for s in ["masrafsız bankacılık", "masrafsız bir bankacılık",
                  "Masrafsız bankacılık ile Havale, EFT, FAST"]:
            self.assertIsNotNone(CF._HIZMET_MASRAFSIZ_RE.match(s), s)

    def test_finansman_iddiasi_dislanmaz(self) -> None:
        self.assertIsNone(
            CF._HIZMET_MASRAFSIZ_RE.match("masrafsız konut finansmanı"))


class TestK1Yakinlik(unittest.TestCase):
    """K1: iddia ürün sözcüğüne YAKIN olmalı."""

    def test_uzak_urun_bahsi_iddia_sayilmaz(self) -> None:
        """ÖLÇÜLDÜ: gevşek pencerede "masrafsız bir bankacılık sunuyoruz"
        cümlesi, 100+ karakter öteki "finansal ihtiyaçlarına" ifadesindeki
        `ihtiyaç` sözcüğüne takılıp İhtiyaç Finansmanı iddiası sayılıyordu."""
        metin = ("Albaraka olarak müşterilerimizin finansal ihtiyaçlarına "
                 "çözüm üretmenin tutkusuyla, yıllardır süregelen köklü "
                 "tecrübemizle ve genç kadromuzla masrafsız bir bankacılık "
                 "sunuyoruz.")
        with tempfile.TemporaryDirectory() as td:
            kok = Path(td)
            _korpus(kok, {"albaraka/live/hakkimizda.txt": metin})
            self.assertEqual(CF.masrafsizlik_iddialari(str(kok)), [])

    def test_bitisik_iddia_yakalanir(self) -> None:
        metin = "Kampanya avantajları: Dosya Masrafsız Konut Finansmanı."
        with tempfile.TemporaryDirectory() as td:
            kok = Path(td)
            _korpus(kok, {"vakif/live/paket.txt": metin})
            iddialar = CF.masrafsizlik_iddialari(str(kok))
            self.assertEqual(len(iddialar), 1)
            self.assertEqual(iddialar[0].urunler, ["konut"])


class TestKosulDaraltmasi(unittest.TestCase):
    """Ayırt etmeyen ifadeler koşul SAYILMAZ."""

    def test_kanal_ve_kampanya_ifadeleri_kosul_degil(self) -> None:
        for s in ["kampanya kapsamında", "mobil üzerinden", "dijital kanal"]:
            self.assertIsNone(CF._KOSUL_RE.search(s), s)

    def test_belirleyici_kosullar_yakalanir(self) -> None:
        for s in ["yeni müşterilere", "31/12/2025 tarihine kadar",
                  "İlk 6 ay", "100.000 TL ve üzeri"]:
            self.assertIsNotNone(CF._KOSUL_RE.search(s), s)


class TestK5AyniBelge(unittest.TestCase):
    """K5: iddia, kendi belgesindeki ücret kaydıyla eşleştirilmez.

    Kontrol belgeler ARASI olmak zorunda — zor-vaka ölçümü belge içi çelişkinin
    korpusta pratik olarak bulunmadığını gösterdi (13 adayın 12'si ücret
    tarifesiydi ve hiçbiri çelişki değildi).
    """

    IDDIA = CF.Iddia(banka="x", doc_id="x--a", kaynak_dosya="x/products/a.txt",
                     urunler=["konut"], iddia_alinti="masrafsız konut")

    def test_kendi_belgesi_kaynak_sayilmaz(self) -> None:
        ucret = CF.IlanEdilenUcret(banka="x", urun="konut", deger="%0,5",
                                   kaynak_dosya="x/products/a.txt",
                                   kaynak_alinti="Tahsis Ücreti %0,5")
        rows = CF.crosscheck([self.IDDIA], [ucret])
        self.assertEqual(rows[0].sonuc, CF.V_TARIFE_YOK)

    def test_baska_belge_kaynak_sayilir(self) -> None:
        ucret = CF.IlanEdilenUcret(banka="x", urun="konut", deger="%0,5",
                                   kaynak_dosya="x/docs/tarife.txt",
                                   kaynak_alinti="Tahsis Ücreti %0,5")
        rows = CF.crosscheck([self.IDDIA], [ucret])
        self.assertEqual(rows[0].sonuc, CF.V_KAPSAMSIZ)


class TestBirimFarkiTutarsizlikDegil(unittest.TestCase):
    """Yan bulgu bölümü: yalnız AYNI BİRİMDEKİ çatışma tutarsızlıktır.

    Bu bölümün ilk hâli `%0,5` ile `500 ₺`yi çatışma sayıyordu; oysa 500 TL,
    100.000 TL'nin %0,5'idir — birim farkı, tutarsızlık değil.
    """

    def _ucret(self, deger: str, dosya: str) -> CF.IlanEdilenUcret:
        return CF.IlanEdilenUcret(banka="b", urun="tasit", deger=deger,
                                  kaynak_dosya=dosya, kaynak_alinti="Tahsis")

    def test_yuzde_ve_TL_catismaz(self) -> None:
        rapor = CF.render_report(
            [], [self._ucret("%0,5", "a.txt"), self._ucret("500₺", "b.txt")], 1)
        self.assertNotIn("Banka içi tutarsızlık", rapor)

    def test_ayni_birimde_farkli_oran_catisir(self) -> None:
        rapor = CF.render_report(
            [], [self._ucret("%0,5", "a.txt"), self._ucret("0.1%", "b.txt")], 1)
        self.assertIn("Banka içi tutarsızlık", rapor)
        self.assertIn("`b` / `tasit`", rapor)

    def test_bicim_varyanti_catisma_degil(self) -> None:
        """`%0,5` = `0.5%` = `%0.5` — aynı sayı, farklı yazım."""
        rapor = CF.render_report(
            [], [self._ucret("%0,5", "a.txt"), self._ucret("0.5%", "b.txt"),
                 self._ucret("%0.5", "c.txt")], 1)
        self.assertNotIn("Banka içi tutarsızlık", rapor)


class TestSiniflandirma(unittest.TestCase):
    """Dört sonuç sınıfı doğru ayrışıyor mu."""

    UCRET = CF.IlanEdilenUcret(banka="x", urun="konut", deger="%0,5",
                               kaynak_dosya="x/docs/tarife.txt",
                               kaynak_alinti="Tahsis Ücreti Konut %0,5 Hariç")

    def _iddia(self, kosullar: list[str]) -> CF.Iddia:
        return CF.Iddia(banka="x", doc_id="x--k", kaynak_dosya="x/live/k.txt",
                        urunler=["konut"], iddia_alinti="Dosya Masrafsız Konut",
                        kosullar=kosullar)

    def test_kosullu_muafiyet(self) -> None:
        row = CF.crosscheck([self._iddia(["yeni müşterilere"])],
                            [self.UCRET])[0]
        self.assertEqual(row.sonuc, CF.V_KOSULLU)
        # Dashboard'da "masrafsız" TEK BAŞINA yazılmamalı — §17 adil kıyas.
        self.assertIn("aksi hâlde", row.dashboard_ifadesi)
        self.assertIn("%0,5", row.dashboard_ifadesi)

    def test_kapsamsiz_iddia(self) -> None:
        row = CF.crosscheck([self._iddia([])], [self.UCRET])[0]
        self.assertEqual(row.sonuc, CF.V_KAPSAMSIZ)

    def test_tarifede_ucret_alinmiyorsa_tutarli(self) -> None:
        sifir = CF.IlanEdilenUcret(
            banka="x", urun="konut", deger="%0,5",
            kaynak_dosya="x/docs/t.txt",
            kaynak_alinti="Konut Finansmanı Tahsis Ücreti alınmaz")
        row = CF.crosscheck([self._iddia([])], [sifir])[0]
        self.assertEqual(row.sonuc, CF.V_TUTARLI)

    def test_tarife_yoksa_isaretlenir_atlanmaz(self) -> None:
        """Kapsam boşluğu SESSİZCE atlanmaz — satır üretilir, işaretlenir.

        Sessiz kırpma "her şey kapsandı" gibi okunur; oysa kapsamı büyütmenin
        yolu hasattır, kod değil.
        """
        row = CF.crosscheck([self._iddia([])], [])[0]
        self.assertEqual(row.sonuc, CF.V_TARIFE_YOK)
        self.assertIn("bağımsız kaynak eksik", row.not_)


class TestUctanUca(unittest.TestCase):
    """Geçici korpus üzerinde tüm hat."""

    def test_kampanya_tarife_esleser(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            kok = Path(td)
            _korpus(kok, {
                "banka/docs/ucret-tablosu.txt":
                    "Bireysel Krediler Tahsis Ücreti Konut Finansmanı 0.5% "
                    "Hariç 01/04/2020 Ekspertiz Ücreti 23.645 TL Dahil",
                "banka/live/kampanya.txt":
                    "Yeni müşterilerimize Dosya Masrafsız Konut Finansmanı! "
                    "Kampanya 31/12/2026 tarihine kadar geçerlidir.",
            })
            ucretler = CF.ilan_edilen_ucretler(str(kok))
            iddialar = CF.masrafsizlik_iddialari(str(kok))
            rows = CF.crosscheck(iddialar, ucretler)

            self.assertEqual([(u.urun, u.deger) for u in ucretler],
                             [("konut", "0.5%")])
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].sonuc, CF.V_KOSULLU)
            self.assertEqual(rows[0].doc_id, "banka--kampanya")

    def test_rapor_uretilir_ve_kapsami_bildirir(self) -> None:
        rows = [CF.Row(banka="x", doc_id="x--a", urun="konut",
                       sonuc=CF.V_TARIFE_YOK, iddia_alinti="masrafsız")]
        rapor = CF.render_report(rows, [], 0)
        self.assertIn("Kapsam boşluğu", rapor)
        self.assertIn("`x` / `konut`", rapor)

    def test_csv_alanlari_sabit(self) -> None:
        """Kolon adı değişirse anotasyoncunun şablonu bozulur."""
        for ad in ("banka", "doc_id", "urun_sinifi", "sonuc",
                   "iddia_alintisi", "ilan_edilen_tahsis_ucreti",
                   "muafiyet_kosulu", "ilan_kaynagi", "dashboard_ifadesi"):
            self.assertIn(ad, CF.CSV_ALANLARI)


class TestAnotasyonKorumasi(unittest.TestCase):
    """Çıktı, insan kararını taşıyan dosyalara DOKUNMAZ."""

    def test_gold_value_kolonu_uretilmez(self) -> None:
        """`gold_value` insanın kararı; makine önerisini oraya yazmak
        değerlendirmeyi kendi kendini doğrulayan bir döngüye sokar."""
        self.assertNotIn("gold_value", CF.CSV_ALANLARI)

    def test_cikti_anotasyon_dizinine_yazmaz(self) -> None:
        """Varsayılan çıktı `data/gold/review/` ALTINDA olamaz.

        Orada insanın doldurduğu `round*.csv` dosyaları duruyor; oraya yazan
        bir betik anotasyonu ezme riskini taşır.
        """
        with tempfile.TemporaryDirectory() as td:
            kok = Path(td)
            _korpus(kok, {"b/live/k.txt": "Dosya Masrafsız Konut Finansmanı"})
            cikti = kok / "cikti.csv"
            rapor = kok / "rapor.md"
            kod = CF.main(["--raw-dir", str(kok), "--out", str(cikti),
                           "--report", str(rapor)])
            self.assertEqual(kod, 0)
            self.assertTrue(cikti.is_file())
            self.assertTrue(rapor.is_file())

    def test_varsayilan_cikti_review_altinda_degil(self) -> None:
        for yol in (CF.VARSAYILAN_CSV, CF.VARSAYILAN_RAPOR):
            self.assertNotIn("review", yol.split("/"))


if __name__ == "__main__":
    unittest.main()
