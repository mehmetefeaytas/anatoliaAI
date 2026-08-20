"""Kanıt-tazeliği kapısı — ölçemediğini "uyumlu" saymaz.

İlgili: ../scripts/kanit_tazeligi.py

Bu dosyanın koruduğu beş şey:

1. **TR sayı biçimi.** `2.631` binlik, `0,452` ondalık. Karıştırmak `0,452`yi
   452 yapar — kapı sessizce her şeyi sapma sanır ya da hiçbirini görmez.
2. **Ölçülemeyen SAPMA DEĞİLDİR, ama TAMAM da değildir.** Kanıt üretilemiyorsa
   sonuç `kanit_yok` olmalı. `tamam` saymak kapının varlık sebebini siler:
   ölçemediğimiz bir sayıyı doğrulanmış gibi göstermek, tam da kapatmak için
   var olduğu hatanın kendisidir.
3. **Bayat kanıt kanıt değildir.** Başka bir gold'dan ya da kirli ağaçtan
   üretilmiş rapor reddedilmeli — sayı tesadüfen tutsa bile.
4. **Şeması farklı rapor sessizce okunmaz.** Ablasyon raporu aynı gold'dan
   üretilmiş olabilir ama tek-kol metriği taşımaz; elenmezse yanlış sayı okunur.
5. **Tanımsız oran uydurulmaz.** Gold'da hiç `absent` kararı yoksa halüsinasyon
   oranının paydası sıfırdır; `0,0` yazmak yalan olur (CLAUDE.md §19).
6. **Proza tablo kadar denetlenir — ama gürültüye boğulmadan.** Kapı 2026-08-16'ya
   kadar yalnız TABLO HÜCRESİNE bakıyordu; cümle içinde duran bayat sayı kör
   noktadaydı. Kör nokta kapatılırken ikinci bir tuzak açılır: prozadaki her
   sayıyı denetlemek (sürüm, tarih, satır no, madde no, port, örneklem) kapıyı
   kullanılamaz kılar. Bu yüzden aşağıdaki testler **hem yakalamayı hem
   yakalamamayı** doğrular; ikisinden biri düşerse mekanizma çöker.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import kanit_tazeligi as K
from tests._ortam_gereksinimleri import git_gerekir


class TestTrSayi(unittest.TestCase):
    def test_binlik_ayirici(self) -> None:
        self.assertEqual(K.tr_sayi("2.631"), 2631.0)
        self.assertEqual(K.tr_sayi("1.782"), 1782.0)

    def test_ondalik_virgul(self) -> None:
        self.assertEqual(K.tr_sayi("0,452"), 0.452)
        self.assertEqual(K.tr_sayi("0,059"), 0.059)

    def test_yuzde_isareti_atilir(self) -> None:
        self.assertAlmostEqual(K.tr_sayi("%3,9"), 3.9)

    def test_nokta_ondalik_bozulmaz(self) -> None:
        """`0.452` binlik SANILMAMALI — tam kısmı "0", binlik grubu olamaz."""
        self.assertEqual(K.tr_sayi("0.452"), 0.452)

    def test_dort_haneli_binliksiz(self) -> None:
        self.assertEqual(K.tr_sayi("2000"), 2000.0)

    def test_sayi_olmayan_hata_verir(self) -> None:
        with self.assertRaises(ValueError):
            K.tr_sayi("bir hayli")


class TestYazTr(unittest.TestCase):
    def test_tam_sayi_binlikli(self) -> None:
        self.assertEqual(K.yaz_tr(2777.0), "2.777")

    def test_ondalik_virgulle(self) -> None:
        self.assertEqual(K.yaz_tr(0.452), "0,452")


class _RaporTemeli(unittest.TestCase):
    """Sahte `eval/reports` ağacı — gerçek sözleşmenin aynısı."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self._tmp.name)
        (self.kok / "data" / "gold").mkdir(parents=True)
        (self.kok / "eval" / "reports").mkdir(parents=True)
        self.gold = self.kok / "data" / "gold" / "gold.test.json"
        self.gold.write_text(json.dumps([{"id": "a"}]), encoding="utf-8")
        self._yamalar = [mock.patch.object(K, "KOK", self.kok),
                         mock.patch.object(K, "DEPO", self.kok)]
        for y in self._yamalar:
            y.start()

    def tearDown(self) -> None:
        for y in self._yamalar:
            y.stop()
        self._tmp.cleanup()

    def _rapor(self, ad: str, *, gold_sha: str | None = None, kirli: bool = False,
               matchers: list[str] | None = None, ablasyon: bool = False,
               tn: int = 10, uydurma: int = 1, f1: float = 0.75,
               zaman: str = "2026-08-15T00:00:00+00:00") -> Path:
        d = self.kok / "eval" / "reports" / ad
        d.mkdir()
        (d / "env.json").write_text(json.dumps({
            "gold_sha256": gold_sha if gold_sha is not None
            else K.sha256_dosya(self.gold),
            "git_dirty": kirli,
            "created_utc": zaman,
            "extra": {"bootstrap_resamples": 1000},
        }), encoding="utf-8")
        if ablasyon:
            govde: dict = {"kind": "ablation", "arms": [], "comparisons": []}
        else:
            govde = {"results": [
                {"matcher": m,
                 "macro_f1": 0.6,
                 "micro_f1_kalem": 0.7,
                 "micro": {"f1": f1, "tn": tn, "fp_hallucinated": uydurma}}
                for m in (matchers or ["strict"])]}
        (d / "metrics.json").write_text(json.dumps(govde), encoding="utf-8")
        return d


