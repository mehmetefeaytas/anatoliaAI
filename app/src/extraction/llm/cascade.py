"""Kademeli istemci zinciri — uzak uç düşerse yerel yol devralır.

İlgili: CLAUDE.md §5.9 (on-prem uygulanabilirlik), §11 (canlı LLM'e bağlı
        demo yasak), §7 (vLLM birincil, Ollama yedek)
        clients.py (`LLMTransportError` / `LLMHTTPError` ayrımı)
        docs/evren-servisi.md (SSB EVREN kurulumu ve kapsam sınırları)

## Bu modül neden var

SSB EVREN, yarışmanın tüm takımlarına açık UZAK bir çıkarım servisidir ve
122B'lik `llm-large` bizim yerel 9B'lik yolumuzdan belirgin biçimde güçlüdür.
Ama teslim yolunu ona BAĞLAMAK kabul edilemez, iki ayrı gerekçeyle:

1. **Şartname §5.9 (on-prem, ağırlık %20).** Sistemin çalışması dış bir
   servise bağlı olamaz. Kanıt paketimiz (`docs/OFFLINE-KANIT.md`) ağsız
   koşuyor ve bu kalem en güçlü kalemimiz.
2. **Ölçülmüş donma riski.** Servis paylaşımlı; jüri önünde yavaşlarsa
   arayüz bekler. `_urllib_transport` docstring'indeki 18 dakikalık asılı
   çağrı tam bu sınıftan bir olaydı.

Çözüm bağımlılık değil KADEME: EVREN varsa kullanılır, düşerse yerel vLLM
ya da Ollama devralır, o da yoksa `NullLLMExtractor` ile kural-only koşulur
(fabrikanın işi, bkz. `extractor.default_extractor`). Böylece uzak uç
sistemi İYİLEŞTİREN bir katman olur, AYAKTA TUTAN bir katman olmaz — ve
"dış servis düştüğünde de çalışır" ölçülebilir bir iddiaya dönüşür.

## Devre kesici (circuit breaker) neden zorunlu

Düşen istemci her belgede yeniden denenirse 48 belgelik bir koşum 48 kez
duvar-saati sınırını bekler — yani yedeğe geçmek koşumu kurtarmaz, sadece
yavaşlatır. Bu yüzden bir kez düşen istemci `cooldown` saniye boyunca
ATLANIR; denenmez bile. Zincirde denenecek kimse kalmazsa körü körüne
beklemek yerine gene denenir (aksi hâlde tek istemcili bir zincir ilk
hatadan sonra sessizce ölürdü).

## Hangi hata kademeye tabi

Yalnız `LLMError` soyu: "servise ulaşamadım" (`LLMTransportError`) ve
"sunucu reddetti" (`LLMHTTPError`). Bir `ValueError`/`KeyError` bizim kodumuz
ya da şemamızla ilgilidir; onu yedeğe geçerek gizlemek hatayı kaybetmek
olur — o yüzden olduğu gibi yükselir.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Optional, Sequence

from .clients import LLMError, LLMResponse

logger = logging.getLogger(__name__)

#: Düşen istemcinin atlanacağı süre (sn). 4 dakikalık sunumu kapsayacak
#: kadar uzun, uzun bir toplu koşumda yeniden denemeyi engellemeyecek kadar
#: kısa. `LLM_CASCADE_COOLDOWN` ile ayarlanır; 0 devre kesiciyi kapatır.
COOLDOWN_VARSAYILAN = 300.0


def _cooldown_env() -> float:
    ham = os.environ.get("LLM_CASCADE_COOLDOWN", "").strip()
    if not ham:
        return COOLDOWN_VARSAYILAN
    try:
        return max(0.0, float(ham))
    except ValueError:
        logger.warning("LLM_CASCADE_COOLDOWN okunamadi (%r) -> %.0f sn",
                       ham, COOLDOWN_VARSAYILAN)
        return COOLDOWN_VARSAYILAN


class _DevreDurumu:
    """Hangi KADEME ne zamana kadar atlanacak — kopyalar arasında paylaşılır.

    ## Neden `id(istemci)` değil, kademe İNDEKSİ

    İlk hâli istemci nesnesinin kimliğiyle anahtarlıyordu ve ölçüldüğünde
    çalışmadığı görüldü: `LLMExtractor._butceli_istemci` çalışma sırasında
    her kademenin bütçeli bir KOPYASINI çıkarıyor (`butceyle`), kopya yeni
    bir nesne olduğu için yeni bir `id()` alıyor ve devre kesici o kademeyi
    hiç düşmemiş sayıyordu — yani kesici sessizce devre dışı kalıyordu.

    Kademe sırası ise kopyada birebir korunur. İndeks bu yüzden doğru
    anahtar: bütçeli kopya da, sıcaklık kopyası da aynı kademeyi işaret eder.
    """

    def __init__(self) -> None:
        self.acilis: dict[int, float] = {}      # kademe indeksi -> düşme anı

    def dusuk(self, kademe: int, simdi: float, cooldown: float) -> bool:
        if cooldown <= 0:
            return False
        t = self.acilis.get(kademe)
        return t is not None and (simdi - t) < cooldown

    def dustu(self, kademe: int, simdi: float) -> None:
        self.acilis[kademe] = simdi

    def kalkti(self, kademe: int) -> None:
        self.acilis.pop(kademe, None)


class CascadingClient:
    """Sıralı istemci zinciri; tek bir istemci gibi davranır.

    `LLMExtractor` istemciden `generate` / `generate_json` bekler,
    `structured_mode` / `model` / `butceyle` / `sicaklikla` varsa kullanır
    (bkz. `extractor._butceli_istemci`). Zincir bunların hepsini taşır.
    """

    def __init__(self, clients: Sequence[Any], *,
                 cooldown: Optional[float] = None,
                 clock: Callable[[], float] = time.monotonic,
                 _durum: Optional[_DevreDurumu] = None):
        if not clients:
            raise ValueError("CascadingClient bos zincirle kurulamaz")
        self.clients = list(clients)
        self.cooldown = _cooldown_env() if cooldown is None else float(cooldown)
        self.clock = clock
        self._durum = _durum if _durum is not None else _DevreDurumu()
        # Son BAŞARILI istemci — `structured_mode`/`model` bunu raporlar ki
        # eval raporu "hangi uçta koştuk" sorusunu doğru cevaplasın.
        self._aktif: Any = self.clients[0]
        # Son çağrıda hangi kademe neden düştü — artefakta/loga taşınır.
        self.son_hatalar: list[str] = []

    # ------------------------------------------------------------------ #
    # Zincir yürütücüsü
    # ------------------------------------------------------------------ #
    def _sirali(self) -> list[tuple[int, Any]]:
        """Denenecek kademeler `(indeks, istemci)` olarak; devresi kapalılar hariç.

        Hepsi cooldown'daysa liste BOŞ kalmaz — tam sıra döndürülür. Aksi
        hâlde tek istemcili bir zincir ilk hatadan sonra cooldown boyunca
        hiç çağrı yapmaz ve sistem sessizce ölür.
        """
        simdi = self.clock()
        tum = list(enumerate(self.clients))
        acik = [(i, c) for i, c in tum
                if not self._durum.dusuk(i, simdi, self.cooldown)]
        return acik or tum

    def _kademe(self, ad: str, *args, **kwargs) -> Any:
        """`ad` metodunu zincir boyunca dener; ilk başarılıyı döndürür."""
        self.son_hatalar = []
        son: Optional[LLMError] = None
        adaylar = self._sirali()
        atlanan = len(self.clients) - len(adaylar)
        if atlanan:
            logger.debug("kademe: %d istemci devre kesicide atlandi", atlanan)

        for kademe, istemci in adaylar:
            try:
                sonuc = getattr(istemci, ad)(*args, **kwargs)
            except LLMError as exc:
                self._durum.dustu(kademe, self.clock())
                etiket = self._etiket(istemci)
                self.son_hatalar.append(
                    f"{etiket}: {type(exc).__name__}: {exc}")
                son = exc
                logger.warning(
                    "LLM kademesi: %s dustu (%s) -> siradaki istemci",
                    etiket, type(exc).__name__)
                continue
            self._durum.kalkti(kademe)
            self._aktif = istemci
            return sonuc

        # Zincirin tamamı düştü. Hata TÜRÜ korunarak yükselir: üst katman
        # "ulaşamadım" ile "reddedildi"yi ayırt ediyor (bkz. clients.py hata
        # sınıfları) ve tür sarmalanırsa o ayrım kaybolur. Kademe kademe
        # gerekçe `son_hatalar`da ve log'da durur.
        logger.error("LLM zincirinin tamami dustu (%d kademe): %s",
                     len(self.son_hatalar), " | ".join(self.son_hatalar))
        assert son is not None      # adaylar boş olamaz (bkz. `_sirali`)
        raise son

    @staticmethod
    def _etiket(istemci: Any) -> str:
        return (f"{type(istemci).__name__}"
                f"({getattr(istemci, 'model', '?')})")

    # ------------------------------------------------------------------ #
    # İstemci arayüzü
    # ------------------------------------------------------------------ #
    def generate(self, system: str, user: str, schema: dict) -> LLMResponse:
        return self._kademe("generate", system, user, schema)

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        return self._kademe("generate_json", system, user, schema)

    def negotiate(self, schema: dict, force: bool = False) -> str:
        return self._kademe("negotiate", schema, force)

    @property
    def structured_mode(self) -> Optional[str]:
        return getattr(self._aktif, "structured_mode", None)

    @property
    def model(self) -> Optional[str]:
        return getattr(self._aktif, "model", None)

    def butceyle(self, token: int) -> "CascadingClient":
        return self._kopya("butceyle", token)

    def sicaklikla(self, sicaklik: float) -> "CascadingClient":
        return self._kopya("sicaklikla", sicaklik)

    def _kopya(self, ad: str, deger: Any) -> "CascadingClient":
        """Her kademenin kopyasını içeren yeni zincir; devre durumu PAYLAŞILIR.

        Bir kademe istenen metodu taşımıyorsa (sahte istemciler, ileride
        eklenecek bir istemci) o kademe olduğu gibi geçer — `_butceli_istemci`
        ile aynı hoşgörü.
        """
        yeni = [getattr(c, ad)(deger) if hasattr(c, ad) else c
                for c in self.clients]
        return CascadingClient(yeni, cooldown=self.cooldown, clock=self.clock,
                               _durum=self._durum)
