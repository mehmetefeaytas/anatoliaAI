"""RAG erişim değerlendirmesi doğru şeyi, doğru katmanda ölçüyor mu.

İlgili: ../eval/rag_eval.py, ../src/chatbot/bot.py (`Chatbot.ask`)
        ../data/safety/katilim-guvenlik-seti.jsonl

## Bu testlerin varlık sebebi

Ölçüm modülünün en tehlikeli hata biçimi, YANLIŞ ŞEYİ ölçüp doğru
görünmektir. `rag_eval` yazılırken iki kez oldu:

1. Çekimserlik `rag.answer()` üzerinden ölçüldü -> 0,267. Yanlıştı:
   reddetme kararı giriş taramasının işidir, `rag.answer()` o kapının
   ALTINDA çalışır. Ölçüm sistemin hiç kullanmadığı bir yolu ölçüyordu.
2. `safety_report.abstained` bayrağına bakıldı -> 0,333. O da yanlıştı:
   bayrak yalnız kapsam-dışı için set ediliyor; fıkhî hüküm KAPI 2'den
   geçer ve bayrağı set etmez.

Doğru sinyal `handler == "safety"` ve doğru ölçüt setin kendi
`reddedilmeli` alanı; sonuç 30/30. Aşağıdaki testler bu üç şeyi kilitler:
doğru katman, iki yönlü ölçüt, uydurulmamış cevap anahtarı.
"""

from __future__ import annotations

import json
import unittest

from eval.rag_eval import (
    GUVENLIK_SETI,
    CekimserSonucu,
    OlcutSonucu,
    _kayit,
    _kaynakli,
    banka_sorulari,
    olc_banka_hedefleme,
    olc_terim_kapsama,
)


class _SahteRepo:
    """`all_campaigns()` sözleşmesini karşılayan en küçük depo."""

    def __init__(self, kayitlar):
        self._k = kayitlar

    def all_campaigns(self):
        return self._k


class _SahteRetriever:
    """Sorgudan bağımsız, sabit sıra döndürür — sıralamayı testin kendisi kurar."""

    def __init__(self, sonuclar):
        self._s = sonuclar

    def retrieve(self, query, k=3):
        return self._s[:k]


# Depo kaydı ile retriever pasajı AYNI BİÇİM DEĞİLDİR ve tek yardımcıyla
# üretilemez — bu ayrımı ilk sürüm karıştırmıştı ve testler onu yakaladı:
#   depo   : bank / raw_text   (`repo.all_campaigns()` sözleşmesi)
#   pasaj  : bank_slug / text  (`KeywordRetriever.retrieve()` sözleşmesi)
def _repo_kaydi(cid, slug, metin):
    return {"id": cid, "bank": slug, "bank_name": slug.title(),
            "source_url": "https://ornek/1", "raw_text": metin, "ozet": None}


def _pasaj(cid, slug, metin, url="https://ornek/1"):
    return {"campaign_id": cid, "bank_slug": slug, "bank": slug.title(),
            "source_url": url, "text": metin, "ozet": None, "score": 1.0}


class TestSiraVeMRR(unittest.TestCase):
    """Ölçüm aritmetiği — MRR sıraya duyarlı olmalı."""

    def test_ilk_sirada_isabet_mrr_1(self):
        s = OlcutSonucu("t")
        _kayit(s, 1, "soru")
        self.assertEqual(s.mrr, 1.0)
        self.assertEqual(s.recall_at_1, 1.0)

    def test_ucuncu_sirada_isabet_mrr_ucte_bir(self):
        s = OlcutSonucu("t")
        _kayit(s, 3, "soru")
        self.assertAlmostEqual(s.mrr, 1 / 3)
        self.assertEqual(s.recall_at_1, 0.0)
        self.assertEqual(s.recall, 1.0, "sıra 3 de olsa isabet isabettir")

    def test_isabetsiz_soru_basarisizlara_yazilir(self):
        s = OlcutSonucu("t")
        _kayit(s, None, "bulunamayan soru")
        self.assertEqual(s.recall, 0.0)
        self.assertIn("bulunamayan soru", s.basarisizlar)

    def test_kaynak_orani_paydasi_ISABETTIR(self):
        """İsabetsiz sonucun kaynak taşıyıp taşımaması anlamsızdır."""
        s = OlcutSonucu("t")
        _kayit(s, 1, "a", kaynakli=True)
        _kayit(s, None, "b")
        self.assertEqual(s.kaynak_orani, 1.0)


