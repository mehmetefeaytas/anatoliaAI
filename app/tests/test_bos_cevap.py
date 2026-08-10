"""Boş cevap da bir cevaptır — "veri bulunamadı" yerine "elimde şu var".

İlgili: ../src/chatbot/structured.py (`_kiyaslanamaz_metni`, `_hic_kayit_metni`)
        ../src/comparison/compare.py (`eleme_sebebi`, `RankRow.confidence`)

## Bu testin varlık sebebi

Kıyaslanabilir satır kalmadığında chatbot doğru ama sessiz bir cevap
veriyordu. Demonun manşet sorusunda ölçüldü (`data/demo.db`, 2026-08-10):

    — "Araba alımında en yüksek finansman kimde var?"
    — "Karşılaştırılabilir veri bulunamadı. finansman tutarı alanında bulunan
       3 kaydın hiçbiri doğrudan kıyaslanamıyor:
       - kampanya süresi dolmuş — doğrudan kıyaslanamaz (3 kayıt)"

Elde olup söylenmeyenler: hangi bankalar, en son bilinen kapanışın ne zaman
olduğu, iki kaydın bitiş tarihinin belgede hiç yazmadığı ve bu alanın hangi
ürün ailelerinde bulunduğu. Hiçbiri ek sorgu istemiyordu.

24 soruluk temsilî kümede (aynı DB) 8 soru boş cevap alıyordu ve bunların
**üçü tek cümleydi** ("Bu kritere uyan kampanya bulunamadı." / "Karşılaştırı-
labilir veri bulunamadı."), yani sayı da sebep de vermiyordu.

## Bu dosya neyi kilitler

  1. Sayım, ayrıntı ve sonraki adım cümlelerinin HER eleme sebebi için
     üretilmesi (yalnız "süresi dolmuş" değil).
  2. **Uydurma yasağı**: bilinmeyen bitiş tarihi tarih olarak basılmaz.
  3. Superlatif ile listeleme sorusunun FARKLI boş cevap alması.
  4. Cevabın kısa kalması (sohbet cevabı, rapor değil).
  5. `compare` içindeki eleme notlarının tamamının bir koda eşlenmesi —
     yeni bir not eklenip kod eklenmezse burada patlar.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chatbot import structured
from src.chatbot.router import Route
from src.comparison.compare import (
    ASGARI_GUVEN,
    ELEME_ARALIK,
    ELEME_BILINMIYOR,
    ELEME_DUSUK_GUVEN,
    ELEME_PARA_BIRIMI,
    ELEME_SURESI_DOLMUS,
    ELEME_TUTAR_BELIRSIZ,
    NOT_ARALIK,
    NOT_DEGER_YOK,
    NOT_SAYISAL_DEGIL,
    NOT_SURESI_DOLMUS,
    NOT_TUTAR_BELIRSIZ,
    eleme_sebebi,
    rank,
)


def _satir(bank, deger, *, guven=0.95, tur="Taşıt Finansmanı", cid=1,
           durum=None, ad=None):
    return {"bank": bank, "bank_name": ad or bank, "canonical_value": deger,
            "confidence": guven, "source_span": "", "campaign_id": cid,
            "campaign_type": tur, "campaign_status": durum}


class _SahteDepo:
    """`query_fields` çağrılarını SAYAN asgari depo.

    Boş cevap ağ isteği yapmamalı ve gereksiz sorgu atmamalı; sayaç bunu
    ölçülebilir kılar.
    """

    def __init__(self, alanlar: dict):
        self.alanlar = alanlar
        self.cagrilar: list[str] = []

    def query_fields(self, field_name, **_kw):
        self.cagrilar.append(field_name)
        return list(self.alanlar.get(field_name, []))


def _sure(cid, iso):
    return {"campaign_id": cid, "canonical_value": iso}


class TestElemeSebebiKodlari(unittest.TestCase):
    """`compare`'in ürettiği her not kararlı bir koda düşmeli."""

    def test_sabit_notlar_kodlanir(self):
        self.assertEqual(ELEME_SURESI_DOLMUS, eleme_sebebi(NOT_SURESI_DOLMUS))
        self.assertEqual(ELEME_ARALIK, eleme_sebebi(NOT_ARALIK))
        self.assertEqual(ELEME_TUTAR_BELIRSIZ,
                         eleme_sebebi(NOT_TUTAR_BELIRSIZ))
        self.assertEqual("deger_yok", eleme_sebebi(NOT_DEGER_YOK))
        self.assertEqual("sayisal_degil", eleme_sebebi(NOT_SAYISAL_DEGIL))

    def test_olculen_sayi_tasiyan_notlar_da_kodlanir(self):
        """Güven ve para birimi notları sabit dize DEĞİL — önekten tanınır."""
        (dusuk,) = rank([_satir("a", 5.0, guven=0.40)], "vade_ay")
        self.assertEqual(ELEME_DUSUK_GUVEN, eleme_sebebi(dusuk.note))
        (doviz,) = rank([_satir("a", {"value": 5.0, "currency": "USD"})],
                        "finansman_tutari")
        self.assertEqual(ELEME_PARA_BIRIMI, eleme_sebebi(doviz.note))

    def test_uretilebilen_TUM_notlar_bilinmiyor_kutusuna_dusmez(self):
        """Kapı: yeni bir eleme notu eklenip kodu eklenmezse test söyler."""
        ornekler = [
            _satir("a", None),                                    # değer yok
            _satir("b", {"min": 1.0, "max": 2.0}),                # aralık
            _satir("c", {"value": 5.0, "currency": "USD"}),       # döviz
            _satir("d", {"has_fee": True, "amount": None}),       # tutar yok
            _satir("e", "on iki"),                                # sayısal değil
            _satir("f", 5.0, guven=0.40),                         # düşük güven
            _satir("g", 5.0, durum="expired"),                    # süresi dolmuş
        ]
        notlar = [x.note for x in rank(ornekler, "kar_payi_orani")
                  if x.note is not None]
        self.assertEqual(len(ornekler), len(notlar), "bir satır elenmedi")
        self.assertEqual([], [n for n in notlar
                              if eleme_sebebi(n) == ELEME_BILINMIYOR],
                         "sınıflandırılamayan eleme notu var")


