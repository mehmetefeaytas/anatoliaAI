"""WCAG kontrast kapısı — `web/app/styles/tokens.css` paletini ÖLÇER.

İlgili: web/app/styles/tokens.css, tests/test_kontrast.py

## Bu betiğin varlık sebebi

Arayüz yeniden tasarımında "renk uyumu" bir iddiadır ve bu projede iddialar
ölçülür (CLAUDE.md §16 mantığının tasarıma uygulanmış hâli). Palet iki temaya
çıkınca göz kararı büsbütün yetersiz kalır: açık temada okunan bir gri, koyu
temada AA sınırının altına düşebilir ve bunu kimse fark etmez.

Betik `tokens.css`'i okur, `:root` bloğundan AÇIK temayı,
`@media (prefers-color-scheme: dark)` bloğundan KOYU temayı çözer ve aşağıda
adı geçen her metin/zemin çiftinin kontrast oranını WCAG 2.1 formülüyle
hesaplar.

## Eşik

Normal metin için **4,5:1** (AA). Büyük metin (>= 18,66px kalın veya 24px)
için 3:1 yeterlidir, ama burada gevşetme YAPILMAZ: eşiği tek tutmak, bir
tokenın sonradan küçük metinde kullanılmasıyla sessizce ihlale düşmesini
önler.

`--mark` bir ZEMİN rengidir, metin değil; üstüne gelen `--on-mark` ile
çiftlenerek ölçülür. Aynı şekilde `--accent` zemininin metni `--on-accent`.

## Kullanım

    .venv/bin/python -m scripts.kontrast_kontrol
    .venv/bin/python -m scripts.kontrast_kontrol --ayrinti   # geçenleri de yaz

Çıkış kodu: ihlal varsa 1, yoksa 0.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

_KOK = Path(__file__).resolve().parents[1]
TOKENS_CSS = _KOK / "web" / "app" / "styles" / "tokens.css"

#: Normal metin için WCAG AA eşiği.
ESIK = 4.5

#: Ölçülen çiftler: (metin tokenı, zemin tokenı, nerede kullanıldığı).
#: Yeni bir renk kombinasyonu bileşen CSS'ine girdiğinde buraya da eklenir —
#: liste, paletin "sözleşmesi"dir.
CIFTLER: tuple[tuple[str, str, str], ...] = (
    ("--fg", "--bg", "sayfa gövdesi"),
    ("--fg", "--bg-2", "kart içi gövde metni"),
    ("--fg", "--bg-3", "çip metni (seçili değil)"),
    ("--fg", "--accent-wash", "seçili tablo satırı"),
    ("--fg-dim", "--bg", "ikincil metin, sayfa zemininde"),
    ("--fg-dim", "--bg-2", "ikincil metin, kart içinde"),
    ("--fg-dim", "--bg-3", "çip üzerindeki ikincil etiket"),
    ("--fg-faint", "--bg", "üçüncül not, sayfa zemininde"),
    ("--fg-faint", "--bg-2", "üçüncül not, kart içinde"),
    # v2 tasarımda mono göz-üstü etiketi (`--fg-faint`) çip ve dolgu zemininde
    # (`--bg-3`) de basılıyor: kapsama cetvelinin `veri yok · N belge` etiketi,
    # ısı haritasının `belgesiz` hücresi, alan çipleri. Çift bugüne kadar
    # ölçülmemişti ve KOYU temada 4,39:1 ile eşiğin ALTINDAYDI — bu yüzden
    # `--fg-faint` koyu değeri `#8a8a93` → `#8e8e97` yapıldı (gerekçe:
    # web/app/styles/tokens.css).
    ("--fg-faint", "--bg-3", "mono göz-üstü etiketi, dolgu zemininde"),
    ("--accent-soft", "--bg", "bağlantı, girintili yüzeyde"),
    ("--accent-soft", "--bg-2", "bağlantı, kart içinde"),
    ("--on-accent", "--accent", "birincil düğme metni"),
    ("--on-mark", "--mark", "span vurgusu"),
    ("--ok", "--bg", "rozet: kural katmanı"),
    ("--ok", "--bg-2", "rozet: kural katmanı, kart içinde"),
    ("--ok", "--ok-wash", "başarı bildirimi"),
    ("--warn", "--bg", "rozet: uyarı"),
    ("--warn", "--bg-2", "rozet: uyarı, kart içinde"),
    ("--warn", "--warn-wash", "uyarı bildirimi"),
    ("--bad", "--bg", "rozet: düşük güven"),
    ("--bad", "--bg-2", "rozet: düşük güven, kart içinde"),
    ("--bad", "--bad-wash", "hata bildirimi"),
    # `--llm` bu paletin en yeni rengi ve KENDİ çiftlerini getirir: eskiden
    # `.badge-llm` `--warn` ödünç alıyordu, yani ölçülen çift zaten vardı.
    # Ödünç bitti; ölçüm de kendi adına yapılır.
    ("--llm", "--bg", "rozet: LLM katmanı (üretilmiş)"),
    ("--llm", "--bg-2", "rozet: LLM katmanı, kart içinde"),
    ("--llm", "--llm-wash", "üretilmiş içerik şeridi / etiketi"),
    # Karantina kaydında banka adı `--fg`, gerekçesi `--fg-dim`: "bir güçlü
    # satır + bir fısıltı". Fısıltı `--bad-wash` zemininde okunuyor ve o çift
    # bugüne kadar ölçülmemişti.
    ("--fg-dim", "--bad-wash", "karantina kaydının fısıltı satırı"),
)

_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_BILDIRIM = re.compile(r"(--[a-z0-9-]+)\s*:\s*([^;]+);")
_KOYU_BLOK = re.compile(
    r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{(.*)\}", re.DOTALL
)


class Olcum(NamedTuple):
    """Tek bir metin/zemin çiftinin ölçülmüş sonucu."""

    tema: str
    metin: str
    zemin: str
    nerede: str
    oran: float

    @property
    def gecti(self) -> bool:
        return self.oran >= ESIK


def _kanal_dogrusal(deger: float) -> float:
    """sRGB kanalını doğrusal ışığa çevirir (WCAG 2.1, göreli parlaklık)."""
    return deger / 12.92 if deger <= 0.04045 else ((deger + 0.055) / 1.055) ** 2.4


def hex_to_rgb(renk: str) -> tuple[int, int, int]:
    """`#abc` ve `#aabbcc` biçimlerini (r, g, b) demetine çevirir."""
    ham = renk.strip().lstrip("#")
    if len(ham) == 3:
        ham = "".join(k * 2 for k in ham)
    if len(ham) != 6:
        raise ValueError(f"hex renk çözülemedi: {renk!r}")
    return int(ham[0:2], 16), int(ham[2:4], 16), int(ham[4:6], 16)


def goreli_parlaklik(renk: str) -> float:
    """WCAG göreli parlaklık (0 = siyah, 1 = beyaz)."""
    r, g, b = (_kanal_dogrusal(k / 255) for k in hex_to_rgb(renk))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def kontrast(on: str, arka: str) -> float:
    """İki renk arasındaki WCAG kontrast oranı (1,0 – 21,0)."""
    a, b = goreli_parlaklik(on), goreli_parlaklik(arka)
    parlak, koyu = max(a, b), min(a, b)
    return (parlak + 0.05) / (koyu + 0.05)


def _bildirimleri_topla(govde: str) -> dict[str, str]:
    """Bir CSS bloğundaki `--token: değer;` çiftlerini sözlüğe alır."""
    return {ad: deger.strip() for ad, deger in _BILDIRIM.findall(govde)}


def paletleri_coz(css: str) -> dict[str, dict[str, str]]:
    """`tokens.css` metninden açık ve koyu paletleri çıkarır.

    Koyu palet, açığın ÜSTÜNE yazılır: koyu blok yalnızca değişen isimleri
    yeniden tanımlar (bkz. tokens.css dosya başlığı), tanımlamadıklarını açık
    temadan devralır.
    """
    koyu_eslesme = _KOYU_BLOK.search(css)
    koyu_govde = koyu_eslesme.group(1) if koyu_eslesme else ""
    # Açık palet: koyu bloğun DIŞINDA kalan bildirimler.
    acik_govde = css.replace(koyu_govde, "") if koyu_govde else css

    acik = {a: d for a, d in _bildirimleri_topla(acik_govde).items() if _HEX.match(d)}
    koyu = dict(acik)
    koyu.update(
        {a: d for a, d in _bildirimleri_topla(koyu_govde).items() if _HEX.match(d)}
    )
    return {"açık": acik, "koyu": koyu}


def olc(paletler: dict[str, dict[str, str]]) -> list[Olcum]:
    """Her tema için CIFTLER listesini ölçer."""
    sonuc: list[Olcum] = []
    for tema, palet in paletler.items():
        for metin, zemin, nerede in CIFTLER:
            if metin not in palet or zemin not in palet:
                raise KeyError(
                    f"{tema} paletinde token yok: "
                    f"{metin if metin not in palet else zemin}"
                )
            sonuc.append(
                Olcum(tema, metin, zemin, nerede, kontrast(palet[metin], palet[zemin]))
            )
    return sonuc


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ayristirici.add_argument(
        "--ayrinti",
        action="store_true",
        help="eşiği geçen çiftleri de listele",
    )
    args = ayristirici.parse_args(argv)

    if not TOKENS_CSS.exists():
        print(f"HATA: token dosyası bulunamadı: {TOKENS_CSS}", file=sys.stderr)
        return 1

    olcumler = olc(paletleri_coz(TOKENS_CSS.read_text(encoding="utf-8")))
    ihlaller = [o for o in olcumler if not o.gecti]

    if args.ayrinti:
        for o in olcumler:
            isaret = "  " if o.gecti else "!!"
            print(
                f"{isaret} {o.tema:5} {o.oran:5.2f}:1  "
                f"{o.metin} / {o.zemin}  — {o.nerede}"
            )

    if ihlaller:
        print(
            f"\nKONTRAST İHLALİ: {len(ihlaller)} çift AA eşiğinin "
            f"({ESIK}:1) altında.",
            file=sys.stderr,
        )
        for o in ihlaller:
            print(
                f"  {o.tema:5} {o.oran:5.2f}:1  {o.metin} / {o.zemin}  — {o.nerede}",
                file=sys.stderr,
            )
        return 1

    print(
        f"kontrast TEMİZ — {len(olcumler)} çift, iki tema, hepsi >= {ESIK}:1 "
        f"(en düşük {min(o.oran for o in olcumler):.2f}:1)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
