"""Tek bankayı ağdan tazeleyen OPERATÖR işi — kullanıcı sorusu yolu buraya bağlanmaz.

İlgili: ./collector.py, ./fetcher.py, ./robots.py, ./harvest.py
        ../api/main.py (`/refresh*` uçları), CLAUDE.md §11, §14

## Neden ayrı bir iş, neden kritik yolun dışında

Sistem internetsiz çalışmak zorunda (CLAUDE.md §1) ve 4 dakikalık sunumda canlı
toplamaya bağlanmış bir demo donma riskidir (§11, §21). Bu yüzden tazeleme
sohbet/kıyas yoluna GÖMÜLMEZ; ayrı bir uçtan, açık bir onayla, ayrı bir iş
parçacığında koşar. Sohbet ve kıyas her hâlde önceden doldurulmuş veri
tabanından okumaya devam eder — bu modül veri tabanı katmanını İÇE AKTARMAZ
(`tests/test_tazeleme.py::TestVeriTabaniDokunulmaz` bunu `ast` ile denetler).

## Alt akış: `alt_akis` geri çağrısı — bağ VAR ama bağımlılık YOK

Tazeleme ham arşive yazıp susarsa, metni değişmiş bir belgenin veri
tabanındaki AI özeti artık o belgeyi tarif etmez ve panelde sessizce durmaya
devam eder. "Bayat özet sessizce durmaz" kuralı gereği bu kabul edilemez.

Çözüm bir geri çağrıdır: `tazele(..., alt_akis=...)` yalnız metni DEĞİŞEN
belgeleri, yazma evresi bittikten SONRA bu çağrılabilire verir. Veri tabanına
ne olacağını çağıran taraf (`api/main.py`) bilir; bu modül bilmez. Böylece
bağ kurulur ama katman ters çevrilmez ve testlerde geri çağrı sahtelenebilir.

Geri çağrının düşmesi tazelemeyi HATA'ya çevirmez: ham arşiv o noktada zaten
doğru yazılmıştır ve onu "başarısız" göstermek operatörü var olmayan bir veri
kaybına inandırırdı. Düşüş nota yazılır, sessiz kalmaz.

## Nereye yazar: `data/raw/<slug>/live/` — kampanya verisine DOKUNMAZ

`data/demo.db` içinde 1751 önceden üretilmiş özet ve 458 geçerlilik damgası var;
bunlar uzun ve pahalı çevrimdışı koşuların ürünü. Canlı bir tazelemenin ortasında
o veri tabanına yazmak, yarıda kesilen bir koşuda kampanya kayıtlarıyla özetleri
tutarsız bırakırdı. Tazeleme bu yüzden yalnızca HAM ARŞİVE yazar; ham arşivden
veri tabanına geçiş ayrı, çevrimdışı ve tekrarlanabilir bir adımdır.

Tek istisna yukarıdaki alt akıştır ve kapsamı KASITLI olarak dar: yalnız metni
değişen belgenin bayat özeti düşer. Kampanya kaydı, çıkarılmış alanlar, gömme
vektörleri ve değişmemiş belgelerin özetleri ellenmez; üstelik bu adım ağ evresi
bittikten SONRA, saniyenin altında koşar — yani "yarıda kesilme veriyi tutarsız
bırakır" riski onun için doğmaz.

Sonuç: en kötü senaryoda bile kaybedilen şey birkaç HTML dosyasıdır, demo değil.

## Yarıda kesilme: ağ evresinde SIFIR yazma

İş iki evreye ayrılmıştır ve ayrım bilinçlidir:

1. **Çekim evresi** (dakikalarca sürer, ağa bağlıdır, her an kesilebilir) —
   belgeler yalnızca BELLEĞE toplanır, diske hiçbir şey yazılmaz.
2. **Yazma evresi** (saniyenin altında, yerel disk) — `save_docs` bir kerede
   çağrılır.

Bu yüzden iptal, ağ kopması ya da sürecin ölmesi ham arşivde yarım belge
bırakmaz. Aynı URL yeniden hasat edildiğinde dosya adı değişmez (`save_docs`
idempotenttir), yani tekrar koşmak güvenlidir.

## Aynı anda iki tazeleme

`TazelemeYoneticisi` tek yuvalıdır: koşan bir iş varken ikinci istek REDDEDİLİR
(`TazelemeMesgul`). İki iş aynı bankaya paralel yazsaydı `save_docs`'un çakışma
koruması iki koşuyu birbirine karıştırırdı; farklı bankalara paralel koşsalardı
bile alan başına gecikme bütçesi (2–5 sn) ortak bir sayaç olmadığı için
delinirdi. Sıraya alma yerine reddetme seçildi: operatör ne olduğunu görür.

## Etik kısıtlar GEVŞETİLMEZ

robots.txt uyumu bu yolda kapatılamaz — `RobotsCache(ignore=...)` parametresi
buradan hiç geçirilmez, sabit olarak uyumlu kurulur. Alan başına gecikme
2–5 saniye aralığına KIRPILIR, User-Agent açıklayıcıdır ve her belge ham
HTML + zaman damgası + kaynak adresiyle (provenance) yazılır.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from .collector import (
    LIVE_SUBDIR,
    collect_live,
    save_docs,
    text_key,
    url_to_slug,
    utc_now_iso,
)
from .config import BankConfig
from .fetcher import (
    KOD_BASLATILAMADI,
    KOD_IKILI_YOK,
    KOD_SURUCU_YOK,
    BrowserFetcher,
    FetcherBundle,
    RateLimiter,
    StaticFetcher,
)
from .robots import DEFAULT_USER_AGENT, RobotsCache

logger = logging.getLogger(__name__)

# Alan başına gecikme sınırları (CLAUDE.md §14: 2–5 sn). API'den gelen değer
# bu aralığa KIRPILIR; uç noktaya 0 yazıp siteyi dövmek mümkün olmamalı.
GECIKME_ALT_SN = 2.0
GECIKME_UST_SN = 5.0
VARSAYILAN_GECIKME_SN = 3.0

# İstek başına zaman aşımı. `harvest.py` ile aynı varsayılan: bazı alan adları
# 25 sn'ye yakın yanıt veriyor, düşürmek onları sessizce eler.
VARSAYILAN_ZAMAN_ASIMI_SN = 25.0

# Tek bir tazelemede çekilecek azami belge. `banks.yaml`'daki `max_docs`
# (bazı bankalarda 200'ün üzerinde) BİLEREK kullanılmıyor: operatör eylemi
# dakikalar sürmeli, saatler değil. Tam hasat CLI'ın işidir.
#
# 25 → 35 (2026-08-13). Sınır ölçümle yükseltildi, tahminle değil: 25 URL'lik
# gerçek bir koşu (albaraka, 20 belge çekildi) ~90 saniye sürdü, yani belge
# başına ~3,6 sn. 35 belge aynı hızda ~2 dakika eder ve keşif evresiyle
# birlikte en kötü hâlde birkaç dakikada kalır — "dakikalar sürmeli, saatler
# değil" gerekçesi hâlâ karşılanıyor. Kazanç: bankaların kampanya listesi 25
# girdiyi aştığında kuyruktaki belgeler sessizce kesiliyordu.
VARSAYILAN_AZAMI_BELGE = 35

# Rapora yazılacak azami satır — hata listesi ekranı boğmasın.
_AZAMI_LISTE = 40

# Durum kodları (arayüz bunlara göre ekran çizer).
DURUM_BEKLIYOR = "bekliyor"
DURUM_KESIF = "kesif"
DURUM_CEKILIYOR = "cekiliyor"
DURUM_YAZILIYOR = "yaziliyor"
DURUM_TAMAM = "tamam"
DURUM_HATA = "hata"
DURUM_IPTAL = "iptal"

# Belge karşılaştırma sonucu.
BELGE_YENI = "yeni"
BELGE_DEGISEN = "degisen"
BELGE_AYNI = "ayni"


# --------------------------------------------------------------------------- #
# Toplama katmanı eksikse: Türkçe, kısa, EYLEME DÖNÜK mesaj
# --------------------------------------------------------------------------- #
# Ekranda görülen eski mesaj şuydu:
#
#   Bu banka için toplama katmanı hazır değil: tarayici baslatilamadi:
#   Error: BrowserType.launch: Executable doesn't exist at
#   /Users/<kullanici>/Library/Caches/ms-playwright/chromium_headless_shell-…
#
# İki ayrı kusur: (1) operatöre ne yapacağını söylemiyor, (2) makinedeki mutlak
# bir dosya yolunu — kullanıcı adı dahil — arayüze taşıyor. Ham istisna metni
# bu yoldan artık HİÇ geçmez: çekici sonlu bir kod üretir (`fetcher.py`),
# ayrıntıyı kendi içinde tutup günlüğe yazar, buradaki eşleme koddan Türkçe
# cümleyi kurar. Bilinmeyen kod için de ham metne DÜŞÜLMEZ; genel cümle
# kullanılır, çünkü "bilinmeyen" tam olarak ham metnin sızdığı yerdir.
#
# Kurulum komutu gösterilir ama ÇALIŞTIRILMAZ: `playwright install chromium`
# internetten indirme yapar ve sistemin çevrimdışı çalışma iddiası (CLAUDE.md
# §1) gereği bu kararı operatör verir.

_KURULUM_KOMUTU = "playwright install chromium"

TARAYICI_MESAJLARI: dict[str, str] = {
    KOD_SURUCU_YOK: (
        "Bu bankanın sayfaları tarayıcıyla açılmayı gerektiriyor, tarayıcı "
        "sürücüsü ise bu makinede kurulu değil. Kurmak için önce "
        "`pip install playwright`, ardından `" + _KURULUM_KOMUTU + "` "
        "komutunu çalıştırın; ikisi de internet gerektirir."
    ),
    KOD_IKILI_YOK: (
        "Bu bankanın sayfaları tarayıcıyla açılmayı gerektiriyor. Tarayıcı "
        "sürücüsü kurulu ancak tarayıcı bileşeni indirilmemiş. Kurmak için "
        "`" + _KURULUM_KOMUTU + "` komutunu çalıştırın; bu komut internet "
        "gerektirir."
    ),
    KOD_BASLATILAMADI: (
        "Bu bankanın sayfaları tarayıcıyla açılmayı gerektiriyor, tarayıcı "
        "ise bu makinede başlatılamadı. Ayrıntı sunucu günlüğüne yazıldı."
    ),
}

_TARAYICI_SONU = (
    " Bu banka atlandı; diğer bankaların toplanması ve önceden hazırlanmış "
    "veri tabanından okuyan kıyas, sohbet ve pano ekranları bundan "
    "etkilenmez."
)

_GENEL_MESAJ = ("Bu banka için toplama katmanı hazır değil, bu yüzden banka "
                "atlandı. Ayrıntı sunucu günlüğüne yazıldı. Diğer bankaların "
                "toplanması ve önceden hazırlanmış veri tabanından okuyan "
                "ekranlar bundan etkilenmez.")


def toplama_katmani_mesaji(kod: Optional[str]) -> str:
    """Toplama katmanı eksikliğinin operatöre dönük Türkçe karşılığı.

    Ham istisna metni ARGÜMAN OLARAK BİLE alınmaz: alınsaydı "bilinmeyen kod"
    dalında ona düşmek cazip olurdu ve sızıntı ilk beklenmedik hatada geri
    gelirdi. Bilinmeyen kod = genel cümle.
    """
    mesaj = TARAYICI_MESAJLARI.get(kod or "")
    return (mesaj + _TARAYICI_SONU) if mesaj else _GENEL_MESAJ


class TazelemeMesgul(RuntimeError):
    """Koşan bir tazeleme varken ikinci iş başlatılmak istendi."""

    def __init__(self, calisan_banka: str) -> None:
        super().__init__(calisan_banka)
        self.calisan_banka = calisan_banka


def gecikmeyi_kirp(deger: Optional[float]) -> float:
    """İstenen gecikmeyi etik aralığa kırpar (2–5 sn)."""
    if deger is None:
        return VARSAYILAN_GECIKME_SN
    return max(GECIKME_ALT_SN, min(GECIKME_UST_SN, float(deger)))


# --------------------------------------------------------------------------- #
# Ön izleme — AĞA ÇIKMAZ
# --------------------------------------------------------------------------- #

def onizleme(bank: BankConfig, *, raw_dir: str | Path = "data/raw",
             azami_belge: int = VARSAYILAN_AZAMI_BELGE,
             gecikme_sn: Optional[float] = None) -> dict[str, Any]:
    """Düğmeye basılmadan ÖNCE ne olacağını anlatan kayıt.

    Tek bir ağ isteği bile yapmaz: sayılar `banks.yaml`'daki giriş noktalarından
    ve sınırlardan türetilir. Operatörün "bu ne kadar sürer" sorusuna cevabı
    ağa çıkmadan verebilmek şart — aksi halde ön izlemenin kendisi bir ağ
    bağımlılığı olurdu.
    """
    gecikme = gecikmeyi_kirp(gecikme_sn)
    giris = len(bank.campaign_paths) + len(bank.sitemap_urls)
    # 1 istek robots.txt için; giriş sayfaları; sonra belge sayfaları.
    istek_alt = 1 + giris + 1
    istek_ust = 1 + giris + azami_belge
    # Alt sınır saf gecikme; üst sınırda istek başına ~2 sn yanıt süresi eklenir.
    sure_alt = int(istek_alt * gecikme)
    sure_ust = int(istek_ust * (gecikme + 2.0))
    mevcut = _mevcut_belge_sayisi(bank, raw_dir)
    return {
        "bank": bank.slug,
        "bank_name": bank.name,
        "website_url": bank.website_url,
        "scrape_mode": bank.scrape_mode,
        "giris_sayfasi": giris,
        "azami_belge": azami_belge,
        "gecikme_sn": gecikme,
        "tahmini_istek_alt": istek_alt,
        "tahmini_istek_ust": istek_ust,
        "tahmini_sure_alt_sn": sure_alt,
        "tahmini_sure_ust_sn": sure_ust,
        "arsivdeki_belge": mevcut,
        "hedef_dizin": str(Path(raw_dir) / bank.slug / LIVE_SUBDIR),
        "internet_gerekir": True,
        # 2026-08-13'e kadar `False`'tu ve o gün YALAN oldu: tazeleme artık
        # bittiğinde metni değişen belgelerin bayat AI özetini düşürüyor
        # (`alt_akis`). Kampanya kayıtları, çıkarılmış alanlar ve değişmeyen
        # belgelerin özetleri ellenmiyor — ama "hiç dokunulmuyor" demek artık
        # doğru değil ve ön izlemenin görevi tam olarak ne olacağını önceden
        # söylemek. Kapsamı `veri_tabani_etkisi` cümlesi taşır.
        "veri_tabani_etkilenir": True,
        "veri_tabani_etkisi": (
            "Yalnız metni DEĞİŞEN belgelerin AI özeti düşürülür (bayat özet "
            "panelde durmasın diye). Kampanya kayıtları, çıkarılmış alanlar ve "
            "değişmeyen belgelerin özetleri olduğu gibi kalır."
        ),
        "robots_uyumu": True,
        "user_agent": DEFAULT_USER_AGENT,
    }


def _mevcut_belge_sayisi(bank: BankConfig, raw_dir: str | Path) -> int:
    """Bu bankanın ham arşivinde şu an kaç canlı belge var."""
    dizin = Path(raw_dir) / bank.slug / LIVE_SUBDIR
    if not dizin.is_dir():
        return 0
    return sum(1 for p in dizin.glob("*.txt") if p.is_file())


# --------------------------------------------------------------------------- #
# Diskteki karşılığı bulma (save_docs'un ad seçimiyle AYNI kural)
# --------------------------------------------------------------------------- #

# `save_docs` çakışan adlarda `-2`, `-3` … ekler. Karşılaştırma aynı kuralı
# izlemezse "değişti" ile "yeni" karışır. Sonsuz döngüye karşı üst sınır.
_AZAMI_AD_DENEMESI = 50


def _diskteki_metin(hedef_dizin: Path, stem: str, source_url: str) -> Optional[str]:
    """Bu kaynak adresine ait, diskte DURAN temiz metin — yoksa None.

    `save_docs._baska_belgeye_ait` ile aynı mantık: sidecar yoksa ya da
    `source_url` eşleşiyorsa aday odur; başka bir adrese aitse sıradaki ad
    denenir.
    """
    aday, n = stem, 2
    for _ in range(_AZAMI_AD_DENEMESI):
        meta = hedef_dizin / f"{aday}.txt.meta.json"
        if not meta.is_file():
            return None  # bu ada hiç yazılmamış → belge yeni
        kayitli: Optional[str] = None
        try:
            kayitli = json.loads(meta.read_text(encoding="utf-8")).get("source_url")
        except (OSError, ValueError):
            kayitli = None
        if not kayitli or not source_url or kayitli == source_url:
            metin_yolu = hedef_dizin / f"{aday}.txt"
            if not metin_yolu.is_file():
                return None
            try:
                return metin_yolu.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                return None
        aday, n = f"{stem}-{n}", n + 1
    return None


def _belgeleri_kiyasla(
        docs: list,
        hedef_dizin: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Her belgeyi diskteki hâliyle karşılaştırır: yeni / değişen / aynı.

    Karşılaştırma TEMİZ METİN üzerindendir, ham bayt özeti üzerinden değil:
    oturum simgesi ve analitik kimliği her istekte değişir, ham özet ölçülseydi
    her tazeleme "hepsi değişti" derdi ve sayı hiçbir şey anlatmazdı.

    İki liste döner:

    * **rapor** — arayüze giden kayıt (`durum.belgeler`). Metin TAŞIMAZ.
    * **degisenler** — alt akış geri çağrısına giden kayıt; her biri belgenin
      ÖNCEKİ metnini taşır. Önceki metin şart: veri tabanındaki hangi satırın
      bu belgeye ait olduğunu güvenle bulmanın yolu odur (aynı `source_url`
      birden fazla kayıtta geçiyor — `live/` ve `archive/` kopyaları).
      İki liste ayrı, çünkü ham metinleri iş durumuna koymak onları HTTP
      cevabına da koyardı: durum uçları 1,5 saniyede bir sorgulanıyor.
    """
    out: list[dict[str, Any]] = []
    degisenler: list[dict[str, Any]] = []
    for doc in docs:
        url = doc.source_url or ""
        stem = url_to_slug(url)
        eski = _diskteki_metin(hedef_dizin, stem, url)
        if eski is None:
            durum = BELGE_YENI
        elif text_key(eski) == text_key(doc.clean_text):
            durum = BELGE_AYNI
        else:
            durum = BELGE_DEGISEN
            degisenler.append({"source_url": url, "title": doc.title,
                               "onceki_metin": eski})
        out.append({
            "source_url": url,
            "title": doc.title,
            "durum": durum,
            "karakter": len(doc.clean_text),
            "onceki_karakter": len(eski) if eski is not None else None,
        })
    return out, degisenler


