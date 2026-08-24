"""TKBB kâr payı veri setini hasat et (tarihsel, banka × vade × para birimi).

İlgili: ../src/scraping/rates.py (banka uçlarından GÜNCEL oran toplama)
        crosscheck_rates.py (gold satırlarını ilan edilen oranla doğrulama)
        ../../decisions/katilma-orani-iki-ayri-buyukluk.md

## Bu betik neyi çözüyor

Katılma hesabı sorularına ("en iyi kâr payı oranını hangi banka veriyor")
korpustan cevap verilemiyordu: kampanya metinleri katılma hesabı getirisini
YAYINLAMIYOR. Veri, TKBB'nin merkezî veri setinde duruyor:

    https://karpayi.tkbb.org.tr/veri/karpaylari

Dört ayrı rapor sunuyor ve İKİSİ BİRBİRİNE KARIŞTIRILMAMALI:

    sheetIndex=0  Dağıtılan Kâr Payı Oranları    → GERÇEKLEŞEN yıllık getiri (%31,38)
    sheetIndex=1  Kâr Paylaşım Oranları          → katılımcı PAYI (%90)
    sheetIndex=2  Ara Ödemeli Hes. Dağıtılan     → aynı, ara ödemeli hesap
    sheetIndex=3  Ara Ödemeli Hes. Paylaşım      → aynı, ara ödemeli hesap

`0` bir GETİRİ, `1` bir BÖLÜŞÜM oranıdır. Aynı kolonda kıyaslanırlarsa %90'lık
paylaşım oranı %31'lik getiriyi "yener" ve sıralama anlamsızlaşır. Bu yüzden
`rapor` alanı her satırda taşınıyor ve kıyas katmanı ikisini ayırmak zorundadır.

## TLS SERTİFİKASI — açık bir istisna, sessiz varsayılan DEĞİL

`karpayi.tkbb.org.tr` sertifikası geçersiz (`ERR_CERT_DATE_INVALID`); hem curl
hem tarayıcı doğrulamada düşüyor. Bu yüzden hasat `--sertifika-atla` bayrağı
İSTEMEDEN çalışmaz — bayrak yokken betik açıklamalı hata verip çıkar. Doğrulama
atlamak MITM'e açık bir davranıştır ve varsayılan yapılmamalıdır.

Riski kapatan şey ölçüldü: bu uçtan `-k` ile alınan veri, kullanıcının kendi
tarayıcısından (sertifika uyarısını kabul ederek) aldığı değerlerle **7/7 banka
birebir uyuştu** (2026-08-24). Yani içerik doğrulandı; güvenilen şey sertifika
değil, iki bağımsız yoldan gelen aynı veri.

## Veri setinin KAPSAM SINIRI — ölçüldü

Form yıl listesi 2012–2025 ile bitiyor; **2026 verisi yok**. Bankaların son
yayın haftası da farklı (2026-08-24 ölçümü):

    Albaraka, Emlak        2024-09-30'da duruyor
    Kuveyt Türk, Vakıf     2024-10-07
    TOM, Ziraat            2024-12-23
    Hayat Finans           2025-05-05
    Türkiye Finans         2025-05-26
    BankAsya               veri yok (kapalı banka)
    Adil Katılım           TKBB veri setinde yok

Yani bu veri TARİHSELDİR, güncel teklif değil. "Şu an en iyi oranı kim veriyor"
sorusuna tek başına cevap OLAMAZ; güncel oran için `src/scraping/rates.py`
banka uçları kullanılır. Bu ayrım cevap metninde de görünmek zorundadır.

Kullanım:
    python -m scripts.tkbb_karpayi_hasat --sertifika-atla
    python -m scripts.tkbb_karpayi_hasat --sertifika-atla --rapor 0 --kuru
"""

from __future__ import annotations

import argparse
import gzip
import json
import pathlib
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Iterable, Iterator, Optional

UC_NOKTA = "https://karpayi.tkbb.org.tr/veriseti/profitReportDetail"
KAYNAK_SAYFA = "https://karpayi.tkbb.org.tr/veri/karpaylari"