class TestKaynakDenetlenebilirligi(unittest.TestCase):
    def test_url_ve_id_birlikte_gerekir(self):
        self.assertTrue(_kaynakli({"source_url": "u", "campaign_id": 1}))
        self.assertFalse(_kaynakli({"source_url": "u", "campaign_id": None}))
        self.assertFalse(_kaynakli({"source_url": None, "campaign_id": 1}))


class TestTerimKapsama(unittest.TestCase):
    def test_terimi_ICEREN_belge_isabet_sayilir(self):
        r = _SahteRetriever([_pasaj(1, "x", "murabaha bir yöntemdir")])
        s = olc_terim_kapsama(r, k=5)
        self.assertGreater(s.isabet, 0)

    def test_terimi_ICERMEYEN_belge_isabet_SAYILMAZ(self):
        """Alakasız belge döndürmek 'cevap buldum' demek değildir."""
        r = _SahteRetriever([_pasaj(1, "x", "konut finansmanı kampanyası")])
        s = olc_terim_kapsama(r, k=5)
        self.assertEqual(s.isabet, 0)


class TestBankaHedefleme(unittest.TestCase):
    KORPUS = [_repo_kaydi(i, "vakif-katilim", "metin") for i in range(6)] + \
             [_repo_kaydi(100, "tek-belgeli-banka", "metin")]

    def test_az_belgeli_banka_soru_URETMEZ(self):
        """Ölçüt erişimi ölçmeli, korpus boşluğunu değil."""
        sorular = banka_sorulari(_SahteRepo(self.KORPUS), en_az_belge=5)
        slugler = {s for _, s in sorular}
        self.assertIn("vakif-katilim", slugler)
        self.assertNotIn("tek-belgeli-banka", slugler)

    def test_yanlis_banka_isabet_SAYILMAZ(self):
        repo = _SahteRepo(self.KORPUS)
        r = _SahteRetriever([_pasaj(1, "baska-banka", "metin")])
        s = olc_banka_hedefleme(r, repo, k=5)
        self.assertEqual(s.isabet, 0)

    def test_dogru_banka_isabet_sayilir(self):
        repo = _SahteRepo(self.KORPUS)
        r = _SahteRetriever([_pasaj(1, "vakif-katilim", "metin")])
        s = olc_banka_hedefleme(r, repo, k=5)
        self.assertEqual(s.isabet, 1)


class TestOlcutSetiIkiYonlu(unittest.TestCase):
    """Cevap anahtarı UYDURULMAZ — setin kendi alanından gelir."""

    @classmethod
    def setUpClass(cls):
        if not GUVENLIK_SETI.is_file():                    # pragma: no cover
            raise unittest.SkipTest("güvenlik seti yok")
        cls.rows = [json.loads(s) for s in
                    GUVENLIK_SETI.read_text(encoding="utf-8").splitlines()
                    if s.strip()]

    def test_set_hem_reddedilecek_hem_cevaplanacak_soru_ICERIR(self):
        """Tek yönlü set, her şeyi reddeden bir sistemi 1,000 gösterirdi."""
        bayraklar = {bool(r["gecme_olcutu"]["reddedilmeli"])
                     for r in self.rows if "reddedilmeli" in r["gecme_olcutu"]}
        self.assertEqual(bayraklar, {True, False},
                         "ölçüt seti tek yönlü — aşırı reddetme ölçülemez")

    def test_alan_disi_soru_reddedilmeli_isaretli(self):
        hava = next(r for r in self.rows if "hava" in r["soru"].lower())
        self.assertTrue(hava["gecme_olcutu"]["reddedilmeli"])

    def test_gercek_veri_sorusu_reddedilMEmeli_isaretli(self):
        veri = [r for r in self.rows
                if r["kategori"] == "cekimserlik"
                and not r["gecme_olcutu"]["reddedilmeli"]]
        self.assertTrue(veri, "sette cevaplanması gereken soru yok")


class TestCekimserSonucu(unittest.TestCase):
    def test_iki_hata_bicimi_AYRI_tutulur(self):
        s = CekimserSonucu(dogru=8, toplam=10)
        s.kacan.append("F01")
        s.asiri_red.append("C03")
        self.assertEqual(s.dogruluk, 0.8)
        self.assertEqual(len(s.kacan), 1)
        self.assertEqual(len(s.asiri_red), 1)


if __name__ == "__main__":                                # pragma: no cover
    unittest.main()
