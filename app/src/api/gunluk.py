"""İşlem günlüğü (audit log) — "ne oldu, ne zaman oldu, kim tetikledi".

İlgili: ./main.py (`GET /log` + istek ara katmanı), ../scraping/tazeleme.py
        ../summarize/ozet_isi.py, CLAUDE.md §1 (offline), §19, §20

## Neden var — gerçek olay

2026-08-13'te bir canlı tazeleme koştu ve `data/raw/albaraka/live/` altına 40
dosya yazdı. "Bunu kim tetikledi, ne zaman" sorusu SAATLERCE cevapsız kaldı;
sonunda cevabı sistem değil, kullanıcının hafızası verdi. Sistemde bu soruya
cevap veren KALICI hiçbir kayıt yoktu: `/refresh` gibi ağa çıkan uçlar, ham
arşive yazan uçlar (`/summaries/build`) ve yerel modeli çalıştıran uçlar
(`/extract`) izsiz koşuyordu. İş yöneticilerinin (`TazelemeYoneticisi`,
`OzetYoneticisi`) tuttuğu durum kayıtları BELLEKTEDİR — süreç yeniden
başladığında yok olurlar ve zaten yalnız son işi taşırlar.

Bu modül tam olarak o boşluğu kapatır ve başka bir şey yapmaz: metrik toplamaz,
kullanıcı profili çıkarmaz, iş kuyruğu yönetmez.

## Biçim: ekleme-only JSONL, yeni bağımlılık YOK

Kayıt başına tek satır JSON. Seçimin gerekçesi üç maddede:

1. **Yeni bağımlılık yok.** Sistem tamamen offline ve yalnız Apache/MIT
   lisanslı bileşen kullanabiliyor (CLAUDE.md §1, §7). Bir günlük kütüphanesi
   ya da ayrı bir tablo için `stdlib` dışına çıkmaya değecek bir kazanç yok.
2. **Ekleme-only.** Denetim kaydının değeri değiştirilmemiş olmasından gelir.
   JSONL'de bir kayıt yazıldıktan sonra dosyanın geri kalanına dokunulmaz;
   veri tabanına yazsaydık aynı `UPDATE` yüzeyi günlüğü de kapsardı.
3. **Veri tabanından AYRI.** `data/demo.db` demo korpusudur ve `build_demo_db`
   ile yeniden kurulur. Günlüğü oraya koymak, "kim ne yaptı" kaydını demo
   verisiyle birlikte silinebilir hâle getirirdi.

Yol yapılandırılabilir (`AUDIT_LOG_PATH`); varsayılanı `data/gunluk/` altındadır
ve `.gitignore`'dadır — günlük bir çalışma artefaktıdır, depoya girmez.

## NE KAYDEDİLMEZ — bilinçli kararlar

- **İstek gövdesi.** `POST /chat` gövdesi kullanıcının sorusudur ve kişisel veri
  taşıyabilir ("50 bin TL kredim var, 36 ay vadede..."). Gövdeyi kaydetmek,
  kaydı asla silinmeyen bir yere kişisel veri yazmak olurdu (CLAUDE.md §19:
  repoda kişisel/müşteri verisi olmaz).
- **Sorgu dizgesi (query string).** `?q=` `/search` ve `/campaigns` yollarında
  serbest metindir; gövdeyle aynı risk. Yalnız yolun kendisi (`request.url.path`)
  yazılır — `/campaigns/847/text` gibi kimlikler kalır, arama terimi kalmaz.
- **Başlıklar / çerezler / kimlik bilgileri.** Hiçbiri okunmaz.
- **Yanıt gövdesi.** Ara katman yanıtı AÇMAZ. Yazan uçların özeti, ucun
  KENDİSİNİN bildirdiği dar bir sözlükten gelir (`eylem_bildir()`), yani
  kaydedilen şey ucun sonucudur, isteğin kopyası değil. `_eylem_temizle()` o
  sözlüğü de ayrıca budar (yalnız skaler, sınırlı anahtar, sınırlı uzunluk) ki
  ileride bir uç yanlışlıkla gövde geçirse bile günlüğe dökülmesin.

Kaydedilen: zaman (UTC ISO-8601), metot, yol, durum kodu, süre (ms), yazan-mı
bayrağı, istemci adresi, iş kimliği (varsa), eylem özeti (yazan uçlarda).

**İstemci adresi** kaydedilir çünkü olayın tamamı "kim" sorusuydu. Kaynak
`request.client.host`'tur; `X-Forwarded-For` gibi BAŞLIKLARA GÜVENİLMEZ — onlar
istemcinin yazdığı metindir ve denetim kaydında sahtelenebilir bir alanı
gerçekmiş gibi tutmak kaydın kendisini değersizleştirir.

## "Yazan" bayrağı — panel gürültüde boğulmasın

Panel her sekme değişiminde `/compare`, `/stats`, `/advantageous` çağırıyor ve
`/refresh/status` iş koşarken saniyede bir yoklanıyor. Hepsi eşit ağırlıkta
gösterilseydi "bunu kim yaptı" sorusu okuma trafiğinin içinde kaybolurdu. Bu
yüzden her istek KAYDEDİLİR ama yazanlar ayrıca İŞARETLENİR ve panel varsayılan
olarak yalnız onları gösterir.

Ölçüt METODA bakar: `POST` / `PUT` / `PATCH` / `DELETE`. İkinci bir yol listesi
TUTULMAZ, çünkü iki doğruluk kaynağı zamanla ayrışır ve ayrıştığında sessizce
yanlış etiket üretir. Bugün kullanıcının saydığı eylem uçlarının hepsi zaten bu
metotlardadır: `POST /refresh`, `POST /refresh/cancel/{id}`,
`POST /summaries/build`, `POST /summaries/cancel/{id}`, `POST /extract`
(`tests/test_api_gunluk.py::TestYazanUclarIsaretlenir` bunu kilitler).

`POST /chat` ve `POST /extract` diske hiçbir şey yazmaz ama yine `yazan`
sayılır. Bilinçli: bayrağın ayırdığı şey "sistem üzerinde eylem" ile "ekran
okuma"dır, ve elle bakımlı bir istisna listesi ilk yeni uçta bayatlar. Bir
eyleme yanlışlıkla "okuma" demek, bir okumaya "eylem" demekten daha pahalıdır.

## Döndürme (rotation) — sınırsız büyümez, ama sessizce de kaybolmaz

Dosya `AUDIT_LOG_MAX_BYTES`'ı aştığında `.1`, `.2`, ... `.N` olarak kaydırılır;
`.N` silinir. Toplam tavan `(N+1) × azami_bayt`'tır.

Döndürmenin KENDİSİ yeni dosyanın ilk satırına kayıt olarak düşer
(`olay: "gunluk_dondu"`, hangi dosyaya taşındığı ve hangisinin silindiği ile).
Gerekçe: döndürme sessiz olsaydı, kısalmış bir günlüğe bakan kişi "kayıt
kayboldu mu, yoksa hiç mi olmadı" sorusunu cevaplayamazdı — ve denetim kaydında
bu ayrım her şeydir. `oku()` bu kaydı `yalniz_yazanlar` süzgecinde de GÖSTERİR.

## Okuma: `oku()` ham dosyayı dökmez

`GET /log` bu dosyayı olduğu gibi göndermez; `oku()` süzer, sayfalar ve yeniden
eskiye sıralar. Sıralama zaman damgasına DEĞİL dosya sırasına bakar: dosya
ekleme-only olduğu için yazılış sırası zaten kronolojiktir ve damgaya güvenmek,
saat geri alındığında sıralamayı bozardı.

`oku()` yalnız ETKİN dosyayı okur, döndürülmüş kuşakları değil. Kasıtlı: bir uç
noktanın cevabı sınırlı ve öngörülebilir olmalı, ve "eski kuşakta ne vardı"
sorusunun cevabı diskte duruyor. Nereye taşındığı zaten döndürme kaydındadır.

## Eşzamanlılık

FastAPI `def` uçlarını threadpool'da koşturur, yani yazma çok iş parçacıklıdır.
Döndürme + ekleme tek bir `threading.Lock` altındadır. Okuma kilit ALMAZ
(uzun bir dosya taraması yazarları bekletirdi); bozuk/yarım satırlar sessizce
atlanır — POSIX'te `O_APPEND` ile yazılan tek satırlık kayıtlar bölünmez, bu
yüzden atlama pratikte ölü bir savunmadır ama bedeli de yoktur.

## Değişmez: günlük yazımı isteği DÜŞÜRMEZ

Disk dolduğunda, izin kalktığında ya da yol bir dizine dönüştüğünde istek
BAŞARISIZ OLMAZ. `yaz()` her hatayı yutar, `logger.warning` ile ayrı kanaldan
bildirir ve `False` döner. Denetim kaydı bir kolaylıktır; onun yokluğu yüzünden
kullanıcının kıyas ekranının açılmaması, çözdüğünden büyük bir sorun olurdu.
Bu davranış `tests/test_api_gunluk.py::TestGunlukIstegiDusurmez` ile çitlenmiştir.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from datetime import time as _time
from pathlib import Path
from typing import Any, Optional

from ..scraping.collector import utc_now_iso

logger = logging.getLogger(__name__)

#: Günlük dosyasının varsayılan yolu. `data/` altında, ama `data/demo.db`'den
#: AYRI bir dizinde: demo veri tabanı yeniden kurulabilir bir artefakt,
#: denetim kaydı ise değil.
VARSAYILAN_YOL = "data/gunluk/islem-gunlugu.jsonl"

#: Etkin dosyanın üst sınırı. 5 MB ~ 30 bin kayıt (kayıt başına ~170 bayt
#: ölçüldü); demo ölçeğinde aylarca yeter, tek bir `cat` ile de okunabilir.
VARSAYILAN_AZAMI_BAYT = 5 * 1024 * 1024

#: Saklanan döndürülmüş kuşak sayısı. Toplam tavan `(N+1) × azami_bayt` = 20 MB.
VARSAYILAN_YEDEK = 3

#: `olay` alanının değerleri. Kayıtların çoğu isteklerdir; döndürme ise
#: sistemin kendi hakkındaki tek kaydıdır.
OLAY_ISTEK = "istek"
OLAY_DONDURME = "gunluk_dondu"

#: Yazan sayılan HTTP metotları (gerekçe: modül başlığı "Yazan bayrağı").
YAZAN_METOTLAR = frozenset({"POST", "PUT", "PATCH", "DELETE"})

VARSAYILAN_LIMIT = 100
AZAMI_LIMIT = 500

#: Eylem özetinin budama sınırları. Uçlar bu sözlüğü kendileri veriyor, yani
#: bugün güvenilir; sınırlar ileride bir ucun yanlışlıkla gövde geçirmesine
#: karşı durur (bkz. modül başlığı "NE KAYDEDİLMEZ").
EYLEM_AZAMI_ANAHTAR = 12
EYLEM_AZAMI_METIN = 200

#: `request.state` üzerinde eylem özetinin taşındığı ad. Ara katman ile uçlar
#: arasındaki tek sözleşme budur.
DURUM_ANAHTARI = "gunluk_eylem"


def yazan_mi(metot: Optional[str]) -> bool:
    """İstek "yazan" (sistem üzerinde eylem) sayılır mı.

    Ölçüt yalnız metottur; ikinci bir yol listesi bilerek tutulmaz — gerekçe
    modül başlığındaki "Yazan bayrağı" bölümünde.
    """
    return (metot or "").upper() in YAZAN_METOTLAR


def _eylem_temizle(eylem: Any) -> Optional[dict[str, Any]]:
    """Eylem özetini kaydedilebilir hâle budar; budanamazsa `None`.

    Yalnız skaler değerler geçer (metin / sayı / bool / `None`). İç içe sözlük
    ve liste DÜŞÜRÜLÜR: bir uç yanlışlıkla yanıt gövdesini geçirdiğinde günlük
    o gövdeyi yutmasın diye. Metinler kırpılır, anahtar sayısı sınırlanır.
    """
    if not isinstance(eylem, dict) or not eylem:
        return None
    out: dict[str, Any] = {}
    for ad, deger in eylem.items():
        if len(out) >= EYLEM_AZAMI_ANAHTAR:
            break
        if not isinstance(ad, str):
            continue
        if isinstance(deger, str):
            kirpik = deger.strip()
            out[ad] = (kirpik[:EYLEM_AZAMI_METIN] + "…"
                       if len(kirpik) > EYLEM_AZAMI_METIN else kirpik)
        elif isinstance(deger, bool) or isinstance(deger, (int, float)) or deger is None:
            out[ad] = deger
        # Diğer her tip (dict, list, nesne) SESSİZCE düşer — kaydedilecek bir
        # şey olmadığı için değil, kaydedilmemesi gerektiği için.
    return out or None


def eylem_bildir(request: Any, **alanlar: Any) -> None:
    """Uç, kendi sonucundan çıkardığı eylem özetini ara katmana bildirir.

    Neden `request.state` üzerinden: ara katman yanıtın GÖVDESİNİ açmaz
    (gerekçe modül başlığında), bu yüzden "hangi banka, hangi iş" bilgisini
    ucun kendisi vermek zorunda. `contextvars` kullanılamaz — FastAPI `def`
    uçlarını threadpool'da koşturur ve orada yapılan bağlam değişikliği
    çağırana geri dönmez; `request.state` ise ara katmanın elindeki NESNENİN
    kendisidir.

    Çağrı hiçbir koşulda isteği düşürmez: `request` beklenmedik bir şeyse
    (test, sahte nesne) sessizce hiçbir şey yapılmaz.
    """
    try:
        setattr(request.state, DURUM_ANAHTARI, dict(alanlar))
    except Exception:  # pragma: no cover - savunma; günlük isteği düşürmez
        logger.debug("Eylem özeti request.state'e yazılamadı", exc_info=True)


def _zaman_coz(deger: str, *, gun_sonu: bool = False) -> datetime:
    """Süzgeç zamanını UTC `datetime`'a çevirir; bozuksa `ValueError`.

    Yalnız tarih verilmişse (`2026-08-13`) gün sonu süzgeci o günün SONUNU
    kapsar. Aksi hâlde "13 Ağustos'a kadar" diyen bir süzgeç 13 Ağustos'un
    tamamını dışarıda bırakırdı ve kullanıcı kaydın silindiğini sanırdı.
    """
    ham = (deger or "").strip()
    if not ham:
        raise ValueError("Boş zaman süzgeci.")
    try:
        cozum = datetime.fromisoformat(ham.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            f"Zaman süzgeci ISO-8601 değil: {ham!r} "
            "(örnek: 2026-08-13 veya 2026-08-13T09:00:00Z)") from exc
    if len(ham) == 10 and gun_sonu:
        cozum = datetime.combine(cozum.date(), _time.max)
    if cozum.tzinfo is None:
        # Damgasız girdi UTC sayılır: kayıtların tamamı UTC ve iki farklı
        # saat dilimini karıştıran bir süzgeç sessizce yanlış aralık verir.
        cozum = cozum.replace(tzinfo=timezone.utc)
    return cozum.astimezone(timezone.utc)


def _kayit_zamani(kayit: dict[str, Any]) -> Optional[datetime]:
    """Kaydın damgasını `datetime`'a çevirir; çözülemezse `None`."""
    ham = kayit.get("zaman")
    if not isinstance(ham, str):
        return None
    try:
        cozum = datetime.fromisoformat(ham.replace("Z", "+00:00"))
    except ValueError:
        return None
    if cozum.tzinfo is None:
        cozum = cozum.replace(tzinfo=timezone.utc)
    return cozum.astimezone(timezone.utc)


