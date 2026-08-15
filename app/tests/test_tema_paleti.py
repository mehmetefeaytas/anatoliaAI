"""Kullanıcının seçtiği tema, ÖLÇÜLEN paletin aynısını kullanmalı.

İlgili: ../web/app/styles/tema.css, ../web/app/styles/tokens.css,
        ../scripts/kontrast_kontrol.py, ./test_kontrast.py

## Bu testin varlık sebebi

Kontrast kapısı `tokens.css`'i ölçer: `:root` bloğundan açık paleti,
`prefers-color-scheme: dark` bloğundan koyu paleti çözer ve her metin/zemin
çiftinin AA eşiğini geçtiğini doğrular.

Kullanıcının elle seçtiği tema ise başka bir dosyada, `tema.css`'te yaşar:
`:root[data-tema="acik"]` ve `:root[data-tema="koyu"]` blokları sistem
tercihini ezer. Saf CSS'te bir bildirim kümesi hem medya sorgusunun içine hem
dışına aynı anda konamaz, bu yüzden değerler TEKRARLANIR.

Tekrarın sessiz kayma riski buradadır: `tokens.css`'teki bir rengin
düzeltilmesi `tema.css`'e yansımazsa, kontrast kapısı düzeltilmiş paleti
ölçmeye devam eder ve KULLANICININ GÖRDÜĞÜ palet ölçüsüz kalır. Kapı yeşil
yanar, ekran bozulur.

Bu test o boşluğu kapatır: seçilen temanın her değeri, ölçülen paletteki
karşılığıyla birebir aynı olmak zorundadır. Aynıysa, `test_kontrast.py`'nin
verdiği AA garantisi seçilen temalar için de geçerlidir.

Ara token (`--koyu-bg: …` + `--bg: var(--koyu-bg)`) tekrarı kaldırırdı ama
kontrast betiği düz `hex` okur; `var(...)` gören betik o paleti ölçemez ve
sessizce "temiz" derdi. Ölçülemeyen bir palet, ölçülmüş bir tekrarın yerini
tutmaz — bu yüzden tekrar KASITLIDIR ve testle bağlanmıştır.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests._ortam_gereksinimleri import arayuz_gerekir

_KOK = Path(__file__).resolve().parents[1]
TOKENS_CSS = _KOK / "web" / "app" / "styles" / "tokens.css"
TEMA_CSS = _KOK / "web" / "app" / "styles" / "tema.css"
BASKI_CSS = _KOK / "web" / "app" / "styles" / "baski.css"

_BILDIRIM = re.compile(r"(--[a-z0-9-]+)\s*:\s*([^;]+);")
_KOYU_MEDYA = re.compile(
    r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{(.*)\}", re.DOTALL
)


def _bildirimler(govde: str) -> dict[str, str]:
    """Bir CSS gövdesindeki `--token: değer;` çiftleri."""
    return {ad: deger.strip() for ad, deger in _BILDIRIM.findall(govde)}


def _secici_govdesi(css: str, secici: str) -> str:
    """`secici { … }` bloğunun gövdesi. Blok yoksa `AssertionError`."""
    baslangic = css.find(secici)
    assert baslangic != -1, f"{secici} bloğu yok"
    ac = css.index("{", baslangic)
    kapa = css.index("}", ac)
    return css[ac + 1 : kapa]


@arayuz_gerekir
class TestTemaPaleti(unittest.TestCase):
    """`tema.css` ile `tokens.css` arasında değer kayması OLMAMALI."""

    @classmethod
    def setUpClass(cls) -> None:
        tokens = TOKENS_CSS.read_text(encoding="utf-8")
        tema = TEMA_CSS.read_text(encoding="utf-8")

        koyu_medya = _KOYU_MEDYA.search(tokens)
        assert koyu_medya, "tokens.css'te koyu tema medya sorgusu bulunamadı"
        cls.koyu_kaynak = _bildirimler(koyu_medya.group(1))
        # Açık palet: koyu bloğun DIŞINDA kalan bildirimler.
        cls.acik_kaynak = _bildirimler(tokens.replace(koyu_medya.group(1), ""))

        cls.acik_secim = _bildirimler(_secici_govdesi(tema, ':root[data-tema="acik"]'))
        cls.koyu_secim = _bildirimler(_secici_govdesi(tema, ':root[data-tema="koyu"]'))

    def test_paletler_BOS_COZULMEDI(self) -> None:
        """Ayrıştırma bozulursa diğer testler boş küme üzerinde koşar.

        Boş bir döngü her zaman geçer. Bu yüzden önce, çözümün gerçekten bir
        palet bulduğu ölçülür — aksi hâlde bu dosya bir tiyatroya dönüşür.
        """
        self.assertGreaterEqual(len(self.koyu_kaynak), 15)
        self.assertGreaterEqual(len(self.acik_kaynak), 15)
        for ad in ("--bg", "--fg", "--accent", "--on-accent"):
            with self.subTest(token=ad):
                self.assertIn(ad, self.koyu_kaynak)
                self.assertIn(ad, self.acik_kaynak)

    def test_koyu_secim_koyu_paletin_AYNISI(self) -> None:
        """Elle seçilen koyu tema, sistemin verdiği koyu temayla aynı olmalı."""
        for ad, beklenen in self.koyu_kaynak.items():
            with self.subTest(token=ad):
                self.assertEqual(
                    self.koyu_secim.get(ad),
                    beklenen,
                    f"{ad}: seçilen koyu tema, ölçülen koyu paletten sapıyor",
                )

    def test_acik_secim_acik_paletin_AYNISI(self) -> None:
        """Elle seçilen açık tema, `:root`'taki açık paletle aynı olmalı.

        Kapsam koyu bloğun yeniden tanımladığı tokenlardır: sistem koyuyken
        «Açık» seçen kullanıcı için EZİLMESİ GEREKEN tokenlar tam olarak
        bunlardır. Ötekiler zaten `:root`'tan devralınır.
        """
        for ad in self.koyu_kaynak:
            with self.subTest(token=ad):
                self.assertEqual(
                    self.acik_secim.get(ad),
                    self.acik_kaynak.get(ad),
                    f"{ad}: seçilen açık tema, ölçülen açık paletten sapıyor",
                )

    def test_koyu_blogun_EZDIGI_her_token_iki_secimde_de_var(self) -> None:
        """Eksik bir token, iki paletin karışmasıyla sonuçlanır.

        Koyu blok `--bg`yi ezip `--fg`yi ezmeseydi, sistem koyuyken «Açık»
        seçen kullanıcı açık zemin üstünde açık metin görürdü. Kayma değil,
        EKSİKLİK de bir kusurdur ve ayrı ölçülür.
        """
        for ad in self.koyu_kaynak:
            with self.subTest(token=ad):
                self.assertIn(ad, self.acik_secim, f"{ad} açık seçimde tanımsız")
                self.assertIn(ad, self.koyu_secim, f"{ad} koyu seçimde tanımsız")

    def test_secim_tanimsiz_token_UYDURMAZ(self) -> None:
        """Seçim blokları paletin dışına çıkmamalı.

        `tokens.css` tek doğruluk kaynağıdır. Yalnız seçim bloklarında yaşayan
        bir renk, kontrast kapısının hiç görmediği bir renktir.
        """
        palet = set(self.acik_kaynak) | set(self.koyu_kaynak)
        for ad, blok in (("acik", self.acik_secim), ("koyu", self.koyu_secim)):
            for token in blok:
                with self.subTest(secim=ad, token=token):
                    self.assertIn(
                        token, palet, f"{token} yalnız tema.css'te tanımlı"
                    )


@arayuz_gerekir
class TestBaskiPaleti(unittest.TestCase):
    """Baskı paleti, paletin ÜÇÜNCÜ kopyasıdır ve o da kayabilir.

    `styles/baski.css` koyu temayı baskıda zorla açık palete çevirir: koyu bir
    PDF okunmaz ve toner yakar. Ama bu, aynı hex değerlerinin depoda üçüncü kez
    yazılması demek — `tema.css`'in başlığında açıklanan aynı çıkmaz geçerli:
    saf CSS'te bir bildirim kümesi hem `@media print` içine hem dışına aynı
    anda konamaz, ve ara token kullanmak kontrast kapısını kör ederdi (kapı düz
    `hex` okur, `var(...)` göreni ölçemez).

    O yüzden kopya teste bağlanır. `tema.css` için kurulan emsalin aynısı:
    kopya kayarsa kapı düşer, sessizce sapmaz.
    """

    @classmethod
    def setUpClass(cls) -> None:
        tokens = TOKENS_CSS.read_text(encoding="utf-8")
        baski = BASKI_CSS.read_text(encoding="utf-8")

        cls.acik_kaynak = _bildirimler(_KOYU_MEDYA.sub("", tokens))
        koyu = _KOYU_MEDYA.search(tokens)
        assert koyu, "tokens.css'te koyu blok yok"
        cls.koyu_kaynak = _bildirimler(koyu.group(1))
        # Baskı bloğu üç seçiciyi birden hedefler; gövde tektir.
        cls.baski = _bildirimler(
            _secici_govdesi(baski, ':root[data-tema="koyu"]')
        )

    def test_baski_bloguu_COZULDU(self) -> None:
        self.assertGreater(len(self.baski), 10, "baskı paleti boş çözüldü")

    def test_baski_paleti_ACIK_PALETIN_AYNISI(self) -> None:
        """Baskıda basılan her renk, ölçülmüş açık paletten gelmeli.

        Kapsam koyu bloğun yeniden tanımladığı tokenlardır: koyu temada açılan
        bir sayfa yazdırıldığında EZİLMESİ GEREKEN tokenlar tam olarak
        bunlardır. Gölge dışarıda — kâğıtta yükseklik anlamsız, `none` bilinçli
        bir sapmadır.
        """
        for ad in self.koyu_kaynak:
            if ad.startswith("--shadow"):
                continue
            if ad not in self.baski:
                continue
            with self.subTest(token=ad):
                self.assertEqual(
                    self.baski[ad],
                    self.acik_kaynak.get(ad),
                    f"{ad}: baskı paleti, ölçülen açık paletten sapıyor",
                )

    def test_koyu_blogun_EZDIGI_her_RENK_baskida_da_var(self) -> None:
        """Eksik bir token, koyu temada yazdırılan sayfada karışık palet demek.

        Örneğin `--fg` ezilip `--bg` unutulursa kâğıda koyu zemin üstüne koyu
        metin basılır — ekranda hiç görünmeyen, yalnız çıktıda ortaya çıkan bir
        kusur.
        """
        for ad in self.koyu_kaynak:
            if ad.startswith("--shadow"):
                continue
            with self.subTest(token=ad):
                self.assertIn(ad, self.baski, f"{ad} baskı paletinde tanımsız")

    def test_baski_tanimsiz_token_UYDURMAZ(self) -> None:
        palet = set(self.acik_kaynak) | set(self.koyu_kaynak)
        for token in self.baski:
            with self.subTest(token=token):
                self.assertIn(
                    token, palet, f"{token} yalnız baski.css'te tanımlı"
                )


if __name__ == "__main__":
    unittest.main()