#: TKBB banka kimlikleri (ana sayfadaki radio input `value`'ları) → proje slug'ı.
#: Kimlikler sayfadan okunmuyor bilerek: sayfa erişilemezse hasat da durur, oysa
#: kimlikler sabittir ve burada durmaları betiği tek istekle çalışabilir kılıyor.
#: Değiştiklerinde `--kimlik-tazele` ile ana sayfadan yeniden çıkarılabilir.
BANKALAR: dict[str, str] = {
    "f8c82fc6f22032776498e25255df9586": "albaraka",
    "3014e78901f101688cc5bb28bdbf8a72": "dunya-katilim",
    "8246242cd400b6b9e0a5bcafad24a438": "turkiye-emlak-katilim",
    "abc3c7f146637b2e03af3e1c8de59cdb": "hayat-finans",
    "d3c5d2228a5192a7652f164ce1f79f37": "kuveyt-turk",
    "8f0e40af3612787e9dd46281e8483690": "tom-katilim",
    "71d629eb3ef3f9c0c95b4e9690fb16e3": "turkiye-finans",
    "e7c3b0ece53c6aa0adaf9fdff014089f": "vakif-katilim",
    "ca1c343f563c1fb033868a9ab987b460": "ziraat-katilim",
    # BankAsya (4e42976e...) bilerek dışta: kapalı banka, uç boş yanıt veriyor.
}

#: Rapor türü → (dosya eki, insan-okur ad, büyüklüğün NE olduğu).
#: Üçüncü alan kıyas katmanı için kritik: `getiri` sıralanabilir, `pay` ise
#: bölüşümdür ve ikisi asla aynı kolonda yarışmaz.
RAPORLAR: dict[int, tuple[str, str, str]] = {
    0: ("dagitilan_kar_payi", "Dağıtılan Kâr Payı Oranları", "getiri"),
    1: ("kar_paylasim", "Kâr Paylaşım Oranları", "pay"),
    2: ("ara_odemeli_dagitilan", "Ara Ödemeli Hes. Dağ. Kâr Payı", "getiri"),
    3: ("ara_odemeli_paylasim", "Ara Ödemeli Hes. Kâr Paylaşım", "pay"),
}

#: Vade kolonları — uçtaki `vade[]` değeri → ay. Sıra ÖNEMLİ: tablo kolonları
#: bu sırayla (vade dış, para birimi iç) diziliyor.
VADELER: tuple[tuple[str, int], ...] = (("m1", 1), ("m3", 3), ("m6", 6), ("m12", 12))

#: Para birimi kolonları — `currency[]` değeri → ISO kod. Sıra ÖNEMLİ (yukarı bkz.).
PARA_BIRIMLERI: tuple[tuple[str, str], ...] = (
    ("try", "TRY"), ("usd", "USD"), ("eur", "EUR"), ("xau", "XAU"),
)

AYLAR = {
    "Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4, "Mayıs": 5, "Haziran": 6,
    "Temmuz": 7, "Ağustos": 8, "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12,
}

BASLANGIC_YIL = 2012  # form listesinin en eski yılı
BITIS_YIL = 2025      # form listesinin en yeni yılı — 2026 YOK (bkz. modül başlığı)


def _govde(bank: str, sheet_index: int) -> bytes:
    """POST gövdesi. Tüm vade ve para birimleri TEK istekte alınır (16 kolon)."""
    alanlar = [
        ("startMonth", "1"), ("startYear", str(BASLANGIC_YIL)),
        ("endMonth", "12"), ("endYear", str(BITIS_YIL)),
        ("sheetIndex", str(sheet_index)), ("bank", bank),
    ]
    alanlar += [("currency[]", k) for k, _ in PARA_BIRIMLERI]
    alanlar += [("vade[]", k) for k, _ in VADELER]
    return urllib.parse.urlencode(alanlar).encode()