class TestTazelikKapisi(_RaporTemeli):
    def test_ayni_golddan_uretilmis_rapor_KABUL(self) -> None:
        self._rapor("20260815-000000")
        rapor = K.taze_rapor("gold.test.json", "strict")
        self.assertEqual(rapor.dizin.name, "20260815-000000")

    def test_BASKA_golddan_uretilmis_rapor_RED(self) -> None:
        """Doğru sayıyı taşısa bile başka gold'dan gelen rapor kanıt değildir."""
        self._rapor("20260815-000000", gold_sha="0" * 64)
        with self.assertRaises(K.KanitYok) as ctx:
            K.taze_rapor("gold.test.json", "strict")
        self.assertIn("ölçüm raporu yok", str(ctx.exception))

    def test_KIRLI_agacta_uretilmis_rapor_RED(self) -> None:
        self._rapor("20260815-000000", kirli=True)
        with self.assertRaises(K.KanitYok) as ctx:
            K.taze_rapor("gold.test.json", "strict")
        self.assertIn("git_dirty", str(ctx.exception))

    def test_ablasyon_raporu_tek_kol_metrigi_icin_ELENIR(self) -> None:
        """Aynı gold'dan üretilmiş ama `results` şeması yok — sessiz okunamaz."""
        self._rapor("20260815-120000", ablasyon=True)
        with self.assertRaises(K.KanitYok):
            K.taze_rapor("gold.test.json", "strict")

    def test_ablasyon_varken_ESKI_gecerli_rapor_secilir(self) -> None:
        self._rapor("20260814-000000", zaman="2026-08-14T00:00:00+00:00")
        self._rapor("20260815-120000", ablasyon=True,
                    zaman="2026-08-15T12:00:00+00:00")
        self.assertEqual(K.taze_rapor("gold.test.json", "strict").dizin.name,
                         "20260814-000000")

    def test_en_yeni_gecerli_rapor_secilir(self) -> None:
        self._rapor("20260814-000000", zaman="2026-08-14T00:00:00+00:00")
        self._rapor("20260815-000000", zaman="2026-08-15T00:00:00+00:00")
        self.assertEqual(K.taze_rapor("gold.test.json", "strict").dizin.name,
                         "20260815-000000")

    def test_gold_dosyasi_yoksa_KanitYok(self) -> None:
        with self.assertRaises(K.KanitYok):
            K.taze_rapor("olmayan.json", "strict")