# --------------------------------------------------------------------------- #
# İş durumu
# --------------------------------------------------------------------------- #

@dataclass
class TazelemeDurumu:
    """Bir tazeleme işinin dışarıya açılan tüm durumu.

    Alanlar kilit altında güncellenir (`TazelemeYoneticisi`), okuma her zaman
    kopya üzerinden yapılır — arayüz yarım güncellenmiş bir kayıt görmez.
    """

    is_id: str
    bank: str
    bank_name: str
    durum: str = DURUM_BEKLIYOR
    asama: str = "Sıraya alındı."
    baslangic: str = field(default_factory=utc_now_iso)
    bitis: Optional[str] = None
    tamamlanan: int = 0
    toplam: int = 0
    cekilen: int = 0
    yeni: int = 0
    degisen: int = 0
    ayni: int = 0
    hata: int = 0
    yazilan_dosya: int = 0
    iptal_istendi: bool = False
    hatalar: list[dict[str, Any]] = field(default_factory=list)
    belgeler: list[dict[str, Any]] = field(default_factory=list)
    notlar: list[str] = field(default_factory=list)
    robots_ozet: Optional[str] = None
    mesaj: Optional[str] = None
    hedef_dizin: Optional[str] = None
    #: Alt akış geri çağrısının raporu (bkz. modül başlığı). `None` = alt akış
    #: hiç koşmadı; boş sözlük değil, çünkü "koşmadı" ile "koştu, iş çıkmadı"
    #: aynı şey değil.
    alt_akis: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_id": self.is_id,
            "bank": self.bank,
            "bank_name": self.bank_name,
            "durum": self.durum,
            "asama": self.asama,
            "baslangic": self.baslangic,
            "bitis": self.bitis,
            "tamamlanan": self.tamamlanan,
            "toplam": self.toplam,
            "cekilen": self.cekilen,
            "yeni": self.yeni,
            "degisen": self.degisen,
            "ayni": self.ayni,
            "hata": self.hata,
            "yazilan_dosya": self.yazilan_dosya,
            "iptal_istendi": self.iptal_istendi,
            "hatalar": self.hatalar[:_AZAMI_LISTE],
            "hata_tamami": len(self.hatalar),
            "belgeler": self.belgeler[:_AZAMI_LISTE],
            "notlar": self.notlar[:_AZAMI_LISTE],
            "robots_ozet": self.robots_ozet,
            "mesaj": self.mesaj,
            "hedef_dizin": self.hedef_dizin,
            "alt_akis": self.alt_akis,
            "bitti": self.durum in (DURUM_TAMAM, DURUM_HATA, DURUM_IPTAL),
        }