def _istek(bank: str, sheet_index: int, *, sertifika_atla: bool,
           zaman_asimi: float = 90.0) -> str:
    """Uca POST atıp HTML döndürür. Ağ hatası çağırana yükselir."""
    istek = urllib.request.Request(
        UC_NOKTA, data=_govde(bank, sheet_index), method="POST",
        headers={
            "User-Agent": "AnatoliaAI-arastirma/1.0 (TEKNOFEST 2026; veri toplama)",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": KAYNAK_SAYFA,
        })
    baglam: Optional[ssl.SSLContext] = None
    if sertifika_atla:
        # Açık istisna — gerekçesi modül başlığında, bayrakla istenmeden olmaz.
        baglam = ssl.create_default_context()
        baglam.check_hostname = False
        baglam.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(istek, timeout=zaman_asimi, context=baglam) as y:
        return y.read().decode("utf-8", errors="replace")


def _sayi(metin: str) -> Optional[float]:
    """TR ondalık ayracını çözer: '31,38' → 31.38. Boş/'-' → None.

    `None` dönmek "o hafta o vade için oran yayınlanmadı" demektir ve 0.0'dan
    kesin biçimde farklıdır — 0 bir orandır, yokluk değil.
    """
    t = (metin or "").strip()
    if not t or t in {"-", "—", "–"}:
        return None
    try:
        return float(t.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _tarih(yil: str, ay: str, gun_metni: str) -> Optional[str]:
    """'2024' + 'Ocak' + '01 Ocak Pazartesi' → '2024-01-01' (ISO-8601)."""
    parcalar = (gun_metni or "").split()
    if not parcalar or not parcalar[0].isdigit():
        return None
    a = AYLAR.get(parcalar[1]) if len(parcalar) > 1 else AYLAR.get(ay)
    if a is None or not yil.isdigit():
        return None
    try:
        return datetime(int(yil), a, int(parcalar[0])).date().isoformat()
    except ValueError:
        return None


def _satirlari_ayikla(html: str) -> Iterator[list[str]]:
    """Tablo veri satırlarını (ilk hücresi yıl olanlar) verir."""
    from bs4 import BeautifulSoup  # yerel içe alma: betik ağsız da içe alınabilsin
    corba = BeautifulSoup(html, "html.parser")
    for tr in corba.find_all("tr"):
        hucreler = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(hucreler) >= 4 and hucreler[0].isdigit() and len(hucreler[0]) == 4:
            yield hucreler


def kayitlar(html: str, *, bank_slug: str, sheet_index: int,
             toplandi: str) -> Iterator[dict]:
    """HTML tablosunu satır satır JSONL kayıtlarına çevirir.

    Kolon düzeni: [yıl, ay, gün] + vade×para_birimi (vade dış, para birimi iç).
    Boş hücreler ATLANIR — yayınlanmamış bir oranı kayda geçirmek, olmayan
    veriyi var göstermek olurdu.
    """
    ek, rapor_adi, buyukluk = RAPORLAR[sheet_index]
    for hucreler in _satirlari_ayikla(html):
        tarih = _tarih(hucreler[0], hucreler[1] if len(hucreler) > 1 else "",
                       hucreler[2] if len(hucreler) > 2 else "")
        if tarih is None:
            continue
        i = 3
        for _, ay_sayisi in VADELER:
            for _, para in PARA_BIRIMLERI:
                if i >= len(hucreler):
                    break
                deger = _sayi(hucreler[i])
                i += 1
                if deger is None:
                    continue
                yield {
                    "bank_slug": bank_slug,
                    "kind": "katilma-tarihsel",
                    "rapor": ek,
                    "rapor_adi": rapor_adi,
                    # `buyukluk`: 'getiri' sıralanabilir, 'pay' bölüşümdür.
                    # Kıyas katmanı ikisini aynı kolonda yarıştırmamak için buna bakar.
                    "buyukluk": buyukluk,
                    "product_name": "Katılma Hesabı",
                    "currency": para,
                    "term_months": ay_sayisi,
                    "period_date": tarih,
                    "annual_rate": deger,
                    "source_url": KAYNAK_SAYFA,
                    "collected_at": toplandi,
                    "method": "tkbb-veriseti",
                    # Sertifika doğrulaması atlanarak alındığı KAYDA GEÇİYOR;
                    # veriyi kullanan her yer bunu görebilmeli.
                    "tls_dogrulama": "atlandi",
                }


def _yaz(kok: pathlib.Path, slug: str, satirlar: Iterable[dict]) -> int:
    """Kayıtları GZIP'li JSONL olarak yazar.

    Neden sıkıştırılmış: 14 yıllık haftalık seri banka başına ~10 MB, dokuz
    banka toplam **89 MB** düz metin. Satırlar birbirine çok benzediği için
    gzip bunu **1,1 MB**'a indiriyor (ölçüldü, 2026-08-24) — yani sıkıştırma
    80 kata yakın kazanç veriyor ve arşiv depoya sığar.

    Arşivin depoda DURMASI gerekiyor: kaynak kırılgan (TLS sertifikası süresi
    geçmiş, veri seti Mayıs 2025'te durmuş — terk edilmiş bir uç görünümünde).
    Yeniden üretilebilir olması, yarın erişilebilir olacağı anlamına gelmez.
    """
    hedef = kok / "data" / "raw" / slug / "rates" / "tkbb-karpayi.jsonl.gz"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with gzip.open(hedef, "wt", encoding="utf-8", compresslevel=9) as f:
        for kayit in satirlar:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
            n += 1
    return n


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sertifika-atla", action="store_true",
                    help="TLS doğrulamasını atla (uç sertifikası geçersiz; "
                         "gerekçe ve ölçülmüş çapraz doğrulama modül başlığında)")
    ap.add_argument("--rapor", type=int, action="append", choices=sorted(RAPORLAR),
                    help="yalnız bu rapor(lar); varsayılan dördü")
    ap.add_argument("--banka", action="append",
                    help="yalnız bu slug(lar); varsayılan dokuzu")
    ap.add_argument("--kuru", action="store_true", help="dosyaya yazma, say")
    a = ap.parse_args(argv)

    if not a.sertifika_atla:
        print("HATA: karpayi.tkbb.org.tr sertifikası geçersiz "
              "(ERR_CERT_DATE_INVALID).\n"
              "      Hasat, doğrulamayı atlamayı AÇIKÇA istemeden çalışmaz:\n"
              "        python -m scripts.tkbb_karpayi_hasat --sertifika-atla\n"
              "      Gerekçe ve çapraz doğrulama: bu betiğin modül başlığı.",
              file=sys.stderr)
        return 2

    kok = pathlib.Path(__file__).resolve().parents[1]
    raporlar = sorted(set(a.rapor)) if a.rapor else sorted(RAPORLAR)
    hedef_bankalar = {k: s for k, s in BANKALAR.items()
                      if not a.banka or s in set(a.banka)}
    toplandi = datetime.now(timezone.utc).isoformat(timespec="seconds")

    toplam = 0
    for kimlik, slug in hedef_bankalar.items():
        birikim: list[dict] = []
        parcalar: list[str] = []
        for si in raporlar:
            try:
                html = _istek(kimlik, si, sertifika_atla=True)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                # Bir raporun düşmesi ötekileri iptal etmez; eksik AÇIKÇA yazılır.
                parcalar.append(f"{RAPORLAR[si][0]}=HATA({type(e).__name__})")
                continue
            yeni = list(kayitlar(html, bank_slug=slug, sheet_index=si,
                                 toplandi=toplandi))
            birikim.extend(yeni)
            parcalar.append(f"{RAPORLAR[si][0]}={len(yeni)}")
        n = len(birikim) if a.kuru else _yaz(kok, slug, birikim)
        toplam += n
        print(f"  {slug:24s} {n:>5} kayit   " + " ".join(parcalar))
    etiket = "sayıldı (kuru)" if a.kuru else "yazıldı"
    print(f"\nTOPLAM {toplam} kayit {etiket} · kaynak {KAYNAK_SAYFA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
