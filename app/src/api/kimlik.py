"""API kimlik doğrulama kancası — kurumun kendi sistemine bağlanmak için.

İlgili: main.py (`build_app()` bağlaması), gunluk.py (`yazan_mi`),
        ../../docs/kimlik-dogrulama.md (tehdit modeli + entegrasyon)

## Bu dosya NE DEĞİL

Bir kimlik sistemi değil. Kullanıcı tablosu, oturum, parola, jeton üretimi,
anahtar döndürme (rotation), yenileme akışı YOK ve olmayacak. Bir bankanın
zaten çalışan bir dizin servisi (LDAP/AD), bir API geçidi (gateway) ve bir
imtiyaz yönetimi var; ürün onların yerine geçmeye kalkarsa hem gereksiz hem
de kurumun denetlediği yolun DIŞINDA bir kimlik yüzeyi açar.

Bu dosya o sisteme bağlanacak **kancayı** sunar: paylaşılan-sır bir API
anahtarı, iki rol ve muaf uçların açık listesi. Kurum ya anahtarı kendi
geçidinden enjekte eder ya da bu kancayı kendi doğrulamasıyla değiştirir
(nasıl olduğu docs/kimlik-dogrulama.md "Kurum kendi sistemine nasıl bağlar").

## Neden JWT/OAuth YOK

İki gerekçe, ikisi de bu projeye özgü:

1. **Dış servis yasak.** OAuth sağlayıcısı, kimlik sunucusu ya da uzaktan
   çekilen bir JWKS anahtar kümesi, sistemin `--network none` ile ölçülmüş
   çevrimdışı iddiasını (docs/OFFLINE-KANIT.md) doğrudan çökertir. Ağı
   olmayan bir konteynerde imza anahtarını indiremeyen bir doğrulayıcı ya
   çalışmaz ya da doğrulamayı atlar; ikincisi sessiz güvensizliktir.
2. **Yeni ağır bağımlılık gereksiz.** Yerel olarak doğrulanan bir jeton için
   `hmac.compare_digest` STDLIB'de duruyor ve tam olarak bu iş için var.
   `PyJWT`/`python-jose` eklemek bir bağımlılık daha, bir lisans denetimi
   daha ve imza algoritması yanlış yapılandırıldığında (`alg: none`,
   HS256/RS256 karışması) yeni bir hata sınıfı demekti — hepsi, kurumun
   geçidinin zaten yaptığı bir iş için.

Kurum JWT İSTİYORSA doğru yer bu süreç değil, önündeki geçittir: geçit jetonu
doğrular ve arka uca bu dosyanın anlayacağı anahtarı koyar.

## Varsayılan GERİYE UYUMLU, ama SESSİZ DEĞİL

Hiç anahtar tanımlı değilse doğrulama KAPALI'dır ve API bugünkü gibi çalışır.
Bu bilinçli: jüri demosu, `docker compose up` ile açılan çevrimdışı koşum ve
mevcut test paketi bir anahtar dağıtımı gerektirmeden çalışmalı.

Ama kapalı olması **açılışta log'a yazılır** (`logger.warning`). Güvenliğin
sessizce kapalı olması, hiç olmamasından kötüdür: kimse kapalı olduğunu
bilmiyorsa kimse açmaz.

## Muaf uçlar — gerekçeli, kısa ve KAPALI uçlu

`/health`: konteyner sağlık probu ve çevrimdışı kanıt koşumu bu ucu ağsız
(`--network none`) ortamda, anahtar dağıtımı olmadan çağırıyor
(docs/OFFLINE-KANIT.md adım 7-8). Kapatmak ölçülmüş bir kanıtı kırardı.
Uç yalnız üç alan döndürür (`status`, `llm`, `backend`) ve hiçbiri korpus
verisi değildir.

`OPTIONS`: tarayıcı ön-uçuşu (CORS preflight) özel başlık TAŞIMAZ; 401
verilirse tarayıcı gerçek isteği hiç göndermez ve panel "ağ hatası" görür.
Ara katman zaten `CORSMiddleware`'in İÇİNDE kurulu olduğu için ön-uçuş
normalde buraya hiç ulaşmaz; muafiyet, CORS katmanı bir gün kaldırılırsa
sessiz bir kırılma bırakmamak için var.

Liste bunun DIŞINDA hiçbir şey içermez. `/docs`, `/openapi.json` bilerek
muaf DEĞİL: uç envanteri bir saldırganın ilk istediği şeydir ve şema
kapalıyken sistem çalışmaya devam eder.

## Rol ayrımı — okuma ile EYLEM

İki rol var: `tam` (okuma + eylem) ve `salt-okuma`.

Ölçüt METODA bakar ve ölçütün kaynağı `gunluk.yazan_mi()`'dir — işlem
günlüğünün "yazan uç" tanımıyla AYNI yer. İkinci bir yol listesi tutmak iki
doğruluk kaynağı demekti ve ayrıştıklarında biri sessizce yanlış karar
verirdi (aynı gerekçe gunluk.py başlığında yazılı).

Tek istisna `SALT_OKUMA_SORGU_YOLLARI`: `POST /chat` ve `POST /extract` disk
ya da ağ üzerinde hiçbir eylem yapmaz, kullanıcı sorusunu cevaplar. Panelin
salt-okuma anahtarıyla çalışabilmesi için bu ikisi salt-okuma rolüne açıktır.
Liste **izin listesidir**, yasak listesi değil: yarın eklenen yeni bir yazan
uç listede olmadığı için kendiliğinden KAPALI başlar. Ters yönde bir istisna
listesi (yasaklananlar) ilk yeni uçta sessizce açık kalırdı.
"""

