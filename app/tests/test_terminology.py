"""Terim sözlüğü — yükleyici, yönlendirici, kart üreteci, çıktı bekçisi.

İlgili: ../src/domain/terminology.py, ../data/terminology/katilim-terim-sozlugu.json,
        ../docs/terminoloji-sozlugu.md

Buradaki en kritik test `TestBekciKarsitligiBozmaz`. Bekçinin işi yanlış
eşitlemeyi ("sukuk bir tür tahvildir") yakalamak; ama bizim DOĞRU cevabımız da
aynı iki kelimeyi yan yana kullanır ("sukuk tahvil değildir"). Karşıtlık kapısı
çalışmazsa bekçi kendi doğru çıktımızı bloklar ve K2 politikası (üret → denetle
→ yeniden üret) sonsuz döngüye girer.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.domain import terminology as T


def _girdi(**kw) -> T.TermEntry:
    ham = {"id": "x", "kanonik": "X", "tanim": "t"}
    ham.update(kw)
    return T._kayit_coz(ham)


class TestYukleyici(unittest.TestCase):
    def test_gercek_sozluk_yuklenir(self) -> None:
        g = T.load_terminology()
        self.assertGreaterEqual(len(g), 100)
        self.assertEqual(T.DUSURULEN[str(Path(T.VARSAYILAN_YOL).resolve())], 0)

    def test_id_benzersiz_ve_iliskili_cozulur(self) -> None:
        g = T.load_terminology()
        idler = {e.id for e in g}
        self.assertEqual(len(idler), len(g), "mükerrer id")
        for e in g:
            for ref in e.iliskili:
                self.assertIn(ref, idler, f"{e.id} -> kırık referans {ref}")

    def test_dosya_yoksa_cokmez(self) -> None:
        """Sözlük bir ZENGİNLEŞTİRME; eksikse hat sözlüksüz davranışa düşmeli."""
        T.onbellegi_temizle()
        self.assertEqual(T.load_terminology("/olmayan/yol.json"), ())

    def test_bozuk_kayit_dusurulur_ve_SAYILIR(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.json"
            p.write_text(json.dumps([
                {"id": "a", "kanonik": "A", "tanim": "t"},
                {"id": "b"},                       # tanim/kanonik yok
                {"kanonik": "C", "tanim": "t"},    # id yok
                {"id": "a", "kanonik": "A2", "tanim": "t"},   # mükerrer
                "düz metin",
            ]), encoding="utf-8")
            T.onbellegi_temizle()
            g = T.load_terminology(str(p))
            self.assertEqual([e.id for e in g], ["a"])
            self.assertEqual(T.DUSURULEN[str(p.resolve())], 4)

    def test_bilinmeyen_alan_sessizce_atlanir(self) -> None:
        e = T._kayit_coz({"id": "a", "kanonik": "A", "tanim": "t",
                          "gelecekteki_alan": 1})
        self.assertIsNotNone(e)
        self.assertEqual(e.id, "a")


class TestYonlendirici(unittest.TestCase):
    def test_sozcuk_sinirli_eslesme(self) -> None:
        """'fon' -> 'fonksiyon' hatası: mentörün uyardığı kelimenin ta kendisi."""
        g = [_girdi(id="f", kanonik="fon", tanim="t", degildir=("x",))]
        self.assertEqual(T.relevant_terms("fonksiyon çağrısı", entries=g), [])
        self.assertEqual(len(T.relevant_terms("bir fon aldım", entries=g)), 1)

    def test_halk_dili_VARSAYILAN_OLARAK_KAPALI(self) -> None:
        """Açık olsaydı 'ödeme' geçen her belge `tediye` kartı çekerdi."""
        g = [_girdi(id="t", kanonik="Tediye", tanim="t",
                    halk_dili=("ödeme",), degildir=("tahsil",))]
        self.assertEqual(T.relevant_terms("ödeme yapıldı", entries=g), [])
        self.assertEqual(len(T.relevant_terms("ödeme yapıldı", entries=g,
                                              halk_dili=True)), 1)

    def test_expand_query_halk_dilini_ACAR(self) -> None:
        """Sorgu genişletmede amaç tersidir: günlük dili kanonik terime bağla."""
        self.assertIn("Sukuk", T.expand_query("faizsiz tahvil almak istiyorum"))
        self.assertIn("Kefalet", T.expand_query("birine kefil olmak riskli mi"))

    def test_uslup_terimi_kart_almaz(self) -> None:
        """Ölçüldü: filtresiz koşuda `isbu` EN SIK çekilen terimdi."""
        elenen = {e.id for e in T.load_terminology() if T._uslup_terimi(e)}
        self.assertEqual(elenen, {"isbu", "mezkur", "bila-kayd-u-sart"})
        metin = "İşbu sözleşme mezkûr hükümler çerçevesinde tanzim edilmiştir."
        self.assertNotIn("isbu", [e.id for e in T.relevant_terms(metin)])

    def test_ayrim_tasiyan_uslup_terimi_ELENMEZ(self) -> None:
        """`muaccel`/`müeccel` üslup değil: tek harf farkla anlam tersine döner."""
        ids = [e.id for e in T.relevant_terms(
            "Borç muaccel hale geldi.", limit=20)]
        self.assertIn("muaccel", ids)

    def test_es_anlamli_cift_tek_kart_alir(self) -> None:
        ids = [e.id for e in T.relevant_terms(
            "Sukuk ihracı ve kira sertifikası getirisi", limit=20)]
        self.assertIn("sukuk", ids)
        self.assertNotIn("kira-sertifikasi", ids, "eş anlamlı çift iki kart aldı")

    def test_tek_yonlu_varyant_es_anlamli_SAYILMAZ(self) -> None:
        ust = _girdi(id="u", kanonik="Üst", tanim="t", varyantlar=("alt",))
        alt = _girdi(id="a", kanonik="Alt", tanim="t", varyantlar=())
        self.assertFalse(T._es_anlamli(ust, alt))

    def test_deterministik(self) -> None:
        """Ölçüm kolunun yeniden üretilebilmesi buna bağlı."""
        m = "Kâr payı oranı, katılma hesabı ve sukuk ile tekâfül ve havale."
        a = [e.id for e in T.relevant_terms(m, limit=5)]
        b = [e.id for e in T.relevant_terms(m, limit=5)]
        self.assertEqual(a, b)

    def test_riskli_terim_once_gelir(self) -> None:
        m = "Havale işlemi ve tanzim tarihi ile sukuk getirisi."
        ilk = T.relevant_terms(m, limit=2)
        self.assertTrue(all(e.risk_notu for e in ilk))

    def test_limit_uygulanir(self) -> None:
        m = ("kâr payı katılma hesabı sukuk tekâfül havale kefalet ipotek "
             "murabaha icare mudaraba zekât nisap teverruk")
        self.assertLessEqual(len(T.relevant_terms(m, limit=3)), 3)

    def test_bos_metin_bos_sonuc(self) -> None:
        self.assertEqual(T.relevant_terms(""), [])


class TestKartUreteci(unittest.TestCase):
    def test_ayrim_tanimdan_ONCE_gelir(self) -> None:
        """Model tanımı zaten biliyor; bilmediği ayrımdır."""
        e = _girdi(id="s", kanonik="Sukuk", tanim="TANIM",
                   degildir=("tahvil",), ayrim_notu="AYRIM")
        k = T.to_prompt_cards([e])
        self.assertIn("DEĞİLDİR: tahvil", k)
        self.assertIn("AYRIM", k)
        self.assertNotIn("TANIM", k, "ayrım varken tanım da yazılmış")

    def test_ayrim_yoksa_tanim_yazilir(self) -> None:
        e = _girdi(id="s", kanonik="S", tanim="TANIM")
        self.assertIn("TANIM", T.to_prompt_cards([e]))

    def test_butce_asilmaz(self) -> None:
        g = T.load_terminology()
        k = T.to_prompt_cards(g, budget_chars=500)
        self.assertLessEqual(len(k), 500 + len(T._kart(g[0])))

    def test_kart_YARIDA_KESILMEZ(self) -> None:
        """Yarım bir 'DEĞİLDİR:' satırı modele yanlış bilgi verirdi."""
        g = T.load_terminology()
        k = T.to_prompt_cards(g, budget_chars=400)
        for kart in [x for x in k.split("\n- ") if x]:
            if "DEĞİLDİR:" in kart:
                self.assertTrue(kart.split("DEĞİLDİR:")[1].strip().endswith("."))

    def test_ilk_kart_butce_sifir_olsa_bile_yazilir(self) -> None:
        """Aksi halde sessizce sözlüksüz koşardık ve fark ölçülemezdi."""
        self.assertTrue(T.to_prompt_cards([_girdi(id="a", kanonik="A",
                                                  tanim="t")], budget_chars=1))

    def test_gercek_belgede_butce_icinde(self) -> None:
        m = ("Kâr payı oranı %2,05, katılma hesabı, sukuk, tekâfül, havale, "
             "kefalet, ipotek, murabaha, teverruk, TMSF, nisap, zekât.")
        self.assertLessEqual(len(T.cards_for(m)), T.VARSAYILAN_BUTCE)


class TestBekciKarsitligiBozmaz(unittest.TestCase):
    """Bekçi KENDİ doğru cevabımızı işaretlerse sistem kullanılamaz."""

    def test_dogru_ayrim_cumlesi_isaretlenmez(self) -> None:
        for c in ("Sukuk tahvil değildir; varlığa dayanır.",
                  "Sukuk yani kira sertifikası, tahvilden farklıdır.",
                  "Kâr payı ile faiz arasındaki farklar şunlardır.",
                  "Katılma hesabı vadeli mevduat ile karıştırılmamalıdır."):
            self.assertEqual(T.output_violations(c), [], f"yanlış alarm: {c}")

    def test_yanlis_esitleme_isaretlenir(self) -> None:
        for c in ("Sukuk bir tür tahvildir.",
                  "Sukuk, yani tahvil, sabit getiri sağlar."):
            ihl = T.output_violations(c)
            self.assertTrue(any(v.kural == "degildir_esitleme" for v in ihl), c)

    def test_esitleme_isareti_yoksa_beraber_gecmek_yeterli_DEGIL(self) -> None:
        self.assertEqual(
            T.output_violations("Portföyde sukuk ve tahvil bulunuyor."), [])


class TestBekciRiskKurallari(unittest.TestCase):
    def test_degisken_tutara_sabit_rakam(self) -> None:
        ihl = T.output_violations("TMSF sigorta limiti 400.000 TL'dir.")
        self.assertTrue(any(v.kural == "degisken_tutara_sabit_rakam"
                            for v in ihl))

    def test_rakamsiz_anlatim_serbest(self) -> None:
        ihl = T.output_violations(
            "TMSF kapsamı mevzuattan teyit edilmelidir.")
        self.assertFalse(any(v.kural == "degisken_tutara_sabit_rakam"
                             for v in ihl))

    def test_tartismali_yapida_kesin_hukum(self) -> None:
        ihl = T.output_violations("Teverruk caizdir, sorun yoktur.")
        self.assertTrue(any(v.kural == "tartismali_yapida_hukum" for v in ihl))

    def test_tartismali_yapiyi_yonlendirmek_serbest(self) -> None:
        ihl = T.output_violations(
            "Teverruk için kurumun Danışma Kurulu görüşü esas alınır.")
        self.assertFalse(any(v.kural == "tartismali_yapida_hukum" for v in ihl))

    def test_temiz_cevap_ihlalsiz(self) -> None:
        self.assertEqual(T.output_violations(
            "Kuveyt Türk konut finansmanında kâr payı oranı %2,05'tir."), [])

    def test_bos_metin(self) -> None:
        self.assertEqual(T.output_violations(""), [])


class TestTuretilmisGorunumler(unittest.TestCase):
    def test_kapsam_sozlugu_halk_dilini_ICERIR(self) -> None:
        """KAPI 5 haksız çekimserliği: 'tekâfül' bugün kapsam dışı sayılıyor."""
        s = T.scope_terms()
        self.assertIn("tekaful", s)
        self.assertIn("vekalet", s)
        self.assertTrue(all(len(t) >= 4 for t in s))

    def test_5_5_YALNIZ_gercek_karsiligi_olani_esler(self) -> None:
        """Üç kavramın sözlükte karşılığı YOK; zorlama eşleme yazılmamalı."""
        g = T.terminology_5_5()
        self.assertEqual(set(g), {"kar_payi_orani", "katilim_fonu"})
        self.assertIn("faiz", g["kar_payi_orani"]["degildir"])
        self.assertTrue(g["kar_payi_orani"]["karistirma"])


class TestGercekKorpus(unittest.TestCase):
    """Yönlendiricinin gerçek belgelerde gürültü üretmediğini sabitler."""

    def test_perakende_kampanyasi_terim_cekmez(self) -> None:
        m = ("Anasayfa Kampanyalar Vatan Vatan'da Peşin Fiyatına 6 Aya Varan "
             "Taksit Fırsatı! Paraf ile Vatan Bilgisayar'da geçerlidir.")
        self.assertEqual(T.relevant_terms(m), [])

    def test_katilim_urunu_sayfasi_dogru_terimleri_ceker(self) -> None:
        m = ("Katılma hesabı açarak birikiminizi kâr payı ile "
             "değerlendirebilirsiniz. Kâr/zarara katılım oranı sözleşmede "
             "belirlenir.")
        ids = {e.id for e in T.relevant_terms(m, limit=8)}
        self.assertIn("katilma-hesabi", ids)
        self.assertIn("kar-payi", ids)


if __name__ == "__main__":
    unittest.main()
