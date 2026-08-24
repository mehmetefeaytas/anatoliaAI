"""Vakıf Katılım kâr paylaşım oranı PDF'ini JSONL'e çevirir (bakiye dilimi bazında).

İlgili: kt_paylasim_pdf.py (Kuveyt Türk için AYNI iş, aynı çıktı şeması)
        ../src/scraping/rates.py (`VakifKatilimBlockedAdapter` — niçin otomatik değil)
        tkbb_guncel_hasat.py (TKBB'nin tek temsili değeri)

## Niçin bu banka OTOMATİK toplanamıyor

Vakıf Katılım oranları HTML'de yayımlamıyor; tek kaynak
`/documents/PerakendeBankacilik/kar-paylasim-oranlari.pdf` ve bankanın
`robots.txt`'i `/documents/` yolunu **açıkça** engelliyor (yalnız
`.jpg/.png/.jpeg` uzantılarına izin var). Bu bir kaza değil, bankanın bilinçli
tercihi ve `VakifKatilimBlockedAdapter` onu kayıt altına alıyor.

Şartname §5.1 böyle bir belge için **manuel toplamaya** izin veriyor. Bu yüzden
PDF elle indirildi (`data/raw/vakif-katilim/manual/`) ve bu betik yalnız YEREL
dosyayı okuyor — ağa çıkmıyor, bir tarayıcı taklit etmiyor, robots kuralını
dolanmıyor. Ayrım önemli: engellenen şey OTOMATİK GEZİNMEDİR, belgenin kendisi
kamuya açık bir yayındır.

## Niçin ayrıca bu banka — segment ayrımı

TKBB her banka için TEK temsili paylaşım oranı yayımlıyor. Bankanın kendi PDF'i
ise **bakiye dilimi** bazında veriyor ve fark küçük değil:

    250-99.999 TL      → 85/15
    100.000+ TL        → 90/10

Yani küçük bakiyeli müşteri, merkezî veride görünen orandan **5 puan düşük**
oran alıyor. Aynı boşluk Kuveyt Türk'te de ölçülmüştü
([[merkezi-veri-segment-ayrimini-gizliyor]]); bu betik ikinci bankayı da
kapatıyor.

## Değerler PAYLAŞIM oranıdır, getiri DEĞİL

"85/15" = kârın %85'i katılımcıya, %15'i bankaya. Bu bir **bölüşümdür** ve
`buyukluk='pay'` ile işaretlenir; dağıtılan getiriyle (%42 gibi) aynı kolonda
kıyaslanamaz (bkz. `decisions/katilma-orani-iki-ayri-buyukluk.md`).

## Kullanım

    python -m scripts.vakif_paylasim_pdf                 # varsayılan yol
    python -m scripts.vakif_paylasim_pdf --kuru          # yazma, yalnız ölç
    python -m scripts.vakif_paylasim_pdf --pdf <yol>
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Iterator, Optional

KAYNAK_URL = ("https://www.vakifkatilim.com.tr/documents/PerakendeBankacilik/"
              "kar-paylasim-oranlari.pdf")
BANKA = "vakif-katilim"

VARSAYILAN_PDF = "data/raw/vakif-katilim/manual/kar-paylasim-oranlari.pdf"
VARSAYILAN_CIKTI = "data/raw/vakif-katilim/rates/vakif-paylasim-pdf.jsonl"

PARA_KODU = {"TL": "TRY", "USD": "USD", "EUR": "EUR", "EURO": "EUR",
             "ALTIN": "XAU"}

#: Bölüm başlıkları. `ARA DÖNEM` ayrı yakalanıyor: o tabloların sütun düzeni
#: farklı (açılış bakiyesi + 4 vade) ve satır etiketi bir ÜRÜN adı.
BOLUM_DESENI = re.compile(
    r"^\s*(TL|USD|EUR|EURO|ALTIN)\s+(ARA DÖNEM KÂR PAYI ÖDEMELİ\s+)?"
    r"KATILMA (?:HESAPLARI|HESABI)\s*$", re.IGNORECASE)

#: Vade başlığı satırı — hangi sütunun hangi vadeye denk geldiğini BURADAN
#: okuyoruz, sabit sıraya güvenmiyoruz. ALTIN tablosunda "1 Ay" sütunu YOK ve
#: sabit sıra varsayımı bütün altın satırlarını bir sütun kaydırırdı.
VADE_BASLIK_DESENI = re.compile(
    r"(\d+)\s*(Ay|Yıl)\s*(?:\((\d+)\s*Gün\))?\s*\(?%?\)?", re.IGNORECASE)
UZUN_VADE_DESENI = re.compile(r"1\s*Yıldan\s*Uzun\s*Vade", re.IGNORECASE)

#: KATILMA HESABI OLMAYAN bölüm başlıkları — bağlamı KAPATIR.
#:
#: Ölçülmüş uydurma (2026-08-24): «ÇEYİZ VE KONUT HESABI» tablosunun 95/5
#: oranı, kendinden önceki `USD ARA DÖNEM` bölümünün bağlamını devralıyor ve
#: «USD · 3 ay · 95/5» diye SAHTE bir kayıt üretiyordu. PDF'te öyle bir satır
#: yok.
#:
#: Bu bölüm bilerek AYRIŞTIRILMIYOR, atlanıyor. Düzeni satır-sütun eşlemesine
#: uygun değil: ürün adı ("Çeyiz Hesabı") kendi satırında, tutarlar başka
#: satırlarda ve 95/5 ikisinin ORTASINDA tek başına duruyor. Hangi oranın
#: hangi ürüne ait olduğunu metinden güvenle bağlayamıyoruz — tahmin etmek
#: değer uydurmak olurdu (CLAUDE.md §3: bilgi yoksa üretme).
KATILMA_DISI_BOLUM = re.compile(
    r"ÇEYİZ\s+VE\s+KONUT\s+HESABI|ALTIN\s+BİRİKİM|EMEKLİLİK", re.IGNORECASE)

#: Ara dönem tablolarında açılış bakiyesi ürün adından SONRA gelen ilk sayıdır
#: ("Yatırım (TL)   150.000   90/10 …"). Dilim deseni onu yakalamıyor çünkü
#: satır bir sayıyla başlamıyor.
ACILIS_BAKIYE_DESENI = re.compile(r"\s([\d][\d.,]{3,})\s")

#: "85/15" — katılımcı payı / banka payı.
PAY_DESENI = re.compile(r"(\d{1,3})\s*/\s*(\d{1,3})")

#: Bakiye dilimi: "250-99.999", "1.500.000", "50 gr ve üzeri".
DILIM_DESENI = re.compile(
    r"^\s*([\d.,]+(?:\s*-\s*[\d.,]+)?(?:\s*gr(?:\s*ve\s*üzeri)?)?)\s", re.IGNORECASE)


def _sayi(ham: str) -> Optional[float]:
    """`1.500.000` → 1500000.0. TR biçimi: nokta binlik, virgül ondalık."""
    t = ham.strip().replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _vade_aylari(baslik: str) -> list[Optional[int]]:
    """Başlık satırından sütun sırasına göre vade listesi (ay).

    `None` = "1 Yıldan Uzun Vade" — üst sınırı olmayan bir kova ve ona bir sayı
    atamak uydurma olurdu. Kıyas tarafı `term_months is None` satırı ayrı
    gösteriyor.
    """
    # Uzun vade sütununu önce işaretle: "1 Yıldan Uzun" ifadesi "1 Yıl"
    # desenine de uyuyor ve önce eşleşirse sütun sayısı bir eksik çıkardı.
    kalan = UZUN_VADE_DESENI.sub("\x00", baslik)
    yerler: list[tuple[int, Optional[int]]] = []
    for m in VADE_BASLIK_DESENI.finditer(kalan):
        n, birim = int(m.group(1)), m.group(2).lower()
        yerler.append((m.start(), n * 12 if birim.startswith("y") else n))
    for m in re.finditer("\x00", kalan):
        yerler.append((m.start(), None))
    yerler.sort()
    return [ay for _, ay in yerler]


def ayristir(metin: str, *, damga: Optional[str] = None) -> Iterator[dict]:
    """PDF metninden kayıt üretir.

    Bölüm başlığı para birimini, vade başlığı sütun sırasını, satırın kendisi
    dilimi ve payları veriyor. Üçü de METİNDEN okunuyor — hiçbiri sabit
    yazılmıyor, çünkü banka tabloyu değiştirdiğinde sabit varsayım SESSİZCE
    yanlış kayıt üretirdi.
    """
    zaman = damga or datetime.now(timezone.utc).isoformat(timespec="seconds")
    para: Optional[str] = None
    ara_donem = False
    vadeler: list[Optional[int]] = []

    for satir in metin.splitlines():
        if KATILMA_DISI_BOLUM.search(satir):
            # Bağlamı KAPAT — sonraki satırlar önceki bölümün para birimini ve
            # vade sütunlarını DEVRALMAMALI.
            para, vadeler, ara_donem = None, [], False
            continue
        bas = BOLUM_DESENI.match(satir)
        if bas:
            para = PARA_KODU.get(bas.group(1).upper())
            ara_donem = bool(bas.group(2))
            vadeler = []
            continue
        if para is None:
            continue
        # Vade başlığı mı? En az iki vade sütunu görüyorsak öyledir.
        if "Ay" in satir or "Yıl" in satir:
            aday = _vade_aylari(satir)
            if len(aday) >= 2 and not PAY_DESENI.search(satir):
                vadeler = aday
                continue
        paylar = PAY_DESENI.findall(satir)
        if not paylar or not vadeler:
            continue
        # Stopaj satırı pay taşımaz; taşısaydı bile dilimi olmaz.
        if "stopaj" in satir.lower():
            continue
        dilim_m = DILIM_DESENI.match(satir)
        etiket = satir.strip().split("  ")[0].strip()
        alt = _sayi(dilim_m.group(1).split("-")[0]) if dilim_m else None
        if alt is None and ara_donem:
            # Ara dönem satırı ürün adıyla başlıyor; bakiye ilk sayıdır ve
            # PAY_DESENI'nden ÖNCE gelir. Payların kendisini bakiye sanmamak
            # için satır ilk pay eşleşmesinde kesiliyor.
            ilk_pay = PAY_DESENI.search(satir)
            bas_kismi = satir[:ilk_pay.start()] if ilk_pay else satir
            bakiye_m = ACILIS_BAKIYE_DESENI.search(bas_kismi)
            if bakiye_m:
                alt = _sayi(bakiye_m.group(1))

        for i, (kat, bank) in enumerate(paylar):
            if i >= len(vadeler):
                break                      # sütundan fazla pay: kayıt üretme
            k, b = float(kat), float(bank)
            yield {
                "bank_slug": BANKA,
                "kind": "katilma",
                "rapor": "kar_paylasim",
                "rapor_adi": "Kâr Paylaşım Oranları (banka PDF'i)",
                "buyukluk": "pay",
                "product_name": ("Ara Dönem Kâr Payı Ödemeli Katılma Hesabı"
                                 if ara_donem else "Katılma Hesabı"),
                "segment": etiket or None,
                "opening_balance": alt,
                "min_balance": alt,
                "currency": para,
                "term_label": None,
                "term_months": vadeler[i],
                "term_days": None,
                "annual_rate": k,
                "bank_share": b,
                "toplam": k + b,
                # Toplam 100 değilse KAYIT DÜŞÜRÜLMEZ, İŞARETLENİR: kaynağı
                # sessizce düzeltmek, veriyi uydurmak olurdu (kt_paylasim_pdf
                # ile aynı kural).
                "toplam_tutarsiz": abs(k + b - 100.0) > 0.01,
                "source_url": KAYNAK_URL,
                "collected_at": zaman,
                "method": "banka-pdf-manuel",
                "note": ("robots.txt /documents/ yolunu engelliyor; PDF şartname "
                         "§5.1 gereği ELLE indirildi, betik yalnız yerel dosyayı "
                         "okuyor"),
            }


def pdf_metni(yol: pathlib.Path) -> str:
    if not yol.exists():
        raise FileNotFoundError(
            f"{yol} yok. PDF elle indirilmeli:\n  curl -sL -o {yol} '{KAYNAK_URL}'")
    r = subprocess.run(["pdftotext", "-layout", str(yol), "-"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"pdftotext düştü: {r.stderr[:200]}")
    return r.stdout


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", default=VARSAYILAN_PDF)
    ap.add_argument("--cikti", default=VARSAYILAN_CIKTI)
    ap.add_argument("--kuru", action="store_true", help="yazma, yalnız ölç")
    a = ap.parse_args(argv)

    kayitlar = list(ayristir(pdf_metni(pathlib.Path(a.pdf))))
    if not kayitlar:
        print("hiç kayıt çıkmadı — PDF düzeni değişmiş olabilir", file=sys.stderr)
        return 1

    tutarsiz = sum(1 for k in kayitlar if k["toplam_tutarsiz"])
    paralar = sorted({k["currency"] for k in kayitlar})
    segment = len({k["segment"] for k in kayitlar})
    print(f"kayıt        : {len(kayitlar)}")
    print(f"para birimi  : {', '.join(paralar)}")
    print(f"segment      : {segment}")
    if tutarsiz:
        print(f"⚠ toplamı 100 OLMAYAN kayıt: {tutarsiz} (düşürülmedi, işaretlendi)")

    if a.kuru:
        print("(kuru koşum — yazılmadı)")
        return 0
    hedef = pathlib.Path(a.cikti)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(
        "".join(json.dumps(k, ensure_ascii=False) + "\n" for k in kayitlar),
        encoding="utf-8")
    print(f"yazıldı: {hedef}")
    return 0


if __name__ == "__main__":                   # pragma: no cover
    raise SystemExit(main())