from __future__ import annotations

import hmac
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from . import gunluk

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Yapılandırma yüzeyi
# --------------------------------------------------------------------------- #
#: Tam yetkili anahtarlar — virgülle ayrık.
ORTAM_ANAHTARLAR = "API_KEYS"
#: Salt-okuma anahtarları — virgülle ayrık.
ORTAM_SALT_OKUMA = "API_KEYS_READONLY"
#: Anahtar dosyası (satır başına bir giriş). Docker/Kubernetes secret dostu.
ORTAM_DOSYA = "API_KEYS_FILE"

#: Birincil başlık. `Authorization: Bearer <anahtar>` da kabul edilir.
BASLIK = "X-API-Key"
BASLIK_YETKI = "Authorization"
_BEARER = "bearer "

ROL_TAM = "tam"
ROL_SALT_OKUMA = "salt-okuma"
#: Doğrulama kapalıyken atanan rol — bir anahtarın rolü DEĞİL.
ROL_KAPALI = "kapali"
#: Muaf uçlara atanan rol.
ROL_MUAF = "muaf"

#: Anahtar İSTENMEYEN yollar (gerekçe: modül başlığı "Muaf uçlar").
MUAF_YOLLAR = frozenset({"/health"})
#: Anahtar İSTENMEYEN metotlar.
MUAF_METOTLAR = frozenset({"OPTIONS"})
#: Salt-okuma rolünün çağırabildiği `POST` uçları — İZİN listesi.
SALT_OKUMA_SORGU_YOLLARI = frozenset({"/chat", "/extract"})

#: Bundan kısa anahtarlar açılışta uyarılır (reddedilmez — kararı kurum verir).
ASGARI_UZUNLUK = 16

MESAJ_ANAHTAR_YOK = ("Kimlik doğrulama gerekli: `X-API-Key` başlığı ya da "
                     "`Authorization: Bearer <anahtar>` gönderin.")
#: Yanlış anahtar ile TANIMSIZ anahtar aynı cevabı alır: hangi anahtarın
#: yanlış olduğunu söylemek, deneme-yanılma saldırısına yön verirdi.
MESAJ_GECERSIZ = "Kimlik doğrulanamadı."
MESAJ_YETKI_YOK = ("Bu uç eylem yetkisi gerektiriyor; sunulan anahtar "
                   "salt-okuma yetkisine sahip.")


