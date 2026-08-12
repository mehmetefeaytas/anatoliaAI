"""Gelecek faz uçları: TANIMLI, kapalı, ve sahte başarı DÖNDÜRMÜYOR.

İlgili: ../src/api/gelecek.py (sözleşme), ../src/api/main.py (`/admin/*`)
        ../web/app/components/AyarlarPanel.tsx (ekran)

## Bu testlerin varlık sebebi

Banka/kampanya/ürün ekleme uçları gelecek faz için tanımlandı ama bu sürümde
çalışmıyor. Bir sonraki geliştiricinin (ya da bir sonraki oturumdaki benim)
yapabileceği en zararlı iki şey:

1. **Uçları sahte 200 döndürür hâle getirmek.** Operatör kampanyayı eklediğini
   sanır, hiçbir yere yazılmaz ve kayıp ancak demoda fark edilir. Sessiz
   başarısızlık, gürültülü bir 501'den her zaman kötüdür.
2. **Uçları gerçekten açıp veri tabanına yazdırmak.** Arayüzden girilen bir
   kayıt, korpustaki her belgenin taşıdığı kanıt zincirini (ham sayfa +
   toplama zamanı + kaynak adresi + karakter aralığı) taşımaz; ölçüm yollarına
   girmesi doğrulanmış zincire doğrulanmamış halka eklerdi.

İkincisi bilinçli bir karar olabilir — ama o karar verildiğinde bu test
düşecek ve gerekçenin yeniden yazılmasını ZORLAYACAK. Testin işi kararı
yasaklamak değil, sessizce alınmasını engellemek.

Üçüncü kapı ekran içindir: `AyarlarPanel` sözleşmeyi kendi içinde
TEKRARLAMAMALI, `/admin/plan`'dan okumalı. Bu projede altı kez tekrarlayan
kusur tam olarak buydu.

Dördüncü kapı ZAMAN ÇERÇEVESİ içindir (2026-08-12'de eklendi). Ekran eskiden
"gelecek faz" diyordu ve bu bir takvim değil, bir erteleme gibi okunuyordu:
uçların NE ZAMAN açılacağı hiçbir yerde yazmıyordu. Doğru cümle "yakın dönem,
iş birliği durumunda" ve o cümle sunucuda yaşamalı — ekranda sabit yazılsaydı
sözleşme değiştiğinde ikisi ayrışırdı. Aşağıdaki testler cümlenin hem sunucu
yanıtında hem de ekranda (sabit yazılmadan) bulunmasını kilitler.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api import gelecek
from src.db.repository import Repository

KOK = Path(__file__).resolve().parents[1]


class _ApiTemel(unittest.TestCase):
    """Kendi geçici veri tabanıyla uygulama kurar.

    `data/demo.db`ye dayanmak iki yönden kırılgan: dosya bir geliştiricinin
    makinesinde hiç olmayabilir ve `DATABASE_PATH` başka bir testin
    temizlenmiş geçici dizinini gösteriyor olabilir. Bu uçlar zaten veriye
    bakmıyor — sözleşme döndürüyorlar.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        Repository(str(Path(self._tmp.name) / "t.db")).close()
        self._eski = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(Path(self._tmp.name) / "t.db")

    def tearDown(self) -> None:
        if self._eski is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = self._eski
        self._tmp.cleanup()

    def istemci(self):
        import importlib

        from fastapi.testclient import TestClient

        from src.api import main as M
        # `DB_PATH` modül düzeyinde, İÇE AKTARMA anında okunuyor. Ortam
        # değişkenini setUp'ta yazmak yetmez: modül zaten yüklüyse eski yolu
        # taşır — ve o yol başka bir testin temizlenmiş geçici dizini olabilir.
        importlib.reload(M)
        return TestClient(M.build_app())


class TestSozlesme(_ApiTemel):
    def test_plan_ucu_sozlesmeyi_dondurur(self) -> None:
        y = self.istemci().get("/admin/plan")
        self.assertEqual(y.status_code, 200)
        veri = y.json()
        self.assertFalse(veri["acik"], "bu sürümde uçlar KAPALI olmalı")
        self.assertTrue(veri["sebep"].strip())
        self.assertTrue(veri["bugunku_yol"].strip())
        self.assertGreaterEqual(len(veri["uclar"]), 3)

    def test_zaman_cercevesi_YANITTA(self) -> None:
        """"Ne zaman açılacak" sorusunun cevabı sözleşmenin parçasıdır."""
        veri = self.istemci().get("/admin/plan").json()
        baslik = veri["baslik"].casefold()
        self.assertIn("yakın dönem", baslik)
        self.assertIn("iş birliği", baslik)
        self.assertIn(gelecek.ZAMAN_CERCEVESI, veri["baslik"],
                      "başlık zaman çerçevesini taşımalı")
        self.assertTrue(veri["durum_etiketi"].strip())

    def test_gerekce_de_zaman_cercevesini_soyler(self) -> None:
        """501 gövdesini gören biri de takvimi görmeli, yalnız ekran değil."""
        sebep = gelecek.KAPALI_SEBEBI.casefold()
        self.assertIn("yakın dönem", sebep)
        self.assertIn("iş birliği", sebep)

    def test_her_ucun_alanlari_tam(self) -> None:
        for uc in gelecek.plan()["uclar"]:
            self.assertTrue(uc["yol"].startswith("/admin/"))
            self.assertIn(uc["yontem"], ("POST", "PUT", "PATCH", "DELETE"))
            self.assertTrue(uc["baslik"] and uc["ozet"])
            self.assertTrue(uc["alanlar"], f"{uc['yol']} alansız kalamaz")
            for alan in uc["alanlar"]:
                self.assertTrue(alan["ad"] and alan["tip"] and alan["aciklama"])
                self.assertIsInstance(alan["zorunlu"], bool)


