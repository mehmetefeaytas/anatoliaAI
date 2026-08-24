"""TKBB Veri Peteği'nden GÜNCEL katılma hesabı oranlarını hasat et.

İlgili: tkbb_karpayi_hasat.py (aynı verinin TARİHSEL arşivi, 2012–2025)
        ../src/scraping/rates.py (banka uçlarından ürün oranı toplama)

## İki TKBB kaynağı, iki ayrı uç — karıştırılmamalı

    karpayi.tkbb.org.tr        TARİHSEL arşiv, 2012-01-02 → 2025-05-26'da DURUYOR,
                               TLS sertifikası GEÇERSİZ  → tkbb_karpayi_hasat.py
    veri-petegi.tkbb.org.tr    GÜNCEL, "bu hafta" filtresiyle canlı,
                               sertifika geçerli, CSRF ister → BU BETİK

Güncel uç, tarihsel arşivin bıraktığı yerden sonrasını kapatıyor: arşiv Mayıs
2025'te bitiyor, bu uç içinde bulunulan haftayı veriyor. Kampanya korpusu katılma
hesabı getirisini hiç yayınlamadığı için ("en iyi kâr payı oranı hangi bankada"
sorusu korpustan cevaplanamıyordu) bu iki kaynak birlikte o boşluğu kapatır.

## İki büyüklük — aynı kolonda YARIŞTIRILAMAZ

    Dağıtılan Kâr Payı Oranları %   gerçekleşen yıllık GETİRİ   (ör. %42,79)
    Kâr Paylaşım Oranları %         katılımcıya düşen PAY       (ör. %90)

Paylaşım oranı her zaman getiriden büyük görünür; ikisi tek sıralamaya girerse
"en iyi oran" sorusunun cevabı anlamsızlaşır. `buyukluk` alanı ('getiri'|'pay')
bu ayrımı taşır ve kıyas katmanı ona bakmak zorundadır.

## Ölçülmüş doğrulama (2026-08-24)

Aynı Albaraka TL paylaşım oranı üç bağımsız kaynakta AYNI çıktı: bu uç
(90/90/92/93), tarihsel arşiv `sheetIndex=1` (90/90/92/93) ve Albaraka'nın kendi
PDF'i (`kar-paylasim-oranlari-09-07-25.pdf`, 90/90/92/93). Üç yol aynı değeri
veriyor.

## period_date TÜRETİLMİŞTİR

Uç, satırlarda tarih DÖNDÜRMÜYOR; hangi haftaya ait olduğu istekteki
`snap_beginning`/`snap_ending` filtresinden gelir. Bu yüzden `period_date`
toplama gününün haftasının Pazartesi'sine ayarlanır ve `period_date_kaynak`
alanı bunun türetilmiş olduğunu AÇIKÇA kaydeder — ölçülmüş bir tarih gibi
görünmesin.

Kullanım:
    python -m scripts.tkbb_guncel_hasat
    python -m scripts.tkbb_guncel_hasat --kuru
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import pathlib
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Iterator, Optional

KOK = "https://veri-petegi.tkbb.org.tr"
CSRF_UC = f"{KOK}/api/v1/auth/csrf/"
VERI_UC = f"{KOK}/api/v1/data/"
DASHBOARD = "db-fyfb30he1txl19b"
KAYNAK_SAYFA = "https://tkbb.org.tr/veripetegi-detay/40"

#: Panelin "bu hafta" filtresi. İki kez geçmesi ucun beklediği biçim (başlangıç
#: ve bitiş aynı filtre kimliğiyle gönderiliyor); tek kopya 400 döndürür.
_HAFTA = ("%7B%22anchor%22%3A%22now%22%2C%22unit%22%3A%22week%22%2C"
          "%22move%22%3A0%2C%22behavior%22%3A%22snap_{u}%22%7D")
FILTRE = urllib.parse.quote(
    f"dbfl-5amu0677cd7d07a={_HAFTA.format(u='beginning')}"
    f"&dbfl-5amu0677cd7d07a={_HAFTA.format(u='ending')}", safe="")

#: Panel bileşeni (dashlet) → (dosya eki, insan-okur ad, büyüklük türü).
DASHLETLER: dict[str, tuple[str, str, str]] = {
    "DL-FFC6K484A682B8I": ("dagitilan_kar_payi", "Dağıtılan Kâr Payı Oranları",
                           "getiri"),
    "DL-0M0C2ABB615D062": ("kar_paylasim", "Kâr Paylaşım Oranları", "pay"),
}

#: Ölçüt kolon eki → para birimi. Panelin `dashletmeasures` sırasından okundu
#: (m0=TL, m1=USD, m2=EUR, m3=Altın) ve buraya SABİTLENDİ: sıra değişirse
#: sessizce yanlış para birimine yazmak yerine `--dogrula` bunu yakalar.
PARA_BIRIMI = {"m0": "TRY", "m1": "USD", "m2": "EUR", "m3": "XAU"}

#: Vade kolon adı → ay.
VADE_AY = {"Aylık": 1, "3 Aylık": 3, "6 Aylık": 6, "Yıllık": 12}

#: Uçtan gelen banka adı → proje slug'ı (`config/banks.yaml`).
BANKA_SLUG = {
    "Albaraka Türk Katılım Bankası A.Ş.": "albaraka",
    "Dünya Katılım Bankası A.Ş.": "dunya-katilim",
    "Türkiye Emlak Katılım Bankası A.Ş.": "turkiye-emlak-katilim",
    "Hayat Finans Katılım Bankası A.Ş.": "hayat-finans",
    "Kuveyt Türk Katılım Bankası A.Ş.": "kuveyt-turk",
    "T.O.M. Katılım Bankası A.Ş.": "tom-katilim",
    "Türkiye Finans Katılım Bankası A.Ş.": "turkiye-finans",
    "Vakıf Katılım Bankası A.Ş.": "vakif-katilim",
    "Ziraat Katılım Bankası A.Ş.": "ziraat-katilim",
}


def _acici() -> tuple[urllib.request.OpenerDirector, str]:
    """CSRF çerezini alır; (opener, token) döndürür.

    Uç, çerezdeki `csrftoken`'ı `X-CSRFToken` başlığında da bekler; başlık
    olmadan HTTP 400 döner (ölçüldü).
    """
    kavanoz = http.cookiejar.CookieJar()
    acici = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(kavanoz))
    istek = urllib.request.Request(
        CSRF_UC, headers={"User-Agent": "AnatoliaAI-arastirma/1.0",
                          "Accept": "application/json"})
    with acici.open(istek, timeout=45):
        pass
    for c in kavanoz:
        if c.name == "csrftoken":
            return acici, c.value
    raise RuntimeError(f"csrftoken çerezi gelmedi: {CSRF_UC}")


def veri_al(dashlet: str) -> dict:
    """Bir panel bileşeninin bu haftalık verisini JSON olarak döndürür."""
    acici, token = _acici()
    sorgu = (f"?id={dashlet}&type=pivot&refresh_cache=false"
             f"&dashboard={DASHBOARD}&filters={FILTRE}"
             "&date_aggregate=auto&dashboard_date_aggregate=auto"
             "&rowLevel=0&ordering=")
    istek = urllib.request.Request(
        VERI_UC + sorgu,
        headers={"User-Agent": "AnatoliaAI-arastirma/1.0",
                 "Accept": "application/json, text/plain, */*",
                 "X-CSRFToken": token,
                 "Referer": f"{KOK}/public/dashboards/{DASHBOARD}"})
    with acici.open(istek, timeout=60) as y:
        return json.loads(y.read().decode("utf-8"))


def _hafta_basi(gun: Optional[date] = None) -> str:
    """İçinde bulunulan haftanın Pazartesi'si (ISO). Bkz. modül başlığı."""
    g = gun or datetime.now(timezone.utc).date()
    return (g - timedelta(days=g.weekday())).isoformat()


