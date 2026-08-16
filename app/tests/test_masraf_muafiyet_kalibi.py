"""Masraf muafiyeti: "X ücreti BANKA TARAFINDAN karşılanmaktadır" = ücretsiz.

İlgili: src/extraction/rules/extract.py (`_MUAFIYET_RE`, `_ucret_muafiyeti`)
        raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf s.11–12
        CLAUDE.md §6 (negasyon: masrafsız = 0), §10 (masrafsız ≈ ücretsiz)

## Bu testin varlık sebebi

Şartname s.11, B Bankası metninin son cümlesi birebir:

    "Kampanya kapsamında ekspertiz ücreti banka tarafından karşılanmaktadır."

s.12'deki beklenen çıktı tablosu bu TEK cümleden İKİ hücre bekliyor:

    «Kampanya Avantajı» = "Ekspertiz ücreti banka tarafından karşılanıyor"
    «Masraf Durumu»     = "Ekspertiz ücretsiz"

`masraf_durumu` bu cümleden hiçbir şey üretmiyordu (ölçüldü: `None`), yani
iki hücre birden boş kalıyordu. Tek çıkarım düzeltmesi ikisini birden kapatır.

## Kapının neden bu kadar dar olduğu — ölçüm

1782 belgelik korpusta gevşek bir "ücret … karşılanır" kalıbı 52 eşleşme /
27 belge veriyor ve **baskın özne müşteridir** (müşteri 9 · banka 4):

    "ekspertiz ücreti MÜŞTERİ tarafından karşılanacaktır"   (cid=867)
    "Noter Masrafları … MÜŞTERİ tarafından ödenecektir"     (7 belge)

Yani kalıbın çoğunluğu muafiyetin TERSİdir. Özneyi bankaya sabitlemek de
yetmiyor: "banka öznesi + öde" korpusta 4 eşleşme veriyor ve 4'ü de yanlış.
Kapı üç yerden sıkıldı (fiil `karşılan`/`üstlenil`, boşluk ≤12 kr, yüklem
olumlu) ve korpusta **0 eşleşme** üretiyor — 47 karşıt vakanın hiçbirine
dokunulmadığının kanıtı.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.extraction.rules.extract import extract_masraf

#: Şartname s.11 B Bankası konut finansmanı metni — BİREBİR.
B_BANKASI = (
    "Konut finansmanında avantajlı ödeme seçenekleri. %1,95 kâr payı oranı "
    "ile 120 ay vadeye kadar finansman imkanı sunulmaktadır. Kampanya "
    "kapsamında ekspertiz ücreti banka tarafından karşılanmaktadır."
)


def _masraf(text: str):
    field = extract_masraf(text)
    return field.canonical_value if field else None


class SartnameBBankasiMasrafHucresi(unittest.TestCase):
    """s.11 metni → s.12 «Masraf Durumu» = "Ekspertiz ücretsiz"."""

    def test_muafiyet_tanindi(self):
        canon = _masraf(B_BANKASI)
        self.assertIsNotNone(canon, "B Bankası masraf hücresi hâlâ boş")
        self.assertIs(canon["has_fee"], False)
        self.assertEqual(canon["amount"], 0.0)

    def test_ucret_turu_TASINDI(self):
        """Şartname "Ekspertiz ücretsiz" diyor, "masrafsız" değil.

        Türü düşürmek o hücreyi yanlış doldurmak olurdu: ekspertiz muafiyeti
        dosya masrafı muafiyeti DEĞİLDİR.
        """
        self.assertEqual(_masraf(B_BANKASI).get("muaf_ucret"), "ekspertiz")

    def test_tur_baglam_sozcugunu_YUTMAZ(self):
        """"Kampanya kapsamında ekspertiz ücreti" — tür "kapsamında" değil."""
        self.assertEqual(_masraf(B_BANKASI)["muaf_ucret"], "ekspertiz")


class MuafiyetTanininanBicimler(unittest.TestCase):
    """Ünlü uyumunun iki kolu + yaygın yüklem çekimleri."""

    def test_kalin_ve_ince_unlu_kollari(self):
        for metin in (
                "ekspertiz ücreti banka tarafından karşılanmaktadır",
                "ekspertiz ücreti banka tarafından üstlenilmektedir",
                "ekspertiz ücreti banka tarafından karşılanacaktır",
                "ekspertiz ücreti banka tarafından üstlenilecektir",
                "ekspertiz ücreti bankamızca karşılanır",
                "ekspertiz ücreti banka tarafından karşılanıyor"):
            with self.subTest(metin=metin):
                canon = _masraf(metin)
                self.assertIsNotNone(canon)
                self.assertIs(canon["has_fee"], False)

    def test_farkli_ucret_turleri(self):
        for metin, tur in (
                ("dosya masrafı bankamız tarafından karşılanacaktır", "dosya"),
                ("ipotek ücreti bankamızca karşılanır", "ipotek"),
                ("sigorta komisyonu banka tarafından karşılanıyor", "sigorta")):
            with self.subTest(metin=metin):
                self.assertEqual(_masraf(metin).get("muaf_ucret"), tur)


class KarsitKaliplarREDDEDILIR(unittest.TestCase):
    """Bu sınıf testin KALBİ — korpusun çoğunluğu bu tarafta.

    Ücreti MÜŞTERİ ödüyorsa bu bir muafiyet değil, tersidir. Gevşek bir kural
    bunları "masrafsız" okuyup en ağırlıklı ikinci alana
    (`compare.DEFAULT_WEIGHTS["masraf_durumu"] = 0.20`) yalan yazardı.
    """

    def test_ucreti_musteri_odiyorsa_muafiyet_YOK(self):
        for metin in (
                # cid=867 — şartnameyle AYNI ücret türü, TERS yön
                "ekspertiz ücreti Müşteri tarafından karşılanacaktır.",
                "Noter Masrafları Gerektiğinde Müşteri tarafından ödenecektir.",
                "Bu değerleme ile ilgili ücret ve masraflar Müşteri "
                "tarafından karşılanır.",
                "her türlü masraf Kiracı tarafından karşılanacaktır"):
            with self.subTest(metin=metin):
                self.assertIsNone(_masraf(metin))

    def test_olumsuz_yuklem(self):
        for metin in (
                "ekspertiz ücreti banka tarafından karşılanmamaktadır",
                "ekspertiz ücreti banka tarafından üstlenilmemektedir",
                "ekspertiz ücreti banka tarafından karşılanmaz",
                "ekspertiz ücreti banka tarafından karşılanmıyor",
                "ekspertiz ücreti banka tarafından karşılanmayacaktır"):
            with self.subTest(metin=metin):
                self.assertIsNone(_masraf(metin))

    def test_kosullu_muafiyet_mutlak_sayilmaz(self):
        """"ilk yıl banka karşılar" = ikinci yıl ücret VAR. §21."""
        for metin in (
                "dosya masrafı ilk yıl banka tarafından karşılanır",
                "ekspertiz ücreti ilk 1 yıl bankamızca karşılanacaktır",
                "ekspertiz ücreti talep edilmesi halinde banka tarafından "
                "karşılanır",
                "masraf, şubeden başvuru durumunda banka tarafından karşılanır"):
            with self.subTest(metin=metin):
                self.assertIsNone(_masraf(metin))

    def test_banka_ozneli_ama_muafiyet_olmayanlar(self):
        """Korpustaki 4 'banka + öde' eşleşmesinin tamamı yanlıştı."""
        for metin in (
                "Satış Belgesi bedellerinin Kart Hamilinin bankası "
                "tarafından ödenmemesi",
                "mal bedelinin ülkesinde bulunan bir bankadan ödeneceğinin "
                "garantisidir",
                "muhabir banka masrafını müşterinin üstlendiği durumda "
                "tahsil edilecek ücret"):
            with self.subTest(metin=metin):
                self.assertIsNone(_masraf(metin))

    def test_banka_ADI_ozne_alinmaz(self):
        """Bilerek kapsam dışı: aynı biçim bir İŞ İLANINDA da geçiyor.

        "ücreti Kuveyt Türk tarafından karşılanacak MBA" (cid=290) bir çalışan
        yan hakkıdır, kampanya masraf muafiyeti değil. Banka adlarını gömmeden
        ikisi şekilce ayırt edilemiyor; §21 uyarınca ikisi de alınmadı.
        """
        self.assertIsNone(
            _masraf("ücreti Kuveyt Türk tarafından karşılanacak MBA imkânı"))


class MevcutDavranisKORUNUR(unittest.TestCase):
    """Muafiyet kapısı mevcut masraf yollarını bozmamalı."""

    def test_bilinen_kaliplar(self):
        for metin, beklenen in (
                ("masrafsız finansman", {"has_fee": False, "amount": 0.0}),
                ("dosya masrafı alınmaz", {"has_fee": False, "amount": 0.0}),
                ("ücret alınmamaktadır", {"has_fee": False, "amount": 0.0}),
                ("masraftan muaf", {"has_fee": False, "amount": 0.0}),
                ("tahsis ücreti 500 TL", {"has_fee": True, "amount": 500.0}),
                ("tahsis ücreti %0,5", {"has_fee": True, "amount": None})):
            with self.subTest(metin=metin):
                self.assertEqual(_masraf(metin), beklenen)

    def test_muafiyet_yoksa_muaf_ucret_anahtari_da_YOK(self):
        """Anahtar yalnız muafiyet yolunda eklenir — şema kirlenmesin."""
        self.assertNotIn("muaf_ucret", _masraf("masrafsız finansman"))

    def test_alan_disi_ozne_kapisi_muafiyette_de_gecerli(self):
        """SMS/KVKK kapısı (`_ALAN_DISI_OZNE_RE`) muafiyet yolunda da çalışır."""
        self.assertIsNone(_masraf(
            "Katılım SMS'i ücreti banka tarafından karşılanmaktadır"))


if __name__ == "__main__":
    unittest.main()