class TestSuresiDolmus(unittest.TestCase):
    """Demonun manşet vakası: alan var, kayıt var, hepsi kapanmış."""

    def _cevap(self, sureler=(), durum="expired"):
        depo = _SahteDepo({
            "finansman_tutari": [
                _satir("kuveyt-turk", {"value": 150000.0, "currency": "TRY"},
                       cid=1, durum=durum, ad="Kuveyt Türk"),
                _satir("vakif-katilim", {"value": 400000.0, "currency": "TRY"},
                       cid=2, durum=durum, ad="Vakıf Katılım"),
                _satir("vakif-katilim", {"value": 400000.0, "currency": "TRY"},
                       cid=3, durum=durum, ad="Vakıf Katılım"),
            ],
            "kampanya_suresi": list(sureler),
        })
        rota = Route("structured", "finansman_tutari", "highest",
                     {"campaign_type": "Taşıt Finansmanı"})
        return depo, structured.answer(depo, rota).text

    def test_sayim_ve_sebep_yazilir(self):
        _depo, metin = self._cevap()
        self.assertIn("3 kampanya", metin, "kaç kayıt olduğu söylenmiyor")
        self.assertIn("üçü de kapanmış", metin, "eleme sebebi söylenmiyor")
        self.assertIn("Taşıt Finansmanı", metin, "kapsam söylenmiyor")

    def test_en_son_bilinen_kapanis_ve_tarihi_yazilir(self):
        _depo, metin = self._cevap(
            sureler=[_sure(1, "2024-02-29"), _sure(2, "2026-07-31")])
        self.assertIn("En son bilinen kapanış", metin)
        self.assertIn("Vakıf Katılım", metin, "en son kapanan banka yanlış")
        self.assertIn("31.07.2026", metin, "tarih TR biçiminde basılmadı")

    def test_tarihsiz_kayitlar_SAYILIR_gizlenmez(self):
        _depo, metin = self._cevap(sureler=[_sure(1, "2024-02-29")])
        self.assertIn("29.02.2024", metin)
        self.assertIn("2 kaydın bitiş tarihi belgelerde yazmıyor", metin,
                      "tarihsiz kayıtlar sessizce yok sayıldı")

    def test_hicbir_tarih_yoksa_TARIH_UYDURULMAZ(self):
        """82 belgede damga tarih taşımıyor; boşluk boşluk olarak geçmeli."""
        _depo, metin = self._cevap(sureler=[])
        self.assertIn("bitiş tarihi belgelerde yazmıyor", metin)
        self.assertNotRegex(metin, r"\d{2}\.\d{2}\.\d{4}",
                            "bilinmeyen bitiş tarihi uydurulmuş")

    def test_sonraki_adim_onerilir(self):
        _depo, metin = self._cevap()
        self.assertIn("deneyebilirsiniz", metin, "sonraki adım yok")

    def test_cevap_UC_cumleyi_gecmez(self):
        _depo, metin = self._cevap(sureler=[_sure(1, "2024-02-29")])
        self.assertLessEqual(metin.count("."), 6,
                             "sohbet cevabı rapora dönüşmüş")
        self.assertNotIn("\n", metin, "boş cevap çok satıra yayılmış")

    def test_tarih_sorgusu_TEMBEL_kapanmis_kayit_yoksa_atilmaz(self):
        """Bitiş tarihi yalnız gerektiğinde okunur — bedava sorgu yok."""
        depo, _metin = self._cevap(durum=None)
        self.assertNotIn("kampanya_suresi", depo.cagrilar,
                         "gereksiz bitiş tarihi sorgusu atıldı")