def kayitlar(yanit: dict, *, dashlet: str, toplandi: str,
             donem: str) -> Iterator[dict]:
    """Pivot yanıtını JSONL kayıtlarına çevirir.

    Kolon adı biçimi: '<vade>|<ölçüt>' (ör. '3 Aylık|m0'). Boş hücre ATLANIR —
    o banka o vade/para birimi için oran yayınlamamıştır ve 0 yazmak onu
    "sıfır oran veren banka" yapardı.
    """
    ek, rapor_adi, buyukluk = DASHLETLER[dashlet]
    for blok in yanit.get("data", []):
        for satir in blok.get("attributes", {}).get("rows", []):
            ad = satir.get("banka")
            slug = BANKA_SLUG.get(ad)
            if slug is None:
                continue
            for kolon, deger in satir.items():
                if "|" not in kolon:
                    continue
                vade_adi, olcut = kolon.rsplit("|", 1)
                ay = VADE_AY.get(vade_adi.strip())
                para = PARA_BIRIMI.get(olcut.strip())
                if ay is None or para is None:
                    continue
                if deger in ("", None) or not isinstance(deger, (int, float)):
                    continue
                yield {
                    "bank_slug": slug,
                    "bank_name": ad,
                    "kind": "katilma",
                    "rapor": ek,
                    "rapor_adi": rapor_adi,
                    "buyukluk": buyukluk,
                    "product_name": "Katılma Hesabı",
                    "currency": para,
                    "term_months": ay,
                    "period_date": donem,
                    "period_date_kaynak": "turetilmis: istek haftasinin pazartesisi",
                    "annual_rate": float(deger),
                    "source_url": KAYNAK_SAYFA,
                    "collected_at": toplandi,
                    "method": "tkbb-veripetegi",
                }