# --------------------------------------------------------------------------- #
# Son tazeleme özeti — "canlı takip" iddiasının kalıcı izi
# --------------------------------------------------------------------------- #
# `TazelemeDurumu` TAMAMEN bellek içidir: iş bitince süreç kapanınca kaybolur.
# Panelde "en son ne zaman tazeleme yapıldı, kaç belge değişti/yeni geldi"
# gösterebilmek için BİLİNÇLİ TASARIM KARARI: DB şema değişikliği YOK. SQLite
# + Postgres iki backend'i etkileyen bir migration bu küçük ihtiyaç için
# riskli ve gereksiz — basit bir JSON dosyası yeterli (`celiski_artefakti.py`
# ile aynı desen: pahalı/geçici sonuç, artefakt olarak diske yazılır).
#
# Dosya "her banka için EN SON tazeleme özeti" tutar; banka anahtarıyla
# ÜZERİNE YAZILIR, sınırsız büyümez. Sadece iş TAMAM olduğunda yazılır —
# HATA/İPTAL'de ham arşive zaten hiçbir şey yazılmamış olabilir (modül
# başlığı) ve eski geçerli özeti geçersiz bir kayıtla ezmek yanlış olurdu.

#: Artefaktın deponun içindeki yeri. `data/` altında, `celiski-taramasi.json`
#: ile aynı hizada — ikisi de türetilmiş/derived veri, kaynak değil.
_SON_TAZELEME_AD = "son-tazeleme.json"