class TestDigerElemeSebepleri(unittest.TestCase):
    """Her eleme sebebi KENDİ cümlesini hak eder."""

    def _metin(self, rows, alan, *, niyet="lowest", filtreler=None):
        depo = _SahteDepo({alan: rows})
        return structured.answer(
            depo, Route("structured", alan, niyet, filtreler or {})).text

    def test_dusuk_guven_olculen_en_yuksek_guveni_soyler(self):
        metin = self._metin([_satir("a", 12.0, guven=0.45, cid=1),
                             _satir("b", 24.0, guven=0.55, cid=2)], "vade_ay")
        self.assertIn("düşük çıkarım güveniyle işaretli", metin)
        self.assertIn("0,55", metin, "ölçülen en yüksek güven yazılmadı")
        self.assertIn(f"{ASGARI_GUVEN:.2f}".replace(".", ","), metin,
                      "eşik yazılmadı")
        self.assertIn("kıyas dışı", metin)

    def test_aralik_ornek_araligi_gosterir(self):
        metin = self._metin(
            [_satir("albaraka", {"min": 1.99, "max": 2.49}, cid=1,
                    ad="Albaraka Türk")], "kar_payi_orani")
        self.assertIn("aralık olarak ilan edilmiş", metin)
        self.assertIn("%1,99–%2,49", metin, "örnek aralık gösterilmedi")

    def test_tutari_belirsiz_ucret_sifir_sayilmadigini_soyler(self):
        metin = self._metin(
            [_satir("a", {"has_fee": True, "amount": None}, cid=1)],
            "masraf_durumu")
        self.assertIn("tutarı belirtilmemiş ücret taşıyor", metin)
        self.assertIn("masrafsız", metin, "sıfır sayılmama gerekçesi yok")

    def test_karisik_sebepler_KAPI_KAPI_sayilir(self):
        rows = [_satir("a", 12.0, guven=0.45, cid=1),
                _satir("b", 24.0, guven=0.55, cid=2),
                _satir("c", 36.0, cid=3, durum="expired")]
        metin = self._metin(rows, "vade_ay")
        self.assertIn("3 kampanya var:", metin)
        self.assertIn("2 kampanya düşük çıkarım güveniyle işaretli", metin)
        self.assertIn("1 kampanya kapanmış", metin)


