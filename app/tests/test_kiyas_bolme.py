"""`routers/kiyas.py` bölmesinin kapısı — cephe yeniden şişmesin, çekirdek kaymasın.

İlgili: ../src/api/routers/kiyas.py                  (cephe + sıralama çekirdeği)
        ../src/api/routers/kiyas_alan_kiyasi.py      (/compare)
        ../src/api/routers/kiyas_sartname_tablosu.py (/urun-tablosu)
        ../src/api/routers/kiyas_banka_deltasi.py    (/bank-delta)
        ../src/api/routers/kiyas_skor_aciklamasi.py  (/scoring)
        ../src/api/routers/kiyas_bilesik_skor.py     (/advantageous)
        ../src/api/routers/kiyas_toplama.py          (alan × kampanya toplama)
        ../src/api/routers/kiyas_kanit_satiri.py     (kanıtlı satır biçimleri)

## Bu testin varlık sebebi

`kiyas.py` 807 satıra çıkmıştı ve iki denetim turu boyunca "bölünmedi" diye
raporlandı. 21 Ağu 2026'da cepheye + 7 modüle bölündü. Bölme bir DEFA yapılan
bir iş değil: bir sonraki uç eklemesi gövdeyi en kolay yoldan yine cepheye
yazar ve dosya sessizce geri şişer. Bu dosya o yolu kapatır.

Kapı üç şeyi kilitler ve üçü de bölmenin GEREKÇESİNDEN türüyor:

1. **Cephe ince kalır.** Cephede uç GÖVDESİ yoktur; uçlar kendi modüllerinde
   tanımlanır. Satır tavanı da var — ama tavan tek başına kapı değil, çünkü
   satır saymak "kaydırma"yı ödüllendirir.
2. **Sıralama kapı çekirdeği yerinden kaymaz.** `siralanmis_satirlar` ve
   `delta_siralamasi` `kiyas.py`'de KALMAK zorunda: üç ayrı denetim kapısı
   (`test_rank_girdi_paritesi.py` × 2, `test_compare_ortak_kapilar.py`) o
   yolu bu dosyanın adıyla sabitliyor. Çekirdek başka modüle taşınırsa o üç
   kapı da düşer — ama düşme nedeni "bölme yanlış yapıldı" olarak
   okunmayabilir; bu test nedeni AÇIKÇA söyler.
3. **Her modül kendi gerekçesini taşır.** `extract.py` bölmesinde (commit
   1794f93f) jürinin onayladığı ölçüt buydu: "kaydırma değil, gerekçeli
   sorumluluk bölüşümü, çünkü her modül dosya-içi gerekçe metni taşıyordu."
   Gerekçesiz bir modül, bölmenin değil parçalamanın kanıtıdır.

Uç DAVRANIŞININ korunduğunu bu dosya kanıtlamaz — onu zaten mevcut uç
testleri (`test_api_sozlesme.py`, `test_compare_ortak_kapilar.py`,
`test_chatbot_kiyas_paritesi.py`) ve bölme sırasında alınan 30 uç yanıtının
birebir diff'i kanıtladı. Burada denetlenen şey YAPININ kendisi.
"""

from __future__ import annotations

import ast
import inspect
import sys
import unittest
from pathlib import Path

_KOK = Path(__file__).resolve().parents[1]
if str(_KOK) not in sys.path:
    sys.path.insert(0, str(_KOK))

from src.api.routers import kiyas as cephe

_ROUTERS = _KOK / "src" / "api" / "routers"

#: Cephenin dağıttığı uç modülleri ve her birinin kaydettiği yol.
UC_MODULLERI = {
    "kiyas_alan_kiyasi": "/compare",
    "kiyas_sartname_tablosu": "/urun-tablosu",
    "kiyas_banka_deltasi": "/bank-delta",
    "kiyas_skor_aciklamasi": "/scoring",
    "kiyas_bilesik_skor": "/advantageous",
}

#: Paylaşılan katman modülleri — uç kaydetmezler, iki+ uca hizmet ederler.
KATMAN_MODULLERI = ("kiyas_toplama", "kiyas_kanit_satiri")

#: Cephe tavanı. Bölmeden sonra 288 satır; tavan gerekçe metnine yer bırakacak
#: kadar gevşek, gövde geri taşınmasına yer bırakmayacak kadar sıkı seçildi
#: (en küçük uç gövdesi /advantageous'un ~55 satırı).
CEPHE_TAVANI = 340