def _giris_coz(ham: str, varsayilan_rol: str) -> Optional[tuple[str, str]]:
    """Tek yapılandırma girdisini `(anahtar, rol)` çiftine çevirir.

    Kabul edilen biçimler: `anahtar` (varsayılan rol) ve `rol:anahtar`.
    Önek YALNIZCA tam olarak bilinen bir rol adıysa ayrıştırılır; böylece
    içinde iki nokta geçen bir anahtar sessizce kırpılmaz.
    """
    ham = (ham or "").strip()
    if not ham or ham.startswith("#"):
        return None
    for rol in (ROL_TAM, ROL_SALT_OKUMA):
        onek = f"{rol}:"
        if ham.lower().startswith(onek):
            anahtar = ham[len(onek):].strip()
            return (anahtar, rol) if anahtar else None
    return (ham, varsayilan_rol)


def _listeden(ham: Optional[str], varsayilan_rol: str) -> list[tuple[str, str]]:
    """Virgülle ayrık ortam değişkenini çözer."""
    out = []
    for parca in (ham or "").split(","):
        giris = _giris_coz(parca, varsayilan_rol)
        if giris is not None:
            out.append(giris)
    return out


def _dosyadan(yol: str) -> list[tuple[str, str]]:
    """Anahtar dosyasını çözer — satır başına bir giriş, `#` yorum.

    Dosya OKUNAMAZSA istisna yükselir ve `build_app()` açılışta düşer.
    Bilinçli: `API_KEYS_FILE` verilmişse operatör doğrulamayı AÇMAK istemiştir;
    okunamayan bir dosyayı yutup doğrulamasız açılmak, tam olarak istenmeyen
    şeyin sessizce olması demekti. Gürültülü çökme, sessiz güvensizlikten iyi.
    """
    metin = Path(yol).read_text(encoding="utf-8")
    out = []
    for satir in metin.splitlines():
        giris = _giris_coz(satir, ROL_TAM)
        if giris is not None:
            out.append(giris)
    return out


class AnahtarDeposu:
    """Bellekte tutulan anahtar → rol eşlemesi.

    Anahtarlar HİÇBİR yerde log'lanmaz; `__repr__` bile yalnız sayıları
    gösterir. Bir istisna izi (traceback) ya da hata ayıklama çıktısı
    anahtarı diske düşürmemeli.
    """

    def __init__(self, girisler: Iterable[tuple[str, str]] = ()) -> None:
        kayit: dict[str, str] = {}
        for anahtar, rol in girisler:
            anahtar = (anahtar or "").strip()
            if not anahtar:
                continue
            # Aynı anahtar iki listede geçerse DAHA KISITLI rol kazanır:
            # yapılandırma hatasının maliyeti fazla yetki olmamalı.
            if kayit.get(anahtar) == ROL_SALT_OKUMA or rol == ROL_SALT_OKUMA:
                kayit[anahtar] = ROL_SALT_OKUMA
            else:
                kayit[anahtar] = rol
        self._kayit = kayit
        # Karşılaştırma bayt üzerinden yapılır: `hmac.compare_digest` dizgede
        # yalnız ASCII kabul eder ve ASCII dışı bir anahtar `TypeError` verirdi.
        self._ikili = tuple((a.encode("utf-8"), r) for a, r in kayit.items())

    @classmethod
    def ortamdan(cls, ortam: Optional[Mapping[str, str]] = None) -> AnahtarDeposu:
        """`API_KEYS`, `API_KEYS_READONLY` ve `API_KEYS_FILE`'dan kurar."""
        ortam = os.environ if ortam is None else ortam
        girisler: list[tuple[str, str]] = []
        girisler += _listeden(ortam.get(ORTAM_ANAHTARLAR), ROL_TAM)
        girisler += _listeden(ortam.get(ORTAM_SALT_OKUMA), ROL_SALT_OKUMA)
        dosya = (ortam.get(ORTAM_DOSYA) or "").strip()
        if dosya:
            girisler += _dosyadan(dosya)
        return cls(girisler)

    @property
    def acik(self) -> bool:
        """En az bir anahtar tanımlı mı — yani doğrulama devrede mi."""
        return bool(self._kayit)

    def sayim(self) -> dict[str, int]:
        """Rol başına anahtar sayısı (log ve `repr` için; anahtar İÇERMEZ)."""
        out = {ROL_TAM: 0, ROL_SALT_OKUMA: 0}
        for rol in self._kayit.values():
            out[rol] = out.get(rol, 0) + 1
        return out

    def kisa_anahtar_sayisi(self) -> int:
        """`ASGARI_UZUNLUK`tan kısa anahtar sayısı — açılış uyarısı için."""
        return sum(1 for a in self._kayit if len(a) < ASGARI_UZUNLUK)

    def rol(self, sunulan: Optional[str]) -> Optional[str]:
        """Sunulan anahtarın rolü; tanınmıyorsa `None`.

        Döngü ilk eşleşmede KIRILMAZ: erken çıkış, anahtarın listedeki sırasını
        yanıt süresinden okunabilir hâle getirirdi. Karşılaştırmanın kendisi
        `hmac.compare_digest` ile sabit zamanlıdır (uzunluk hariç).
        """
        if not sunulan:
            return None
        hedef = sunulan.encode("utf-8")
        bulunan: Optional[str] = None
        for anahtar, rol in self._ikili:
            if hmac.compare_digest(anahtar, hedef):
                bulunan = rol
        return bulunan

    def __repr__(self) -> str:  # pragma: no cover - hata ayıklama kolaylığı
        s = self.sayim()
        return (f"AnahtarDeposu(acik={self.acik}, tam={s[ROL_TAM]}, "
                f"salt_okuma={s[ROL_SALT_OKUMA]})")