class TestHicKayitYok(unittest.TestCase):
    """"Kıyaslanamaz" ile "hiç yok" ayrı cevaplardır."""

    def _cevap(self, havuz, filtreler, niyet, *, vadeler=None):
        depo = _SahteDepo({"tahsis_ucreti": havuz, "vade_ay": vadeler or []})
        return structured.answer(
            depo, Route("structured", "tahsis_ucreti", niyet, filtreler))

    def _metin(self, havuz, filtreler, niyet):
        return self._cevap(havuz, filtreler, niyet).text

    def test_tur_suzgeci_bosaltmissa_alanin_NEREDE_oldugu_soylenir(self):
        havuz = [_satir("a", 500.0, tur="Konut Finansmanı", cid=1, ad="A"),
                 _satir("b", 750.0, tur="Konut Finansmanı", cid=2, ad="B"),
                 _satir("c", 300.0, tur="Kart", cid=3, ad="C")]
        metin = self._metin(havuz, {"campaign_type": "İhtiyaç Finansmanı"},
                            "lowest")
        self.assertIn("İhtiyaç Finansmanı kampanyalarında", metin)
        self.assertIn("Bu alanı taşıyan ürün aileleri", metin)
        self.assertIn("Konut Finansmanı (2 banka)", metin)

    def test_ipucu_KANITIYLA_birlikte_doner(self):
        """İddianın kaynağı gösterilmezse çekimserlik kapısı haklı olarak siler."""
        havuz = [_satir("a", 500.0, tur="Konut Finansmanı", cid=1, ad="A"),
                 _satir("c", 300.0, tur="Kart", cid=3, ad="C")]
        cevap = self._cevap(havuz, {"campaign_type": "İhtiyaç Finansmanı"},
                            "lowest")
        self.assertEqual({1, 3}, {x.campaign_id for x in cevap.rows},
                         "adı geçen ailelerin kanıt satırları taşınmadı")

    def test_BANKA_suzgecinde_baska_banka_adi_GECMEZ(self):
        """Güvenlik kümesi C03–C05: sorulan banka verimizde yoksa çekimser kal.

        "Peki hangi bankalarda var" cümlesi, kullanıcının sormadığı bankayı
        cevaba sokardı. Kanıt da boş kalmalı ki çekimserlik kapısı çalışsın.
        """
        havuz = [_satir("albaraka", 500.0, cid=1, ad="Albaraka Türk"),
                 _satir("kuveyt-turk", 750.0, cid=2, ad="Kuveyt Türk")]
        for filtre in ({"banks": ["adil-katilim"]},
                       {"banks": ["adil-katilim"],
                        "campaign_type": "Taşıt Finansmanı"}):
            cevap = self._cevap(havuz, filtre, "lowest")
            self.assertNotIn("Albaraka", cevap.text, str(filtre))
            self.assertNotIn("Kuveyt", cevap.text, str(filtre))
            self.assertEqual([], cevap.rows,
                             "kaynaksız kalması gereken cevap kaynak taşıyor")

    def test_tur_icinde_hangi_bankalarin_tasidigi_soylenir(self):
        """Süzgeç bankaya DEĞİL vadeye takıldıysa banka adı vermek serbest."""
        havuz = [_satir("albaraka", 500.0, tur="Taşıt Finansmanı", cid=1,
                        ad="Albaraka Türk")]
        metin = self._metin(havuz, {"campaign_type": "Taşıt Finansmanı",
                                    "vade_ay_min": 36}, "list")
        self.assertIn("Taşıt Finansmanı kampanyalarında bu alanı taşıyan "
                      "bankalar", metin)
        self.assertIn("Albaraka Türk", metin)
        self.assertIn("36 ay ve üzeri vadede", metin, "kapsam söylenmiyor")

    def test_superlatif_ile_listeleme_FARKLI_cevap_alir(self):
        havuz = [_satir("albaraka", 500.0, tur="Konut Finansmanı", cid=1,
                        ad="Albaraka Türk")]
        filtre = {"campaign_type": "Kart"}
        self.assertIn("sıralanacak", self._metin(havuz, filtre, "lowest"))
        self.assertIn("listelenecek", self._metin(havuz, filtre, "list"))

    def test_eski_iceriksiz_cumleler_ARTIK_basilmaz(self):
        havuz = [_satir("albaraka", 500.0, tur="Konut Finansmanı", cid=1,
                        ad="Albaraka Türk")]
        for niyet in ("lowest", "list"):
            metin = self._metin(havuz, {"campaign_type": "Kart"}, niyet)
            self.assertNotIn("Bu kritere uyan kampanya bulunamadı", metin)
            self.assertNotIn("Karşılaştırılabilir veri bulunamadı", metin)