#: Modül tavanı — bölmeden sonra en büyüğü 221 satır.
MODUL_TAVANI = 400


def _kaynak(ad: str) -> str:
    return (_ROUTERS / f"{ad}.py").read_text(encoding="utf-8")


def _satir(ad: str) -> int:
    return len(_kaynak(ad).splitlines())


class TestCepheInceKaliyor(unittest.TestCase):
    def test_cephede_uc_GOVDESI_yok(self) -> None:
        """Cephede `@r.get` dekoratörü olmamalı — uçlar kendi modüllerinde.

        Bu, satır saymaktan daha keskin bir ölçüt: yeni bir uç cepheye
        yazılırsa satır tavanı henüz aşılmamış olsa bile burası düşer.
        """
        agac = ast.parse(_kaynak("kiyas"))
        dekoratorler = [
            ast.unparse(d)
            for dugum in ast.walk(agac)
            if isinstance(dugum, (ast.FunctionDef, ast.AsyncFunctionDef))
            for d in dugum.decorator_list
        ]
        self.assertEqual(
            [d for d in dekoratorler if ".get(" in d or ".post(" in d], [],
            "cephede uç dekoratörü var — uç gövdesi cepheye geri yazılmış. "
            "Uçlar kendi modüllerinde tanımlanıp `router_kur` içinde "
            "kaydedilir; gerekçe `kiyas.py` başlığında.")

    def test_cephe_tavani(self) -> None:
        n = _satir("kiyas")
        self.assertLessEqual(
            n, CEPHE_TAVANI,
            f"cephe {n} satır — tavan {CEPHE_TAVANI}. Gövde cepheye geri "
            "taşınmış olabilir; sorumluluğu bir modüle verin.")

    def test_modul_tavani(self) -> None:
        for ad in (*UC_MODULLERI, *KATMAN_MODULLERI):
            with self.subTest(modul=ad):
                n = _satir(ad)
                self.assertLessEqual(n, MODUL_TAVANI, f"{ad}.py {n} satır")

    def test_router_kur_imzasi_DEGISMEDI(self) -> None:
        """`main.py`'nin çağrısı korunmalı — bölme oraya tek satır getirmedi.

        `src/api/main.py` bu factory'yi anahtar sözcük argümanlarıyla
        çağırıyor ve o dosya bölmenin kapsamı DIŞINDA. İmza değişirse bölme
        `main.py`'ye sızmış olur.
        """
        imza = inspect.signature(cephe.router_kur)
        self.assertEqual(list(imza.parameters), [
            "repo", "field_rows", "kiyas_kapsami", "campaign_view",
            "campaign_contradictions",
        ])
        for ad in ("field_rows", "kiyas_kapsami", "campaign_view",
                   "campaign_contradictions"):
            self.assertEqual(imza.parameters[ad].kind,
                             inspect.Parameter.KEYWORD_ONLY, ad)