class TestMetrikOkuma(_RaporTemeli):
    def test_mikro_f1_okunur(self) -> None:
        self._rapor("20260815-000000", f1=0.452)
        self.assertAlmostEqual(K.olc_metrik("gold.test.json", "mikro_f1")(), 0.452)

    def test_halusinasyon_orani_dogru_paydayla(self) -> None:
        self._rapor("20260815-000000", tn=444, uydurma=28)
        self.assertAlmostEqual(
            K.olc_metrik("gold.test.json", "halusinasyon")(), 28 / 472)

    def test_absent_karari_YOKSA_oran_TANIMSIZ(self) -> None:
        """Payda sıfırken 0,0 yazmak yalandır — kapı bunu KanitYok sayar."""
        self._rapor("20260815-000000", tn=0, uydurma=0)
        with self.assertRaises(K.KanitYok) as ctx:
            K.olc_metrik("gold.test.json", "halusinasyon")()
        self.assertIn("TANIMSIZ", str(ctx.exception))

    def test_bilinmeyen_anahtar_sessiz_gecmez(self) -> None:
        self._rapor("20260815-000000")
        with self.assertRaises(K.KanitYok):
            K.olc_metrik("gold.test.json", "uydurma_anahtar")()


class TestDenetim(_RaporTemeli):
    def _iddia(self, olcer, desen=r"deger: ([\d,.]+)") -> K.Iddia:
        (self.kok / "BELGE.md").write_text("deger: 1.782\n", encoding="utf-8")
        return K.Iddia(ad="deneme", aciklama="test",
                       desenler=(("BELGE.md", desen),),
                       olcer=olcer, tolerans=0.5)

    def test_uyumlu_sayi_TAMAM(self) -> None:
        iddia = self._iddia(lambda: 1782.0)
        with mock.patch.object(K, "iddialar", lambda: [iddia]):
            (s,) = K.denetle()
        self.assertEqual(s.durum, "tamam")

    def test_sapan_sayi_dosya_ve_satirla_bildirilir(self) -> None:
        iddia = self._iddia(lambda: 1774.0)
        with mock.patch.object(K, "iddialar", lambda: [iddia]):
            (s,) = K.denetle()
        self.assertEqual(s.durum, "sapma")
        self.assertEqual(s.sapmalar[0]["dosya"], "BELGE.md")
        self.assertEqual(s.sapmalar[0]["satir"], 1)
        self.assertEqual(s.sapmalar[0]["yazan"], "1.782")

    def test_OLCULEMEYEN_tamam_SAYILMAZ(self) -> None:
        """Kapının en kritik davranışı: ölçemediğini doğrulanmış sayma."""
        def _patlat() -> float:
            raise K.KanitYok("ölçüm artefaktı yok")

        iddia = self._iddia(_patlat)
        with mock.patch.object(K, "iddialar", lambda: [iddia]):
            (s,) = K.denetle()
        self.assertEqual(s.durum, "kanit_yok")
        self.assertNotEqual(s.durum, "tamam")

    def test_belgede_gecmeyen_iddia_olcum_KOSTURMAZ(self) -> None:
        """Yayımlanmamış bir sayı için pahalı ölçüm koşulmaz."""
        cagrildi = []

        def _olcer() -> float:
            cagrildi.append(1)
            return 0.0

        iddia = K.Iddia(ad="yok", aciklama="", desenler=(("BELGE.md", r"asla(x)"),),
                        olcer=_olcer)
        with mock.patch.object(K, "iddialar", lambda: [iddia]):
            (s,) = K.denetle()
        self.assertEqual(s.durum, "tamam")
        self.assertEqual(cagrildi, [])

    def test_cikis_kodu_sapmada_1_kanit_yoksa_2(self) -> None:
        with mock.patch.object(K, "iddialar", lambda: [self._iddia(lambda: 1774.0)]):
            self.assertEqual(K.main(["--json"]), K.CIKIS_SAPMA)

        def _patlat() -> float:
            raise K.KanitYok("yok")

        with mock.patch.object(K, "iddialar", lambda: [self._iddia(_patlat)]):
            self.assertEqual(K.main(["--json"]), K.CIKIS_KANIT_YOK)

        with mock.patch.object(K, "iddialar", lambda: [self._iddia(lambda: 1782.0)]):
            self.assertEqual(K.main(["--json"]), K.CIKIS_TEMIZ)