#: Biçim sürümü. Alan adı değişirse bu artar; eski dosya `surum` uyuşmazsa
#: (bu modülde şu an denetlenmiyor, ileride eklenmek istenirse buraya) yok
#: sayılabilir. Şimdilik tek okuyucu (`/refresh/last-summary`) alan bazında
#: `.get(...)` kullandığı için eksik alan sessizce `None`/varsayılan olur.
_SON_TAZELEME_SURUM = 1


def _son_tazeleme_yolu(kok: Optional[Path] = None) -> Path:
    """Son tazeleme özet dosyasının yolu.

    `kok` yalnız testler için: gerçek `data/` dizinine yazmadan bu dosyayı
    geçici bir dizine yönlendirir. Üretimde `None` kalır ve depo köküne göre
    sabit yol kullanılır (`comparison/celiski_artefakti.py::yol` ile aynı
    desen) — `raw_dir`'den TÜRETİLMEZ, çünkü testler `raw_dir`'e düz bir
    geçici dizin verir ve o dizinin "üstü" makinede rastgele bir yer olurdu.
    """
    taban = kok or Path(__file__).resolve().parents[2]
    return taban / "data" / _SON_TAZELEME_AD


def son_tazeleme_oku(*, kok: Optional[Path] = None) -> dict[str, dict[str, Any]]:
    """Tüm bankalar için en son tazeleme özetini okur (banka slug'ı → özet).

    Dosya hiç yoksa (hiç tazeleme yapılmamışsa) ya da bozuksa BOŞ sözlük
    döner — hata fırlatmaz: panelin bu ucu her hâlde çizebilmesi gerekiyor.
    """
    yol = _son_tazeleme_yolu(kok)
    if not yol.is_file():
        return {}
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(veri, dict):
        return {}
    bankalar = veri.get("bankalar")
    return bankalar if isinstance(bankalar, dict) else {}


