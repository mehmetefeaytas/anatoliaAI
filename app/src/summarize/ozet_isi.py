"""«LLM ile özet üret» — arayüzden başlatılan arka plan işi.

İlgili: ./toplu.py (üretim gövdesi), ./ozet.py (tek belge + sebep etiketleri)
        ../api/main.py (`/summaries/*` uçları)
        ../scraping/tazeleme.py (aynı iş deseni, farklı gerekçe)
        CLAUDE.md §11 (demo doldurulmuş DB'den okur)

## Neden bir düğme gerekti

Özetler `scripts/build_summaries.py` ile TOPLU üretiliyor ve DB'ye yazılıyor.
Veri tazeleme (`/refresh`) ise ham arşive yeni ve değişmiş belgeler indiriyor.
İki yol arasında bağ yoktu: yeni toplanan bir belge DB'ye girdiğinde özetsiz
kalıyordu ve özetini üretmenin tek yolu sunucuya girip komut satırından bir
betik koşturmaktı. Operatörün elinde ekran varken terminal istemek, akışı
gereksiz yere insana bağlar.

## Neden ağ işinden AYRI bir yönetici

`TazelemeYoneticisi` ile aynı iskeleti paylaşır (tek yuva, arka plan iş
parçacığı, ilerleme, iptal) ama ayrı bir sınıftır ve ortak bir taban sınıfa
indirilmedi. İkisinin kısıtları farklı:

* Tazeleme **ağa çıkar**, robots.txt'e uyar, alan başına 2–5 sn gecikir ve
  veri tabanına HİÇ dokunmaz — yalnız ham arşive yazar.
* Özet üretimi **ağa hiç çıkmaz** (model yerel), gecikme bütçesi yoktur ve
  tam da veri tabanına yazar.

Ortak bir tabana indirilseydi, o tabanın hangi kısıtı taşıdığı belirsizleşirdi;
paylaşılan tek şey ~40 satırlık iş parçacığı iskeletidir.

**İkisi aynı anda koşabilir** ve bu bilinçli: birbirlerinin kaynağına
dokunmuyorlar. Kendi içinde her biri tek yuvalıdır.

## Yarıda kesilme: parçalı yazma sayesinde kayıp en fazla bir parça

Gövde 25 belgede bir DB'ye yazar (`toplu.YAZMA_PARCASI`). İptal, sunucunun
ölmesi ya da tarayıcının kapanması, o ana kadar yazılmış özetleri KORUR ve
sonraki koşu kaldığı yerden devam eder — çünkü hedef kümesi her koşuda DB'nin
o anki hâlinden hesaplanır, bir sıra dosyasından değil.

## LLM kapalıysa iş BAŞLAMAZ

Sahte özet yasağı (`ozet.py`) gereği LLM kapalıyken üretilecek hiçbir şey yok.
İşi başlatıp her belgeye `llm_kapali` sebebi yazmak, korpusu sistemin geçici
bir durumuyla kirletirdi. Başlatma reddedilir ve sebep operatöre yazılır.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from . import toplu
from .ozet import OzetSonucu, llm_hazir

logger = logging.getLogger(__name__)

# Durum kodları — arayüz bunlara göre ekran çizer (tazeleme ile aynı sözlük).
DURUM_BEKLIYOR = "bekliyor"
DURUM_URETILIYOR = "uretiliyor"
DURUM_TAMAM = "tamam"
DURUM_HATA = "hata"
DURUM_IPTAL = "iptal"

#: Rapora yazılacak azami hata satırı — liste ekranı boğmasın.
_AZAMI_LISTE = 40


def _simdi() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class OzetMesgul(RuntimeError):
    """Koşan bir özet işi varken ikinci iş başlatılmak istendi."""


class LlmKapali(RuntimeError):
    """LLM arka ucu kapalı; özet üretilemez ve sahte özet basılmaz."""


@dataclass
class OzetDurumu:
    """Bir özet işinin dışarıya açılan tüm durumu.

    Alanlar kilit altında güncellenir, okuma her zaman kopya üzerinden yapılır
    — arayüz yarım güncellenmiş bir kayıt görmez.
    """

    is_id: str
    durum: str = DURUM_BEKLIYOR
    asama: str = "Sıraya alındı."
    baslangic: str = field(default_factory=_simdi)
    bitis: Optional[str] = None
    hedef: int = 0
    islenen: int = 0
    uretilen: int = 0
    yazilan: int = 0
    uretilemeyen: dict[str, int] = field(default_factory=dict)
    korpus_belge: int = 0
    iptal_istendi: bool = False
    mesaj: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_id": self.is_id,
            "durum": self.durum,
            "asama": self.asama,
            "baslangic": self.baslangic,
            "bitis": self.bitis,
            "hedef": self.hedef,
            "islenen": self.islenen,
            "uretilen": self.uretilen,
            "yazilan": self.yazilan,
            "uretilemeyen": dict(list(self.uretilemeyen.items())[:_AZAMI_LISTE]),
            "korpus_belge": self.korpus_belge,
            "iptal_istendi": self.iptal_istendi,
            "mesaj": self.mesaj,
            "bitti": self.durum in (DURUM_TAMAM, DURUM_HATA, DURUM_IPTAL),
        }


class OzetYoneticisi:
    """Tek yuvalı özet üretim işi yöneticisi.

    `repo_ver` bir çağrılabilirdir, depo NESNESİ değil: API'nin deposu uygulama
    ömrü boyunca yaşar ve iş parçacıkları arasında paylaşılır
    (`ThreadSafeRepository`), ama bu sınıfı depoya sabitlemek testlerde sahte
    bir depo geçirmeyi imkânsız kılardı.
    """

    def __init__(self, repo_ver: Callable[[], Any], *,
                 llm_ver: Optional[Callable[[], Any]] = None,
                 kapsam: str = "hepsi") -> None:
        self._repo_ver = repo_ver
        self._llm_ver = llm_ver
        self._kapsam = kapsam
        self._kilit = threading.Lock()
        self._isler: dict[str, OzetDurumu] = {}
        self._son_id: Optional[str] = None
        self._calisan: Optional[str] = None

    # --- sorgulama ---------------------------------------------------- #

    def sayim(self) -> dict[str, Any]:
        """Kapsam sayaçları + LLM durumu. AĞA ÇIKMAZ, model çağırmaz."""
        kayit = toplu.sayim(self._repo_ver())
        llm = self._llm()
        acik = llm_hazir(llm)
        kayit["llm_acik"] = acik
        kayit["llm_notu"] = None if acik else (
            "Model kapalı olduğu için özet üretilemez. Kural tabanlı "
            "sahte bir özet BASILMAZ; açmak için sunucu ortamında "
            "LLM_BACKEND=ollama (yerel) ya da LLM_BACKEND=evren "
            "(+ EVREN_API_KEY) verilmeli."
        )
        with self._kilit:
            kayit["calisan_is"] = self._calisan
        return kayit

    def durum(self, is_id: str) -> Optional[dict[str, Any]]:
        with self._kilit:
            kayit = self._isler.get(is_id)
            return kayit.to_dict() if kayit else None

    def son_is(self) -> Optional[dict[str, Any]]:
        with self._kilit:
            kayit = self._isler.get(self._son_id or "")
            return kayit.to_dict() if kayit else None

    # --- iş yaşam döngüsü --------------------------------------------- #

    def baslat(self) -> dict[str, Any]:
        """Arka planda özet üretimini başlatır ve iş kaydını döndürür."""
        llm = self._llm()
        if not llm_hazir(llm):
            raise LlmKapali(
                "Yerel model kapalı; özet üretilemez ve sahte özet basılmaz.")
        with self._kilit:
            if self._calisan is not None:
                raise OzetMesgul(self._calisan)
            is_id = uuid.uuid4().hex[:12]
            kayit = OzetDurumu(is_id=is_id)
            self._isler[is_id] = kayit
            self._son_id = is_id
            self._calisan = is_id
        threading.Thread(target=self._kos, args=(is_id, llm), daemon=True,
                         name=f"ozet-{is_id}").start()
        return kayit.to_dict()

    def iptal_et(self, is_id: str) -> Optional[dict[str, Any]]:
        """Durdurma ister. İş sıradaki belge sınırında durur."""
        with self._kilit:
            kayit = self._isler.get(is_id)
            if kayit is None:
                return None
            if not kayit.to_dict()["bitti"]:
                kayit.iptal_istendi = True
                kayit.asama = "Durdurma istendi; sıradaki belgede duracak."
            return kayit.to_dict()

    # --- iç ------------------------------------------------------------ #

    def _llm(self) -> Any:
        if self._llm_ver is not None:
            return self._llm_ver()
        from ..extraction.llm.extractor import default_extractor
        return default_extractor()

    def _kos(self, is_id: str, llm: Any) -> None:
        def guncelle(**alanlar: Any) -> None:
            with self._kilit:
                kayit = self._isler[is_id]
                for ad, deger in alanlar.items():
                    setattr(kayit, ad, deger)

        def iptal_mi() -> bool:
            with self._kilit:
                return self._isler[is_id].iptal_istendi

        def adim(islenen: int, hedef: int, sonuc: OzetSonucu) -> None:
            with self._kilit:
                kayit = self._isler[is_id]
                kayit.islenen = islenen
                kayit.hedef = hedef
                if sonuc.uretildi and sonuc.ozet:
                    kayit.uretilen += 1
                else:
                    anahtar = sonuc.sebep or "bilinmiyor"
                    kayit.uretilemeyen[anahtar] = (
                        kayit.uretilemeyen.get(anahtar, 0) + 1)
                kayit.asama = f"{islenen}/{hedef} belge işlendi."

        def ilerleme(islenen: int, hedef: int, yazilan: int) -> None:
            guncelle(yazilan=yazilan)

        guncelle(durum=DURUM_URETILIYOR, asama="Hedef belgeler belirleniyor…")
        # Yuva, işin SON durumu yazıldıktan SONRA boşalır. Erken boşaltmak
        # (üretim çağrısının kendi `finally`si) hâlâ "üretiliyor" görünen bir
        # işin üstüne ikinci işin başlamasına izin verirdi.
        try:
            try:
                rapor = toplu.calistir(
                    repo=self._repo_ver(), kapsam=self._kapsam, devam=True,
                    # Kalıcı sebepliler hedefte YOK: onları her basışta yeniden
                    # denemek aynı sonucu verir ve dakikalar harcardı.
                    kalici_atla=True, llm=llm,
                    ilerleme=ilerleme, adim=adim, iptal=iptal_mi)
            except Exception as exc:  # düşerse iş HATA'ya geçer, sessiz kalmaz
                logger.exception("özet üretim işi düştü: %s", is_id)
                guncelle(durum=DURUM_HATA, bitis=_simdi(),
                         asama="Üretim durdu.",
                         mesaj=f"Özet üretimi tamamlanamadı "
                               f"({type(exc).__name__}). Ayrıntı sunucu "
                               "günlüğüne yazıldı. O ana kadar yazılmış "
                               "özetler korunur.")
                return
            kesildi = bool(rapor.get("iptal"))
            guncelle(
                durum=DURUM_IPTAL if kesildi else DURUM_TAMAM,
                bitis=_simdi(),
                hedef=int(rapor["hedef_belge"]),
                uretilen=int(rapor["ozetlenen"]),
                yazilan=int(rapor["yazilan"]),
                korpus_belge=int(rapor["korpus_belge"]),
                asama=("Durduruldu; o ana kadar üretilen özetler yazıldı."
                       if kesildi else "Tamamlandı."),
            )
        finally:
            with self._kilit:
                self._calisan = None
            # Önbellek geçersizleme geri çağrısı YOK, çünkü gerekmiyor:
            # `main._campaign_view()` özeti OLMAYAN kaydı zaten önbellekten
            # servis etmiyor (kendi yorumundaki gerekçe). Buraya bir geri
            # çağrı koymak, aynı garantiyi ikinci kez — ve ayrışabilir
            # biçimde — kurmak olurdu.