class TestProzadakiBayatSayi(_RaporTemeli):
    """Kapının kör noktası: tablo hücresi denetleniyor, cümle içi denetlenmiyordu.

    Gerçek olay (2026-08-16): `app/README.md` tablosu 12-alan mikro-F1'i **0,464**
    yazarken aynı belgenin iki cümlesi hâlâ **0,452** diyordu; kapı "0 sapma"
    yeşil yanıyordu. Yani kapı, korumak için var olduğu hatanın yanından geçti.
    """

    def _belge(self, govde: str) -> K.Iddia:
        (self.kok / "BELGE.md").write_text(govde, encoding="utf-8")
        return K.Iddia(
            ad="deneme", aciklama="test",
            desenler=(("BELGE.md", r"mikro-F1 \| \*{0,2}([\d,]+)"),),
            olcer=lambda: 0.464)

    def test_TABLO_ve_PROZA_birlikte_yakalanir(self) -> None:
        """Tek belge, iki yayım biçimi: hücre doğru, cümle bayat."""
        iddia = self._belge(
            "| mikro-F1 | 0,464 |\n"
            "Bu sayı 12 Ağustos'takinden iyidir (0,452 → 0,464).\n"
            "Yukarıdaki 0,452 gold.v2 üzerinde ölçüldü.\n"
            "GA'lar daralınca 0,452 savunulabilir hâle gelir.\n")
        with mock.patch.object(K, "iddialar", lambda: [iddia]):
            (s,) = K.denetle()
        self.assertEqual(s.durum, "sapma")
        self.assertEqual([(d["satir"], d["yazan"]) for d in s.sapmalar],
                         [(3, "0,452"), (4, "0,452")])

    def test_ILAN_SATIRI_bayat_sayilmaz(self) -> None:
        """`0,452 → 0,464` yazmak tarihçedir; onu sapma saymak yazarı susturur."""
        iddia = self._belge(
            "| mikro-F1 | 0,464 |\n"
            "Ölçüm iyileşti: 0,452 → 0,464.\n")
        with mock.patch.object(K, "iddialar", lambda: [iddia]):
            (s,) = K.denetle()
        self.assertEqual(s.durum, "tamam", f"yanlış pozitif: {s.sapmalar}")

    def test_ILAN_YOKSA_prozadaki_sayi_denetlenmez(self) -> None:
        """Kural açık: belge bir değeri kendi geçersiz ilan etmediyse dokunulmaz.

        Yoksa kapı, belgedeki her ondalığı bir metrik sanardı.
        """
        iddia = self._belge(
            "| mikro-F1 | 0,464 |\n"
            "makro-F1 0,601 · kalem düzeyi 0,381 · κ 0,302 · RAG R@5 0,867\n")
        with mock.patch.object(K, "iddialar", lambda: [iddia]):
            (s,) = K.denetle()
        self.assertEqual(s.durum, "tamam", f"yanlış pozitif: {s.sapmalar}")

    def test_CIPLAK_TAM_SAYI_supurulmez(self) -> None:
        """`app/README.md` "halüsinasyonu 60 → 53 düşürüyor" gerçek tuzağı.

        53 bugünkü `test_atlandi` ölçümüdür. Çıplak tam sayı süpürülseydi kural
        60'ı "bayat" ilan eder ve belgedeki her 60'ı işaretlerdi — 60 ise
        belgede vade, yüzde, kayıt sayısı olarak sürekli geçer.
        """
        (self.kok / "BELGE.md").write_text(
            "| atlanan | 53 |\n"
            "Halüsinasyonu 60 → 53 düşürüyor.\n"
            "Vade 60 aya kadar; 60 belgede doğrulandı.\n", encoding="utf-8")
        iddia = K.Iddia(ad="atlandi", aciklama="",
                        desenler=(("BELGE.md", r"atlanan \| (\d+)"),),
                        olcer=lambda: 53.0, tolerans=0.5)
        with mock.patch.object(K, "iddialar", lambda: [iddia]):
            (s,) = K.denetle()
        self.assertEqual(s.durum, "tamam", f"yanlış pozitif: {s.sapmalar}")

    def test_SURUM_TARIH_SATIR_MADDE_PORT_yanlis_pozitif_uretmez(self) -> None:
        """Belgedeki her sayı bir ölçüm iddiası değildir."""
        iddia = self._belge(
            "| mikro-F1 | 0,464 |\n"
            "Düzeltme: 0,452 → 0,464.\n"
            "Kılavuz v1.452 → v2; port 8.452; §4.452/8; 2026-08-16; "
            "bkz. README.md:452 ve 0,4521 ile 10,452.\n")
        with mock.patch.object(K, "iddialar", lambda: [iddia]):
            (s,) = K.denetle()
        # `v1.452`, `8.452`, `4.452`, `:452`, `0,4521`, `10,452` — hiçbiri
        # ayrışık bir `0,452` değildir.
        self.assertEqual(s.durum, "tamam", f"yanlış pozitif: {s.sapmalar}")

    def test_ayni_satirda_ilan_ve_kalinti_birlikte(self) -> None:
        """İlanı maskelemek satırın tamamını affetmez."""
        iddia = self._belge(
            "| mikro-F1 | 0,464 |\n"
            "0,452 → 0,464 oldu ama aşağıda hâlâ 0,452 yazıyor.\n")
        with mock.patch.object(K, "iddialar", lambda: [iddia]):
            (s,) = K.denetle()
        self.assertEqual([(d["satir"], d["yazan"]) for d in s.sapmalar],
                         [(2, "0,452")])

    def test_kapsam_desenlerden_turer_ve_ayrisamaz(self) -> None:
        """Denetim listesi ile proza listesi tek kaynaktan gelir."""
        iddia = K.Iddia(
            ad="x", aciklama="",
            desenler=(("A.md", r"(\d+)"), ("B.md", r"(\d+)"), ("A.md", r"x(\d+)")),
            olcer=lambda: 1.0)
        self.assertEqual(iddia.kapsam(), ("A.md", "B.md"))