class TestSiralamaCekirdegiCephede(unittest.TestCase):
    """Üç denetim kapısı bu yolu `kiyas.py` adıyla sabitliyor."""

    CEKIRDEK = ("siralanmis_satirlar", "delta_siralamasi")

    def test_cekirdek_fonksiyonlari_cephede_TANIMLI(self) -> None:
        for ad in self.CEKIRDEK:
            with self.subTest(fonksiyon=ad):
                fn = getattr(cephe, ad, None)
                self.assertIsNotNone(
                    fn, f"{ad} cephede yok — sıralama çekirdeği taşınmış")
                self.assertEqual(
                    fn.__module__, "src.api.routers.kiyas",
                    f"{ad} artık {fn.__module__} içinde. Taşınırsa "
                    "test_rank_girdi_paritesi.py'nin iki kapısı ve "
                    "test_compare_ortak_kapilar.py'nin dört testi düşer: "
                    "birincisi `rank()` çağıranların kümesini, ikincisi "
                    "ortak kapı adlarının HANGİ modülün global'lerinden "
                    "çözüldüğünü sabitliyor.")

    def test_ortak_kapilar_cephe_globallerinden_cozuluyor(self) -> None:
        """Yama yüzeyi: `test_compare_ortak_kapilar.py` bu adları yamalıyor.

        Uygulama KURULDUKTAN SONRA `kiyas.tekil_banka_urun` yamalanıyor ve
        çağrıldığı sayılıyor. Adlar çekirdek fonksiyonun global'lerinde
        durmazsa yama hiç görülmez ve o testler ölçmek istediklerini
        ölçmeden yeşil kalır.
        """
        g = cephe.siralanmis_satirlar.__globals__
        for ad in ("yon_zorla", "tekil_banka_urun", "rank"):
            self.assertIn(ad, g, f"{ad} cephe global'lerinde yok")
        self.assertIs(g, vars(cephe))

    def test_cekirdek_artik_SAF_ve_dogrudan_cagrilabilir(self) -> None:
        """Bölmenin somut kazancı: çekirdek depo/istek olmadan koşuyor.

        Eskiden bu mantık `router_kur` içinde bir closure'dı ve tek başına
        çağrılamıyordu — sınamak için uygulamayı kurup HTTP isteği atmak
        gerekiyordu. Artık saf bir fonksiyon.
        """
        satirlar = [
            {"bank": "a-banka", "bank_name": "A Banka",
             "canonical_value": 1.89, "source_span": "kâr payı %1,89",
             "campaign_id": 1, "campaign_type": "Konut Finansmanı",
             "confidence": 0.95, "campaign_status": None,
             "raw_value": "%1,89", "oran_bazi": None},
            {"bank": "b-banka", "bank_name": "B Banka",
             "canonical_value": 2.95, "source_span": "kâr payı %2,95",
             "campaign_id": 2, "campaign_type": "Konut Finansmanı",
             "confidence": 0.95, "campaign_status": None,
             "raw_value": "%2,95", "oran_bazi": None},
        ]
        kaynak, ranked = cephe.siralanmis_satirlar(
            satirlar, "kar_payi_orani",
            intent=None, per_bank="best", kapsam=[])

        self.assertEqual(set(kaynak), {(1, "kâr payı %1,89"),
                                       (2, "kâr payı %2,95")})
        self.assertEqual([x.bank for x in ranked], ["a-banka", "b-banka"],
                         "kâr payında küçük değer önce gelir")

        # Yön zorlaması ortak kapıdan geçiyor: `highest` sırayı çevirir.
        _, tersi = cephe.siralanmis_satirlar(
            satirlar, "kar_payi_orani",
            intent="highest", per_bank="best", kapsam=[])
        self.assertEqual([x.bank for x in tersi], ["b-banka", "a-banka"])

    def test_delta_cekirdegi_token_hilesini_TAMAMEN_kapsiyor(self) -> None:
        """`_ROW_TOKEN_SEP` başka hiçbir kıyas modülünde geçmemeli.

        Token'ın gömülmesi ve sökülmesi yan yana durmalı; ayrılırsa satır
        kimliği bir yerde gömülüp başka yerde yanlış çözülür.
        """
        eslesmis = cephe.delta_siralamasi([
            {"bank": "a-banka", "bank_name": "A Banka",
             "canonical_value": 36, "source_span": "36 ay",
             "campaign_id": 1, "campaign_type": "Konut Finansmanı",
             "confidence": 0.95, "campaign_status": None,
             "raw_value": "36 ay", "oran_bazi": None},
        ], "vade")
        self.assertEqual(len(eslesmis), 1)
        kayit, _x = eslesmis[0]
        self.assertEqual(kayit["bank"], "a-banka",
                         "token sökülmemiş — kaynak kayda geri eşleme bozuk")

        for ad in (*UC_MODULLERI, *KATMAN_MODULLERI):
            with self.subTest(modul=ad):
                self.assertNotIn(
                    "_ROW_TOKEN_SEP", _kaynak(ad),
                    f"{ad}.py token ayırıcısını tanıyor — hile cepheden "
                    "dışarı sızmış")