class TestBicimBirimleri(unittest.TestCase):
    """Küçük ama sessizce yanlış olabilecek dönüşümler."""

    def test_tarih_TR_bicimine_cevrilir(self):
        self.assertEqual("31.07.2026", structured._tarih_tr("2026-07-31"))
        self.assertEqual("01.02.2026", structured._tarih_tr("2026-2-1"))

    def test_tanimsiz_tarih_bicimi_None_doner(self):
        for ham in (None, "", "yakında", "2026-07", 20260731):
            self.assertIsNone(structured._tarih_tr(ham), repr(ham))

    def test_bas_harf_turkce_kurala_uyar_ve_geri_kalani_BOZMAZ(self):
        self.assertEqual("İhtiyaç", structured._bas_harf("ihtiyaç"))
        self.assertEqual("Kâr payı oranı",
                         structured._bas_harf("kâr payı oranı"))
        self.assertEqual("Kuveyt Türk için vade",
                         structured._bas_harf("Kuveyt Türk için vade"))

    def test_kampanya_birimi_kimlikler_ayrismiyorsa_kayit_olur(self):
        """Aynı kampanyadan iki satır gelirse "2 kampanya" demek yanlıştır."""
        ayni = rank([_satir("a", 1.0, cid=7, durum="expired"),
                     _satir("a", 2.0, cid=7, durum="expired")], "vade_ay")
        self.assertEqual("kayıt", structured._birim(ayni))
        farkli = rank([_satir("a", 1.0, cid=7, durum="expired"),
                       _satir("a", 2.0, cid=8, durum="expired")], "vade_ay")
        self.assertEqual("kampanya", structured._birim(farkli))


class TestKorpustaBosCevap(unittest.TestCase):
    """Gerçek korpusta manşet soru — `data/demo.db` yoksa atlanır."""

    DB = Path(__file__).resolve().parents[1] / "data" / "demo.db"

    def setUp(self):
        if not self.DB.exists():
            self.skipTest("data/demo.db yok")
        import sqlite3

        from src.db.repository import Repository
        # Salt okunur açılır: bu test korpusa YAZMAMALI.
        depo = Repository.__new__(Repository)
        depo.on_nul = "error"
        depo.conn = sqlite3.connect(f"file:{self.DB}?mode=ro", uri=True)
        depo.conn.row_factory = sqlite3.Row
        self.addCleanup(depo.conn.close)
        self.depo = depo

    def test_araba_finansmani_sorusu_bilgi_verir(self):
        from src.chatbot.router import route

        metin = structured.answer(
            self.depo, route("Araba alımında en yüksek finansman kimde var?")
        ).text
        self.assertIn("Taşıt Finansmanı", metin)
        self.assertIn("kapanmış", metin)
        self.assertIn("bitiş tarihi belgelerde yazmıyor", metin,
                      "damgasız kayıtlar sessizce yok sayıldı")
        self.assertNotIn("Karşılaştırılabilir veri bulunamadı", metin)


if __name__ == "__main__":
    unittest.main()