class TestGercekIddiaListesi(unittest.TestCase):
    """Liste bozulursa kapı sessizce hiçbir şey denetlemez."""

    def test_iddialar_bos_degil_ve_adlar_tekil(self) -> None:
        adlar = [i.ad for i in K.iddialar()]
        self.assertGreaterEqual(len(adlar), 8)
        self.assertEqual(len(adlar), len(set(adlar)), "yinelenen iddia adı")

    def test_her_desenin_tek_yakalama_grubu_var(self) -> None:
        import re as _re
        for iddia in K.iddialar():
            for dosya, desen in iddia.desenler:
                with self.subTest(iddia=iddia.ad, dosya=dosya):
                    self.assertEqual(
                        _re.compile(desen).groups, 1,
                        "desen tam bir yakalama grubu içermeli")

    def test_metrik_iddialari_HER_IKI_README_i_kapsar(self) -> None:
        """`app/README.md` aynı metrikleri yayımlıyor; denetim dışı kalamaz.

        Kapsam `desenler`den türediği için bu aynı zamanda proza taramasının
        o belgeyi gördüğünü de garanti eder.
        """
        for ad in ("v2_mikro_f1", "v2_halusinasyon"):
            iddia = next(i for i in K.iddialar() if i.ad == ad)
            with self.subTest(iddia=ad):
                # Kapsam DARALAMAZ ama genişleyebilir: 19 Ağustos'ta sunum
                # HTML'i de bu iki iddiaya eklendi. Eşitlik aramak, kapsamı
                # büyüten bir iyileştirmeyi test hatası gibi gösterirdi.
                self.assertLessEqual(
                    {"README.md", "app/README.md"}, set(iddia.kapsam()))

    def test_halusinasyon_deseni_PAYDA_hucresini_ORAN_sanmaz(self) -> None:
        """Ölçülmüş yanlış pozitif: `**444**` paydadır, halüsinasyon oranı değil."""
        import re as _re
        satir = "| `absent` kararı (halüsinasyon paydası) | **444** | **60** |"
        iddia = next(i for i in K.iddialar() if i.ad == "v2_halusinasyon")
        for _, desen in iddia.desenler:
            with self.subTest(desen=desen):
                self.assertIsNone(_re.compile(desen).search(satir))

    def test_banka_sayaci_semsiye_kurulusu_saymaz(self) -> None:
        """TKBB katılım bankası değildir; README de ikisini ayrı sayıyor."""
        self.assertEqual(K.olc_banka_sayisi(), 10.0)



