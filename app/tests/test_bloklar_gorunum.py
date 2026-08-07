"""Çerçeve KATLAMA — ham metni eksiksiz kaplayan görünürlük aralıkları.

İlgili: ../src/preprocessing/blocks.py (`gorunum_araliklari`, `gorunur_metin`)
        ../src/api/main.py (`GET /campaigns/{id}/text` -> `bloklar`)
        ../tests/test_blocks.py (karar mantığının kendisi — burada DEĞİŞMEZ)

## Bu dosyanın koruduğu tek şey: kapsama garantisi

Çerçeve metinden SİLİNMEZ, yalnız katlanabilir işaretlenir. Sebep pazarlıksız:
`extracted_fields.span_start` / `span_end` offset'leri ham metne göre
saklanır; metni kısaltmak tüm vurguları kaydırır ve "her değer bir karakter
aralığına bağlı" iddiası çöker.

Arayüzün metni aralıklardan yeniden birleştirebilmesi için aralıkların
DÖRT özelliği aynı anda taşıması gerekir:

    1. ilk aralık 0'dan başlar
    2. her aralığın sonu bir sonrakinin başıdır  (boşluk yok, örtüşme yok)
    3. son aralık len(text)'te biter
    4. parçaların birleşimi metnin BİREBİR kendisidir

Dördü de burada, hem elle yazılmış kenar durumlarda hem de gerçek korpustan
alınmış belgelerde sınanır. Kapsama iddiası tek bir örnekle kanıtlanamaz:
`bloklara_ayir()` cümleleri `normalize_whitespace()`'ten geçirir, yani
cümleler arası ayırıcılar blok sınırlarının DIŞINDA kalır ve bir cümle ham
metinde hiç bulunamayabilir. Garantiyi veren, boşlukların açıkça
doldurulmasıdır.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.preprocessing import blocks as B

KVKK = ("6698 sayılı Kişisel Verilerin Korunması Kanunu uyarınca veri "
        "sorumlusu sıfatıyla hareket edilmektedir.")
URUN = ("Konut finansmanında kâr payı oranı %2,05'ten başlıyor. "
        "Vade 120 aya kadar uzayabilir.")
CEREZ = "Çerez politikası ve çerez ayarları için tıklayınız."


def _kapsama_dogrula(testcase: unittest.TestCase, text: str) -> list[B.Aralik]:
    """Dört kapsama özelliğini birden sınar ve aralıkları döndürür."""
    araliklar = B.gorunum_araliklari(text)
    if not text:
        testcase.assertEqual(araliklar, [])
        return araliklar

    testcase.assertTrue(araliklar, "boş olmayan metin için aralık üretilmedi")
    testcase.assertEqual(araliklar[0].start, 0, "ilk aralık 0'dan başlamıyor")
    testcase.assertEqual(araliklar[-1].end, len(text),
                         "son aralık metnin sonunda bitmiyor")
    for onceki, sonraki in zip(araliklar, araliklar[1:], strict=False):
        testcase.assertEqual(
            onceki.end, sonraki.start,
            f"bitişik değil: {onceki.end} -> {sonraki.start}")
    for a in araliklar:
        testcase.assertLess(a.start, a.end, "boş aralık üretildi")
    testcase.assertEqual(
        "".join(text[a.start:a.end] for a in araliklar), text,
        "aralıkların birleşimi metne eşit değil")
    return araliklar


class TestKapsamaGarantisi(unittest.TestCase):
    """Aralıklar metni EKSİKSİZ ve BİTİŞİK kaplamalı."""

    def test_karisik_belgede_kapsama(self) -> None:
        _kapsama_dogrula(self, f"{URUN} {KVKK} {CEREZ}")

    def test_yalnizca_cerceve_belgesinde_kapsama(self) -> None:
        _kapsama_dogrula(self, f"{KVKK} {CEREZ}")

    def test_yalnizca_urun_belgesinde_kapsama(self) -> None:
        _kapsama_dogrula(self, URUN)

    def test_kenar_durumlar(self) -> None:
        """Cümle bulunamayan / tuhaf boşluklu metinler kapsamayı bozmamalı."""
        for metin in ("", " ", "\n\n", "Tek cümle", "...", "%2,05",
                      "Satır bir.\n\n\nSatır iki.\t\tSatır üç.",
                      "   Baştaki boşluk ve sondaki boşluk   ",
                      f"{CEREZ}\n\n{URUN}\n\n{KVKK}"):
            with self.subTest(metin=metin[:30]):
                _kapsama_dogrula(self, metin)

    def test_gercek_korpus_belgelerinde_kapsama(self) -> None:
        """Elle yazılmış örnekler yetmez — gerçek belgelerde de tutmalı."""
        kok = Path(__file__).resolve().parents[1] / "data" / "raw-classic"
        belgeler = sorted(kok.rglob("*.txt"))[:25] if kok.exists() else []
        if not belgeler:
            self.skipTest("korpus bulunamadı — kapsama testi atlanıyor")
        for yol in belgeler:
            metin = yol.read_text(encoding="utf-8", errors="replace")
            with self.subTest(belge=yol.name):
                _kapsama_dogrula(self, metin)


class TestGizlemeKarari(unittest.TestCase):
    """`gizle` / `gerekce` `kararlar()`'ın kararını AYNEN taşımalı."""

    def test_kvkk_bloklari_gizlenir_urun_gizlenmez(self) -> None:
        metin = f"{URUN} {KVKK}"
        araliklar = _kapsama_dogrula(self, metin)
        gizli = "".join(metin[a.start:a.end] for a in araliklar if a.gizle)
        gorunen = "".join(metin[a.start:a.end] for a in araliklar if not a.gizle)
        self.assertIn("Kişisel Verilerin Korunması", gizli)
        self.assertIn("kâr payı oranı", gorunen)
        self.assertNotIn("kâr payı oranı", gizli)

    def test_gerekce_yalnizca_gizlenende_ve_bilinen_addan(self) -> None:
        araliklar = _kapsama_dogrula(self, f"{URUN} {KVKK} {CEREZ}")
        for a in araliklar:
            if a.gizle:
                self.assertIn(a.gerekce, B.GIZLEME_GEREKCELERI,
                              f"uydurma gerekçe: {a.gerekce!r}")
            else:
                self.assertIsNone(a.gerekce,
                                  "gösterilen aralıkta gerekçe olmamalı")

    def test_gerekceler_kararlar_ile_ayni_kumeden(self) -> None:
        """Sunum katmanı yeni bir gerekçe adı ÜRETMEZ."""
        metin = f"{URUN} {KVKK} {CEREZ}"
        karar_gerekceleri = {k.gerekce for k in B.kararlar(metin) if not k.tut}
        aralik_gerekceleri = {a.gerekce for a in B.gorunum_araliklari(metin)
                              if a.gizle}
        self.assertTrue(aralik_gerekceleri.issubset(karar_gerekceleri))

    def test_tekrar_sinyali_cerceve_ile_gizler(self) -> None:
        """Grup içi tekrar eden değersiz cümle katlanır."""
        # Nokta ŞART: `split_sentences` cümle sınırını noktalamadan bulur.
        # Noktasız bir menü satırı ardından gelen ürün cümlesiyle TEK bloğa
        # girer ve tekrar anahtarı tutmaz.
        menu = "Bireysel Bankacılık Ürünleri Şubelerimiz İletişim."
        cerceve = B.cerceve_cumleler([menu] * 3, min_docs=3)
        araliklar = B.gorunum_araliklari(f"{menu} {URUN}", cerceve)
        gizli = [a for a in araliklar if a.gizle]
        self.assertTrue(gizli, "tekrar eden menü satırı gizlenmedi")
        self.assertEqual({a.gerekce for a in gizli}, {"tekrar"})