def son_tazeleme_yaz(durum: TazelemeDurumu, *, kok: Optional[Path] = None) -> None:
    """Bir tazeleme işi TAMAM olduğunda banka özetini kalıcı dosyaya yazar.

    Yalnız `durum.durum == DURUM_TAMAM` iken yazar; başka bir çağıran bunu
    HATA/İPTAL'de çağırırsa sessizce hiçbir şey yapmaz — çağıran taraf bunu
    kendi denetlemek zorunda kalmasın diye kontrol burada tekrarlanır.

    Aynı bankanın eski kaydı ÜZERİNE YAZILIR, diğer bankaların kaydı KORUNUR.
    `TazelemeYoneticisi` tek yuvalı olduğu için (aynı anda tek tazeleme koşar)
    ekstra bir kilide gerek yok; yine de yarım/bozuk dosya bırakmamak için
    önce geçici dosyaya yazılıp `os.replace` ile ATOMİK taşınır.
    """
    if durum.durum != DURUM_TAMAM:
        return

    degisen_belgeler = [
        {"title": b.get("title"), "source_url": b.get("source_url")}
        for b in durum.belgeler if b.get("durum") == BELGE_DEGISEN
    ]

    yol = _son_tazeleme_yolu(kok)
    yol.parent.mkdir(parents=True, exist_ok=True)

    bankalar = son_tazeleme_oku(kok=kok)
    bankalar[durum.bank] = {
        "bank": durum.bank,
        "bank_name": durum.bank_name,
        "is_id": durum.is_id,
        "bitis": durum.bitis,
        "yeni": durum.yeni,
        "degisen": durum.degisen,
        "ayni": durum.ayni,
        "hata": durum.hata,
        "degisen_belgeler": degisen_belgeler,
    }

    gecici = yol.with_name(f"{yol.name}.tmp-{uuid.uuid4().hex[:8]}")
    try:
        gecici.write_text(
            json.dumps({"surum": _SON_TAZELEME_SURUM, "bankalar": bankalar},
                       ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8")
        os.replace(gecici, yol)
    except OSError:
        # Bu bir yan etkidir, asıl iş (ham arşive yazma) o ana kadar zaten
        # bitmiş ve BAŞARILI. Diske ikinci kez yazamamak tazelemeyi HATA'ya
        # çevirmemeli — panel geçmiş özeti eksik/bayat görür, veri kaybetmez.
        logger.exception("son tazeleme özeti yazılamadı: %s", durum.bank)
        gecici.unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
# Ağ sayacı — "internet yok" ile "site engelledi" ayrımı
# --------------------------------------------------------------------------- #
# Ayrım operatöre farklı şeyler söyler ve farklı aksiyon gerektirir; ikisini
# tek bir "belge alınamadı" mesajına indirmek en sık sorulan soruyu ("makinede
# internet var mı?") cevapsız bırakır.
#
# Sayaç neden burada ve neden bir sarmalayıcı: keşif evresindeki istekler
# (site haritası, liste sayfaları) `collect_live`'ın tanılama sözlüğüne
# YAZILMIYOR — orada yalnız belge döngüsünün hataları toplanıyor. Ağın hiç
# olmadığı durumda keşif zaten sıfır URL bulur, belge döngüsü hiç koşmaz ve
# hata listesi BOŞ kalır. Sarmalayıcı, iki evredeki tüm denemeleri görür.


class _SayacliCekici:
    """Bir çekiciyi sarar, isteklerin sonucunu sayar. Davranışı değiştirmez."""

    def __init__(self, ic: Any, sayac: "_AgSayaci") -> None:
        self._ic = ic
        self._sayac = sayac

    def __getattr__(self, ad: str) -> Any:
        # `collect_live` sayfalama desteğini `hasattr(fetcher, "fetch_all_pages")`
        # ile yokluyor; delegasyon iç çekicide o metot yoksa AttributeError
        # üretmeli ki yoklama doğru cevabı versin.
        return getattr(self._ic, ad)

    def fetch(self, *args: Any, **kwargs: Any):
        res = self._ic.fetch(*args, **kwargs)
        self._sayac.kaydet(res)
        return res


class _AgSayaci:
    """Bir tazelemedeki tüm HTTP denemelerinin özeti."""

    def __init__(self) -> None:
        self.deneme = 0
        self.yanit_veren = 0
        self.baglanti_hatasi = 0

    def kaydet(self, res: Any) -> None:
        self.deneme += 1
        if getattr(res, "status", None) is not None:
            self.yanit_veren += 1
        elif getattr(res, "error", None) and res.error != "robots disallow":
            self.baglanti_hatasi += 1

    @property
    def ag_yok(self) -> bool:
        """Hiçbir istek yanıt almadı ama en az bir bağlantı denemesi düştü."""
        return self.yanit_veren == 0 and self.baglanti_hatasi > 0


class _SayacliBundle:
    """`FetcherBundle` sarmalayıcısı — `for_mode` sayaçlı çekici döndürür."""

    def __init__(self, ic: Any, sayac: _AgSayaci) -> None:
        self._ic = ic
        self._sayac = sayac

    def for_mode(self, scrape_mode: str) -> _SayacliCekici:
        return _SayacliCekici(self._ic.for_mode(scrape_mode), self._sayac)

    def close(self) -> None:
        self._ic.close()


# --------------------------------------------------------------------------- #
# Çekirdek iş
# --------------------------------------------------------------------------- #

def tazele(bank: BankConfig, raw_dir: str | Path, durum: TazelemeDurumu, *,
           azami_belge: int = VARSAYILAN_AZAMI_BELGE,
           gecikme_sn: Optional[float] = None,
           zaman_asimi_sn: float = VARSAYILAN_ZAMAN_ASIMI_SN,
           bundle: Optional[FetcherBundle] = None,
           robots: Optional[RobotsCache] = None,
           iptal: Optional[Callable[[], bool]] = None,
           alt_akis: Optional[Callable[[list[dict[str, Any]]],
                                       dict[str, Any]]] = None,
           guncelle: Optional[Callable[..., None]] = None,
           son_tazeleme_kok: Optional[Path] = None) -> TazelemeDurumu:
    """Bir bankayı tazeler: çek → karşılaştır → yaz → alt akışı uyar.

    `bundle` / `robots` enjekte edilebilir — testler ağa çıkmadan koşar.
    Enjekte EDİLMEZSE robots denetimi her zaman AÇIK kurulur; bu yolda denetimi
    kapatan bir parametre bilerek yoktur.

    `alt_akis` verilirse YALNIZ metni değişen belgelerle çağrılır (modül
    başlığı). Değişmeyen ya da yeni belge için çağrılmaz: değişmeyen belgenin
    aşağı akışta düzeltilecek bir yanı yok, yeni belgenin ise veri tabanında
    henüz bir karşılığı yok.

    `son_tazeleme_kok` yalnız testler için: iş TAMAM olduğunda `data/
    son-tazeleme.json`'a yazılan kalıcı özetin (bkz. `son_tazeleme_yaz`)
    kök dizinini değiştirir. `None` kalırsa depo köküne göre sabit yol
    kullanılır — üretim akışı bunu hiç geçirmez.
    """
    gecikme = gecikmeyi_kirp(gecikme_sn)
    hedef_dizin = Path(raw_dir) / bank.slug / LIVE_SUBDIR

    def yaz(**kwargs: Any) -> None:
        if guncelle is not None:
            guncelle(**kwargs)
        else:
            for k, v in kwargs.items():
                setattr(durum, k, v)

    yaz(hedef_dizin=str(hedef_dizin), durum=DURUM_KESIF,
        asama=f"{bank.name} sitesinde kampanya sayfaları aranıyor…")

    kendi_bundle = bundle is None
    if bundle is None:
        limiter = RateLimiter(gecikme)
        bundle = FetcherBundle(
            static=StaticFetcher(user_agent=DEFAULT_USER_AGENT, limiter=limiter,
                                 timeout=zaman_asimi_sn),
            browser=BrowserFetcher(user_agent=DEFAULT_USER_AGENT, limiter=limiter,
                                   timeout_ms=int(zaman_asimi_sn * 1000)))
    if robots is None:
        # `ignore` parametresi BİLEREK geçirilmiyor: bu uçtan robots.txt
        # denetimini kapatmanın bir yolu olmamalı.
        robots = RobotsCache(user_agent=DEFAULT_USER_AGENT)

    tani: dict[str, Any] = {}
    sayac = _AgSayaci()
    sayacli = _SayacliBundle(bundle, sayac)

    def ilerleme(tamamlanan: int, toplam: int) -> None:
        yaz(durum=DURUM_CEKILIYOR, tamamlanan=tamamlanan, toplam=toplam,
            asama=f"Belgeler çekiliyor — {tamamlanan}/{toplam}")

    try:
        docs = collect_live(bank, bundle=sayacli, robots=robots,
                            max_docs=azami_belge, report=tani,
                            ilerleme=ilerleme, iptal=iptal)
    except Exception:  # ağ katmanı çökse bile uç ayakta kalmalı
        logger.exception("tazeleme çekim evresinde düştü: %s", bank.slug)
        # Ham istisna metni EKRANA GEÇMEZ: yığın izini `logger.exception`
        # zaten günlüğe tam hâliyle yazdı ve o metin dosya yolu taşıyabilir.
        yaz(durum=DURUM_HATA, bitis=utc_now_iso(),
            asama="Tazeleme tamamlanamadı.",
            mesaj="Toplama katmanı beklenmedik bir hata verdi ve tazeleme "
                  "tamamlanamadı. Ham arşive hiçbir belge yazılmadı; ayrıntı "
                  "sunucu günlüğüne kaydedildi.")
        return durum
    finally:
        if kendi_bundle:
            bundle.close()

    hatalar = list(tani.get("blocked") or [])
    notlar = [str(n) for n in (tani.get("notes") or [])]
    try:
        robots_ozet = robots.policy_for(bank.website_url).summary()
    except Exception:  # robots özeti bir raporlama ayrıntısıdır, iş değil
        robots_ozet = None

    yaz(cekilen=len(docs), hata=len(hatalar), hatalar=hatalar, notlar=notlar,
        robots_ozet=robots_ozet)

    # İPTAL: hiçbir şey yazılmaz. Çekim evresi diske dokunmadığı için ham
    # arşiv, iş hiç başlamamış gibi kalır.
    if tani.get("iptal") or (iptal is not None and iptal()):
        yaz(durum=DURUM_IPTAL, bitis=utc_now_iso(),
            asama="Tazeleme durduruldu.",
            mesaj="İşlem operatör tarafından durduruldu; ham arşive hiçbir "
                  "belge yazılmadı.")
        return durum

    if not docs:
        if sayac.ag_yok:
            mesaj = ("Ağ bağlantısı kurulamadı. Bu eylem internet gerektirir; "
                     "sistemin geri kalanı çevrimdışı çalışmaya devam ediyor.")
        elif hatalar:
            mesaj = ("Hiçbir belge alınamadı: site istekleri reddetti ya da "
                     "sayfalar erişime kapalı. Ayrıntılar aşağıdaki listede.")
        elif tani.get("skipped_reason"):
            mesaj = toplama_katmani_mesaji(tani.get("skipped_code"))
        else:
            mesaj = ("Site erişilebilir ancak yeni belge bulunamadı. Ham arşiv "
                     "değişmedi.")
        basarisiz = bool(sayac.ag_yok or hatalar or tani.get("skipped_reason"))
        yaz(durum=DURUM_HATA if basarisiz else DURUM_TAMAM,
            bitis=utc_now_iso(), asama="Tazeleme bitti.", mesaj=mesaj)
        son_tazeleme_yaz(durum, kok=son_tazeleme_kok)
        return durum

    yaz(durum=DURUM_YAZILIYOR,
        asama=f"{len(docs)} belge ham arşive yazılıyor…")

    # Karşılaştırma YAZMADAN ÖNCE yapılır: yazdıktan sonra bakılsaydı diskteki
    # metin zaten yeni hâli olurdu ve "değişen" sayısı her zaman sıfır çıkardı.
    belgeler, degisenler = _belgeleri_kiyasla(docs, hedef_dizin)
    yeni = sum(1 for b in belgeler if b["durum"] == BELGE_YENI)
    degisen = sum(1 for b in belgeler if b["durum"] == BELGE_DEGISEN)
    ayni = sum(1 for b in belgeler if b["durum"] == BELGE_AYNI)

    try:
        yazilan = save_docs(docs, raw_dir)
    except OSError:
        # `str(exc)` mutlak dosya yolu taşır ("[Errno 13] Permission denied:
        # /Users/…"). Yol günlüğe gider, ekrana değil.
        logger.exception("ham arşive yazma başarısız: %s", bank.slug)
        yaz(durum=DURUM_HATA, bitis=utc_now_iso(),
            asama="Yazma başarısız.",
            belgeler=belgeler, yeni=yeni, degisen=degisen, ayni=ayni,
            mesaj="Belgeler ham arşive yazılamadı; disk dolu ya da hedef "
                  "dizine yazma izni yok olabilir. Ayrıntı sunucu günlüğüne "
                  "kaydedildi.")
        return durum

    # Alt akış YAZMADAN SONRA koşar: ham arşiv doğru hâline gelmeden veri
    # tabanındaki özeti düşürmek, yarıda kesilen bir koşuda özeti de belgeyi
    # de kaybettirirdi.
    alt_rapor: Optional[dict[str, Any]] = None
    if degisenler and alt_akis is not None:
        yaz(asama="Değişen belgelerin bayat özetleri düşürülüyor…")
        try:
            alt_rapor = alt_akis(degisenler)
        except Exception:
            # Ham arşiv doğru yazıldı; işi HATA'ya çevirmek olmayan bir veri
            # kaybını haber vermek olurdu. Sessiz de kalınmaz: not düşülür.
            logger.exception("tazeleme alt akışı düştü: %s", bank.slug)
            notlar = notlar + [
                "Değişen belgelerin özetleri geçersizlenemedi; panelde eski "
                "özet görünmeye devam edebilir. Ayrıntı sunucu günlüğünde."]
            yaz(notlar=notlar)

    mesaj = ("Belgeler ham arşive yazıldı. Kıyas ve sohbet ekranları önceden "
             "hazırlanmış veri tabanından okumaya devam ediyor; bu belgeler "
             "oraya ayrı bir çevrimdışı adımda aktarılır.")
    if alt_rapor and alt_rapor.get("mesaj"):
        mesaj = f"{mesaj} {alt_rapor['mesaj']}"

    yaz(durum=DURUM_TAMAM, bitis=utc_now_iso(), asama="Tazeleme tamamlandı.",
        belgeler=belgeler, yeni=yeni, degisen=degisen, ayni=ayni,
        yazilan_dosya=len(yazilan), alt_akis=alt_rapor, mesaj=mesaj)
    son_tazeleme_yaz(durum, kok=son_tazeleme_kok)
    return durum


# --------------------------------------------------------------------------- #
# Yönetici — tek yuva, kilitli durum
# --------------------------------------------------------------------------- #

class TazelemeYoneticisi:
    """Tek yuvalı tazeleme işi yöneticisi (iş parçacığı güvenli).

    Aynı anda EN FAZLA bir iş koşar. Bitmiş işin durumu saklanır ki operatör
    sonucu ekranda görebilsin; yeni bir iş başlatmak eskisinin kaydını
    değiştirmez, yalnızca "son iş" işaretini taşır.
    """

    def __init__(self, raw_dir: str | Path = "data/raw", *,
                 calisma_fn: Optional[Callable[..., Any]] = None,
                 azami_belge: int = VARSAYILAN_AZAMI_BELGE,
                 alt_akis: Optional[Callable[[list[dict[str, Any]]],
                                             dict[str, Any]]] = None,
                 gecikme_sn: float = VARSAYILAN_GECIKME_SN,
                 son_tazeleme_kok: Optional[Path] = None) -> None:
        self.raw_dir = str(raw_dir)
        self._calisma_fn = calisma_fn or tazele
        # Öntanım `None`: yöneticiyi alt akış olmadan kurmak GEÇERLİ bir
        # kullanım (CLI, testler, veri tabanı olmayan ortam). Varsayılan bir
        # depo bağlantısı kurmak, bu modülü veri tabanına bağlardı.
        self._alt_akis = alt_akis
        self.azami_belge = azami_belge
        self.gecikme_sn = gecikmeyi_kirp(gecikme_sn)
        # `raw_dir`'DEN TÜRETİLMEZ (bkz. `_son_tazeleme_yolu`): testler
        # `raw_dir`'e düz bir geçici dizin verir, bu yüzden `None` öntanımı
        # depo köküne göre sabit `data/son-tazeleme.json` yolunu kullanır.
        self._son_tazeleme_kok = son_tazeleme_kok
        self._kilit = threading.Lock()
        self._isler: dict[str, TazelemeDurumu] = {}
        self._aktif: Optional[str] = None
        self._son: Optional[str] = None

    # -- durum okuma ------------------------------------------------------ #

    def durum(self, is_id: str) -> Optional[dict[str, Any]]:
        with self._kilit:
            kayit = self._isler.get(is_id)
            return kayit.to_dict() if kayit else None

    def son_is(self) -> Optional[dict[str, Any]]:
        with self._kilit:
            if self._son is None:
                return None
            kayit = self._isler.get(self._son)
            return kayit.to_dict() if kayit else None

    def aktif_banka(self) -> Optional[str]:
        with self._kilit:
            if self._aktif is None:
                return None
            kayit = self._isler.get(self._aktif)
            return kayit.bank_name if kayit else None

    # -- iş yaşam döngüsü ------------------------------------------------- #

    def baslat(self, bank: BankConfig) -> dict[str, Any]:
        """Yeni bir tazeleme başlatır. Koşan iş varsa `TazelemeMesgul` fırlatır."""
        with self._kilit:
            if self._aktif is not None:
                calisan = self._isler.get(self._aktif)
                raise TazelemeMesgul(calisan.bank_name if calisan else "bilinmeyen")
            is_id = uuid.uuid4().hex[:12]
            kayit = TazelemeDurumu(is_id=is_id, bank=bank.slug, bank_name=bank.name)
            self._isler[is_id] = kayit
            self._aktif = is_id
            self._son = is_id

        def guncelle(**kwargs: Any) -> None:
            with self._kilit:
                for k, v in kwargs.items():
                    setattr(kayit, k, v)

        def iptal_mi() -> bool:
            with self._kilit:
                return kayit.iptal_istendi

        def kos() -> None:
            try:
                self._calisma_fn(bank, self.raw_dir, kayit,
                                 azami_belge=self.azami_belge,
                                 gecikme_sn=self.gecikme_sn,
                                 alt_akis=self._alt_akis,
                                 iptal=iptal_mi, guncelle=guncelle,
                                 son_tazeleme_kok=self._son_tazeleme_kok)
            except Exception:  # iş parçacığı sessizce ölmemeli
                logger.exception("tazeleme işi düştü: %s", bank.slug)
                guncelle(durum=DURUM_HATA, bitis=utc_now_iso(),
                         asama="Tazeleme tamamlanamadı.",
                         mesaj="Beklenmedik bir hata oluştu; ayrıntı sunucu "
                               "günlüğünde.")
            finally:
                with self._kilit:
                    self._aktif = None

        # `daemon=True`: çekim evresi dakikalarca sürebilir ve o evrede diske
        # hiçbir şey yazılmaz, dolayısıyla sürecin kapanışını bu iş parçacığı
        # için bekletmenin bir bedeli var, kazancı yok.
        threading.Thread(target=kos, name=f"tazeleme-{bank.slug}",
                         daemon=True).start()
        return kayit.to_dict()

    def iptal_et(self, is_id: str) -> Optional[dict[str, Any]]:
        """İptal İSTER; iş bir sonraki belge sınırında durur."""
        with self._kilit:
            kayit = self._isler.get(is_id)
            if kayit is None:
                return None
            if kayit.durum not in (DURUM_TAMAM, DURUM_HATA, DURUM_IPTAL):
                kayit.iptal_istendi = True
                kayit.asama = "Durdurma istendi; sıradaki belgede duracak…"
            return kayit.to_dict()


__all__ = [
    "TazelemeDurumu", "TazelemeMesgul", "TazelemeYoneticisi",
    "gecikmeyi_kirp", "onizleme", "tazele",
    "son_tazeleme_oku", "son_tazeleme_yaz",
    "GECIKME_ALT_SN", "GECIKME_UST_SN", "VARSAYILAN_AZAMI_BELGE",
    "DURUM_BEKLIYOR", "DURUM_KESIF", "DURUM_CEKILIYOR", "DURUM_YAZILIYOR",
    "DURUM_TAMAM", "DURUM_HATA", "DURUM_IPTAL",
    "BELGE_YENI", "BELGE_DEGISEN", "BELGE_AYNI",
]