class TestUclarSahteBasariDondurmez(_ApiTemel):
    """Kapalı uçlar 501 döner; 2xx dönerlerse sessiz veri kaybı olur."""

    def test_banka_ekleme_501(self) -> None:
        y = self.istemci().post("/admin/banks", json={"slug": "x", "name": "X"})
        self.assertEqual(y.status_code, 501)

    def test_kampanya_ekleme_501(self) -> None:
        y = self.istemci().post("/admin/banks/ornek/campaigns",
                            json={"title": "t", "raw_text": "m"})
        self.assertEqual(y.status_code, 501)

    def test_urun_ekleme_501(self) -> None:
        y = self.istemci().post("/admin/banks/ornek/products",
                            json={"name": "Konut Finansmanı"})
        self.assertEqual(y.status_code, 501)

    def test_501_govdesi_gerekceyi_ve_bugunku_yolu_TASIR(self) -> None:
        """Kapalı bir uç, ne yapılacağını söylemeden kapanmaz."""
        detay = self.istemci().post("/admin/banks", json={}).json()["detail"]
        self.assertEqual(detay["sebep"], gelecek.KAPALI_SEBEBI)
        self.assertEqual(detay["bugunku_yol"], gelecek.BUGUNKU_YOL)

    def test_yazma_uclari_veri_tabanina_DOKUNMAZ(self) -> None:
        """Kapalı uçların gövdesinde depo çağrısı OLMAMALI.

        Kaynak düzeyinde denetlenir: bir sonraki değişiklik uçları "geçici
        olarak" açıp `repo.insert_campaign` çağırırsa, 501 testi hâlâ geçse
        bile bu kapı düşer.
        """
        kaynak = (KOK / "src" / "api" / "main.py").read_text(encoding="utf-8")
        bas = kaynak.index("Gelecek faz — tanımlı ama KAPALI uçlar")
        son = kaynak.index('@app.get("/contradictions")', bas)
        bolum = kaynak[bas:son]
        for yasak in ("repo.insert_campaign", "repo.upsert_bank",
                      "repo.set_ozet", "repo.rows"):
            self.assertNotIn(yasak, bolum,
                             f"kapalı uçlar bölümünde depo yazımı var: {yasak}")


class TestEkranSozlesmeyiTekrarlamiyor(unittest.TestCase):
    """`AyarlarPanel` uç listesini KENDİ İÇİNDE tutmamalı."""

    def test_panel_admin_plandan_okuyor(self) -> None:
        panel = (KOK / "web" / "app" / "components"
                 / "AyarlarPanel.tsx").read_text(encoding="utf-8")
        self.assertIn("adminPlan", panel,
                      "panel sözleşmeyi sunucudan okumalı")

    def test_panel_uc_yollarini_sabit_yazmiyor(self) -> None:
        panel = (KOK / "web" / "app" / "components"
                 / "AyarlarPanel.tsx").read_text(encoding="utf-8")
        for uc in gelecek.UCLAR:
            self.assertNotIn(uc["yol"], panel,
                             f"{uc['yol']} ekranda SABİT yazılmış — sunucu "
                             "sözleşmeyi değiştirdiğinde ekran eskisini "
                             "göstermeye devam eder")

    def test_zaman_cercevesi_EKRANDA_ama_SABIT_DEGIL(self) -> None:
        """Cümle görünür olmalı; ama kaynağı sunucu olmalı.

        İki kapı birlikte: panel `baslik` ile `durum_etiketi` alanlarını
        ÇİZMELİ, ve cümlenin kendisini kendi içinde yazmamalı.
        """
        panel = (KOK / "web" / "app" / "components"
                 / "AyarlarPanel.tsx").read_text(encoding="utf-8")
        for alan in ("durum_etiketi", "baslik"):
            self.assertIn(alan, panel, f"panel {alan} alanını çizmeli")
        self.assertNotIn(gelecek.ZAMAN_CERCEVESI, panel,
                         "zaman çerçevesi ekranda SABİT yazılmış — sunucu "
                         "cümleyi değiştirdiğinde ekran eskisini gösterir")
        self.assertNotIn("Gelecek faz", panel,
                         "eski, takvimsiz ifade geri gelmiş")

    def test_panelde_gonderilebilir_form_yok(self) -> None:
        """Çalışmayan bir uca form koymak, çalışacağını vaat etmektir."""
        panel = (KOK / "web" / "app" / "components"
                 / "AyarlarPanel.tsx").read_text(encoding="utf-8")
        for yasak in ("<form", "<input", "onSubmit"):
            self.assertNotIn(yasak, panel)


if __name__ == "__main__":
    unittest.main()
