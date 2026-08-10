"""Özetin EKRANDAKİ hâli — kısa boşluk notu, «AI» sözcüğü, korunan dürüstlük.

İlgili: ../web/app/components/SummaryNotice.tsx, ../web/app/components/SummaryCoverage.tsx
        ../web/app/styles/components.css, ./test_ozet.py (üretim tarafı),
        ./test_ic_referans_sizmasi.py (aynı teknik: JSX gövdesini tarama)

## Bu dosyanın koruduğu üç şey

1. **Boşluk notu KISA kalır.** İlk yazılan not dört cümleydi ve kendini
   savunuyordu ("Eksik özet, belgenin kendisiyle ilgili bir eksiklik
   değildir…"). Ekranların çoğunda görünen bir not, anlattığı belgeden çok yer
   kaplayınca bilgi değil gürültü olur. Not iki cümleye indirildi; bu test onu
   yeniden uzamaya karşı kilitler.

2. **Kısalırken dürüstlük DÜŞMEZ.** Kısaltma sırasında feda edilmesi en kolay
   iki cümle şunlardı: özetin üretilmediği ve uydurulmayacağı. İkisi de
   kalmak ZORUNDA — `src/summarize/ozet.py` sahte özeti kural düzeyinde
   yasaklıyor, arayüzün o yasağı söylemeyi bırakması yasağı görünmez kılardı.

3. **Görünen sözcük «AI».** «LLM» bir mimari adıdır; paneli okuyan jüri ya da
   banka kullanıcısı için bir şey ifade etmez. Şema adları (`ozet_kaynak`
   değeri `"llm"`, `.badge-llm` sınıfı) DEĞİŞMEZ — onlar veri sözleşmesidir.
   Değişen yalnız kullanıcının okuduğu dizgedir.

## Neden dosya taraması

Bileşenler TSX; bu repoda JSX'i çalıştıran bir test koşucusu yok. Aynı sorun
`test_ic_referans_sizmasi.py` içinde de vardı ve orada çözüm dosyayı okuyup
yorumları eleyerek GÖRÜNÜR metni taramaktı. Aynı teknik burada da yeterli:
korunan şey davranış değil, ekrana basılan sabit metin.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

_KOK = Path(__file__).resolve().parents[1]
_BILESENLER = _KOK / "web" / "app" / "components"

NOTICE = _BILESENLER / "SummaryNotice.tsx"
COVERAGE = _BILESENLER / "SummaryCoverage.tsx"

_BLOK_YORUM = re.compile(r"/\*.*?\*/", re.DOTALL)
_SATIR_YORUM = re.compile(r"^\s*(//|\*).*$", re.MULTILINE)

#: Boşluk notunun gövdesi (`<p className="summary-body">…</p>`).
_BOS_GOVDE = re.compile(
    r'summary-empty.*?<p className="summary-body">(.*?)</p>', re.DOTALL)

#: Boşluk notunun üst satırı (rozetin yanındaki cümle).
_BOS_ETIKET = re.compile(
    r'summary-empty.*?<span className="summary-note">(.*?)</span>', re.DOTALL)

#: İki cümlelik notun üst sınırı. Ölçüm: yürürlükteki metin 122 karakter,
#: kaldırılan eski metin 239 karakterdi. 160 ikisinin arasında durur —
#: bir cümle daha eklemek testi kırar, sözcük düzeltmesi kırmaz.
BOSLUK_NOTU_SINIRI = 160


def _gorunur(yol: Path) -> str:
    """Dosyanın yorumları ELENMİŞ hâli — geriye kod + görünür metin kalır."""
    govde = _BLOK_YORUM.sub("", yol.read_text(encoding="utf-8"))
    return _SATIR_YORUM.sub("", govde)


def _sadelestir(jsx: str) -> str:
    """JSX gövdesini tek satırlık düz metne indirger (JSX ifadeleri atılır)."""
    duz = re.sub(r"\{[^}]*\}", " ", jsx)
    duz = re.sub(r"<[^>]*>", " ", duz)
    duz = duz.replace("&apos;", "'").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", duz).strip()


class TestBoslukNotuKisa(unittest.TestCase):
    """«Özet üretilmedi» notu ekranda yer kaplamamalı."""

    def setUp(self) -> None:
        self.kaynak = _gorunur(NOTICE)

    def test_govde_iki_cumleyi_asmaz(self) -> None:
        m = _BOS_GOVDE.search(self.kaynak)
        self.assertIsNotNone(m, "boş özet gövdesi bulunamadı")
        metin = _sadelestir(m.group(1))
        self.assertLessEqual(
            len(metin), BOSLUK_NOTU_SINIRI,
            f"boşluk notu yeniden uzadı ({len(metin)} karakter): {metin!r}")

    def test_govde_bir_ekran_dolusu_cumle_icermez(self) -> None:
        """Cümle sayısı da sınırlı: uzunluk tek başına kandırılabilir."""
        m = _BOS_GOVDE.search(self.kaynak)
        assert m is not None
        metin = _sadelestir(m.group(1))
        cumle = [c for c in re.split(r"[.!?]\s", metin) if c.strip()]
        self.assertLessEqual(len(cumle), 2,
                             f"boşluk notu {len(cumle)} cümleye çıkmış")


class TestDurustlukKorundu(unittest.TestCase):
    """Kısaltma, sahte özet yasağını GÖRÜNMEZ kılmamalı."""

    def setUp(self) -> None:
        self.kaynak = _gorunur(NOTICE)
        m = _BOS_GOVDE.search(self.kaynak)
        assert m is not None, "boş özet gövdesi bulunamadı"
        e = _BOS_ETIKET.search(self.kaynak)
        assert e is not None, "boş özet etiketi bulunamadı"
        self.bos_metin = _sadelestir(e.group(1) + " " + m.group(1))

    def test_uretilmedigi_yaziyor(self) -> None:
        self.assertRegex(
            self.bos_metin, r"[Uu]ydurma",
            "sahte özet basılmayacağı VAADİ nottan düşmüş: " + self.bos_metin)

    def test_uydurulmayacagi_yaziyor(self) -> None:
        self.assertRegex(
            self.bos_metin, r"[Uu]ydurma|uydurul",
            "sahte özet yasağı notttan düşmüş: " + self.bos_metin)

    def test_kaynak_metnin_durdugu_yaziyor(self) -> None:
        self.assertIn(
            "kaynak metin", self.bos_metin.lower(),
            "boşluğun kaynak metni etkilemediği bilgisi düşmüş: "
            + self.bos_metin)


class TestGorunenSozcukAI(unittest.TestCase):
    """Kullanıcının okuduğu etiket «AI»dır; şema adları «llm» kalır."""

    #: Kullanıcıya dönük metinde artık geçmemesi gereken kalıplar.
    YASAK = re.compile(r"LLM özeti|LLM Özeti|LLM tarafından|yerel LLM")

    def test_gorunur_metinde_LLM_etiketi_YOK(self) -> None:
        bulgular = []
        for yol in (NOTICE, COVERAGE):
            for m in self.YASAK.finditer(_gorunur(yol)):
                bulgular.append(f"{yol.name}: {m.group()}")
        self.assertEqual(
            bulgular, [],
            "kullanıcıya görünen metinde eski «LLM» etiketi: "
            + "; ".join(bulgular))

    def test_AI_ozeti_etiketi_var(self) -> None:
        self.assertIn("AI özeti", _gorunur(NOTICE))
        self.assertIn("AI özeti", _gorunur(COVERAGE))

    def test_sema_adlari_DEGISMEDI(self) -> None:
        """`llm` anahtarı ve `.badge-llm` sınıfı veri sözleşmesidir.

        Etiketi çevirirken bunları da çevirmek, API'nin `ozet_kaynak: "llm"`
        değeriyle arayüzün eşleşmesini sessizce bozardı.
        """
        kaynak = NOTICE.read_text(encoding="utf-8")
        self.assertIn("llm:", kaynak, "KAYNAK_ETIKET'in `llm` anahtarı kaybolmuş")
        self.assertIn("badge-llm", kaynak)
        self.assertIn("badge-llm", COVERAGE.read_text(encoding="utf-8"))


class TestSummaryNoteSinifi(unittest.TestCase):
    """Etiket cümlesi BÜYÜK HARFE çevrilmez — `.summary-note` bunu sağlar."""

    def test_sinif_hem_kullaniliyor_hem_tanimli(self) -> None:
        kaynak = NOTICE.read_text(encoding="utf-8")
        self.assertIn('className="summary-note"', kaynak)
        css = (_KOK / "web" / "app" / "styles" / "components.css").read_text(
            encoding="utf-8")
        self.assertIn(".summary-note", css)
        # Sınıfın tek işi büyük harf dönüşümünü geri almaktır; kaybolursa
        # ekranda tam bir cümle bağırmaya başlar.
        blok = css.split(".summary-note", 1)[1].split("}", 1)[0]
        self.assertIn("text-transform: none", blok)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