class GunlukYazici:
    """Ekleme-only JSONL denetim günlüğü — yazar, döndürür, süzerek okur.

    İş parçacığı güvenlidir (yazma tarafı); hiçbir yazma hatası çağırana
    yansımaz. Gerekçelerin tamamı modül başlığındadır.
    """

    def __init__(self, yol: str | Path = VARSAYILAN_YOL, *,
                 azami_bayt: int = VARSAYILAN_AZAMI_BAYT,
                 yedek_sayisi: int = VARSAYILAN_YEDEK) -> None:
        self.yol = Path(yol)
        # Sıfır/negatif bir sınır her yazmada döndürme demekti; en az 1 KB'a
        # kırpılır ki yanlış yapılandırma günlüğü kullanılamaz hâle getirmesin.
        self.azami_bayt = max(1024, int(azami_bayt))
        self.yedek_sayisi = max(0, int(yedek_sayisi))
        self._kilit = threading.Lock()

    # -- kurulum ---------------------------------------------------------- #

    @classmethod
    def ortamdan(cls) -> "GunlukYazici":
        """Ortam değişkenlerinden kurar (`build_app()` bunu çağırır).

        Bozuk bir sayı değeri uygulamayı DÜŞÜRMEZ: varsayılana düşülür ve
        durum uyarı olarak bildirilir. API'nin `AUDIT_LOG_MAX_BYTES=abc`
        yüzünden hiç açılmaması, günlüğün kendisinden pahalı olurdu.
        """
        return cls(
            os.environ.get("AUDIT_LOG_PATH", VARSAYILAN_YOL),
            azami_bayt=_sayi_oku("AUDIT_LOG_MAX_BYTES", VARSAYILAN_AZAMI_BAYT),
            yedek_sayisi=_sayi_oku("AUDIT_LOG_KEEP", VARSAYILAN_YEDEK),
        )

    # -- yazma ------------------------------------------------------------ #

    def istek_kaydet(self, *, metot: str, yol: str, durum: int,
                     sure_ms: float, istemci: Optional[str] = None,
                     is_id: Optional[str] = None,
                     eylem: Any = None) -> bool:
        """Bir HTTP isteğini kaydeder. Hiçbir koşulda istisna fırlatmaz."""
        kayit: dict[str, Any] = {
            "zaman": utc_now_iso(),
            "olay": OLAY_ISTEK,
            "metot": (metot or "").upper(),
            "yol": yol,
            "durum": int(durum),
            # Milisaniye tek ondalıkla: denetim kaydında mikrosaniye gürültüsü
            # okunabilirlikten başka bir şey götürmez.
            "sure_ms": round(float(sure_ms), 1),
            "yazan": yazan_mi(metot),
            "istemci": istemci,
            "is_id": is_id,
        }
        temiz = _eylem_temizle(eylem)
        if temiz is not None:
            kayit["eylem"] = temiz
        return self.yaz(kayit)

    def yaz(self, kayit: dict[str, Any]) -> bool:
        """Kaydı dosyaya ekler. Başarısızlık `False` döner, İSTİSNA ATMAZ.

        Gerekçe modül başlığında: denetim kaydının yokluğu, kullanıcının
        isteğini düşürmeye değmez.
        """
        try:
            satir = json.dumps(kayit, ensure_ascii=False, default=str)
        except Exception:  # pragma: no cover - json.dumps default=str ile düşmez
            logger.warning("İşlem günlüğü kaydı JSON'a çevrilemedi",
                           exc_info=True)
            return False
        try:
            with self._kilit:
                self.yol.parent.mkdir(parents=True, exist_ok=True)
                dondurme = self._gerekirse_dondur()
                with self.yol.open("a", encoding="utf-8") as dosya:
                    if dondurme is not None:
                        dosya.write(json.dumps(dondurme, ensure_ascii=False) + "\n")
                    dosya.write(satir + "\n")
            return True
        except Exception:
            # Disk dolu, izin yok, yol bir dizin... Hepsi burada biter.
            logger.warning("İşlem günlüğü yazılamadı: %s", self.yol,
                           exc_info=True)
            return False

    def _yedek_yolu(self, kusak: int) -> Path:
        return self.yol.with_name(f"{self.yol.name}.{kusak}")

    def _gerekirse_dondur(self) -> Optional[dict[str, Any]]:
        """Sınır aşıldıysa dosyayı döndürür ve döndürme kaydını döner.

        Kilit ÇAĞIRANDA tutulur (`yaz()`): döndürme ile ekleme arasına başka
        bir yazar girerse kayıt yanlış kuşağa düşerdi.
        """
        try:
            bayt = self.yol.stat().st_size
        except FileNotFoundError:
            return None
        if bayt < self.azami_bayt:
            return None

        silinen: Optional[str] = None
        if self.yedek_sayisi == 0:
            # Kuşak tutulmuyorsa etkin dosya doğrudan gider. Kaydın kaybolduğu
            # yine de YAZILIR — sessiz kısalma denetim kaydının en kötü hâli.
            silinen = self.yol.name
            self.yol.unlink()
            hedef = None
        else:
            en_eski = self._yedek_yolu(self.yedek_sayisi)
            if en_eski.exists():
                silinen = en_eski.name
                en_eski.unlink()
            for kusak in range(self.yedek_sayisi - 1, 0, -1):
                kaynak = self._yedek_yolu(kusak)
                if kaynak.exists():
                    kaynak.rename(self._yedek_yolu(kusak + 1))
            hedef = self._yedek_yolu(1)
            self.yol.rename(hedef)

        return {
            "zaman": utc_now_iso(),
            "olay": OLAY_DONDURME,
            "bayt": bayt,
            "azami_bayt": self.azami_bayt,
            "tasinan_dosya": hedef.name if hedef is not None else None,
            "silinen_dosya": silinen,
        }

    # -- okuma ------------------------------------------------------------ #

    def oku(self, *, yalniz_yazanlar: bool = True,
            metot: Optional[str] = None, yol: Optional[str] = None,
            baslangic: Optional[str] = None, bitis: Optional[str] = None,
            limit: int = VARSAYILAN_LIMIT,
            offset: int = 0) -> tuple[list[dict[str, Any]], int]:
        """Süzülmüş, sayfalanmış kayıtlar + süzgeç sonrası TOPLAM.

        Sıra yeniden eskiye. Dayanak dosya sırasıdır, zaman damgası değil:
        dosya ekleme-only olduğu için yazılış sırası kronolojiktir ve saat
        geri alındığında damgaya güvenen bir sıralama bozulurdu.

        Bozuk zaman süzgeci `ValueError` yükseltir (çağıran 400'e çevirir);
        bozuk KAYIT satırı ise sessizce atlanır — biri istemcinin hatası,
        diğeri bizim tarafımızdaki bir artık.
        """
        alt = _zaman_coz(baslangic) if baslangic else None
        ust = _zaman_coz(bitis, gun_sonu=True) if bitis else None
        metot_suzgec = metot.strip().upper() if metot and metot.strip() else None
        yol_suzgec = yol.strip().lower() if yol and yol.strip() else None

        secilenler: list[dict[str, Any]] = []
        for kayit in self._satirlar():
            if not self._gecer(kayit, yalniz_yazanlar=yalniz_yazanlar,
                               metot=metot_suzgec, yol=yol_suzgec,
                               alt=alt, ust=ust):
                continue
            secilenler.append(kayit)

        toplam = len(secilenler)
        secilenler.reverse()  # yeniden eskiye
        basla = max(0, offset)
        return secilenler[basla:basla + max(0, limit)], toplam

    def _satirlar(self) -> list[dict[str, Any]]:
        """Etkin dosyadaki kayıtlar, yazılış sırasıyla. Dosya yoksa boş liste.

        Kilit ALINMAZ: uzun bir tarama yazarları bekletirdi ve okuma yolu
        kritik değil. Yarım/bozuk satır atlanır.
        """
        try:
            ham = self.yol.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        except Exception:
            logger.warning("İşlem günlüğü okunamadı: %s", self.yol,
                           exc_info=True)
            return []
        out: list[dict[str, Any]] = []
        for satir in ham.splitlines():
            satir = satir.strip()
            if not satir:
                continue
            try:
                kayit = json.loads(satir)
            except ValueError:
                continue
            if isinstance(kayit, dict):
                out.append(kayit)
        return out

    @staticmethod
    def _gecer(kayit: dict[str, Any], *, yalniz_yazanlar: bool,
               metot: Optional[str], yol: Optional[str],
               alt: Optional[datetime], ust: Optional[datetime]) -> bool:
        """Kayıt süzgeçlerden geçiyor mu."""
        istek_mi = kayit.get("olay", OLAY_ISTEK) == OLAY_ISTEK
        # Döndürme kaydı `yalniz_yazanlar` süzgecinde de GÖRÜNÜR: "kayıt
        # kayboldu mu" sorusu tam da bu görünümde soruluyor.
        if yalniz_yazanlar and istek_mi and not kayit.get("yazan"):
            return False
        if metot is not None and (kayit.get("metot") or "").upper() != metot:
            return False
        if yol is not None and yol not in (kayit.get("yol") or "").lower():
            return False
        if alt is not None or ust is not None:
            zaman = _kayit_zamani(kayit)
            if zaman is None:
                return False
            if alt is not None and zaman < alt:
                return False
            if ust is not None and zaman > ust:
                return False
        return True


def _sayi_oku(ad: str, varsayilan: int) -> int:
    """Ortamdan tam sayı okur; bozuksa varsayılana düşer ve uyarır."""
    ham = os.environ.get(ad)
    if ham is None or not ham.strip():
        return varsayilan
    try:
        return int(ham.strip())
    except ValueError:
        logger.warning("%s sayı değil (%r); varsayılan kullanılıyor: %s",
                       ad, ham, varsayilan)
        return varsayilan


__all__ = [
    "AZAMI_LIMIT",
    "DURUM_ANAHTARI",
    "GunlukYazici",
    "OLAY_DONDURME",
    "OLAY_ISTEK",
    "VARSAYILAN_LIMIT",
    "VARSAYILAN_YOL",
    "YAZAN_METOTLAR",
    "eylem_bildir",
    "yazan_mi",
]
