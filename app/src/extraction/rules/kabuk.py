"""Kabuk bölgesi: metnin hangi kısmı KOMŞU kampanyalara ait.

İlgili: extract.py (`extract_all` sonundaki süzgeç — tek uygulama noktası)
        ../../../data/gold/ANNOTATION_GUIDE.md §4.13/8
        ../../preprocessing/blocks.py (blok düzeyi çerçeve ayrımı — farklı katman)

## Neden var

Kılavuz §4.13/8 anotatöre şunu söylüyor: değer yalnızca yan menü ya da
"İlginizi çekebilir" bloğunda geçiyorsa `absent` yaz + `#kabuk_kirliligi`.
Gerekçesi de yazılı: *"Blok değeri onaylanırsa komşu bankanın oranı bu bankaya
yazılır ve karşılaştırma motoru yanlış sıralama üretir."*

Kural KILAVUZDA vardı, KODDA yoktu. Gümüş turunun kör kalite testi bunu
ölçtü: A ve B'nin bağımsız olarak aynı kararı verdiği 60 hücrenin 9'unda
insanlar kabuk değerini ONAYLAMIŞTI (`taksit_sayisi`=4 "Diğer Kampanyalar"
bloğundan, `finansman_tutari`=5.000 komşu kampanyadan, `vade_ay`=24 ücret
tarifesi satır başlığından).

## NAİF TASARIM FELAKET — ölçüldü

"İşaretten metin sonuna kadar at" tasarımı denendi ve gold'da 16+5 gerçek
değer öldürdü. Sebep: bu işaretler belgede medyan **%8–19** konumunda
duruyor — yani üst menüde ya da başlıkta, altbilgide değil. Tek bir menü
bağlantısı bütün gövdeyi kabuk ilan ediyordu.

## Doğru tanım: KUYRUK KÜMESİ

Kabuk, işaretlerin YOĞUNLAŞTIĞI yerdir, ilk göründüğü yer değil:

  - İşaret >= 2 kez geçiyor ve ardışık ikisi arası < `bosluk` karakter ise,
    kabuk bölgesi o kümenin İLK işaretinde başlar. (Komşu kampanya listeleri
    arka arkaya sıralanır; menüdeki tek bağlantı küme oluşturmaz.)
  - İşaret yalnız BİR kez geçiyorsa, ancak metnin son %25'indeyse sayılır.

## İşaret kümesi ölçümle daraltıldı

`Kampanyayı Paylaş` ve `Tüm Kampanyalar` DIŞARIDA: ikisi de kampanya
gövdesinin ortasında geçiyor ve gerçek koşul cümlelerini kesiyordu.
"""
from __future__ import annotations

import re
from typing import Optional

# Komşu kampanya listelerinin başlıkları. Ölçümle daraltıldı — bkz. modül başlığı.
KABUK_ISARETLERI = re.compile(
    r"Diğer\s+Kampanyalar|İlginizi\s+Çekebil\w*|Benzer\s+Kampanyalar",
    re.IGNORECASE)

# Aynı kümeye ait sayılacak azami mesafe. Komşu kampanya kartları arka arkaya
# gelir; 600 karakter bir kart başlığı + kısa açıklama için bol paydır.
KUME_BOSLUK = 600

# Tek geçişte kabuk sayılması için gereken konum (metnin son çeyreği).
TEK_GECIS_ESIGI = 0.75


def kabuk_baslangici(text: str, *, bosluk: int = KUME_BOSLUK) -> Optional[int]:
    """Kabuk bölgesinin başlangıç ofseti; kabuk yoksa `None`.

    Bu ofsetten SONRA başlayan hiçbir alan bu belgenin kampanyasına ait
    sayılmaz.
    """
    if not text:
        return None
    yerler = [m.start() for m in KABUK_ISARETLERI.finditer(text)]
    if not yerler:
        return None

    if len(yerler) == 1:
        # Tek geçiş: yalnız kuyrukta anlamlı. Baştaki menü bağlantısı değil.
        return yerler[0] if yerler[0] >= len(text) * TEK_GECIS_ESIGI else None

    # İlk KÜMEYİ bul: ardışık işaretlerin `bosluk` içinde kaldığı en erken dizi.
    kume_bas = yerler[0]
    for onceki, sonraki in zip(yerler, yerler[1:], strict=False):
        if sonraki - onceki < bosluk:
            return kume_bas
        kume_bas = sonraki
    # Hiçbir ikili yeterince yakın değil -> yoğunlaşma yok, kabuk da yok.
    return None