@dataclass(frozen=True)
class Karar:
    """Tek isteğin kimlik kararı. `durum == 0` ise istek geçer."""

    durum: int
    rol: Optional[str]
    mesaj: Optional[str] = None

    @property
    def gecer(self) -> bool:
        return self.durum == 0


def anahtar_oku(basliklar: Any) -> Optional[str]:
    """İstek başlıklarından sunulan anahtarı çıkarır (yoksa `None`).

    Önce `X-API-Key`, sonra `Authorization: Bearer`. İkisi de kabul edilir
    çünkü kurum geçitleri ikisinden birini dayatabiliyor ve arada seçim
    yapmak zorunda bırakmak, kancayı tam da bağlanacağı yerde zorlaştırırdı.
    """
    try:
        ham = basliklar.get(BASLIK)
    except Exception:  # pragma: no cover - başlık nesnesi beklenmedik tipte
        return None
    if ham and ham.strip():
        return ham.strip()
    yetki = basliklar.get(BASLIK_YETKI) or ""
    if yetki[:len(_BEARER)].lower() == _BEARER:
        deger = yetki[len(_BEARER):].strip()
        if deger:
            return deger
    return None


def yol_muaf(metot: Optional[str], yol: str) -> bool:
    """Bu istek anahtar İSTEMEZ mi (gerekçe: modül başlığı)."""
    if (metot or "").upper() in MUAF_METOTLAR:
        return True
    return yol in MUAF_YOLLAR


def eylem_mi(metot: Optional[str], yol: str) -> bool:
    """İstek "eylem" mi — yani salt-okuma anahtarına kapalı mı.

    Ölçüt `gunluk.yazan_mi()`: işlem günlüğünün "yazan uç" tanımıyla aynı
    kaynak. `SALT_OKUMA_SORGU_YOLLARI` yalnız `POST` için delik açar.
    """
    if not gunluk.yazan_mi(metot):
        return False
    if (metot or "").upper() == "POST" and yol in SALT_OKUMA_SORGU_YOLLARI:
        return False
    return True


