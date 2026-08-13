"""Tazelemeden SONRA veri tabanını dürüst hâle getiren uzlaştırma adımı.

İlgili: ./scraping/tazeleme.py (`alt_akis` geri çağrısı), ./summarize/ozet.py
        ./api/main.py (`/refresh*` uçları), ../scripts/build_demo_db.py
        ../scripts/ozet_geri_yukle.py, CLAUDE.md §11

## Hangi somut kusuru kapatıyor

Tazeleme yalnız `data/raw/` altına yazıyordu. Bir belgenin metni sitede
değiştiğinde ham arşiv güncelleniyor, veri tabanındaki AI özeti ise olduğu
gibi kalıyordu — yani panelde, artık var olmayan bir metni tarif eden bir özet
"AI özeti" etiketiyle durmaya devam ediyordu. Proje "sahte özet basmaz"
kuralına sahip (`summarize/ozet.py`); bayat özet de o kuralın ihlalidir,
sadece daha sessiz olanı.

## Neden SADECE özet düşürülüyor — metin ve alanlar neden tazelenmiyor

Doğru görünen ama YANLIŞ olan yol: değişen belgenin metnini veri tabanına
yazmak. Kampanya satırının metnini tazelemek, o metinden türetilmiş
`extracted_fields` satırlarını (oran, vade, masraf, kanıt aralıkları),
sınıflandırmayı ve gömme vektörlerini bir anda YALANCI yapardı: panel yeni
metni gösterirken kıyas tablosu eski metinden çıkarılmış değerleri ve o
metindeki karakter aralıklarına dayanan kanıt vurgularını sıralardı. Depo
sözleşmesinde kampanya metnini güncelleyen bir metot da yok
(`db/base.py::RepositoryProtocol`) — çünkü bu yol bilinçli olarak açılmamış:
ham arşivden veri tabanına geçiş ayrı, çevrimdışı ve tekrarlanabilir bir
adımdır (`scripts/build_demo_db.py`).

Bu yüzden buradaki iş, kapsamı KASITLI olarak dar tutulmuş tek bir hamledir:

    metni değişen belgenin özetini DÜŞÜR, gerekçesini YAZ, operatöre SÖYLE.

Sonuç dürüsttür: özet yoksa bayat özet de yoktur; `ozet_sebep` neden
olmadığını söyler; kalan tazeleme işi (metin + alanlar) çevrimdışı adıma
kalır ve iş raporunda açıkça anlatılır.

## Neden özet üretimi otomatik ZİNCİRLENMİYOR

"Özeti düşürdük, hemen yenisini üretelim" cazip ama yanlış: üretim veri
tabanındaki (hâlâ ESKİ) metinden okur. Zincirlenseydi, az önce düşürdüğümüz
bayat özetin aynısı saniyeler içinde geri gelir ve operatörün elindeki tek
uyarı sinyali sessizce silinirdi. Doğru sıra şudur ve `mesaj` alanı bunu
operatöre yazar:

    1. tazeleme (bu adım — ham arşiv + bayat özet düşürme)
    2. çevrimdışı yeniden kurulum (`build_demo_db` + `ozet_geri_yukle`)
    3. «LLM ile özet üret» (`/summaries/build`)

2. adımın kendisi de aynı kuralı zaten uyguluyor: `ozet_geri_yukle` özeti
`sha256(raw_text)` ile anahtarlıyor, yani metni değişmiş belgeye eski özet
GERİ YÜKLENMEZ; belge `denenmemis` kovasına düşer ve 3. adımda YENİ metinden
özetlenir. Buradaki karar o zincirin eksik ilk halkasıdır.

## Eşleştirme neden (source_url + önceki metin) ikilisi

`source_url` tek başına YETMEZ: aynı adres birden fazla kampanya kaydında
geçiyor (aynı sayfanın `live/` ve `archive/` kopyaları, bölüm tekrarları —
`ozet_geri_yukle` başlığında 97 mükerrer olarak ölçülmüş). Yalnız adrese
bakılsaydı, hiç değişmemiş bir arşiv kopyasının özeti de düşerdi; oysa kural
nettir: **değişmeyen belgeye dokunulmaz.**

İkinci anahtar belgenin ÖNCEKİ metnidir: veri tabanındaki satır o metinden
üretildiyse, düşürülecek özet tam olarak odur. İkisi birden tutmazsa hiçbir
şey yazılmaz ve kayıt "eşleşmeyen" olarak raporlanır — yanlış satıra dokunmak
yerine görünür biçimde dokunmamak.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Iterable, Optional

from .preprocessing.clean import normalize_text
from .scraping.collector import text_key
from .summarize.ozet import SEBEP_KAYNAK_DEGISTI

logger = logging.getLogger(__name__)

#: Rapordaki örnek liste sınırı — arayüzü boğmasın.
_AZAMI_LISTE = 40


def _metin_anahtari(metin: str) -> str:
    """Ham dosya metninin veri tabanındaki karşılığının anahtarı.

    `normalize_text` ŞART: korpus yolu belgeyi veri tabanına yazarken tam
    olarak bu dönüşümden geçiriyor (`pipeline.run_pipeline`). Ham dosya metnini
    doğrudan anahtarlasaydık, NBSP / zero-width / tırnak farkları yüzünden
    hiçbir kayıt eşleşmez ve bu adım sessizce hiçbir şey yapmayan bir süs olurdu.
    """
    return text_key(normalize_text(metin or ""))


def ozetleri_gecersizle(
        repo: Any,
        degisenler: Iterable[dict[str, Any]],
        *,
        unut: Optional[Callable[[list[int]], None]] = None) -> dict[str, Any]:
    """Metni değişen belgelerin bayat özetlerini düşürür. Rapor döndürür.

    `degisenler`: `tazeleme._belgeleri_kiyasla`'nın ürettiği kayıtlar —
    `source_url` + `onceki_metin`.

    `unut`: etkilenen kampanya kimlikleriyle çağrılır. API'nin görünüm
    önbelleği özeti OLAN kayıtları saklıyor; özet veri tabanından silindiğinde
    o önbellek temizlenmezse panel silinmiş özeti göstermeye devam eder — yani
    tam da düzeltmeye çalıştığımız kusur, bir katman yukarıda tekrarlanır.
    """
    kayitlar = [d for d in degisenler if (d.get("source_url") or "").strip()]
    if not kayitlar:
        return _rapor(0, [], 0, 0)

    aranan: dict[tuple[str, str], dict[str, Any]] = {
        ((d.get("source_url") or "").strip(),
         _metin_anahtari(d.get("onceki_metin") or "")): d
        for d in kayitlar
    }

    hedef: list[int] = []
    zaten_ozetsiz = 0
    eslesen_anahtar: set[tuple[str, str]] = set()
    for satir in repo.all_campaigns():
        anahtar = ((satir.get("source_url") or "").strip(),
                   text_key(satir.get("raw_text") or ""))
        if anahtar not in aranan:
            continue
        eslesen_anahtar.add(anahtar)
        if (satir.get("ozet") or "").strip():
            hedef.append(int(satir["id"]))
        else:
            zaten_ozetsiz += 1

    if hedef:
        # Sıra önemli: `set_ozet(None)` sebebi ELLEMEZ (bkz. depo docstring'i),
        # sebebi ayrıca yazmak bu yüzden zorunlu. Ters sırada yazmak da
        # çalışırdı ama araya düşen bir hata "özeti var, sebebi de var"
        # çelişkisini bırakırdı; bu sırada en kötü hâl sebepsiz boş özettir.
        repo.set_ozet({cid: None for cid in hedef})
        repo.set_ozet_sebep({cid: SEBEP_KAYNAK_DEGISTI for cid in hedef})
        if unut is not None:
            unut(sorted(hedef))

    eslesmeyen = [d for anahtar, d in aranan.items()
                  if anahtar not in eslesen_anahtar]
    return _rapor(len(kayitlar), eslesmeyen, len(hedef), zaten_ozetsiz)


def _rapor(degisen: int, eslesmeyen: list[dict[str, Any]],
           gecersizlenen: int, zaten_ozetsiz: int) -> dict[str, Any]:
    """İş durumuna eklenecek kayıt + operatöre okunacak cümle."""
    parcalar: list[str] = []
    if gecersizlenen:
        parcalar.append(
            f"Metni değişen {gecersizlenen} belgenin AI özeti düşürüldü; "
            "panel artık bu belgelerde bayat özet göstermiyor. Yeni metin veri "
            "tabanına ayrı bir çevrimdışı adımda aktarılır, özetler ondan "
            "sonra yeniden üretilmelidir.")
    elif degisen:
        parcalar.append(
            f"Metni değişen {degisen} belgenin veri tabanında düşürülecek bir "
            "özeti yoktu.")
    if eslesmeyen:
        parcalar.append(
            f"{len(eslesmeyen)} belge veri tabanında bulunamadı (henüz "
            "aktarılmamış olabilir); onlara dokunulmadı.")
    return {
        "degisen_belge": degisen,
        "gecersizlenen_ozet": gecersizlenen,
        "zaten_ozetsiz": zaten_ozetsiz,
        "eslesmeyen_belge": len(eslesmeyen),
        "eslesmeyen": [d.get("source_url") for d in eslesmeyen[:_AZAMI_LISTE]],
        "mesaj": " ".join(parcalar) or None,
    }


def alt_akis_kur(repo_ver: Callable[[], Any], *,
                 unut: Optional[Callable[[list[int]], None]] = None
                 ) -> Callable[[list[dict[str, Any]]], dict[str, Any]]:
    """`TazelemeYoneticisi(alt_akis=...)` için hazır geri çağrı üretir.

    `repo_ver` bir çağrılabilirdir, depo NESNESİ değil — `OzetYoneticisi` ile
    aynı gerekçe: API'nin deposu uygulama ömrü boyunca yaşar ve iş parçacıkları
    arasında paylaşılır; sınıfı depoya sabitlemek testlerde sahte depo
    geçirmeyi imkânsız kılardı.
    """
    def calistir(degisenler: list[dict[str, Any]]) -> dict[str, Any]:
        return ozetleri_gecersizle(repo_ver(), degisenler, unut=unut)

    return calistir


__all__ = ["alt_akis_kur", "ozetleri_gecersizle", "SEBEP_KAYNAK_DEGISTI"]