class TestBirlestirme(unittest.TestCase):
    """Aynı kararlı ardışık bloklar tek aralığa inmeli (UI parçalanmasın)."""

    def test_ardisik_ayni_karar_birlesir(self) -> None:
        # BLOK_CUMLE=1 olduğu için üç ürün cümlesi üç ayrı blok kararıdır;
        # hepsi görünür olduğundan tek aralığa inmeli.
        metin = ("Kâr payı oranı %2,05'tir. Vade 36 aydır. "
                 "Tahsis ücreti 500 TL'dir.")
        araliklar = _kapsama_dogrula(self, metin)
        self.assertEqual(len(araliklar), 1)
        self.assertFalse(araliklar[0].gizle)

    def test_farkli_gerekceler_ayri_kalir(self) -> None:
        """`alan_disi` ile `alan_disi_bolge` denetim için ayrışmalı."""
        metin = (f"{KVKK} Talebiniz otuz gün içinde sonuçlandırılır. "
                 "Başvuru sahibine yazılı bildirim yapılır.")
        araliklar = _kapsama_dogrula(self, metin)
        gerekceler = [a.gerekce for a in araliklar if a.gizle]
        self.assertIn("alan_disi", gerekceler)
        self.assertIn("alan_disi_bolge", gerekceler)


class TestGorunurMetin(unittest.TestCase):
    """`gorunur_metin()` aralıklarla BİREBİR tutarlı olmalı."""

    def test_araliklardan_turetilir(self) -> None:
        metin = f"{URUN} {KVKK} {CEREZ}"
        beklenen = "".join(metin[a.start:a.end]
                           for a in B.gorunum_araliklari(metin)
                           if not a.gizle).strip()
        self.assertEqual(B.gorunur_metin(metin), beklenen)

    def test_cerceve_metne_sizmaz(self) -> None:
        metin = f"{URUN} {KVKK}"
        gorunur = B.gorunur_metin(metin)
        self.assertIn("kâr payı", gorunur)
        self.assertNotIn("Kişisel Verilerin Korunması", gorunur)

    def test_bos_metin(self) -> None:
        self.assertEqual(B.gorunur_metin(""), "")


class TestKararMantigiDegismedi(unittest.TestCase):
    """Sunum katmanı `kararlar()`'ı DEĞİŞTİRMEMELİ — yalnız okur."""

    def test_gizlenen_araliklar_kararlarla_ortusur(self) -> None:
        metin = f"{URUN} {KVKK} {CEREZ}"
        silinecek = {(k.blok.bas, k.blok.son) for k in B.kararlar(metin)
                     if not k.tut}
        for bas, son in silinecek:
            ortada = (bas + son) // 2
            kapsayan = [a for a in B.gorunum_araliklari(metin)
                        if a.start <= ortada < a.end]
            self.assertEqual(len(kapsayan), 1)
            self.assertTrue(kapsayan[0].gizle,
                            f"karar sildi ama aralık göstermiş: {bas}-{son}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