def karar_ver(depo: AnahtarDeposu, metot: Optional[str], yol: str,
              sunulan: Optional[str]) -> Karar:
    """Tek isteğin kimlik kararı — HTTP'den bağımsız, saf fonksiyon.

    Sıra önemlidir: muafiyet önce gelir (sağlık probu anahtar dağıtımı
    beklemeden çalışsın), doğrulamanın kapalı olması sonra (geriye uyum),
    rol kapısı en son.
    """
    if yol_muaf(metot, yol):
        return Karar(0, ROL_MUAF)
    if not depo.acik:
        return Karar(0, ROL_KAPALI)
    if not sunulan:
        return Karar(401, None, MESAJ_ANAHTAR_YOK)
    rol = depo.rol(sunulan)
    if rol is None:
        return Karar(401, None, MESAJ_GECERSIZ)
    if rol == ROL_SALT_OKUMA and eylem_mi(metot, yol):
        return Karar(403, rol, MESAJ_YETKI_YOK)
    return Karar(0, rol)


def kur(app) -> AnahtarDeposu:
    """Kimlik ara katmanını uygulamaya bağlar ve durumu log'a yazar.

    `CORSMiddleware`'den ÖNCE çağrılmalı. Starlette'te en son eklenen ara
    katman en DIŞTA durur; bu ara katman en içte olsun ki (a) CORS başlıkları
    401/403 yanıtlarına da eklensin — aksi halde tarayıcı gerçek durum kodunu
    göremez ve "ağ hatası" gösterir — ve (b) işlem günlüğü ara katmanı reddi
    de KAYDEDEBİLSİN: reddedilen bir isteğin denetim kaydında hiç görünmemesi,
    kaydın en çok işe yarayacağı anda susması olurdu.

    Depo `app.state.kimlik`'e asılır: testler ve kurum kancası onu
    değiştirebilsin diye (`app.state.gunluk` ile aynı desen).
    """
    from fastapi.responses import JSONResponse

    depo = AnahtarDeposu.ortamdan()
    app.state.kimlik = depo
    if depo.acik:
        s = depo.sayim()
        logger.info("Kimlik doğrulama AÇIK — %d anahtar (tam: %d, salt-okuma: %d)",
                    s[ROL_TAM] + s[ROL_SALT_OKUMA], s[ROL_TAM], s[ROL_SALT_OKUMA])
        kisa = depo.kisa_anahtar_sayisi()
        if kisa:
            logger.warning(
                "%d anahtar %d karakterden kısa — tahmin edilebilir anahtar "
                "doğrulamayı süs hâline getirir", kisa, ASGARI_UZUNLUK)
    else:
        logger.warning(
            "Kimlik doğrulama KAPALI — üretimde `%s` verin. Şu anda uçlar "
            "(`%s` hariç) anahtarsız çağrılabilir.",
            ORTAM_ANAHTARLAR, "`, `".join(sorted(MUAF_YOLLAR)))

    @app.middleware("http")
    async def kimlik_ara_katmani(request, call_next):
        """Her isteği anahtar kapısından geçirir; muaf uçlara dokunmaz."""
        # Depo `app.state`ten OKUNUR, kapanıştan değil: testler ve kurum
        # kancası anahtar kümesini uygulama kurulduktan sonra değiştirebilsin.
        aktif = getattr(app.state, "kimlik", depo)
        karar = karar_ver(aktif, request.method, request.url.path,
                          anahtar_oku(request.headers))
        if not karar.gecer:
            # SADECE metot + yol log'lanır: anahtar, sorgu dizgesi ve başlıklar
            # kalıcı bir kayda GİRMEZ (gunluk.py "NE KAYDEDİLMEZ" ile aynı kural).
            logger.warning("Kimlik reddi: %s %s -> %d", request.method,
                           request.url.path, karar.durum)
            return JSONResponse(
                status_code=karar.durum, content={"detail": karar.mesaj},
                headers={"WWW-Authenticate": "Bearer"} if karar.durum == 401 else None)
        request.state.kimlik_rol = karar.rol
        return await call_next(request)

    return depo
