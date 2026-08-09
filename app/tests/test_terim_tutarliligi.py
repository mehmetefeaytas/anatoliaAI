"""Kıyas yüzeylerinde `campaign_type` kavramının TEK adı olmalı.

İlgili: ../web/app/components/ComparePanel.tsx, BankDeltaPanel.tsx,
        AdvantageousPanel.tsx, FairnessNotice.tsx, ScoringExplainer.tsx

## Bu testin varlık sebebi

Karşılaştırma ekranında aynı kavram — `campaign_type` alanı, yani 8 sınıflı
kampanya türü — iki ayrı adla dolaşıyordu:

  - açılır süzgecin etiketi:        «Kampanya türü»
  - hemen altındaki tablo notu:     «sıra numaraları ürün ailesi içinde…»
  - banka içi delta ekranı:         «Ürün ailesi» (süzgeç etiketi)

Kullanıcı bunların İKİ FARKLI süzgeç olduğunu sandığını bildirdi. Sanması
makuldü: aynı ekranda iki farklı ad gören biri, iki farklı şey olduğu sonucuna
varır. «Ürün ailesi» iç jargondu; şartnamedeki ve sınıflandırıcıdaki resmî ad
«kampanya türü»dür (Finansman, İhtiyaç Finansmanı, Konut Finansmanı, Taşıt
Finansmanı, Kart, Alışveriş Puanı, Yeni Müşteri, Yatırım Ürünü).

Terim birleştirildi. Bu test, ayrışmanın GERİ GELMESİNİ kapıya bağlar: bir
sonraki geliştirici tek bir yerde «ürün ailesi» yazarsa derleme değil, test
kırılır.

## Neyi denetler, neyi denetlemez

Yalnız **kullanıcının okuduğu dizge** denetlenir. Yorum satırlarında «ürün
ailesi» SERBESTTİR ve gereklidir: yukarıdaki tarihçe ancak orada anlatılabilir.
Ayrım `tests/test_ic_referans_sizmasi.py` ile aynı yöntemle yapılır — blok ve
satır yorumları silinir, kalan gövde taranır.

Sunucu tarafındaki dizgeler (`fairness_note` gibi) bu testin kapsamında
DEĞİLDİR; `src/api/main.py` ayrı bir sahiplik alanıdır. Kapsam genişletilecekse
oradaki metinler önce düzeltilmelidir.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

_KOK = Path(__file__).resolve().parents[1]
_TSX = _KOK / "web" / "app"

#: Kavramın TEK ADI. Sekiz sınıfın resmî üst başlığı.
KANONIK = "kampanya türü"

#: Kullanıcıya görünen metinde yasak eş-adlar.
#:
#: `aile` kökü tek başına da yasaktır: ekranda gerçekten aile kavramı yok, bu
#: kök yalnız `campaign_type`'ın eski adından gelebilir. Yasağı «ürün ailesi»
#: tam ifadesiyle sınırlamak yeterli DEĞİLDİ — kusurun en sinsi hâli
#: «bu ailede belgesi yok» gibi tek kelimelik kalıntılardı.
YASAK = re.compile(r"ürün +ailes\w*|\baile\w*", re.IGNORECASE)

_BLOK_YORUM = re.compile(r"/\*.*?\*/", re.DOTALL)
_SATIR_YORUM = re.compile(r"^\s*(//|\*).*$", re.MULTILINE)

#: CLAUDE.md §12'deki 8 sınıf — tanım bloğunda hepsi sayılmalı.
SEKIZ_SINIF = (
    "Finansman",
    "İhtiyaç Finansmanı",
    "Konut Finansmanı",
    "Taşıt Finansmanı",
    "Kart",
    "Alışveriş Puanı",
    "Yeni Müşteri",
    "Yatırım Ürünü",
)

#: Kavramı kullanan, kullanıcıya dönük kıyas yüzeyleri.
KIYAS_YUZEYLERI = (
    "components/ComparePanel.tsx",
    "components/BankDeltaPanel.tsx",
    "components/AdvantageousPanel.tsx",
)


def gorunur_metin(yol: Path) -> str:
    """Dosyanın yorumları silinmiş — yani kullanıcıya ulaşabilen — gövdesi."""
    govde = _BLOK_YORUM.sub("", yol.read_text(encoding="utf-8"))
    return _SATIR_YORUM.sub("", govde)


class TestEskiTerimGeriGelmez(unittest.TestCase):
    """«Ürün ailesi» hiçbir görünür dizgede olmamalı."""

    def test_gorunur_metinde_urun_ailesi_YOK(self) -> None:
        bulgular = []
        for p in sorted(_TSX.rglob("*.tsx")):
            govde = gorunur_metin(p)
            for m in YASAK.finditer(govde):
                satir = govde[: m.start()].count("\n") + 1
                bulgular.append(f"{p.relative_to(_KOK)}:~{satir} «{m.group()}»")
        self.assertEqual(
            bulgular,
            [],
            "kullanıcıya görünen metinde eski terim kalmış; kanonik ad "
            f"«{KANONIK}»: " + "; ".join(bulgular),
        )

    def test_yorumlarda_SERBEST(self) -> None:
        """Tarihçeyi anlatan yorum silinmemeli — test onu görmemeli."""
        ornek = (
            "/**\n * Eskiden «ürün ailesi» deniyordu.\n */\n"
            "const x = <p>Kampanya türü içinde sıralanır.</p>;\n"
        )
        temiz = _SATIR_YORUM.sub("", _BLOK_YORUM.sub("", ornek))
        self.assertIsNone(YASAK.search(temiz))


class TestKanonikTerimKullaniliyor(unittest.TestCase):
    """Her kıyas yüzeyi kavrama kanonik adıyla seslenmeli."""

    def test_kiyas_yuzeyleri_kanonik_adi_yazar(self) -> None:
        eksik = [
            ad
            for ad in KIYAS_YUZEYLERI
            if KANONIK not in gorunur_metin(_TSX / ad).lower()
        ]
        self.assertEqual(
            eksik, [], f"«{KANONIK}» ifadesi görünür metinde geçmiyor: {eksik}"
        )


class TestTanimBirKezYazilir(unittest.TestCase):
    """Kavramın NE OLDUĞU tek yerde, sekiz sınıf sayılarak yazılmalı.

    Kullanıcı «bu iki şey aynı mı?» diye soruyorsa terimi birleştirmek yetmez;
    kavramın tanımı da bir yerde AÇIKÇA durmalıdır. Tanımın yeri adil kıyas
    şeridi (`FairnessNotice`): her kıyas yüzeyinin bastığı tek ortak bileşen.
    """

    def setUp(self) -> None:
        self.metin = gorunur_metin(_TSX / "components" / "FairnessNotice.tsx")

    def test_sekiz_sinifin_tamami_sayilir(self) -> None:
        eksik = [s for s in SEKIZ_SINIF if s not in self.metin]
        self.assertEqual(
            eksik, [], f"tanım bloğunda sayılmayan kampanya türü: {eksik}"
        )

    def test_tur_ici_siralama_gerekcesi_yazili(self) -> None:
        self.assertIn("alternatifi değildir", self.metin)
        self.assertIn("tür içinde", self.metin)


class TestYakalar(unittest.TestCase):
    """Denetçi gerçek bir sızıntıyı bulmalı (yanlış negatif kapısı)."""

    def test_yasak_desen_calisir(self) -> None:
        self.assertTrue(YASAK.search("Sıra numaraları ürün ailesi içinde verilir"))
        self.assertTrue(YASAK.search("Ürün Ailesi"))
        self.assertTrue(YASAK.search("bu ailede belgesi yok"))
        self.assertTrue(YASAK.search("aileler arası sıralama"))
        self.assertIsNone(YASAK.search("Kampanya türü içinde sıralanır."))


if __name__ == "__main__":
    unittest.main()