class TestHerModulGerekcesiniTasiyor(unittest.TestCase):
    """`extract.py` bölmesinde jürinin onayladığı ölçüt: dosya-içi gerekçe."""

    def test_modul_docstringi_NICIN_AYRI_sorusunu_yanitliyor(self) -> None:
        for ad in (*UC_MODULLERI, *KATMAN_MODULLERI):
            with self.subTest(modul=ad):
                belge = ast.get_docstring(ast.parse(_kaynak(ad)))
                self.assertIsNotNone(belge, f"{ad}.py docstring'siz")
                self.assertIn(
                    "Niçin AYRI bir modül", belge,
                    f"{ad}.py niçin ayrı bir modül olduğunu YAZMIYOR. "
                    "Gerekçesiz modül, bölmenin değil parçalamanın kanıtı.")
                self.assertGreater(
                    len(belge), 400,
                    f"{ad}.py gerekçesi tek cümle — sorumluluk sınırı "
                    "okunmuyor")

    def test_cephe_bolme_eksenini_ANLATIYOR(self) -> None:
        belge = ast.get_docstring(ast.parse(_kaynak("kiyas")))
        self.assertIsNotNone(belge)
        for beklenen in ("Bölmenin ekseni", "sıralama çekirdeği"):
            self.assertIn(beklenen, belge,
                          f"cephe başlığında '{beklenen}' yok")
        # Her modül cephenin haritasında adıyla geçmeli; geçmezse okuyucu
        # gövdenin nereye gittiğini cepheden bulamaz.
        for ad in (*UC_MODULLERI, *KATMAN_MODULLERI):
            self.assertIn(f"{ad}.py", belge, f"{ad}.py haritada yok")


class TestUcModulleriUcKaydediyor(unittest.TestCase):
    """Her uç modülü, haritada yazılı yolu GERÇEKTEN kaydediyor mu."""

    def test_her_modul_kendi_yolunu_kaydediyor(self) -> None:
        for ad, yol in UC_MODULLERI.items():
            with self.subTest(modul=ad):
                kaynak = _kaynak(ad)
                self.assertIn(f'@r.get("{yol}")', kaynak,
                              f"{ad}.py {yol} kaydetmiyor")

    def test_uc_docstringleri_SOZLESME_metnini_tasiyor(self) -> None:
        """Uç docstring'i `/openapi.json`'un `description` alanıdır.

        Gövde taşınırken docstring cephede bırakılsaydı kamuya açık sözleşme
        metni ile onu tutan kod iki dosyaya ayrılırdı — ve `description`
        FastAPI'nin kendi yolundan üretilemezdi.
        """
        for ad in UC_MODULLERI:
            with self.subTest(modul=ad):
                agac = ast.parse(_kaynak(ad))
                belgeler = [
                    ast.get_docstring(d) or ""
                    for d in ast.walk(agac)
                    if isinstance(d, ast.FunctionDef)
                    and any(".get(" in ast.unparse(x) for x in d.decorator_list)
                ]
                self.assertEqual(len(belgeler), 1, f"{ad}.py'de tek uç bekleniyor")
                self.assertGreater(
                    len(belgeler[0]), 300,
                    f"{ad}.py uç docstring'i kısalmış — `/openapi.json` "
                    "açıklaması budanmış olabilir")

    def test_katman_modulleri_UC_KAYDETMIYOR(self) -> None:
        """Katman modülleri iki+ uca hizmet eder; kendileri uç değildir."""
        for ad in KATMAN_MODULLERI:
            with self.subTest(modul=ad):
                self.assertNotIn("@r.get(", _kaynak(ad),
                                 f"{ad}.py uç kaydediyor — katman değil")


class TestImportZinciriFastapiSIZ(unittest.TestCase):
    def test_cephe_ve_moduller_fastapi_OLMADAN_import_edilebilir(self) -> None:
        """`fastapi` import'ları fonksiyon içinde kalmalı.

        Çekirdek kural/normalizasyon katmanı saf stdlib ile çalışır ve bu
        modüllerin import edilmesi tek başına çökmemeli; `main.build_app()`
        zaten anlaşılır bir hata veriyor. Denetim AST üzerinden yapılır —
        `fastapi` yerelde kurulu olduğu için import denemesi kör kalırdı.
        """
        for ad in ("kiyas", *UC_MODULLERI, *KATMAN_MODULLERI):
            with self.subTest(modul=ad):
                agac = ast.parse(_kaynak(ad))
                for dugum in agac.body:      # yalnız MODÜL düzeyi
                    if isinstance(dugum, ast.ImportFrom):
                        self.assertNotEqual(
                            (dugum.module or "").split(".")[0], "fastapi",
                            f"{ad}.py modül düzeyinde fastapi import ediyor")
                    elif isinstance(dugum, ast.Import):
                        for a in dugum.names:
                            self.assertNotEqual(
                                a.name.split(".")[0], "fastapi",
                                f"{ad}.py modül düzeyinde fastapi import ediyor")


if __name__ == "__main__":
    unittest.main()