def _yaz(kok: pathlib.Path, slug: str, satirlar: Iterable[dict]) -> int:
    hedef = kok / "data" / "raw" / slug / "rates" / "tkbb-guncel.jsonl"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with hedef.open("w", encoding="utf-8") as f:
        for k in satirlar:
            f.write(json.dumps(k, ensure_ascii=False) + "\n")
            n += 1
    return n


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kuru", action="store_true", help="dosyaya yazma, say")
    a = ap.parse_args(argv)

    kok = pathlib.Path(__file__).resolve().parents[1]
    toplandi = datetime.now(timezone.utc).isoformat(timespec="seconds")
    donem = _hafta_basi()

    hepsi: list[dict] = []
    for dashlet in DASHLETLER:
        try:
            yanit = veri_al(dashlet)
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as e:
            # Bir bileşenin düşmesi ötekini iptal etmez; eksik AÇIKÇA yazılır.
            print(f"  {DASHLETLER[dashlet][0]:22s} HATA: {type(e).__name__}: {e}")
            continue
        yeni = list(kayitlar(yanit, dashlet=dashlet, toplandi=toplandi,
                             donem=donem))
        hepsi.extend(yeni)
        print(f"  {DASHLETLER[dashlet][0]:22s} {len(yeni):>4} kayit "
              f"({len({k['bank_slug'] for k in yeni})} banka)")

    toplam = 0
    for slug in sorted({k["bank_slug"] for k in hepsi}):
        payi = [k for k in hepsi if k["bank_slug"] == slug]
        toplam += len(payi) if a.kuru else _yaz(kok, slug, payi)
    etiket = "sayıldı (kuru)" if a.kuru else "yazıldı"
    print(f"\nTOPLAM {toplam} kayit {etiket} · dönem {donem} · kaynak {KAYNAK_SAYFA}")
    return 0 if toplam else 1


if __name__ == "__main__":
    raise SystemExit(main())
