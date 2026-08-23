"""RAG erişiminde diakritiksiz sorgu köprüsü.

İlgili: ../src/chatbot/rag.py (`KeywordRetriever._cozumle`, `_ascii_kopru`),
        tests/test_rag_sapkali_unlu.py (şapkalı ünlü kusuru — AYRI bir kusur),
        ../docs/PROJE-DOKUMANTASYONU.md (RAG örneği olarak bu soruyu kullanıyor)

## Neden bu testler

5. tur fonksiyonellik jürisi ölçülmüş bir asimetri buldu:

    "Konut finansmani kampanyasinin kosullari neler?"  -> 0 kaynak, "bilgi yok"
    "Konut finansmanı kampanyasının koşulları neler?"  -> 3 kaynak

Yapısal kol diakritiksiz girdiyi sorunsuz işliyordu; RAG kolu işlemiyordu.
Türkçe klavyesi olmayan ya da hızlı yazan kullanıcı birinci biçimi yazar —
üstelik projenin KENDİ dokümantasyonu RAG örneği olarak birebir o soruyu
kullanıyor, yani kusur teslim edilen belgede gösteriliyordu.

## Çözümün hangi kısmı kilitleniyor

Dizin ASCII'ye ÇÖKERTİLMEDİ. `_tokenize`'ın "`ş ç ğ ı ö ü` ayırt edicidir,
'sac' ile 'saç' birleşmemeli" kararı duruyor. Köprü yalnız **dizinde hiç
karşılığı olmayan** sorgu token'ı için devreye girer. Buradaki testler tam
bu sınırı kilitliyor:

1. Diakritiksiz sorgu artık sonuç döndürür (kusurun kendisi).
2. Dizinde gerçekten var olan bir token GENİŞLETİLMEZ — 'sac' korpusta
   geçiyorsa 'saç'a köprülenmez (hassasiyet korunur).
3. Bir soru sözcüğü iki yazıma çözülse bile örtüşme belge başına **bir kez**
   sayılır; aksi hâlde köprü `min_overlap` kapısını şişirerek delerdi.
4. Eşik ORİJİNAL token sayısına dayanır; köprü yeni soru sözcüğü üretmez.
5. Skorda grup içi **en iyi** varyant alınır, varyantlar toplanmaz — aynı
   soru sözcüğünü çift saymak sıralamayı köprülü sorgularda şişirirdi.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.chatbot import rag


class SahteRepo:
    """`all_campaigns()` dışında hiçbir şey sunmayan asgari depo."""

    def __init__(self, metinler: list[str]):
        self._kayitlar = [
            {
                "id": i + 1,
                "bank": f"banka-{i}",
                "bank_name": f"Banka {i}",
                "campaign_type": "Konut Finansmanı",
                "source_url": f"https://ornek/{i}",
                "raw_text": m,
            }
            for i, m in enumerate(metinler)
        ]

    def all_campaigns(self) -> list[dict]:
        return list(self._kayitlar)


def _retriever(metinler: list[str], min_overlap: int = rag.MIN_OVERLAP):
    return rag.KeywordRetriever(SahteRepo(metinler), min_overlap=min_overlap)


class KusurunKendisi(unittest.TestCase):
    def test_diakritiksiz_sorgu_sonuc_dondurur(self):
        r = _retriever([
            "Konut finansmanı kampanyasının koşulları şunlardır: vade 120 ay.",
            "Taşıt finansmanı kampanyası; kâr payı oranı aylık %2,05.",
        ])
        aksanli = r.retrieve("Konut finansmanı koşulları", k=3)
        aksansiz = r.retrieve("Konut finansmani kosullari", k=3)
        self.assertTrue(aksanli, "referans sorgu boş döndü — zemin bozuk")
        self.assertTrue(
            aksansiz,
            "diakritiksiz sorgu 0 pasaj döndürdü — jüri 2'nin bulduğu kusur geri geldi")
        self.assertEqual(
            [h["campaign_id"] for h in aksansiz],
            [h["campaign_id"] for h in aksanli])

    def test_sapkasiz_yazim_da_koprulenir(self):
        """`_SAPKA_INDIRGEME` yalnız `â î û` katlar; `ı` onun işi değil."""
        r = _retriever([
            "Kâr payı oranı ve vade bilgileri kampanya sayfasındadır.",
            "Alışveriş puanı kampanyası: her harcamada puan.",
        ])
        self.assertTrue(r.retrieve("kar payi orani", k=3))


class HassasiyetKorunuyor(unittest.TestCase):
    def test_dizinde_var_olan_token_genisletilmez(self):
        """'sac' korpusta geçiyorsa 'saç'a köprülenmez."""
        r = _retriever([
            "Sac levha alımı için ticari finansman kampanyası.",
            "Saç bakım ürünlerinde alışveriş puanı kampanyası.",
        ])
        gruplar = r._cozumle({"sac", "finansman"})
        for grup in gruplar:
            self.assertEqual(len(grup), 1, f"gereksiz genişletme: {grup}")
        self.assertIn(["sac"], gruplar)

    def test_kopru_yalnizca_karsiligi_olmayan_tokende_calisir(self):
        r = _retriever(["Taşıt finansmanı kampanyası vade 36 ay."])
        # 'taşıt' dizinde var -> tek eleman
        self.assertEqual(r._cozumle({"taşıt"}), [["taşıt"]])
        # 'tasit' dizinde YOK -> 'taşıt'a köprülenir
        self.assertEqual(r._cozumle({"tasit"}), [["taşıt"]])

    def test_karsiligi_hic_olmayan_token_kendisi_kalir(self):
        """Ne dizinde ne köprüde varsa token olduğu gibi kalır (0 posting)."""
        r = _retriever(["Konut finansmanı kampanyası."])
        self.assertEqual(r._cozumle({"zeplin"}), [["zeplin"]])


class KapiSismiyor(unittest.TestCase):
    def test_ortusme_grup_basina_bir_kez_sayilir(self):
        """Bir soru sözcüğü iki yazıma çözülüp ikisi aynı belgede geçse bile +1."""
        # Aynı belgede hem 'finansmanı' hem 'fınansmanı' (noktasız ı) var.
        r = _retriever([
            "Konut finansmanı ve konut fınansmanı aynı belgede geçiyor.",
        ], min_overlap=2)
        gruplar = r._cozumle({"finansmani"})
        self.assertEqual(len(gruplar), 1, "tek soru sözcüğü tek grup olmalı")
        self.assertGreaterEqual(len(gruplar[0]), 2, "iki yazım da köprüde olmalı")
        overlaps = r._count_overlaps(gruplar)
        self.assertEqual(
            set(overlaps.values()), {1},
            "iki varyant aynı belgede sayıldı — köprü min_overlap kapısını deliyor")

    def test_esik_orijinal_token_sayisina_dayanir(self):
        """Köprü varyant açar ama yeni SORU SÖZCÜĞÜ üretmez."""
        r = _retriever([
            "Konut finansmanı ve konut fınansmanı aynı belgede geçiyor.",
        ], min_overlap=2)
        qtok = set(rag._tokenize("finansmani"))
        self.assertEqual(len(qtok), 1)
        # Tek sözcüklü soruda etkin eşik 1'e iner; köprü bunu 2'ye çıkarmamalı.
        self.assertEqual(rag._etkin_esik(r.min_overlap, qtok), 1)
        self.assertTrue(r.retrieve("finansmani", k=3))


class SkorSismiyor(unittest.TestCase):
    def test_grup_ici_en_iyi_varyant_alinir_toplanmaz(self):
        metinler = [
            "Konut finansmanı kampanyası birinci belge.",
            "Konut finansmanı ve ayrıca konut fınansmanı ikinci belge.",
        ]
        r = _retriever(metinler)
        grup = r._cozumle({"finansmani"})
        self.assertGreaterEqual(len(grup[0]), 2, "zemin: iki yazım köprüde olmalı")

        max_skor = r._bm25_skorlari(grup)
        # Toplama davranışının taklidi: her varyantı AYRI grup gibi ver.
        toplam_skor = r._bm25_skorlari([[t] for t in grup[0]])
        i = 1  # iki yazımı birden taşıyan belge
        self.assertLess(
            max_skor.get(i, 0.0), toplam_skor.get(i, 0.0),
            "grup içi max, varyant toplamından küçük olmalı — yoksa çift sayım var")

    def test_tek_elemanli_grupta_max_toplama_esittir(self):
        """Doğru yazılmış sorguda değişiklik HİÇBİR ŞEYİ etkilemez."""
        r = _retriever([
            "Konut finansmanı kampanyası vade 120 ay.",
            "Taşıt finansmanı kampanyası vade 36 ay.",
        ])
        grup = [["finansmanı"], ["vade"]]
        for g in grup:
            self.assertEqual(r._cozumle(set(g)), [g], "zemin: token doğrudan bulunmalı")
        self.assertEqual(r._bm25_skorlari(grup),
                         r._bm25_skorlari([["finansmanı"], ["vade"]]))


class KopruYapisi(unittest.TestCase):
    def test_kopru_anahtarlari_ascii(self):
        r = _retriever(["Kâr payı oranı, taşıt finansmanı, alışveriş puanı."])
        for anahtar in r._ascii_kopru:
            self.assertEqual(
                anahtar, rag.tr_fold_ascii(anahtar),
                f"köprü anahtarı ASCII katlanmış olmalı: {anahtar!r}")

    def test_bos_korpusta_kopru_bos(self):
        r = _retriever([])
        self.assertEqual(r._ascii_kopru, {})
        self.assertEqual(r.retrieve("konut finansmanı", k=3), [])


if __name__ == "__main__":
    unittest.main()