class TestDesenlerGERCEKTEN_Yakaliyor(unittest.TestCase):
    """Yazılmış her desen, işaret ettiği belgede GERÇEKTEN bir şey yakalıyor mu.

    ## Neden bu test var

    Kapının en tehlikeli arıza biçimi gürültülü değil SESSİZ olanıdır: bir
    desen bozulur (belge yeniden yazılır, biçim değişir, bir `<em>` eklenir)
    ve o iddia denetim dışı kalır. Kapı yine "0 sapma" der, kimse fark etmez
    ve korunduğu sanılan sayı bayatlar.

    Bu tam olarak 19 Ağustos'ta yaşandı. Sunum HTML'i kapsama alındıktan
    sonra elle bir sapma yaratıldı (0,477 -> 0,999) ve kapı **ateşlenmedi**;
    sebebi kirli ağaçta kanıtın reddedilmesiydi, ama arıza tablosu bir desen
    hatasınınkiyle BİREBİR aynı görünüyordu. İki durumu ayırt edecek bir
    ölçüt yoktu.

    ## Neden iddia başına değil BELGE başına

    Bir iddia birden çok belgeyi kapsar (kök README, app README, sunum).
    Yalnız "toplam eşleşme > 0" denetlenirse, üç belgeden biri bozulduğunda
    diğer ikisi testi yeşil tutar — yani asıl korunmak istenen şey, tam da
    gözden kaçan şey olur.
    """

    def test_her_desen_kendi_belgesinde_esleme_veriyor(self) -> None:
        eksik: list[str] = []
        for iddia in K.iddialar():
            for belge in iddia.kapsam():
                if not [x for x in iddia.belgedeki() if x[0] == belge]:
                    eksik.append(f"{iddia.ad} · {belge}")
        self.assertEqual(
            eksik, [],
            "şu desenler işaret ettikleri belgede hiçbir şey yakalamıyor "
            "(iddia sessizce denetim dışı kalmış): " + ", ".join(eksik))

    def test_kapsam_desenlerden_TURETILIYOR(self) -> None:
        """`kapsam()` ayrı bir liste olsaydı desenlerle ayrışabilirdi."""
        for iddia in K.iddialar():
            self.assertEqual(
                set(iddia.kapsam()), {d for d, _ in iddia.desenler},
                f"{iddia.ad}: kapsam ile desen listesi ayrışmış")

    def test_sunum_BES_iddiada_kapsamda(self) -> None:
        """Sunum yayımlanan bir belgedir ve 19 Ağustos'ta kapsama alındı.

        Kapsamdan çıkarılırsa bu test düşer — sunumun sayıları bir kez daha
        iki sürüm geride kalmasın (o gün 2.946 test / 0,464 F1 yazıyordu).

        20 Ağustos'ta iki iddia eklendi: sunum yapısal mikro-F1'i ve κ'yı da
        yayımlıyordu, ikisi de denetim dışıydı ve **ikisi de bayatlamıştı**
        (0,717 ve 0,700).
        """
        kapsayan = [i.ad for i in K.iddialar()
                    if any("docs/sunum" in k for k in i.kapsam())]
        self.assertEqual(
            sorted(kapsayan),
            ["kappa_ikinci_tur", "test_gecti", "v2_halusinasyon",
             "v2_mikro_f1", "v2_yapisal_mikro_f1"],
            "sunumu denetleyen iddia kümesi değişmiş")

    def test_kappa_iddiasi_KAYITLI(self) -> None:
        """κ, kapının 20 Ağustos'ta ölçülen kör noktasıydı.

        README **0,700** yayımlıyordu, gerçek değer **0,714**'tü ve kapı
        ateşlenmedi — çünkü `iddialar()` içinde κ diye bir satır YOKTU.
        Bu test o satırın silinmesini engeller: iddia kaybolursa κ sessizce
        denetim dışına düşer ve aynı sapma tekrar eder.
        """
        adlar = {i.ad for i in K.iddialar()}
        self.assertIn("kappa_ikinci_tur", adlar)

    def test_kappa_deseni_HER_belgede_esliyor(self) -> None:
        """κ üç belgede yayımlanıyor; üçü de ayrı ayrı denetlenmeli.

        Yalnız "toplam eşleşme > 0" yeterli olsaydı, kök README'nin κ satırı
        biçim değiştirdiğinde app README'nin deseni testi yeşil tutardı.
        """
        (iddia,) = [i for i in K.iddialar() if i.ad == "kappa_ikinci_tur"]
        for belge in iddia.kapsam():
            with self.subTest(belge=belge):
                self.assertTrue(
                    [x for x in iddia.belgedeki() if x[0] == belge],
                    f"{belge}: κ deseni hiçbir şey yakalamıyor")

    def test_kappa_tek_deger_yayimliyor(self) -> None:
        """Üç belgedeki κ geçişlerinin HEPSİ aynı sayıyı söylemeli.

        Kapının değer denetimi ölçülen değere karşı koşar; bu test ondan
        bağımsız olarak belgeler arası TUTARLILIĞI korur. 0,700 sapması tam
        buradan girdi: bir belge güncellendi, diğerleri kalmadı.
        """
        (iddia,) = [i for i in K.iddialar() if i.ad == "kappa_ikinci_tur"]
        degerler = {ham for _, _, ham in iddia.belgedeki()}
        self.assertEqual(
            len(degerler), 1,
            f"κ belgeler arasında ayrışmış: {sorted(degerler)}")

    def test_yayimlanan_UC_gorunum_de_denetimde(self) -> None:
        """İkili · kalem · yapısal — üçü birden yayımlanıyor, üçü de gated.

        `kampanya_kosullari` ikili 0,000 alıyor ama kalem düzeyinde 0,520;
        bu yüzden üç görünüm yan yana yayımlanıyor. Biri denetim dışı
        kalırsa "kötü sayıyı saklamıyoruz" iddiası mekanizmasız kalır.
        """
        adlar = {i.ad for i in K.iddialar()}
        for ad in ("v2_mikro_f1", "v2_kalem_mikro_f1", "v2_yapisal_mikro_f1"):
            self.assertIn(ad, adlar)


if __name__ == "__main__":
    unittest.main()


@git_gerekir
class TestKodTazeligi(unittest.TestCase):
    """Gold'un sha'sı aynı kalsa da DEĞİŞMİŞ bir çıkarıcı başka F1 üretir.

    GERÇEK depoda koşar (`_RaporTemeli` DEPO'yu geçici bir dizine yamalar ve
    orası git deposu değildir).

    2026-08-15'te yaşandı: R3 güven skorlarını değiştirdi. Bu denetim
    olmasaydı kapı, eski koddan üretilmiş bir raporu "kanıt" sayıp bayat
    bir sayıyı onaylayacaktı — hem de tam da bunu önlemek için var olduğu
    hâlde.
    """

    def test_olcum_suzgeci_rapor_dizinini_dislar(self) -> None:
        s = K._olcum_suzgeci()
        self.assertIn("app/src", s)
        self.assertIn("app/eval", s)
        self.assertTrue(any(x.startswith(":(exclude)") for x in s),
                        "eval/reports dışlanmazsa her rapor kendi kendini "
                        "bayat yapar")

    def test_bilinmeyen_commit_gerekce_dondurur(self) -> None:
        self.assertIsNotNone(K._kod_degisti_mi("0" * 40))

    def test_HEAD_ile_HEAD_arasinda_fark_yok(self) -> None:
        import subprocess as sp
        head = sp.run(["git", "-C", str(K.DEPO), "rev-parse", "HEAD"],
                      capture_output=True, text=True, check=True).stdout.strip()
        self.assertIsNone(K._kod_degisti_mi(head))
