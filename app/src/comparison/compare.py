"""Karşılaştırma motoru — sıralama + adil-kıyas garantisi.

İlgili: ../../decisions/daraltilmis-yenilikcilik-hedefleri.md (çelişki tespiti)
        ../../concepts/urun-karsilastirma.md
        CLAUDE.md §17 (adil kıyas: yalnız aynı-birim normalize alanlar)
        ../../sorun/manuel-karsilastirma-zorlugu.md

Aralık (min/max) alanları kıyaslanabilir ama "doğrudan kıyaslanamaz" işaretiyle;
sıralamada aralığın alt sınırı (en iyi senaryo) kullanılır ve flag verilir.

İki sıralama vardır:

- `rank(rows, field)`        → TEK alan üzerinden (şartname §5.7'nin ilk dört
                               ölçütü: en düşük kâr payı, en yüksek ödül, en uzun
                               vade, en düşük masraf)
- `rank_advantageous(rows)`  → ÇOK alanlı bileşik (§5.7'nin beşinci ölçütü:
                               "En Avantajlı Kampanya")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from dataclasses import field as dc_field
from typing import Any, Iterable, Mapping, Optional

from ..db.base import suresi_dolmus_mu
from ..normalization.normalize import collapse_degenerate_range


@dataclass
class RankRow:
    bank: str
    bank_name: Optional[str]
    value: Any              # ham canonical değer
    sort_key: Optional[float]  # sıralama için sayısal anahtar
    comparable: bool        # doğrudan kıyaslanabilir mi
    note: Optional[str]     # kıyaslanamazsa neden
    source_span: Optional[str]
    #: Satırın geldiği kampanya ve ürün ailesi. Tekilleştirme ve tür kapısı
    #: bu iki alan olmadan kurulamaz; eskiden `rank()` ikisini de düşürüyordu
    #: ve `/compare` ucu bilgiyi geri getirmek için satır kimliğini `bank`
    #: alanına gömmek zorunda kalmıştı. Varsayılanları `None`: bu alanları
    #: taşımayan sözlüklerle çağıran mevcut yollar aynen çalışır.
    campaign_id: Optional[Any] = None
    campaign_type: Optional[str] = None
    #: Tekilleştirmede bu satırın TEMSİL ETTİĞİ, gösterilmeyen kampanya sayısı.
    #: Satırın HANGİ ALANDAN geldiği. Tek alanlı sıralamada gereksizdir
    #: (çağıran alanı zaten bilir) ama bileşik "en avantajlı" cevabı
    #: satırları BOYUT BOYUT topluyor: vade, masraf, ödül… O cevapta alan
    #: taşınmazsa arayüz her satırı SORGUNUN alanıyla biçimlemek zorunda
    #: kalır. Ölçüldü (24 Ağu 2026): sorgu alanı `kar_payi_orani` iken
    #: 120 aylık vade satırı ekrana **%120** diye basıldı. Sözlük değerler
    #: (masraf, ödül) alan adına bakmayan dallara düştüğü için doğru
    #: görünüyordu — hata yalnız çıplak sayısal alanlarda ortaya çıkıyor,
    #: yani sessiz ve seçici.
    field: Optional[str] = None

    #: `tekil_banka_urun()` doldurur; tekilleştirme yapılmamışsa 0'dır.
    other_count: int = 0
    #: Kampanyanın geçerlilik durumu (`'expired'` | `'active'` | `None`).
    #: `note` alanından AYRI taşınır: not tek bir dizedir ve satır aynı anda
    #: hem aralık hem süresi dolmuş olabilir; ikisini tek metne sıkıştırmak
    #: birini gizlerdi. Arayüz rozeti bu alandan okunur.
    campaign_status: Optional[str] = None
    #: Çıkarımın bu alandaki KENDİ güveni (`extracted_fields.confidence`).
    #: Güven kapısı bu sayıyı okuyup notu üretiyor ama sayının kendisini
    #: düşürüyordu; oysa "hepsi düşük güvenli" diyen bir cevabın *en yüksek*
    #: güveni söyleyebilmesi gerekir ("0,55 — eşik 0,65"). Notun içinden
    #: sayıyı geri ayrıştırmak, aynı bilgiyi iki biçimde taşımak olurdu.
    confidence: Optional[float] = None
    #: Oranın BAZI (`'aylik'` | `'yillik'` | `None`). Yalnız oran alanlarında
    #: anlamlıdır ve `None` "ölçülmedi" demektir — "aylık" değil. Notun içine
    #: gömmek yerine ayrı taşınır: satır aynı anda hem yıllık bazlı hem süresi
    #: dolmuş olabilir ve `note` tek bir dizedir (aynı gerekçe:
    #: `campaign_status`). Arayüz rozeti bu alandan okunur.
    oran_bazi: Optional[str] = None


# --------------------------------------------------------------------------- #
# Eleme sebepleri — metin ve KOD
# --------------------------------------------------------------------------- #
#
# `note` kullanıcıya gösterilecek Türkçe cümledir; iki tanesi ölçülen sayıyı
# (güven, para birimi) gövdesinde taşıdığı için sabit bir dize DEĞİLDİR.
# Bu yüzden sebebi programatik ayırt etmek isteyen çağıranlar (chatbot'un boş
# cevabı, "kaç kayıt hangi kapıda düştü" sayımı) metne bakmak zorunda kalıyordu.
# Metinler burada TEK yerde tanımlıdır ve `eleme_sebebi()` onları kararlı bir
# koda çevirir: cümle güzelleştiğinde kod değişmez, kod değiştiğinde eşleme
# tek dosyada güncellenir.

NOT_DEGER_YOK = "değer yok"
NOT_ARALIK = "aralık — doğrudan kıyaslanamaz"
NOT_TUTAR_BELIRSIZ = "ücret var, tutarı belirtilmemiş"
NOT_SAYISAL_DEGIL = "sayısal değil"
NOT_SURESI_DOLMUS = "kampanya süresi dolmuş — doğrudan kıyaslanamaz"

#: Banka kapsamda ama bu alanda HİÇ kaydı yok (bkz. "kapsam kapısı" bloğu).
#: "değer yok"tan AYRIDIR: orada bir çıkarım satırı vardır ve kanonik değeri
#: boştur; burada satırın kendisi yoktur. İkisini tek nota toplamak, ölçülen
#: bir boşluk ile hiç ölçülmemiş bir alanı aynı şey saymak olurdu.
NOT_ALAN_YOK = "bu alan belirtilmemiş — doğrudan kıyaslanamaz"

#: Ölçülen sayıyı/etiketi gövdesinde taşıyan notların sabit öneki.
_NOT_GUVEN_ONEKI = "düşük çıkarım güveni"
_NOT_PARA_ONEKI = "farklı para birimi"
_NOT_BAZ_ONEKI = "farklı oran bazı"

#: Eleme sebebi kodları. `bilinmiyor` bilerek vardır: tanınmayan bir not
#: sessizce başka bir sebebe yazılmamalı, "sınıflandıramadım" demeli.
ELEME_SURESI_DOLMUS = "suresi_dolmus"
ELEME_DUSUK_GUVEN = "dusuk_guven"
ELEME_ARALIK = "aralik"
ELEME_TUTAR_BELIRSIZ = "tutar_belirsiz"
ELEME_DEGER_YOK = "deger_yok"
ELEME_PARA_BIRIMI = "para_birimi"
ELEME_SAYISAL_DEGIL = "sayisal_degil"
ELEME_ALAN_YOK = "alan_yok"
ELEME_ORAN_BAZI = "oran_bazi"
ELEME_BILINMIYOR = "bilinmiyor"

_TAM_NOT_KODU = {
    NOT_SURESI_DOLMUS: ELEME_SURESI_DOLMUS,
    NOT_ARALIK: ELEME_ARALIK,
    NOT_TUTAR_BELIRSIZ: ELEME_TUTAR_BELIRSIZ,
    NOT_DEGER_YOK: ELEME_DEGER_YOK,
    NOT_SAYISAL_DEGIL: ELEME_SAYISAL_DEGIL,
    NOT_ALAN_YOK: ELEME_ALAN_YOK,
}


def eleme_sebebi(note: Optional[str]) -> Optional[str]:
    """Kullanıcıya dönük eleme notunu kararlı bir koda çevirir.

    `None` → `None` (satır elenmemiş). Tanınmayan bir not `ELEME_BILINMIYOR`
    döner: yanlış bir kutuya koymaktansa bilmediğini söylemek yeğdir.
    """
    if note is None:
        return None
    kod = _TAM_NOT_KODU.get(note)
    if kod is not None:
        return kod
    if note.startswith(_NOT_GUVEN_ONEKI):
        return ELEME_DUSUK_GUVEN
    if note.startswith(_NOT_PARA_ONEKI):
        return ELEME_PARA_BIRIMI
    if note.startswith(_NOT_BAZ_ONEKI):
        return ELEME_ORAN_BAZI
    return ELEME_BILINMIYOR


# Alan → (sayısal_anahtar_çıkarıcı, küçük_mü_iyi)
def _numeric_key(field_name: str, value: Any) -> tuple[Optional[float], bool, Optional[str]]:
    """value'dan sıralama anahtarı üretir.

    Dönüş: (sort_key, comparable, note). Aralık ise alt sınır + comparable=False.
    Para ise value alanı. Sayı ise kendisi.
    """
    if value is None:
        return None, False, NOT_DEGER_YOK
    # Dejenere aralığı ({"min": X, "max": X}) düz sayıya indirge. Aynı savunma
    # normalizasyon katmanında da var; burada TEKRARLANIYOR çünkü LLM katmanı
    # kanonik değeri doğrudan üretebiliyor ve normalize_rate'ten geçmeyebilir.
    # Atlanırsa tamamen kıyaslanabilir bir değer "aralık" sanılıp sıralamadan
    # sessizce düşer -> §5.7 "En Düşük Kâr Payı" yanlış banka verir.
    value = collapse_degenerate_range(value)
    # aralık: {"min":, "max":}
    #
    # Aralık DOĞRUDAN KIYASLANAMAZ (comparable=False) ve bu değişmiyor. Ama
    # döndürülen `sort_key` aralığın hangi ucunu temsil ediyor önemlidir:
    # arayüz o sayıyı gösteriyor ve `BankDeltaPanel` fark hesabında kullanıyor.
    #
    # Eskiden `field_name` parametresi gövdede HİÇ KULLANILMIYOR ve her zaman
    # `min` alınıyordu. Yani `vade_ay` alanında `{min: 12, max: 120}` taşıyan
    # bir kampanya 12 ay gibi görünüyordu — ürünün ilan ettiği en uzun vade
    # 120 iken. Yön, alanın kendisine bağlıdır: düşük-iyi alanlarda ürünün
    # vaat ettiği uç alt sınır, yüksek-iyi alanlarda üst sınırdır.
    #
    # İkiz fonksiyon `_composite_numeric` bunu ZATEN doğru yapıyordu
    # (`best_end = lo if field_name in _LOWER_IS_BETTER else hi`). İlke doğru
    # yazılmış, tek alanlı yola uygulanmamıştı — `masraf_durumu`'nda yaşanan
    # (yukarıda uzun uzun anlatılan) hatanın aynısı.
    if isinstance(value, dict) and "min" in value and "max" in value:
        lo, hi = float(value["min"]), float(value["max"])
        uc = lo if field_name in _LOWER_IS_BETTER else hi
        return uc, False, NOT_ARALIK
    # para: {"value":, "currency":}
    if isinstance(value, dict) and "value" in value:
        cur = value.get("currency")
        if cur and cur != "TRY":
            return None, False, f"{_NOT_PARA_ONEKI} ({cur})"
        return float(value["value"]), True, None
    # masraf: {"has_fee":, "amount":}
    #
    # `has_fee=True, amount=None` SIFIR SAYILMAZ. Eskiden sayılıyordu ve
    # `masraf_durumu` "düşük daha iyi" alanı olduğu için 0,0 sıralamanın
    # TEPESİYDİ: kanıt metninde "1.000 TL başvuru ücreti tahsil edilecektir"
    # yazan bir kampanya, "En Düşük Masraf" ekranında gerçekten ücretsiz
    # olanların ÖNÜNDE, tek bir uyarı işareti olmadan görünüyordu.
    # Ölçüldü (2026-08-08): `sort_key == 0.0` olan 509 satırın **35'i**
    # ücretliydi; korpusta bu kalıptan 39 kayıt var.
    #
    # İkiz fonksiyon `_composite_numeric` bunu ZATEN doğru yapıyordu ve
    # gerekçesini de yazmıştı: *"sıfır saymak 'masrafsız' demek olurdu
    # (yalan), popülasyonun en kötüsünü atamak ise değer uydurmak olurdu."*
    # İlke doğru yazılmış, tek alanlı yola uygulanmamıştı — ve `rank()`
    # dashboard ile chatbot'un kullandığı yoldur.
    #
    # Arayüzdeki `FairnessNotice` şeridi tam bu ayrımı vaat ediyor:
    # "Bilgi gerçekten yoksa hücre — gösterir ve satır kıyaslanamaz
    # işaretlenir; ikisi karıştırılmamalıdır." Sistem uyardığı karışıklığı
    # kendisi yapıyordu.
    if isinstance(value, dict) and "has_fee" in value:
        if value.get("has_fee") is False:
            return 0.0, True, None
        amt = value.get("amount")
        if amt is None:
            return None, False, NOT_TUTAR_BELIRSIZ
        return float(amt), True, None
    if isinstance(value, (int, float)):
        return float(value), True, None
    return None, False, NOT_SAYISAL_DEGIL


# Hangi alanda küçük değer "daha iyi"? (sıralama yönü)
_LOWER_IS_BETTER = {
    "kar_payi_orani", "tahsis_ucreti", "masraf_durumu",
}
_HIGHER_IS_BETTER = {
    "vade_ay", "finansman_tutari", "odul_miktari", "indirim_orani", "alisveris_puani",
    # Katılma hesabının DAĞITILAN getirisi — `kar_payi_orani`nin TERSİ yönde.
    # Ayrı bir alan adı ŞART: aynı alana yazılsaydı %42'lik bir getiri, %2'lik
    # bir finansman oranının yanında "kötü" görünürdü. İki büyüklük ters
    # yönlüdür ve tek kolonda yarışamaz
    # (bkz. decisions/katilma-orani-iki-ayri-buyukluk.md).
    "katilma_getirisi",
}

#: Kampanya türü boş (NULL) olan belgelerin grup adı. Belge GİZLENMEZ, kendi
#: grubunda kalır: türü bilinmeyen bir kampanyayı sınıflandırılmış bir ailenin
#: içine koymak, olmayan bir bilgiyi iddia etmek olurdu.
BILINMEYEN_TUR = "Sınıflandırılamadı"


# --------------------------------------------------------------------------- #
# Güven kapısı — çıkarımın KENDİ belirsizliği sıralamaya girer
# --------------------------------------------------------------------------- #
#
# Çıkarıcı her alana bir `confidence` yazıyor (`extracted_fields.confidence`)
# ve sıralama bu sayıya BAKMIYORDU. Yani sistem kendi belirsizliğini ölçüyor,
# sonra sıralama adımında çöpe atıyordu. Ekranda görünen sonuç şuydu:
#
#     Yeni müşteri taşıt finansmanı → "Dünya Katılım: 0 TRY"
#     kanıt penceresi: "…Belirleyeceğim Aylık Taksit Tutarı 0 TL Ödenecek
#                       Toplam Tutar 0 TL Aylık Kâr Oranı %0 Ödeme Planı…"
#
# Bu, DOLDURULMAMIŞ bir hesaplama aracının varsayılan değeridir; ürünün
# finansman tutarı değildir. Çıkarıcı bunu zaten 0,37–0,40 güvenle
# işaretlemişti — bilgi vardı, kullanılmıyordu.
#
# ## Eşik neden 0,65
#
# ÖLÇÜLDÜ (`data/gold/gold.v2.json`'un 48 belgesi `data/demo.db` ile birebir
# eşleşiyor; sayısal alanlar altın değerle karşılaştırıldı):
#
#     güven          doğru   yanlış   aşırı-üretim   doğruluk
#     0,45–0,55        0       2           5            %0
#     0,72–0,85       11       2           6           %58
#
# Eşiğin ALTINDA kalan 7 çıkarımın 7'si de hatalı. Kanıt pencereleri hatanın
# tek bir sınıftan geldiğini söylüyor — hepsi belgenin KAMPANYA OLMAYAN
# bölümlerinden:
#
#     "…çerezdir. 1 yıl 5.Kişisel Veri Sahibi…"      → vade_ay = 12
#     "Hesap açılışı için minimum tutar 50.000 TL"   → finansman_tutari
#     "ATM Bakiye/Limit/Borç Sorgulama 0.27 TL"      → finansman_tutari
#     "Talimat alt limiti 10 TL'dir"                 → finansman_tutari
#
# Korpus dağılımı da aynı yerden ayrılıyor: güven değerleri {0,15 … 0,55} ve
# {0,65 … 0,95} diye iki kümede toplanıyor ve 0,55 ile 0,65 arasında hiçbir
# kayıt yok. Eşik bu boşluğa oturuyor — ölçümden okundu, seçilmedi.
#
# ## Neden "kıyas dışı", neden "sil" değil
#
# Üç seçenek vardı: (a) satırı düşür, (b) sırala ama işaretle, (c) kıyas dışı
# bırak + gerekçeyi göster. **(c)** seçildi.
#
#   * (a) bilgiyi SAKLAR. Zayıf bir değeri silmek, kullanıcıya "bu bankada
#     böyle bir veri yok" demektir; oysa veri var, güvenilmez. Bu ayrım bu
#     projenin `FairnessNotice` şeridinde açıkça vaat ediliyor.
#   * (b) sıralamanın tepesini düzeltmez: 0 TL hâlâ "en düşük"tür ve rozet
#     okunmadan tablo yanlış okunur.
#   * (c) mevcut "doğrudan kıyaslanamaz" desenini kullanır — aralık ve farklı
#     para birimi için zaten yerleşik olan yol. Değer GÖRÜNÜR kalır, gerekçesi
#     yanındadır, sıralamaya girmez.
#
# ## Neden meşru sıfırlar zarar görmez
#
# Korpustaki 614 sıfır değerin büyük kısmı GERÇEKTİR ve eşik onlara dokunmaz
# (ölçüldü): `masraf_durumu` 543 sıfır ("masrafsız"), `tahsis_ucreti` 7,
# `kar_payi_orani` 8 (gerçek %0 kampanyaları) — üçünün de güveni 0,95.
# Eşiğin düşürdüğü 48 sıfırın 47'si `finansman_tutari`, yani tam da
# hesaplama aracı kalıbı. Çözüm "sıfırı ele" DEĞİLDİR ve öyle davranmaz.
ASGARI_GUVEN = 0.65


def _guven_notu(confidence: Optional[float]) -> Optional[str]:
    """Güveni eşiğin altında kalan satırın kullanıcıya dönük gerekçesi.

    Eşiğin kendisi de metne yazılır: kullanıcı satırın neden elendiğini
    görebilmeli, "kıyaslanamaz" damgası kapalı bir kutu olmamalı.
    """
    if confidence is None or confidence >= ASGARI_GUVEN:
        return None
    olculen = f"{confidence:.2f}".replace(".", ",")
    esik = f"{ASGARI_GUVEN:.2f}".replace(".", ",")
    return (f"{_NOT_GUVEN_ONEKI} ({olculen} < {esik}) — "
            f"doğrudan kıyaslanamaz")


# --------------------------------------------------------------------------- #
# Süre kapısı — kapanmış kampanya açık olanla aynı kolonda sıralanmaz
# --------------------------------------------------------------------------- #
#
# `docs/rapor/suresi-dolmus-damgasi.md` 458 belgeyi `campaign_status: expired`
# ile işaretledi (237 `archive/`, 221 `live/`) ve o raporun §5'i boşluğu açıkça
# yazdı: *"Kıyas motoru bu alanı henüz OKUMUYOR."* Bu kapı o boşluğu kapatır.
#
# Neden gerekli: süresi dolmuş bir kampanyanın oranı hâlâ metinde yazılıdır ve
# çıkarıcı onu yüksek güvenle bulur. Kapanmış bir kampanya çoğu zaman
# sıralamanın TEPESİNDE oturur — bugün başvurulabilecek en iyi tekliften daha
# iyi görünür, çünkü artık kimseye verilmiyor. Kullanıcı "en düşük kâr payı"
# ekranında var olmayan bir ürünü görür. CLAUDE.md §17'nin (adil kıyas
# garantisi) ihlali budur.
#
# ## Neden "kıyas dışı", neden "sil" değil
#
# Güven kapısındaki (yukarıda) aynı üç seçenek ve aynı gerekçe. Satırı düşürmek
# bilgiyi SAKLARDI: kullanıcıya "bu bankada böyle bir kampanya yok" demek
# olurdu, oysa kampanya var — süresi dolmuş. Bu ayrım arayüzdeki `FairnessNotice`
# şeridinde açıkça vaat ediliyor. Değer görünür kalır, gerekçesi yanındadır,
# sıralamaya girmez.
#
# ## Neden damgasız belgeler etkilenmez
#
# `suresi_dolmus_mu()` yalnız `'expired'`e `True` döner; `None` (damgasız)
# geçer. Korpusun 1316 belgesi damgasızdır ve bunları "muhtemelen dolmuştur"
# saymak, ölçülmemiş bir bilgi iddia etmek olurdu (CLAUDE.md §19).


def _durum_notu(campaign_status: Optional[str]) -> Optional[str]:
    """Süresi dolmuş satırın kullanıcıya dönük gerekçesi.

    Metin "doğrudan kıyaslanamaz" ile bitiyor çünkü arayüz o deseni zaten
    tanıyor: aralık, farklı para birimi ve düşük güven aynı sonu kullanıyor.
    Dördüncü bir gerekçeye dördüncü bir dil uydurmak, aynı kararı iki farklı
    biçimde anlatmak olurdu.
    """
    if not suresi_dolmus_mu(campaign_status):
        return None
    return NOT_SURESI_DOLMUS


# --------------------------------------------------------------------------- #
# Koşul kapısı — koşula bağlı oran, koşulsuz oranla aynı kolonda sıralanmaz
# --------------------------------------------------------------------------- #
#
# CLAUDE.md §6 "zaman-koşullu oran (ilk 6 ay %0)"u mimarinin merkezindeki zor
# vakalar arasında sayıyor; §17 ise koşullar farklıysa "doğrudan kıyaslanamaz"
# işaretlenmesini şart koşuyor. Bu kapı o şartı uygular.
#
# ## Ölçülen kusur (2026-08-11, `data/demo.db`)
#
# "En düşük kâr payı oranı" sıralamasının ilk DÖRT satırı **%0**'dı ve dördü de
# `comparable=True` idi. Değerler uydurma değil, metinde gerçekten yazıyor —
# ama hiçbiri koşulsuz bir ürün oranı değil:
#
#     "Mobilden yeni müşterilere özel %0 kâr payı ile 50.000 TL'ye varan…"
#     "Albaraka Mobil'den müşteri olanlar, %0 kâr payı ile…"
#
# Bu satırlar, herkese açık %1,69'luk bir konut finansmanının ÜSTÜNDE
# duruyordu. Kullanıcı "en düşük oran" ekranında, yalnız belirli bir kanaldan
# gelen yeni müşterinin alabileceği bir promosyonu, genel bir teklif sanıyordu.
#
# Taban oranlar da aynı kovada: "%1,89'**dan başlayan**" bir ALT SINIRDIR, o
# bankanın vereceği oran değil. Sabit bir oranla yan yana sıralamak, alt sınırı
# gerçek teklif gibi göstermektir.
#
# ## Neden yön ve cümle sınırı — YANLIŞ POZİTİF ÖLÇÜLDÜ
#
# İlk denemede koşul sözcüğü kanıt penceresinde ARANDI ve 11 satır işaretlendi.
# Dördü yanlıştı, çünkü koşul sözcüğü orana değil BAŞKA bir şeye bağlıydı:
#
#     "…tüm vadelerde sabit %4.09 kâr payı oranı, 3 ay erteleme fırsatı ve
#      YENİ MÜŞTERİLERE ÖZEL dosya masrafsızlık avantajı…"   -> masrafsızlık
#     "…%1,99 - %2,49 arasında, 48 aya kadar vade. İLK 3 AY ödemesiz."  -> ödeme
#
# İlkinde oran açıkça "sabit" diye niteleniyor. Bu satırları kıyas dışı bırakmak
# gerçek bir teklifi ekrandan silmek olurdu. Kapı bu yüzden koşulun orana
# BAĞLI olmasını arar: dar bir pencere, yön ayrımı (koşul ifadeleri oranın
# ÖNÜNDE, taban ifadeleri ARKASINDA durur) ve cümle sınırı — nokta, koşulu
# orandan koparır.
#
# Ölçüm: 54 satırın 7'si işaretlendi, dördü de yanlış pozitif elendi.
#
# ## Neden yalnız kâr payı oranı
#
# `vade_ay`da "120 aya kadar" bir TAVANDIR ve tavanları kıyaslamak anlamlıdır
# ("120'ye kadar" > "36'ya kadar"). Korpusta vade satırlarının %40'ı böyle bir
# ifade taşıyor; hepsini kıyas dışı bırakmak vade karşılaştırmasını yok ederdi.
# Oranda ise durum tersidir: alt sınır, gerçek maliyet hakkında yanıltır.

#: Oranın ÖNÜNDE duran koşul ifadeleri — kimin, hangi kanaldan alabileceği.
_KOSUL_ONCE_RE = re.compile(
    r"yeni\s+müşteri\w*|müşteri\s+olanlar\w*|ilk\s+kez\s+müşteri"
    r"|mobilden|mobil\s*(?:uygulama|şube)\w*|dijital(?:den)?\s+başvur\w*"
    r"|internet\s+şubesi|uygulama\s+üzerinden"
    r"|ilk\s+\d+\s*(?:ay|gün|hafta)\b|ilk\s+(?:üç|iki|bir|altı|alti)\s*ay\b",
    re.IGNORECASE)

#: Oranın ARKASINDA duran taban ifadeleri — "…'dan başlayan".
_KOSUL_SONRA_RE = re.compile(
    r"['’]?d[ae]n\s+başlayan|başlayan\s+oran|['’]?d[ae]n\s+itibaren|başlar",
    re.IGNORECASE)

#: ÜÇÜNCÜ TARAFA bağlı oran: "LCW'**de** %0 kar payıyla kullanılmak üzere".
#:
#: Özel ad + bulunma hâli, hemen oranın önünde. Ölçüldü (`data/demo.db`): desen
#: korpusta 115 yerde geçiyor ama oran alanının kanıtında YALNIZ BİR kez —
#: gerisi indirim kampanyaları ("Civil'de %25 İndirim") ve onlar bu kapının
#: kapsamında değil (`_KOSUL_ALANLARI`).
#:
#: Bankanın KENDİ adı dışlanır: "Albaraka'da %2,49 kâr payı" bir üçüncü taraf
#: koşulu değil, bankanın kendi teklifidir. Dışlama olmadan bu desen ileride
#: meşru bir oranı sessizce kıyas dışı bırakabilirdi — ve sessizce bir teklifi
#: silmek, bir promosyonu fazla iyimser göstermekten kötüdür.
_KOSUL_ORTAK_RE = re.compile(r"([A-ZÇĞİÖŞÜ][\wçğıöşü]{1,})['’]d[ae]\b")

#: Pencere genişlikleri. Ölçümle seçildi: 45/22 ile 7 doğru pozitifin hepsi
#: yakalanıyor ve 4 yanlış pozitifin hiçbiri girmiyor.
_KOSUL_ONCE_PENCERE = 45
_KOSUL_SONRA_PENCERE = 22

#: Kapının yalnız uygulandığı alan. Gerekçe yukarıda ("neden yalnız kâr payı").
_KOSUL_ALANLARI = frozenset({"kar_payi_orani"})

#: Diğer notlarla AYNI biçim: "not:" öneki YOK (arayüz onu kendisi ekliyor)
#: ve cümle "doğrudan kıyaslanamaz" ile bitiyor — dördüncü bir gerekçeye
#: dördüncü bir dil uydurmak, aynı kararı farklı biçimde anlatmak olurdu.
NOT_KOSULLU = "koşullu oran (kanal/müşteri/taban) — doğrudan kıyaslanamaz"


def _ortak_kosulu(onc: str, bank_name: Optional[str]) -> bool:
    """Oran üçüncü bir tarafa mı bağlı ("LCW'de %0")? Banka kendi adı sayılmaz."""
    m = _KOSUL_ORTAK_RE.search(onc)
    if m is None:
        return False
    ad = m.group(1).casefold()
    kendi = (bank_name or "").casefold()
    # "Kuveyt Türk'te" -> `ad` = "Türk"; bankanın adının HERHANGİ bir sözcüğüne
    # eşitse üçüncü taraf değildir.
    return ad not in {p.casefold() for p in kendi.split()}


def _kosul_notu(field_name: str, raw_value: Optional[str],
                source_span: Optional[str],
                bank_name: Optional[str] = None) -> Optional[str]:
    """Oran bir koşula BAĞLIYSA kullanıcıya dönük gerekçe; değilse `None`.

    Koşulun orana bağlı olduğunu, kanıt penceresinde oranın konumuna göre
    arayarak doğrular; gerekçe ve ölçüm yukarıdaki blokta.
    """
    if field_name not in _KOSUL_ALANLARI:
        return None
    ham = (raw_value or "").strip()
    pencere = source_span or ""
    if not ham or not pencere:
        return None
    i = pencere.find(ham)
    if i < 0:
        return None
    j = i + len(ham)
    onc = pencere[max(0, i - _KOSUL_ONCE_PENCERE):i]
    son = pencere[j:j + _KOSUL_SONRA_PENCERE]
    # Cümle sınırı koşulu orandan KOPARIR (ölçülen yanlış pozitif #853).
    if "." in onc:
        onc = onc[onc.rfind(".") + 1:]
    if "." in son:
        son = son[:son.find(".")]
    if (_KOSUL_ONCE_RE.search(onc) or _KOSUL_SONRA_RE.search(son)
            or _ortak_kosulu(onc, bank_name)):
        return NOT_KOSULLU
    return None


# --------------------------------------------------------------------------- #
# Baz kapısı — aylık oran, yıllık oranla aynı kolonda sıralanmaz
# --------------------------------------------------------------------------- #
#
# CLAUDE.md §6 "aylık vs. yıllık baz"ı mimarinin merkezindeki zor vakalar
# arasında sayıyor; §17 ise yalnızca **aynı birime normalize** alanların
# kıyaslanmasını şart koşuyor. Bu kapı o şartı orana uygular.
#
# ## Ölçülen boşluk (2026-08-16, `data/demo.db`)
#
# `delta_between()` ve `rank()` iki oranı yalnız SAYI olarak görüyordu: aylık
# %1,89 ile yıllık %24,0 aynı eksende sıralanıyor ve aylık olan "daha iyi"
# çıkıyordu. Oysa aylık %1,89 kabaca yıllık %25 demektir — yani sıralamanın
# söylediğinin tersi de olabilir. Sayıların birimi yoktu ve kıyas o yüzden
# adil değildi.
#
# Korpus şu an bu tuzağı ÖRTMÜŞ durumda: 70 `kar_payi_orani` satırının
# kanıtında 38 kez "aylık", 3 kez "yıllık" geçiyor ve yıllık geçenlerin
# hiçbirinde saklanan değer yıllık oranın kendisi değil ("Aylık Kar payı oranı
# : %1,20 Efektif Yıllık Kar Payı Oranı : %23,52" satırından 1,20 saklanmış).
# Yani bugün yanlış bir sıralama ÜRETİLMİYOR — ama bunu sağlayan şey çıkarım
# katmanının tesadüfi tercihi, kıyas katmanının bir güvencesi değil. Kapı,
# bazın veriye girdiği gün sessizce yanlış sıralanmaması içindir.
#
# ## Baz UYDURULMAZ, ÇEVRİLMEZ
#
# İki şey bilerek YAPILMIYOR:
#
#  1. **Varsayım yok.** `oran_bazi` yoksa `None`'dır ve kapı ateşlenmez. Alanın
#     baskın kullanımı aylık olsa bile, ölçülmemiş bir bazı "aylık" saymak
#     CLAUDE.md §21'in yasakladığı değer uydurmadır. Bilinmeyen baz, kıyası
#     bugünkü davranışta bırakır.
#  2. **Çevirme yok.** Yıllık %24'ü 12'ye bölüp aylık %2 demek aritmetik olarak
#     mümkün ama olgusal olarak yanlıştır: ilan edilen yıllık oran çoğu zaman
#     *efektif* (bileşik) orandır ve "yıllık maliyet oranı" ücretleri de içerir.
#     Türetilmiş bir sayı üretmek, uydurma sıralamanın hesap makinesiyle
#     yapılmış hâli olurdu. §17'nin dediği yapılır: "doğrudan kıyaslanamaz".
#
# ## Neden kanonik baza göre, çoğunluğa göre DEĞİL
#
# "Popülasyondaki baskın baz kazansın" kuralı, aynı satırı kimin yanında
# durduğuna göre kıyaslanabilir ya da kıyaslanamaz yapardı: iki bankalı bir
# süzgeçte geçen bir oran, süzgeç genişleyince elenirdi. Kapı bunun yerine alan
# başına SABİT bir kıyas bazı okur; karar veriden değil, alanın tanımından
# gelir ve her sorguda aynıdır.

ORAN_BAZI_AYLIK = "aylik"
ORAN_BAZI_YILLIK = "yillik"

#: Kabul edilen baz değerleri. Başka bir dize `None` sayılır — tanınmayan bir
#: etiketi geçerli saymak, ölçülmemiş bir bilgiyi ölçülmüş göstermek olurdu.
ORAN_BAZLARI = frozenset({ORAN_BAZI_AYLIK, ORAN_BAZI_YILLIK})

#: Kullanıcıya dönük Türkçe karşılıklar. Saklanan değer ASCII'dir (`base.py`
#: `KAMPANYA_DURUMU_*` ile aynı gerekçe: sınıf etiketi çevrilmez, gösterilirken
#: Türkçeleşir).
_BAZ_ETIKET = {ORAN_BAZI_AYLIK: "aylık", ORAN_BAZI_YILLIK: "yıllık"}

#: Alan → kıyasın yürütüldüğü baz. Katılım bankacılığında ilan edilen kâr payı
#: oranı murabaha **aylık** kâr oranıdır; `extraction/rules/confidence.py:112`
#: aynı varsayımı makul band olarak zaten yazıyor ("aylık % — yıllıklar da bu
#: bandın üstü"). Bu sözlükte olmayan alanda kapı hiç çalışmaz.
KANONIK_ORAN_BAZI: dict[str, str] = {"kar_payi_orani": ORAN_BAZI_AYLIK}


def oran_bazi_dogrula(deger: Any) -> Optional[str]:
    """Ham baz etiketini `'aylik'` | `'yillik'` | `None`'a indirger.

    Tanınmayan değer (`''`, `'monthly'`, `3`) **`None`** döner: sessizce
    kıyaslanabilir saymak, olmayan bir ölçümü iddia etmek olurdu.
    """
    return deger if deger in ORAN_BAZLARI else None


def _baz_notu(field_name: str, oran_bazi: Any) -> Optional[str]:
    """Oranın bazı kıyas bazından FARKLIYSA gerekçe; değilse `None`.

    Bilinmeyen baz (`None`) kapıyı ateşlemez — gerekçe yukarıdaki blokta.
    """
    kanonik = KANONIK_ORAN_BAZI.get(field_name)
    baz = oran_bazi_dogrula(oran_bazi)
    if kanonik is None or baz is None or baz == kanonik:
        return None
    return (f"{_NOT_BAZ_ONEKI} ({_BAZ_ETIKET[baz]}; kıyas bazı "
            f"{_BAZ_ETIKET[kanonik]}) — doğrudan kıyaslanamaz")


# --------------------------------------------------------------------------- #
# Kapsam kapısı — kapsamdaki her banka görünür, alanı olmasa bile
# --------------------------------------------------------------------------- #
#
# Şartnamenin çalışılmış örneği (s.11–12) üç bankalı bir konut finansmanı
# tablosudur ve **B ile C bankalarının bazı hücreleri boştur**: "Belirtilmemiş",
# "Masraf belirtilmemiş". Satırlar eksik alana rağmen tabloda DURUYOR. Yani
# beklenen çıktı biçimi, alanı olmayan bankayı tablodan düşürmeyi doğrudan
# yasaklıyor.
#
# ## Ölçülen kusur (2026-08-16, `data/demo.db`)
#
# `/compare?field=kar_payi_orani&type=Konut+Finansmanı` sekiz bankanın
# ALTISINI döndürüyordu. Düşen ikisi:
#
#     Ziraat Katılım  46 konut kampanyası — `kar_payi_orani` satırı: 0
#     Adil Katılım     1 konut kampanyası — `kar_payi_orani` satırı: 0
#
# Kök neden `rank()` DEĞİLDİ: `rank()` satırı olan hiçbir bankayı düşürmez,
# yalnız `comparable=False` işaretler. Kayıp bir adım önce, veri getirmede
# oluyordu — `repo.query_fields(field)` `extracted_fields` tablosundan okur ve
# o alanda satırı olmayan banka sorguya HİÇ girmez. Kıyas motoruna hiç
# ulaşmayan bir bankayı kıyas motoru işaretleyemez.
#
# Sonuç kullanıcı için sessiz ve yanlıştı: "Kuveyt Türk ve Ziraat Katılım konut
# finansmanını karşılaştır" sorusunda Ziraat Katılım hiç yokmuş gibi görünüyor.
# Oysa doğru cevap "Ziraat Katılım'ın 46 konut kampanyası var, kâr payı oranı
# hiçbirinde belirtilmemiş" — bu, bilgi YOKLUĞUNUN kendisi bir bilgidir ve
# arayüzdeki `FairnessNotice` şeridi tam bunu vaat ediyor ("veri yok ≠ ürün
# yok"). Kapsama cetveli (`grafik/KapsamaCetveli.tsx`) bu kararı zaten vermiş
# ve verisi olmayan bankayı kesik çizgiyle çiziyordu; tablo ondan ayrışmıştı.
#
# ## Neden yeni bir mekanizma değil
#
# Süre, koşul ve güven kapılarının deseni aynen genişletildi: satır GÖRÜNÜR
# kalır, gerekçesi yanındadır, sıralamaya girmez. Değer `None`'dır ve arayüz
# onu şartnamenin jetonuyla ("Belirtilmemiş") basar; sıfır ya da tahmin
# yazılmaz.


def _kapsam_eksikleri(built: list[RankRow],
                      kapsam: Optional[Iterable[Mapping[str, Any]]]
                      ) -> list[RankRow]:
    """Kapsamda olup çıkarım satırı OLMAYAN (banka, tür) çiftleri için satır.

    `kapsam` öğeleri ``{"bank", "bank_name", "campaign_type"}`` okur; fazlası
    yok sayılır. Anahtar `(bank, campaign_type)`'dır — `tekil_banka_urun()` ve
    `turlere_ayir()` ile AYNI anahtar, çünkü eksiklik de ürün ailesi
    düzeyindedir: bir bankanın konut finansmanında oranı olmaması, taşıt
    finansmanında da olmadığı anlamına gelmez.

    Sıra ada göre sabittir: bu satırların bir sıralama anahtarı yoktur ve
    çağrıdan çağrıya yer değiştirmeleri, sıralama değişmiş gibi okunurdu.
    """
    if not kapsam:
        return []
    var = {(x.bank, x.campaign_type) for x in built}
    eksik: dict[tuple[Any, Any], Mapping[str, Any]] = {}
    for k in kapsam:
        anahtar = (k.get("bank"), k.get("campaign_type"))
        if anahtar in var or anahtar in eksik:
            continue
        eksik[anahtar] = k
    sirali = sorted(eksik.items(),
                    key=lambda kv: (str(kv[1].get("bank_name") or kv[0][0] or ""),
                                    str(kv[0][0] or ""), str(kv[0][1] or "")))
    return [RankRow(bank=k.get("bank"), bank_name=k.get("bank_name"),
                    value=None, sort_key=None, comparable=False,
                    note=NOT_ALAN_YOK, source_span=None,
                    campaign_id=None, campaign_type=k.get("campaign_type"))
            for _, k in sirali]


#: `rank()` kapılarının girdi sözlüğünden OKUDUĞU alanlar.
#:
#: Kapılar eksik alanda sessizce kapanır ve bu bilinçlidir ("bilinmiyor" ile
#: "düşük" aynı şey değildir). Ama aynı tasarım, alanı taşımayı unutan
#: çağıranı da sessizce ödüllendirir: kapı hiç ateşlenmez, testler yeşil kalır,
#: ekran yanlış sıralar. `src/api/main.py` bu tuzağa ÜÇ KEZ düştü (güven, süre,
#: koşul alanları). `tests/test_rank_girdi_paritesi.py` bu listeyi çağrı
#: yerlerine karşı denetler.
RANK_KAPI_ALANLARI: frozenset[str] = frozenset({
    "canonical_value",    # birim / aralık kapısı
    "confidence",         # güven kapısı
    "campaign_status",    # süre kapısı
    "raw_value",          # koşul kapısı — orana göre konum
    "bank_name",          # koşul kapısı — bankanın kendi adını dışlar
    "oran_bazi",          # baz kapısı — aylık/yıllık
})


def rank(rows: list[dict], field_name: str,
         kapsam: Optional[Iterable[Mapping[str, Any]]] = None) -> list[RankRow]:
    """query_fields() çıktısını alıp adil sıralama döndürür.

    rows: [{"bank","bank_name","canonical_value","source_span","confidence",...}]
    Yalnız comparable=True satırlar sıralanır; kıyaslanamazlar sona, not'la eklenir.

    `confidence` taşınmışsa `ASGARI_GUVEN` kapısı uygulanır: eşiğin altındaki
    satır sayıya indirgenebilse bile `comparable=False` olur ve notunda neden
    yazar. Alanı taşımayan çağıranlar (eski sözlükler, testler) aynen çalışır —
    güven bilinmiyorsa kapı ateşlenmez, çünkü "bilinmiyor" ile "düşük" aynı şey
    değildir ve olmayan bir belirsizlik iddia edilmez.

    `campaign_status` taşınmışsa **süre kapısı** de aynı biçimde uygulanır:
    `'expired'` işaretli satır sıralamaya girmez, notunda sebebi yazar ve
    durum `RankRow.campaign_status` alanında ayrıca taşınır (arayüz rozeti).
    Damgasız (`None`) satır etkilenmez.

    `oran_bazi` taşınmışsa **baz kapısı** uygulanır: bazı alanın kıyas bazından
    (`KANONIK_ORAN_BAZI`) farklı olan oran sıralamaya girmez. Baz bilinmiyorsa
    (`None`) kapı ateşlenmez ve baz UYDURULMAZ — gerekçesi "Baz kapısı"
    bloğunda.

    `kapsam` verilirse, kapsamda olup `rows` içinde HİÇ satırı bulunmayan her
    `(bank, campaign_type)` çifti için değeri `None` olan bir satır eklenir
    (`NOT_ALAN_YOK`). Şartnamenin beklenen tablosu (s.11–12) alanı eksik olan
    bankayı da satır olarak gösteriyor; gerekçe "Kapsam kapısı" bloğunda.
    Kapsam verilmezse davranış birebir eskisidir.
    """
    built: list[RankRow] = []
    for r in rows:
        sk, comparable, note = _numeric_key(field_name, r.get("canonical_value"))
        # Süre kapısı GÜVEN kapısından önce: ikisi de ateşlenirse kullanıcıya
        # gösterilecek tek not, kampanyanın artık geçerli olmadığıdır. Düşük
        # güven bir ölçüm kusurudur; süresi dolmuşluk ürünün kendisiyle ilgili
        # bir gerçektir ve daha temel bir eleme sebebidir.
        durum_notu = _durum_notu(r.get("campaign_status"))
        if durum_notu is not None and comparable:
            comparable, note = False, durum_notu
        # Baz kapısı, süre kapısından SONRA ve koşul kapısından ÖNCE. Baz,
        # sayının BİRİMİDİR — farklı para birimi ile aynı sınıftan bir
        # engeldir ve o kontrol zaten `_numeric_key` içinde, her şeyden önce
        # yapılıyor. Koşulluluk ise ürünün kime/nasıl verildiğiyle ilgilidir;
        # birimi yanlış okunan bir sayıda koşulu tartışmak sıra hatasıdır.
        # Süresi dolmuşluk yine en önde: artık verilmeyen bir teklifin bazı
        # ikincil bir ayrıntıdır.
        baz_notu = _baz_notu(field_name, r.get("oran_bazi"))
        if baz_notu is not None and comparable:
            comparable, note = False, baz_notu
        # Koşul kapısı, güven kapısından ÖNCE ve süre kapısından SONRA:
        # süresi dolmuşluk ürünün varlığıyla, koşulluluk ürünün kendisiyle,
        # düşük güven ise bizim ÖLÇÜMÜMÜZLE ilgilidir. Kullanıcıya gösterilecek
        # tek not, en temel eleme sebebi olmalı ve sıra bunu kurar.
        kosul_notu = _kosul_notu(field_name, r.get("raw_value"),
                                 r.get("source_span"), r.get("bank_name"))
        if kosul_notu is not None and comparable:
            comparable, note = False, kosul_notu
        # Güven kapısı sayısallaştırmadan SONRA uygulanır: zaten kıyaslanamayan
        # bir satırın (aralık, farklı para birimi) notunu güvenle değiştirmek
        # daha bilgilendirici olmaz, yalnız asıl nedeni gizlerdi.
        guven_notu = _guven_notu(r.get("confidence"))
        if guven_notu is not None and comparable:
            comparable, note = False, guven_notu
        built.append(RankRow(
            bank=r.get("bank"),
            bank_name=r.get("bank_name"),
            # Gösterilen değer de tekilleştirilir: arayüzde `{min:1.89,
            # max:1.89}` yerine `1.89` görünsün.
            value=collapse_degenerate_range(r.get("canonical_value")),
            sort_key=sk,
            comparable=comparable,
            note=note,
            source_span=r.get("source_span"),
            campaign_id=r.get("campaign_id"),
            campaign_type=r.get("campaign_type"),
            campaign_status=r.get("campaign_status"),
            confidence=r.get("confidence"),
            oran_bazi=oran_bazi_dogrula(r.get("oran_bazi")),
        ))

    lower_better = field_name in _LOWER_IS_BETTER
    comparables = [b for b in built if b.comparable and b.sort_key is not None]
    others = [b for b in built if not (b.comparable and b.sort_key is not None)]
    comparables.sort(key=lambda b: b.sort_key, reverse=not lower_better)
    # Kapsam satırları EN SONA: bir sıralama anahtarları yok ve elenmiş
    # satırların (aralık, süresi dolmuş…) önüne geçmeleri, ölçülmüş bir
    # boşluğu hiç ölçülmemiş bir alanın önünde göstermek olurdu.
    return comparables + others + _kapsam_eksikleri(built, kapsam)


def best(rows: list[dict], field_name: str) -> Optional[RankRow]:
    """En iyi (sıralamada ilk comparable) satırı döndürür."""
    ranked = rank(rows, field_name)
    for r in ranked:
        if r.comparable:
            return r
    return None


# --------------------------------------------------------------------------- #
# Sunum kapıları — "banka başına tek satır" ve "tür içinde kıyas"
# --------------------------------------------------------------------------- #
#
# Bu iki fonksiyon `rank()` çıktısını KULLANICIYA GÖSTERİLECEK hâle getirir ve
# BİLEREK sıralama motorunun yanında durur. Sebebi ölçülmüş bir kusurdur:
# `/compare` ucu 2026-08-09'da banka başına tekilleştirmeyi kendi gövdesinde
# kurdu, chatbot'un yapısal yolu ise `rank()` çıktısını olduğu gibi bastı.
# Sonuç, tarayıcıda görüldü — "Peki vade?" sorusuna aynı banka ve aynı değer
# **232 satır** boyunca tekrarlandı.
#
# Aynı kararın iki yerde ayrı ayrı yaşaması bu depoda üç kez pahalıya mal oldu
# (`ihtar.py` belge süzmesi, oran tablosu başlık deseni, göç listesi paritesi).
# Kural burada TEK bir yerde tanımlıdır; ayrışmayı `tests/
# test_chatbot_kiyas_paritesi.py` kapıda tutar.


def yon_zorla(ranked: list[RankRow], field_name: str,
              intent: Optional[str]) -> list[RankRow]:
    """Kullanıcının istediği sıralama yönünü uygular.

    `rank()` her alanı KENDİ doğal yönünde sıralar (`vade_ay`'da uzun vade
    önce). Kullanıcı bunun tersini isterse ("en kısa vade") sıra çevrilmelidir.

    Kural `/compare?intent=` ile birebir aynıdır:

        lowest  → küçük değer önce
        highest → büyük değer önce
        list / filter / None → alanın kendi doğal yönü

    Çevirme yalnız `comparable=True` önekine uygulanır; kıyaslanamayanlar
    notlarıyla sonda kalır — onların bir "yönü" yoktur.

    Bu kapı olmadan tek alanlı yol sessizce YANLIŞ cevap veriyordu: `vade_ay`
    alanında `intent='lowest'` sorusuna sıralamanın tepesindeki satır, yani
    **en uzun** vade, "en düşük vade" etiketiyle basılıyordu.
    """
    istenen_dusuk = {"lowest": True, "highest": False}.get(intent or "")
    if istenen_dusuk is None or istenen_dusuk == (field_name in _LOWER_IS_BETTER):
        return list(ranked)
    bas = [x for x in ranked if x.comparable and x.sort_key is not None]
    son = [x for x in ranked if not (x.comparable and x.sort_key is not None)]
    return list(reversed(bas)) + son


def tekil_banka_urun(ranked: list[RankRow]) -> list[RankRow]:
    """Banka × ürün ailesi başına TEK satır bırakır (`per_bank=best` kuralı).

    Tekilleştirme anahtarı ``(bank, campaign_type)``'dır, yalnız ``bank``
    değil: bir bankanın konut finansmanı ile taşıt finansmanı **farklı
    ürünlerdir** ve aynı satıra indirgenmeleri, adil kıyas garantisinin ürün
    ailesi düzeyindeki karşılığını bozardı.

    `ranked` zaten en iyiden kötüye sıralı ve kıyaslanabilirler baştadır;
    dolayısıyla bir çiftin İLK görülen satırı o bankanın o ailedeki en
    iyisidir. Ayrı bir "en iyiyi seç" mantığı yazmak, sıralama kuralını ikinci
    kez (ve ayrışma riskiyle) uygulamak olurdu.

    Elenen satırlar SAKLANMAZ, SAYILIR: kalan satırın `other_count` alanı "bu
    bankanın bu ailede kaç kampanyası daha var" sorusunu yanıtlar. Bilgi
    gizlenmiyor, özetleniyor.
    """
    aile_sayisi: dict[tuple[Any, Any], int] = {}
    for x in ranked:
        anahtar = (x.bank, x.campaign_type)
        aile_sayisi[anahtar] = aile_sayisi.get(anahtar, 0) + 1

    gorulen: set[tuple[Any, Any]] = set()
    out: list[RankRow] = []
    for x in ranked:
        anahtar = (x.bank, x.campaign_type)
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        out.append(replace(x, other_count=aile_sayisi[anahtar] - 1))
    return out


def turlere_ayir(ranked: list[RankRow]) -> list[tuple[str, list[RankRow]]]:
    """Sıralamayı **ürün ailesine** böler; grup içi sıra korunur.

    Şartnamenin çalışılmış örneği (s.12–13) aynı ürünü karşılaştırıyor: üç
    bankanın **konut finansmanı** kampanyaları, tek tabloda. Bir kredi kartı
    kampanyası ile bir konut finansmanı birbirinin alternatifi değildir;
    "hangisi daha düşük" sorusu bu ikisi arasında iyi tanımlı değildir.
    `rank_advantageous_by_type()` aynı kararı bileşik skor için çoktan verdi —
    bu, onun tek alanlı sıralamadaki karşılığıdır.

    Grup sırası: **önce kalabalık aile**, eşitlikte ada göre — aynı kural
    `rank_advantageous_by_type()` içinde de geçerli; iki yüzeyin aileleri
    farklı sırada göstermesi kullanıcı için sebepsiz bir tutarsızlık olurdu.

    "Kalabalık" ölçüsü SATIR sayısı değil **kampanya** sayısıdır
    (``1 + other_count``). Tekilleştirmeden sonra tek bankalı bir sorguda her
    ailede tam bir satır kalır ve satır sayısına göre sıralamak eşitlik
    üretir; sıra o zaman alfabeye düşer ve 113 kampanyalık bir aile, tek
    kampanyalık bir ailenin arkasında kalır. Tekilleştirme yapılmamış
    girdilerde `other_count` sıfırdır ve ölçü satır sayısına eşitlenir.

    Türü boş olan satırlar `BILINMEYEN_TUR` grubunda toplanır — elenmezler.
    """
    gruplar: dict[str, list[RankRow]] = {}
    for x in ranked:
        gruplar.setdefault(x.campaign_type or BILINMEYEN_TUR, []).append(x)
    return sorted(gruplar.items(),
                  key=lambda kv: (-sum(1 + x.other_count for x in kv[1]),
                                  -len(kv[1]), kv[0]))


# =========================================================================== #
# Şartname Senaryo-1 tablosu — banka başına TEK satır, YEDİ kolon
# =========================================================================== #
#
# Şartname s.11–12 çözümün çıktısını bir tabloyla TARİF EDİYOR ve o tablo bu
# dosyadaki her şeyden farklı bir şekle sahip:
#
#     Banka | Ürün Türü | Kâr Payı Oranı | Vade | Kampanya Avantajı |
#     Masraf Durumu | Kampanya Süresi
#
# `rank()` TEK alanlıdır (bir kolon, çok banka); bu tablo ÇOK alanlıdır (bir
# banka, yedi kolon). İkisi birbirinin yerine geçmez ve bu blok `rank()`in
# YANINA gelir: tek alanlı ekranın kanıt/güven/katman kolonları denetim
# yüzeyidir, bu tablo ise şartnamenin manşet illüstrasyonudur.
#
# ## Satır = TEK kampanya, birleştirme YOK
#
# Bir bankanın oranını bir kampanyasından, vadesini bir başkasından alıp aynı
# satıra yazmak, var olmayan bir ürün icat etmek olurdu — §21'in yasakladığı
# değer uydurmanın satır düzeyindeki hâli. Bu yüzden satır tek bir kampanyayı
# temsil eder; bankanın o ailedeki diğer kampanyaları `other_count` ile
# SAYILIR (gizlenmez), `tekil_banka_urun()` ile aynı sözleşme.
#
# ## Temsilciyi ne seçer — bileşik skor DEĞİL
#
# `rank_advantageous()` kullanmak cazipti ama yanlış olurdu: o fonksiyon "en
# avantajlı" İDDİASINI üretir ve iddia ağırlıklara (bir ürün kararına) dayanır.
# Bu tablo bir sıralama değil bir KATALOGdur; temsilciyi "en avantajlı" diye
# seçmek, tabloya sormadığı bir soruyu cevaplatmak olurdu.
#
# Ölçüt bunun yerine tablonun kendi amacıdır — **en çok hücreyi dolduran
# kampanya**:
#
#     1. süresi dolmamış olan önce   (kapanmış kampanya ürünü temsil etmez)
#     2. dolu hücresi çok olan önce  (tablonun amacı: okunabilir satır)
#     3. ortalama güveni yüksek olan önce
#     4. küçük `campaign_id` önce    (kararlılık — eşitlikte sıra oynamasın)
#
# ## Sıra: alfabetik, çünkü bu bir SIRALAMA DEĞİL
#
# Satırlar banka adına göre dizilir. Kâr payına göre dizmek tabloyu bir
# sıralama gibi okuturdu; oysa yedi kolonun hepsi aynı yönde "iyi" değildir ve
# kolonların bir kısmı kıyaslanabilir bile değildir (§17).

#: Kampanya avantajını besleyen alanlar — ÖNCELİK SIRASIYLA.
#:
#: Kural: "Kampanya Avantajı" **serbest metin ÜRETİLMEZ**; mevcut çıkarım
#: satırlarından derlenir ve her parça kendi `span`ını taşır. Şartnamenin
#: örnek hücreleri zaten bu alanların biçiminde: "5.000 TL alışveriş çeki" →
#: `odul_miktari` / `alisveris_puani`.
#:
#: Sıra keyfi değil, ÖZGÜLLÜK sırası: doğrudan para ödülü (`odul_miktari`) en
#: somut fayda, puan ondan sonra, oransal indirim en soyutu.
AVANTAJ_ALANLARI: tuple[str, ...] = (
    "odul_miktari", "alisveris_puani", "indirim_orani",
)

#: Ücret MUAFİYETİ de bir avantajdır — ama yalnız yukarıdakiler boşsa.
#:
#: Şartnamenin kendi kavram tablosu (s.10) "Avantajlı Finansman"ı *"daha uygun
#: maliyet, kâr payı oranı **veya ek fayda** sunan"* diye tanımlıyor; s.12
#: tablosunda da A Bankası'nın avantaj hücresi masraf cümlesinden geliyor
#: ("50.000 TL'ye kadar masraf alınmıyor"). Yani muafiyet, şartnamenin kendi
#: okumasında avantajdır.
#:
#: YALNIZ muafiyet yönü sayılır: var olan bir ücret avantaj değildir. Ve
#: yalnız `AVANTAJ_ALANLARI` boşsa devreye girer — "Masraf Durumu" zaten ayrı
#: bir kolondur ve iki hücrede aynı çıkarımı basmak, doluluk sayacını da
#: kendi kopyasıyla şişirirdi.
AVANTAJ_MUAFIYET_ALANLARI: tuple[str, ...] = ("masraf_durumu", "tahsis_ucreti")

# `kampanya_kosullari` BİLEREK kaynak DEĞİL. Alan adı avantaj çağrıştırıyor
# ama içeriği kısıttır — korpustaki 1344 satırdan ölçülen örnekler:
#
#     "Müşteri olma aşamasında \"Davet Kodu\" alanına \"KTOD2026\" kodunun
#      yazılması gerekmektedir."
#     "Kuveyt Türk önceden haber vermeden kampanya koşullarında değişiklik
#      yapabilir ya da kampanyayı sonlandırabilir."
#
# Bir kısıtı "Kampanya Avantajı" kolonuna basmak, anlamını TERSİNE çevirmek
# olurdu. Boş bırakmak yanlış bilgi vermekten iyidir.


def _muafiyet_mi(field_name: str, value: Any) -> bool:
    """Bu masraf/ücret değeri bir MUAFİYET mi (yani avantaj mı)?

    Tutarı bilinmeyen bir ücret (`has_fee=True, amount=None`) muafiyet
    DEĞİLDİR — orada bilinen tek şey ücretin var olduğudur.

    `has_fee` taşıyan bir değerde **yalnız `has_fee is False`** muafiyettir;
    tutara BAKILMAZ. Ölçüldü (`data/demo.db`, Vakıf Katılım konut satırı):
    korpus `{"has_fee": True, "amount": 0.0}` üretebiliyor — kendi içinde
    çelişkili bir kayıt ("ücret var ve sıfır"). Tutara bakan bir kural bunu
    avantaj sayıyordu, yani çelişkili bir çıkarımı kullanıcıya olumlu bir
    iddia olarak sunuyordu. Çelişki halinde `has_fee` bayrağı kazanır ve
    hücre boş kalır: bir avantaj UYDURMAKtansa söylememek yeğdir.

    Bayrak taşımayan para biçimli ücretlerde (`tahsis_ucreti`) sıfır tutar
    muafiyettir — orada çelişki yoktur, "0 TL tahsis ücreti" tek bir şey söyler.
    """
    if field_name not in AVANTAJ_MUAFIYET_ALANLARI or value is None:
        return False
    if isinstance(value, dict):
        if "has_fee" in value:
            return value.get("has_fee") is False
        return value.get("value") == 0 or value.get("amount") == 0
    return value == 0


#: Tablonun kolon sözleşmesi: `(anahtar, başlık, alan_adı)`.
#:
#: Başlıklar şartname s.12'deki yazımla BİREBİR aynıdır — tablo o
#: illüstrasyonun karşılığı olduğunu iddia ediyorsa kolon adını da değiştiremez.
#: `alan_adı` `None` olan iki kolon TÜRETİLMİŞTİR (kampanya kaydından okunur,
#: çıkarımdan değil) ve doluluk sayacına GİRMEZ: her zaman dolu oldukları için
#: sayaca katılmaları kapsama oranını sebepsiz yükseltirdi.
#:
#: `kampanya_avantaji` bir çıkarım alanı DEĞİLDİR ve şemaya böyle bir sütun
#: eklenmez; `AVANTAJ_ALANLARI` üzerinden derlenen BİRLEŞİK kolondur.
SARTNAME_SUTUNLARI: tuple[tuple[str, str, Optional[str]], ...] = (
    ("bank", "Banka", None),
    ("campaign_type", "Ürün Türü", None),
    ("kar_payi_orani", "Kâr Payı Oranı", "kar_payi_orani"),
    ("vade_ay", "Vade", "vade_ay"),
    ("kampanya_avantaji", "Kampanya Avantajı", None),
    ("masraf_durumu", "Masraf Durumu", "masraf_durumu"),
    ("kampanya_suresi", "Kampanya Süresi", "kampanya_suresi"),
)

#: Doluluk sayacına giren kolonlar — türetilmiş ikisi hariç hepsi.
OLCULEN_SUTUNLAR: tuple[str, ...] = (
    "kar_payi_orani", "vade_ay", "kampanya_avantaji",
    "masraf_durumu", "kampanya_suresi",
)


@dataclass
class TabloHucresi:
    """Tablonun tek bir hücresi — değer + KANITI.

    Avantaj parçaları da aynı şekli kullanır (`parcalar`): bir hücre ile onu
    oluşturan parçanın farklı şekilleri olsaydı, arayüz kaynak rozetini iki
    kez yazmak zorunda kalırdı.

    `bos` hesaplanmış bir alandır ve arayüzün `value is None` denemesinden
    farklıdır: birleşik kolonda değer yoktur ama parçalar olabilir.
    """

    sutun: str
    field_name: Optional[str]
    value: Any = None
    raw_value: Optional[str] = None
    confidence: Optional[float] = None
    extractor: Optional[str] = None
    source_span: Optional[str] = None
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    parcalar: list["TabloHucresi"] = dc_field(default_factory=list)

    @property
    def bos(self) -> bool:
        return self.value is None and not self.parcalar

    def to_dict(self) -> dict[str, Any]:
        return {
            "sutun": self.sutun,
            "field_name": self.field_name,
            "value": self.value,
            "raw_value": self.raw_value,
            "confidence": self.confidence,
            "extractor": self.extractor,
            "source_span": self.source_span,
            "span_start": self.span_start,
            "span_end": self.span_end,
            "bos": self.bos,
            "parcalar": [p.to_dict() for p in self.parcalar],
        }


@dataclass
class TabloSatiri:
    """Bir banka × ürün ailesi satırı — TEK kampanyadan."""

    bank: Optional[str]
    bank_name: Optional[str]
    campaign_id: Optional[Any]
    campaign_type: Optional[str]
    campaign_status: Optional[str]
    #: Bu bankanın aynı ailede gösterilmeyen kampanya sayısı.
    other_count: int
    cells: dict[str, TabloHucresi]

    def to_dict(self) -> dict[str, Any]:
        return {
            "bank": self.bank,
            "bank_name": self.bank_name,
            "campaign_id": self.campaign_id,
            "campaign_type": self.campaign_type,
            "campaign_status": self.campaign_status,
            "other_count": self.other_count,
            "cells": {k: h.to_dict() for k, h in self.cells.items()},
        }


def _hucre(sutun: str, field_name: Optional[str],
           alan: Optional[Mapping[str, Any]]) -> TabloHucresi:
    """Çıkarım kaydından hücre kurar; kayıt yoksa BOŞ hücre."""
    if not alan:
        return TabloHucresi(sutun=sutun, field_name=field_name)
    return TabloHucresi(
        sutun=sutun,
        field_name=field_name,
        value=collapse_degenerate_range(alan.get("canonical_value")),
        raw_value=alan.get("raw_value"),
        confidence=alan.get("confidence"),
        extractor=alan.get("extractor"),
        source_span=alan.get("source_span"),
        span_start=alan.get("span_start"),
        span_end=alan.get("span_end"),
    )


#: Avantaj parçasının, yanındaki bir tablo kolonuyla AYNI çıkarımdan geldiğini
#: söyleyen işaret. Arayüz bu parçayı farklı basar (bkz. aşağıdaki blok).
SUTUN_AVANTAJ_CAKISAN = "kampanya_avantaji_cakisan"

#: Tablonun kendi kolonlarında görünen alanlar — çakışma bu kümeyle belirlenir.
_KOLON_ALANLARI: frozenset[str] = frozenset(
    f for _a, _b, f in SARTNAME_SUTUNLARI if f
)


# --------------------------------------------------------------------------- #
# Çakışan avantaj parçası — neden ayrı işaretleniyor
# --------------------------------------------------------------------------- #
#
# "Kampanya Avantajı" hücresi ücret muafiyetinden beslendiğinde, kaynağı
# `masraf_durumu`dur — yani YANINDAKİ "Masraf Durumu" kolonunun ta kendisi.
# Arayüz ikisini de "alan adı: kanonik değer" biçiminde bastığında satır
# kelimesi kelimesine tekrar ediyordu:
#
#     … | Kampanya Avantajı: Masraf Durumu: masrafsız | Masraf Durumu: masrafsız
#
# Şartname s.12 aynı olguyu İKİ FARKLI cümleyle yazıyor ("50.000 TL'ye kadar
# masraf alınmıyor" / "Dosya masrafı yok"), yani tekrar beklenen biçim değil.
#
# Çözüm: çakışan parçada bankanın KENDİ ham ifadesini bas (üretilmiş metin
# değil; kanıtı zaten span'iyle bağlı). Karar sunucuda veriliyor çünkü
# "hangi alanlar tablo kolonudur" bilgisi burada; arayüzde ikinci bir kopya
# tutmak, bu depoda beş kez pahalıya mal olmuş "aynı karar iki yerde" hatası
# olurdu. Ham ifadenin tek başına ayakta durup duramadığına ise ARAYÜZ karar
# verir — o bir okunabilirlik yargısıdır, veri yargısı değil.
#
# Bu işaret YALNIZ çakışan dalda konur. `odul_miktari` / `alisveris_puani` /
# `indirim_orani` kaynaklı parçalar hiçbir kolonu tekrar etmiyor ve olduğu
# gibi kalıyor.


def avantaj_hucresi(alanlar: Mapping[str, Mapping[str, Any]]) -> TabloHucresi:
    """"Kampanya Avantajı" birleşik hücresi — parçalar, serbest metin DEĞİL.

    Kural ve gerekçesi `AVANTAJ_ALANLARI` / `AVANTAJ_MUAFIYET_ALANLARI`
    yorumlarında. Özet: önce doğrudan fayda alanları (hepsi, öncelik
    sırasıyla); hiçbiri yoksa ücret MUAFİYETİ (ilk bulunan). Hiçbiri yoksa
    hücre boştur ve arayüz «Belirtilmemiş» basar.

    Parçaların metne çevrilmesi burada YAPILMAZ: Türkçe biçimlendirme
    arayüzün işidir (`web/app/lib/format.ts`) ve sunucuda ikinci bir
    biçimlendirici tutmak, aynı kararı iki yerde yaşatmak olurdu.
    """
    parcalar: list[TabloHucresi] = []
    for ad in AVANTAJ_ALANLARI:
        alan = alanlar.get(ad)
        if alan and alan.get("canonical_value") is not None:
            parcalar.append(_hucre("kampanya_avantaji", ad, alan))
    if not parcalar:
        for ad in AVANTAJ_MUAFIYET_ALANLARI:
            alan = alanlar.get(ad)
            if alan and _muafiyet_mi(ad, alan.get("canonical_value")):
                # Kaynak aynı zamanda bir tablo kolonuysa parça İŞARETLENİR;
                # gerekçe yukarıdaki blokta.
                sutun = (SUTUN_AVANTAJ_CAKISAN if ad in _KOLON_ALANLARI
                         else "kampanya_avantaji")
                parcalar.append(_hucre(sutun, ad, alan))
                break
    return TabloHucresi(sutun="kampanya_avantaji", field_name=None,
                        parcalar=parcalar)


def _satir_kur(kampanya: Mapping[str, Any], other_count: int) -> TabloSatiri:
    alanlar: Mapping[str, Mapping[str, Any]] = kampanya.get("fields") or {}
    cells: dict[str, TabloHucresi] = {}
    for anahtar, _baslik, field_name in SARTNAME_SUTUNLARI:
        if anahtar == "kampanya_avantaji":
            cells[anahtar] = avantaj_hucresi(alanlar)
        elif field_name is None:
            # Türetilmiş kolon: kampanya kaydının kendisinden okunur.
            deger = (kampanya.get("bank_name") or kampanya.get("bank")
                     if anahtar == "bank" else kampanya.get("campaign_type"))
            cells[anahtar] = TabloHucresi(sutun=anahtar, field_name=None,
                                          value=deger)
        else:
            cells[anahtar] = _hucre(anahtar, field_name, alanlar.get(field_name))
    return TabloSatiri(
        bank=kampanya.get("bank"), bank_name=kampanya.get("bank_name"),
        campaign_id=kampanya.get("campaign_id"),
        campaign_type=kampanya.get("campaign_type"),
        campaign_status=kampanya.get("campaign_status"),
        other_count=other_count, cells=cells,
    )


def _temsilci_anahtari(kampanya: Mapping[str, Any]) -> tuple:
    """Temsilci seçim ölçütü — gerekçesi blok başlığında."""
    alanlar: Mapping[str, Mapping[str, Any]] = kampanya.get("fields") or {}
    gecici = _satir_kur(kampanya, 0)
    dolu = sum(1 for s in OLCULEN_SUTUNLAR if not gecici.cells[s].bos)
    guvenler = [a.get("confidence") for a in alanlar.values()
                if a.get("confidence") is not None]
    ort = sum(guvenler) / len(guvenler) if guvenler else 0.0
    cid = kampanya.get("campaign_id")
    return (
        suresi_dolmus_mu(kampanya.get("campaign_status")),  # False (0) önce
        -dolu,
        -ort,
        cid if isinstance(cid, int) else 0,
    )


def tablo_satirlari(
    kampanyalar: Iterable[Mapping[str, Any]],
    kapsam: Optional[Iterable[Mapping[str, Any]]] = None,
) -> list[TabloSatiri]:
    """Şartname s.12 tablosunun satırları — banka × ürün ailesi başına bir.

    `kampanyalar` öğeleri::

        {"bank": "kuveyt-turk", "bank_name": "Kuveyt Türk",
         "campaign_id": 12, "campaign_type": "Konut Finansmanı",
         "campaign_status": None,
         "fields": {"kar_payi_orani": {"canonical_value": 1.89,
                                       "raw_value": "%1,89",
                                       "confidence": 0.95, ...}, ...}}

    `kapsam` `rank()`teki ile AYNI sözleşmedir ve aynı işi yapar: o ailede
    belgesi olup hiç ölçülebilir alanı olmayan banka tablodan DÜŞMEZ, tüm
    hücreleri boş bir satır alır. Şartnamenin kendi tablosunda da 21 hücrenin
    3'ü "Belirtilmemiş"tir; seyreklik gizlenecek bir şey değil.
    """
    gruplar: dict[tuple[Any, Any], list[Mapping[str, Any]]] = {}
    for k in kampanyalar:
        gruplar.setdefault((k.get("bank"), k.get("campaign_type")), []).append(k)

    satirlar = [
        _satir_kur(min(grup, key=_temsilci_anahtari), len(grup) - 1)
        for grup in gruplar.values()
    ]

    for k in kapsam or ():
        anahtar = (k.get("bank"), k.get("campaign_type"))
        if anahtar in gruplar:
            continue
        gruplar[anahtar] = []
        satirlar.append(_satir_kur(
            {"bank": k.get("bank"), "bank_name": k.get("bank_name"),
             "campaign_type": k.get("campaign_type"), "fields": {}}, 0))

    # Alfabetik: bu bir katalog, sıralama değil (gerekçe blok başlığında).
    satirlar.sort(key=lambda s: (str(s.campaign_type or ""),
                                 str(s.bank_name or s.bank or "")))
    return satirlar


def tablo_dolulugu(satirlar: Iterable[TabloSatiri]) -> dict[str, Any]:
    """"Bu görünümde X hücrenin Y'si dolu" — ÇALIŞMA ANINDA ölçülür.

    Sayı koda GÖMÜLMEZ: korpus doluluğu çıkarım katmanı geliştikçe değişiyor
    ve donmuş bir sayı, ekranda bir gün gerçek olmayan bir iddia olurdu.

    Türetilmiş kolonlar (Banka, Ürün Türü) sayaca girmez — her zaman dolu
    oldukları için oranı sebepsiz yükseltirlerdi. Şartnamenin kendi tablosuyla
    kıyaslanabilsin diye yedi kolonluk toplam da ayrıca döner.
    """
    satirlar = list(satirlar)
    n = len(satirlar)
    sutun_basina = {
        s: sum(1 for x in satirlar if not x.cells[s].bos)
        for s in OLCULEN_SUTUNLAR
    }
    dolu = sum(sutun_basina.values())
    hucre = n * len(OLCULEN_SUTUNLAR)
    return {
        "satir": n,
        "olculen_sutun": len(OLCULEN_SUTUNLAR),
        "hucre": hucre,
        "dolu": dolu,
        "oran": (dolu / hucre) if hucre else 0.0,
        "sutun_basina": {s: {"dolu": d, "toplam": n}
                         for s, d in sutun_basina.items()},
        # Şartname s.12 tablosu 3×7 = 21 hücre sayıyor; karşılaştırılabilirlik
        # için aynı ölçü de verilir. Türetilmiş iki kolon her satırda doludur.
        "tum_sutun": len(SARTNAME_SUTUNLARI),
        "tum_hucre": n * len(SARTNAME_SUTUNLARI),
        "tum_dolu": dolu + n * (len(SARTNAME_SUTUNLARI) - len(OLCULEN_SUTUNLAR)),
    }


# =========================================================================== #
# §5.7 beşinci ölçüt: "En Avantajlı Kampanya" — çok alanlı bileşik sıralama
# =========================================================================== #
#
# Şartname (s.11, §5.7) beş karşılaştırma ölçütü sayar. İlk dördü tek alanlıdır
# ve `rank()` ile karşılanır. Beşincisi ("En Avantajlı Kampanya") doğası gereği
# BİLEŞİKTİR: birden çok alanı tek bir sıralamaya indirmek gerekir.
#
# ------------------------------------------------------------------ #
# Neden ağırlıklar BU değerler? (jüri "neden bu ağırlık" diye soracak)
# ------------------------------------------------------------------ #
#
# Önce saf maliyet modelini ÖLÇTÜK. 100.000 TL / 36 ay referans sepetinde
# (kâr tutarı ≈ tutar × aylık_oran × (n+1)/2) korpustaki değer aralıklarının
# TL etkisi:
#
#   kâr payı oranı  %1,89 → %5,99   ≈  34.965 TL → 110.815 TL   (fark ~75.850 TL)
#   tahsis/masraf   0 TL  → 750 TL  ≈       0 TL →     750 TL   (fark ~   750 TL)
#   ödül miktarı    150 TL → 6.000 TL                (fark ~ 5.850 TL)
#
# Saf TL etkisine göre ağırlık ≈ %92 / %1 / %7 çıkar. Bunu KULLANMIYORUZ, iki
# ölçülmüş sebeple:
#
#  1. Alanlar farklı ürün ailelerinde yaşıyor. Korpusta 849 belgenin yalnız
#     47'sinde kâr payı, 120'sinde ödül miktarı var ve bu iki küme neredeyse
#     hiç kesişmiyor (finansmanın ödülü, kart kampanyasının kâr payı yoktur).
#     %92 ağırlık kâr payına verilirse tüm kart kampanyaları tek bir eksikten
#     dolayı sıralamanın dibine düşer — bu adil kıyas değildir.
#  2. Şartname beş ölçütü EŞİT ölçüt olarak sayar; birini diğerlerini silecek
#     kadar ağırlıklandırmak ölçütü fiilen kaldırmak olur.
#
# Bu yüzden ağırlıklar "TL etkisi sıralamasını koruyan, ama hiçbir ölçütü
# silmeyen" bir uzlaşmadır. Her biri `WEIGHT_RATIONALE`de tek cümleyle
# gerekçelidir, `DEFAULT_WEIGHTS` API'den okunabilir ve `weights=` ile
# geçersiz kılınabilir. Bu bir ÜRÜN KARARIDIR, ölçümden türetilmiş bir sabit
# değildir — bu ayrım bilerek belirtiliyor.

DEFAULT_WEIGHTS: dict[str, float] = {
    "kar_payi_orani": 0.40,
    "masraf_durumu": 0.20,
    "odul_miktari": 0.15,
    "vade_ay": 0.15,
    "finansman_tutari": 0.10,
}

# --------------------------------------------------------------------------- #
# Tür başına ölçüt kümesi — «ölçülemedi» salgınının kökü
# --------------------------------------------------------------------------- #
#
# ## Ölçülmüş arıza (kullanıcı raporu 2026-08-25)
#
# Banka sayfasında türlerin neredeyse tamamı «ölçülemedi» diyordu. Korpus
# genelinde 909 kampanyanın yalnız **58'i** kıyaslanabilirdi (%6,4).
#
# Sebep aritmetikti, veri değil. `DEFAULT_WEIGHTS` her tür için AYNI beş ölçütü
# kullanıyor ve `MIN_COVERAGE = 0.5` ağırlıkça yarısının dolu olmasını istiyor.
# Bir **kart** kampanyasında `kar_payi_orani` (0,40) ve `finansman_tutari`
# (0,10) zaten BULUNMAZ — ölçüldü: kart belgelerinin %2'sinde ve %0'ında
# geçiyor. Yani kartın ulaşabileceği en yüksek kapsama **0,50** ve eşiği ancak
# kalan üç ölçütün ÜÇÜ birden doluysa geçiyor. 751 kart kampanyasının 448'i bu
# yüzden düştü.
#
# Bu bir veri boşluğu değil, **kategori uyuşmazlığı**: kart kampanyasında
# finansman oranı aramak, olmayan bir şeyin eksikliğinden ceza kesmektir.
#
# ## Ölçüm — hangi ölçüt hangi türde GERÇEKTEN var
#
# (kampanya belgeleri, tüm bankalar, 2026-08-25)
#
#     tür                belge   kar  masraf  ödül  vade  finans  taksit  indirim  puan
#     Kart                 751    2%    31%   28%   15%     0%     39%     13%    11%
#     Finansman            307    7%     9%    2%   29%     9%     12%      4%     1%
#     Yatırım Ürünü        271    5%    17%    8%   28%     1%      4%      2%     4%
#     İhtiyaç Finansmanı    99   16%    16%    1%   55%    24%     24%      0%     0%
#     Alışveriş Puanı       60    0%    13%   28%    3%     0%      8%      5%    97%
#     Taşıt Finansmanı      49   29%    33%    6%   61%    10%      0%      4%     4%
#     Konut Finansmanı      47    6%    32%    6%   53%     6%     17%      6%     9%
#     Yeni Müşteri           5    0%    40%   20%    0%     0%      0%      0%     0%
#
# İki sonuç açık: (1) finansman aileleri oran/vade/tutar üzerinden ölçülür,
# (2) kart ve puan aileleri ödül/masraf/taksit/indirim üzerinden. `Alışveriş
# Puanı` türünde belgelerin **%97'sinde** `alisveris_puani` dolu ve o alan
# ağırlık tablosunda HİÇ YOKTU — türün tanımlayıcı ölçütü kıyasa girmiyordu.
#
# ## Karar
#
# Ölçüt KÜMESİ ölçümden, ağırlık DEĞERLERİ üründen gelir. Aşağıdaki tablo
# ikisini birleştiriyor; `weights=` ile hâlâ geçersiz kılınabilir ve
# `/scoring` ucundan okunabilir.
#
# ADİL KIYAS BOZULMUYOR: kıyas zaten TÜR İÇİNDE yapılıyor (§17,
# `rank_advantageous_by_type`). Aynı tür içindeki tüm kampanyalar aynı ölçüt
# kümesiyle ölçülüyor; değişen yalnız türden türe geçerken hangi ölçütlerin
# UYGULANABİLİR olduğu.

TUR_AGIRLIKLARI: dict[str, dict[str, float]] = {
    # Finansman aileleri — oran/vade/tutar ekseni (varsayılanla aynı).
    "Konut Finansmanı": dict(DEFAULT_WEIGHTS),
    "Taşıt Finansmanı": dict(DEFAULT_WEIGHTS),
    "İhtiyaç Finansmanı": dict(DEFAULT_WEIGHTS),
    "Finansman": dict(DEFAULT_WEIGHTS),
    # Kart — kâr payı ve finansman tutarı UYGULANMAZ (%2 ve %0).
    "Kart": {
        "odul_miktari": 0.30,
        "masraf_durumu": 0.25,
        "taksit_sayisi": 0.20,
        "indirim_orani": 0.15,
        "vade_ay": 0.10,
    },
    # Alışveriş Puanı — türün TANIMLAYICI ölçütü `alisveris_puani` (%97).
    "Alışveriş Puanı": {
        "alisveris_puani": 0.40,
        "odul_miktari": 0.30,
        "indirim_orani": 0.15,
        "masraf_durumu": 0.15,
    },
    # Yatırım Ürünü — türün ASIL ölçütü katılma hesabının getirisi.
    #
    # Kampanya belgelerinde oran %5'te; ama bu türün gerçek ürünü katılma
    # hesabıdır ve TKBB onun dağıtılan getirisini HER BANKA için haftalık
    # yayımlıyor. O sayı olmadan "yatırım ürününde hangi banka iyi" sorusu
    # vade ve masraf üzerinden cevaplanıyordu — ürünün kendisine bakmadan.
    "Yatırım Ürünü": {
        "katilma_getirisi": 0.45,
        "vade_ay": 0.25,
        "masraf_durumu": 0.20,
        "odul_miktari": 0.10,
    },
    # Yeni Müşteri — yalnız iki ölçüt gerçekten var (%40 ve %20).
    "Yeni Müşteri": {
        "odul_miktari": 0.55,
        "masraf_durumu": 0.45,
    },
    # Türü belirlenememiş belgeler: kart/puan ailesine benzer dağılım
    # gösteriyor (masraf %34, ödül %20, indirim %20).
    BILINMEYEN_TUR: {
        "masraf_durumu": 0.35,
        "odul_miktari": 0.25,
        "indirim_orani": 0.25,
        "taksit_sayisi": 0.15,
    },
}


def tur_agirliklari(tur: Optional[str]) -> dict[str, float]:
    """Bu kampanya türü için ölçüt ağırlıkları.

    Tanımsız tür `DEFAULT_WEIGHTS` alır — yeni bir tür eklendiğinde sistem
    sessizce boş ağırlıkla çalışmasın diye. Ağırlıklar toplamı 1,0 olacak
    biçimde NORMALLEŞTİRİLİYOR: elle yazılan bir tablo zamanla 0,99 ya da
    1,02'ye kayar ve o kayma kapsama eşiğini sessizce oynatırdı.
    """
    ham = TUR_AGIRLIKLARI.get(tur or BILINMEYEN_TUR) or DEFAULT_WEIGHTS
    toplam = sum(ham.values())
    if toplam <= 0:                          # pragma: no cover - savunma
        return dict(DEFAULT_WEIGHTS)
    return {k: v / toplam for k, v in ham.items()}


WEIGHT_RATIONALE: dict[str, str] = {
    "kar_payi_orani":
        "Toplam maliyeti en çok belirleyen kalem: 100.000 TL / 36 ay sepetinde "
        "korpustaki oran aralığı ~75.850 TL fark yaratıyor; bu yüzden en yüksek "
        "ağırlık.",
    "masraf_durumu":
        "Tutarı küçük (~750 TL) ama PEŞİN ödenir ve şartname §5.7 'En Düşük "
        "Masraf'ı ayrı bir ölçüt sayar; nakit akışı etkisi nedeniyle TL "
        "oranından yüksek tutuldu.",
    "odul_miktari":
        "Doğrudan müşteri kazancı ve §5.7'nin ayrı ölçütü; korpusta ~5.850 TL "
        "aralık — kâr payından küçük, masraftan büyük olduğu için ortada.",
    "vade_ay":
        "Esneklik ölçütü, maliyet ölçütü değil: uzun vade taksidi düşürür ama "
        "toplam maliyeti artırır, bu yüzden ödülle eşit ama kâr payının "
        "altında.",
    "finansman_tutari":
        "Üst limit nadiren bağlayıcıdır (müşteri genelde limitin altında "
        "kullanır); ölçüte dahil ama en düşük ağırlıkla.",
}

# Bileşik skorda güvenilir sayılmak için gereken asgari ağırlıkça kapsama.
# 0.5 = kampanyanın, popülasyonda ölçülebilen ölçütlerin en az yarısını
# (ağırlıkça) taşıması gerekir.
MIN_COVERAGE = 0.5


@dataclass
class ScoreComponent:
    """Bileşik skorun tek bir alandan gelen katkısı — şeffaflık için."""

    field_name: str
    value: Any
    normalized: Optional[float]   # 0..1 (1 = popülasyonun en iyisi)
    weight: float
    contribution: float           # normalized * weight (yoksa 0.0)
    note: Optional[str] = None    # "veri yok", "ücret var tutarı belirtilmemiş"...

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "value": self.value,
            "normalized": self.normalized,
            "weight": self.weight,
            "contribution": self.contribution,
            "note": self.note,
        }


@dataclass
class CompositeScore:
    """Bir kampanyanın "en avantajlı" bileşik skoru + alt puanları."""

    bank: Optional[str]
    bank_name: Optional[str]
    campaign_id: Optional[Any]
    score: Optional[float]        # 0..1; kapsanan ölçütler üzerinden ortalama
    coverage: float               # ağırlıkça kapsama oranı (0..1)
    comparable: bool
    note: Optional[str]
    components: list[ScoreComponent] = dc_field(default_factory=list)
    #: Kampanyanın geçerlilik durumu — `RankRow.campaign_status` ile aynı
    #: gerekçe: rozet, nottan ayrı bir alandan okunur.
    campaign_status: Optional[str] = None
    #: Satırın KAYNAĞI: `"kampanya"` (öntanım) ya da `"banka-yayini"`.
    #:
    #: Yıldız cetveline bankanın KENDİ yayımladığı oranlardan üretilen satırlar
    #: da giriyor (bkz. `kiyas_toplama.yayin_satirlari`). O satırların kanıt
    #: zinciri farklı: kampanya satırı bir belgenin span'ine dayanır, yayın
    #: satırı bankanın hesaplama aracına. Ekranda AYRI etiketlenmeleri şart —
    #: aynı rozetle göstermek "aynı güvenle ölçüldü" demek olurdu.
    kaynak: str = "kampanya"

    def to_dict(self) -> dict[str, Any]:
        return {
            "bank": self.bank,
            "bank_name": self.bank_name,
            "campaign_id": self.campaign_id,
            "kaynak": self.kaynak,
            "score": self.score,
            "coverage": self.coverage,
            "comparable": self.comparable,
            "note": self.note,
            "campaign_status": self.campaign_status,
            "components": [c.to_dict() for c in self.components],
        }


def _composite_numeric(field_name: str,
                       value: Any) -> tuple[Optional[float], Optional[str]]:
    """Kanonik değeri bileşik skor için tek sayıya indirger.

    Dönüş: (sayı, not). Sayı None ise alan skorlanmaz (kapsama düşer) ve not
    nedeni söyler. **Değer UYDURULMAZ** (CLAUDE.md §19 halüsinasyon yasağı).

    `masraf_durumu` özellikle açık yazılmıştır (dict taşır):
      - {"has_fee": False}                → 0.0  (en iyi: masraf yok)
      - {"has_fee": True, "amount": 750}  → 750.0
      - {"has_fee": True, "amount": None} → **skorlanmaz**, not: "ücret var,
        tutarı belirtilmemiş". Sıralama üretmiyoruz çünkü 750 TL ile
        karşılaştırılabilecek bir sayı YOK; sıfır saymak "masrafsız" demek
        olurdu (yalan), popülasyonun en kötüsünü atamak ise değer uydurmak
        olurdu. Korpusta bu durum 22 belgede var — sessizce sıfırlanmaları
        sıralamayı ters çevirirdi.
    """
    value = collapse_degenerate_range(value)
    if value is None:
        return None, "veri yok"
    if isinstance(value, dict):
        if "has_fee" in value:
            if value.get("has_fee") is False:
                return 0.0, None
            amount = value.get("amount")
            if amount is None:
                return None, "ücret var, tutarı belirtilmemiş"
            return float(amount), None
        if "min" in value and "max" in value:
            # Aralık: en iyi senaryo (kâr payında alt sınır, vadede üst sınır)
            # yerine YÖNE GÖRE iyimser uç alınır ve not düşülür.
            lo, hi = float(value["min"]), float(value["max"])
            best_end = lo if field_name in _LOWER_IS_BETTER else hi
            return best_end, "aralık — en iyi uç kullanıldı"
        if value.get("value") is not None:
            cur = value.get("currency")
            if cur and cur != "TRY":
                return None, f"farklı para birimi ({cur})"
            return float(value["value"]), None
        if value.get("rate") is not None:
            # Oran biçimli ücret (%0,50) TL tutarıyla aynı eksende kıyaslanamaz.
            return None, "oran biçimli ücret — TL ile kıyaslanamaz"
        return None, "sayısal değil"
    if isinstance(value, (int, float)):
        return float(value), None
    return None, "sayısal değil"


def _rank_normalize(values: list[float], lower_is_better: bool) -> list[float]:
    """Değerleri SIRALAMA tabanlı 0..1'e indirger (1 = en iyi).

    Neden min-max değil, sıralama tabanlı? Korpus ölçümü (849 belge) alanlarda
    çıkarım kaynaklı uç değerler gösteriyor: `vade_ay` en büyük değer 24.312,
    `tahsis_ucreti` en büyük değer 100.000. Min-max normalizasyonda TEK bir uç
    değer diğer tüm kampanyaları 0'a yapıştırır ve sıralama anlamsızlaşır.
    Sıralama tabanlı normalizasyon uç değerlere dayanıklıdır; yalnız SIRA
    bilgisini kullanır — §5.7 zaten sıralama istiyor, mesafe değil.

    Eşitlikler ortalama sıra alır. Tüm değerler eşitse herkes 1.0 alır
    (kimse cezalandırılmaz).
    """
    n = len(values)
    if n == 0:
        return []
    if n == 1 or len(set(values)) == 1:
        return [1.0] * n
    order = sorted(range(n), key=lambda i: values[i], reverse=not lower_is_better)
    # ham sıra: en iyi 0 ... en kötü n-1
    raw: list[float] = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0
        for k in range(i, j + 1):
            raw[order[k]] = avg
        i = j + 1
    return [1.0 - r / (n - 1) for r in raw]


def rank_advantageous(rows: Iterable[dict],
                      weights: Optional[dict[str, float]] = None,
                      min_coverage: float = MIN_COVERAGE) -> list[CompositeScore]:
    """§5.7 "En Avantajlı Kampanya" — çok alanlı, şeffaf, adil bileşik sıralama.

    `rows`: her biri şu biçimde sözlük::

        {"bank": "kuveyt-turk", "bank_name": "Kuveyt Türk",
         "campaign_id": 12,
         "fields": {"kar_payi_orani": 1.89, "vade_ay": 120, ...},
         "field_confidence": {"kar_payi_orani": 0.95, "vade_ay": 0.45}}

    `field_confidence` isteğe bağlıdır; verilmişse `ASGARI_GUVEN` kapısı tek
    alanlı `rank()` ile AYNI eşikte uygulanır. İki yüzeyin aynı değeri biri
    kıyaslanabilir biri değil sayması, bu depoda beş kez pahalıya mal olmuş
    "aynı karar iki yerde" hatasının bileşik skordaki karşılığı olurdu.

    `field_oran_bazi` de aynı biçimde isteğe bağlıdır ve aynı gerekçeyle
    `rank()`in **baz kapısını** bileşik skora taşır::

        {"field_oran_bazi": {"kar_payi_orani": "yillik"}}

    Bazı `KANONIK_ORAN_BAZI`den farklı olan alan skorlanmaz (kapsamayı düşürür,
    kampanyayı cezalandırmaz); baz bilinmiyorsa kapı ateşlenmez.

    Yöntem (docstring'de olması istendi):

    1. **Sayısallaştırma** — her kanonik değer `_composite_numeric()` ile tek
       sayıya indirgenir; indirgenemiyorsa alan SKORLANMAZ ve nedeni not olarak
       taşınır. Değer asla uydurulmaz. Güveni eşiğin altında kalan alan da
       burada düşer: skoru olmayan bir alan `coverage`'ı düşürür, kampanyayı
       CEZALANDIRMAZ — eksik ölçüt "sıfır puan" değildir.
    2. **Normalizasyon** — her alan KENDİ dağılımında sıralama tabanlı olarak
       0..1'e indirgenir (1 = popülasyonun en iyisi), yön `_LOWER_IS_BETTER` /
       `_HIGHER_IS_BETTER` sözlüklerinden gelir. Böylece %1,89'luk oran ile
       5.000 TL'lik ödül aynı eksende toplanabilir.
    3. **Ağırlıklandırma** — `DEFAULT_WEIGHTS` (gerekçeleri `WEIGHT_RATIONALE`).
       Popülasyonda HİÇ kimsede olmayan alanların ağırlığı dağıtılır; yoksa
       herkesin kapsaması sebepsiz düşük görünür.
    4. **Adil kıyas** — skor, YALNIZ o kampanyada bulunan ölçütler üzerinden
       ortalanır: eksik alan "sıfır puan" DEĞİLDİR. Eksikliğin bilgisi ayrı bir
       `coverage` alanında raporlanır; `coverage < min_coverage` olan kampanya
       `comparable=False` işaretlenir ve listenin sonuna alınır (CLAUDE.md §17:
       uydurma sıralama yapma).

    Dönüş: skora göre azalan, kıyaslanamayanlar sonda.
    """
    rows = list(rows)
    w = dict(weights or DEFAULT_WEIGHTS)
    if not rows:
        return []

    # 1) Sayısallaştırma
    numeric: dict[str, list[Optional[float]]] = {}
    notes: dict[str, list[Optional[str]]] = {}
    for fname in w:
        col_v: list[Optional[float]] = []
        col_n: list[Optional[str]] = []
        for r in rows:
            raw = (r.get("fields") or {}).get(fname)
            num, note = _composite_numeric(fname, raw)
            # Süre kapısı: `rank()` ile aynı sıra (güvenden ÖNCE), aynı metin.
            # Kampanya düzeyinde bir gerçektir, bu yüzden o kampanyanın TÜM
            # alanlarını birden düşürür — bir alanı skorlayıp diğerini elemek,
            # kapanmış bir kampanyayı kısmen sıralamaya sokmak olurdu.
            durum_notu = _durum_notu(r.get("campaign_status"))
            if durum_notu is not None and num is not None:
                num, note = None, durum_notu
            # Baz kapısı: `rank()` ile aynı sıra (süreden sonra, güvenden
            # önce), aynı metin. Süre kapısının aksine yalnız BU alanı
            # düşürür — baz, kampanyanın değil tek bir oranın özelliğidir ve
            # yıllık ilan edilmiş bir oran yüzünden vadeyi de elemek,
            # ölçülmemiş bir kusur iddia etmek olurdu.
            baz_notu = _baz_notu(fname, (r.get("field_oran_bazi") or {}).get(fname))
            if baz_notu is not None and num is not None:
                num, note = None, baz_notu
            # Güven kapısı: `rank()` ile aynı eşik, aynı gerekçe metni.
            guven_notu = _guven_notu((r.get("field_confidence") or {}).get(fname))
            if guven_notu is not None and num is not None:
                num, note = None, guven_notu
            col_v.append(num)
            col_n.append(note)
        numeric[fname] = col_v
        notes[fname] = col_n

    # 3a) Popülasyonda hiç ölçülemeyen alanın ağırlığı dağıtılır
    active = {f: wt for f, wt in w.items() if any(v is not None for v in numeric[f])}
    total_active = sum(active.values())
    if total_active <= 0:
        return [CompositeScore(bank=r.get("bank"), bank_name=r.get("bank_name"),
                               campaign_id=r.get("campaign_id"), score=None,
                               coverage=0.0, comparable=False,
                               note=(_durum_notu(r.get("campaign_status"))
                                     or "hiçbir ölçüt ölçülemedi"),
                               components=[],
                               campaign_status=r.get("campaign_status"),
                               kaynak=r.get("kaynak") or "kampanya")
                for r in rows]

    # 2) Alan içi sıralama normalizasyonu
    normalized: dict[str, list[Optional[float]]] = {}
    for fname in active:
        idx = [i for i, v in enumerate(numeric[fname]) if v is not None]
        vals = [numeric[fname][i] for i in idx]
        lower = fname in _LOWER_IS_BETTER
        scores = _rank_normalize(vals, lower_is_better=lower)
        col: list[Optional[float]] = [None] * len(rows)
        for pos, i in enumerate(idx):
            col[i] = scores[pos]
        normalized[fname] = col

    # 4) Ağırlıklı toplama + kapsama
    out: list[CompositeScore] = []
    for i, r in enumerate(rows):
        components: list[ScoreComponent] = []
        covered_w = 0.0
        total = 0.0
        for fname, wt in active.items():
            nv = normalized[fname][i]
            contribution = (nv or 0.0) * wt if nv is not None else 0.0
            if nv is not None:
                covered_w += wt
                total += contribution
            components.append(ScoreComponent(
                field_name=fname,
                value=(r.get("fields") or {}).get(fname),
                normalized=nv,
                weight=wt,
                contribution=contribution,
                note=notes[fname][i],
            ))
        coverage = covered_w / total_active
        score = (total / covered_w) if covered_w > 0 else None
        comparable = coverage >= min_coverage and score is not None
        # Süre kapısı bu kampanyanın alanlarını düşürmüşse, üst düzey not
        # bunu SÖYLEMELİ. Aksi halde kapanmış bir kampanya "ölçülebilen ölçüt
        # yok" diye görünürdü — çıkarımın başarısızlığı gibi okunan, yanlış
        # bir gerekçe. Kapı, kapsamayı düşüren diğer sebeplerin önüne geçer:
        # süresi dolmuş bir kampanyada eksik veri artık ikincil bir sorundur.
        durum_notu = _durum_notu(r.get("campaign_status"))
        note = None
        if durum_notu is not None:
            comparable, note = False, durum_notu
        elif score is None:
            note = "ölçülebilen ölçüt yok"
        elif not comparable:
            note = (f"veri kapsaması düşük ({coverage:.0%}) — doğrudan "
                    f"kıyaslanamaz")
        components.sort(key=lambda c: -c.weight)
        out.append(CompositeScore(
            bank=r.get("bank"), bank_name=r.get("bank_name"),
            campaign_id=r.get("campaign_id"), score=score, coverage=coverage,
            comparable=comparable, note=note, components=components,
            campaign_status=r.get("campaign_status"),
            kaynak=r.get("kaynak") or "kampanya",
        ))

    ok = [c for c in out if c.comparable]
    rest = [c for c in out if not c.comparable]
    ok.sort(key=lambda c: (-(c.score or 0.0), -c.coverage))
    rest.sort(key=lambda c: (-(c.score or -1.0), -c.coverage))
    return ok + rest


def best_advantageous(rows: Iterable[dict],
                      weights: Optional[dict[str, float]] = None
                      ) -> Optional[CompositeScore]:
    """En avantajlı (kıyaslanabilir) kampanya; yoksa None."""
    for c in rank_advantageous(rows, weights=weights):
        if c.comparable:
            return c
    return None


# Bir türde bu sayıdan az kampanya varsa sıralama yapılmaz.
# Sıralama tabanlı normalizasyon 2 öğede dejenere olur (biri 1.0, biri 0.0)
# ve "en avantajlı" iddiası anlamsızlaşır — 2 kampanyadan birinin en iyi
# olduğunu söylemek bilgi taşımaz. Grup gizlenmez, sebebiyle raporlanır.
MIN_GROUP_SIZE = 3


def rank_advantageous_by_type(
    rows: Iterable[dict],
    weights: Optional[dict[str, float]] = None,
    min_coverage: float = MIN_COVERAGE,
    min_group_size: int = MIN_GROUP_SIZE,
) -> dict[str, dict[str, Any]]:
    """§5.7 "En Avantajlı Kampanya" — **kampanya türü İÇİNDE** sıralama.

    ## Neden tür içinde

    Şartnamenin kendi çalışılmış örneği (s.12–13) **aynı ürünü** karşılaştırıyor:
    A Bankası, B Bankası ve C Bankası'nın **konut finansmanı** kampanyaları,
    tek tabloda, banka başına bir satır. Türler arası karşılaştırma istenmiyor.

    Bunun ölçülmüş gerekçesi de var. 849 belgelik korpusta 495 skorlanabilir
    kampanya var ama alanlar türlere göre keskin ayrışıyor::

        Kart               114 kampanya —   3'ünde kâr payı var
        İhtiyaç Finansmanı 104 kampanya —   5'inde
        Alışveriş Puanı     13 kampanya —   0'ında
        Konut Finansmanı    72 kampanya —  11'inde

    Toplamda kampanyaların yalnızca **%9,5'inde** kâr payı oranı var. Türler
    arası tek listede kâr payına ne ağırlık verilirse verilsin, kampanyaların
    %90'ı için o ağırlık yeniden dağıtılır ve karşılaştırma bulanıklaşır.

    Daha temel sorun: bir **kredi kartı kampanyası** ile bir **konut
    finansmanı** birbirinin alternatifi değildir. "Hangisi daha avantajlı"
    sorusu bu ikisi arasında iyi tanımlı değildir. `CLAUDE.md` §17 zaten
    "yalnızca aynı birime normalize alanlar kıyaslanır" diyor; bu, o kuralın
    ürün ailesi düzeyine uygulanmış hâli.

    ## Normalizasyon nerede yapılıyor

    Sıralama tabanlı normalizasyon **grup içinde** koşar: her tür kendi
    popülasyonuna göre 0..1'e indirgenir. Bu kritiktir — konut finansmanı
    kampanyaları kart kampanyalarına göre normalize edilseydi, oranı olmayan
    114 kart kampanyası dağılımı bozardı.

    Dönüş: ``{tür: {"ranked": [...], "count": n, "note": str|None}}``.
    Küçük gruplar `ranked=[]` ve bir `note` ile döner — **gizlenmez**.
    """
    from collections import defaultdict

    gruplar: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        gruplar[(r.get("campaign_type") or BILINMEYEN_TUR)].append(r)

    out: dict[str, dict[str, Any]] = {}
    for tur, grup in sorted(gruplar.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if len(grup) < min_group_size:
            out[tur] = {
                "ranked": [], "count": len(grup),
                "note": (f"{len(grup)} kampanya — sıralama için en az "
                         f"{min_group_size} gerekiyor; bu türde 'en avantajlı' "
                         f"iddiası bilgi taşımaz."),
            }
            continue
        # Ağırlık AÇIKÇA verilmediyse TÜRE ÖZEL tablo kullanılıyor — gerekçe
        # `TUR_AGIRLIKLARI` başlığında. Çağıran `weights=` geçtiyse ona
        # dokunulmaz: dışarıdan verilen tablo bir denetim aracıdır ve tür
        # başına yeniden yazmak onu işlevsiz kılardı.
        out[tur] = {
            "ranked": rank_advantageous(grup,
                                        weights=weights or tur_agirliklari(tur),
                                        min_coverage=min_coverage),
            "count": len(grup),
            "note": None,
        }
    return out


def best_advantageous_by_type(
    rows: Iterable[dict],
    weights: Optional[dict[str, float]] = None,
) -> dict[str, Optional[CompositeScore]]:
    """Her kampanya türünün en avantajlısı; kıyaslanabilir yoksa None."""
    out: dict[str, Optional[CompositeScore]] = {}
    for tur, bilgi in rank_advantageous_by_type(rows, weights=weights).items():
        out[tur] = next((c for c in bilgi["ranked"] if c.comparable), None)
    return out


def weight_manifest(weights: Optional[dict[str, float]] = None) -> list[dict[str, Any]]:
    """Ağırlıkları gerekçeleriyle döndürür — API/dashboard bunu gösterir.

    Jüri "neden bu ağırlık" diye sorduğunda cevap kodun içinde gömülü kalmasın;
    `GET /compare/weights` gibi bir uçtan okunabilsin diye ayrı fonksiyon.
    """
    w = weights or DEFAULT_WEIGHTS
    return [{"field_name": f, "weight": wt,
             "rationale": WEIGHT_RATIONALE.get(f),
             "direction": "dusuk_iyi" if f in _LOWER_IS_BETTER else "yuksek_iyi"}
            for f, wt in sorted(w.items(), key=lambda kv: -kv[1])]


# --------------------------------------------------------------------------- #
# Banka içi delta — "bende ne eksik, rakipte ne var?"
# --------------------------------------------------------------------------- #
#
# Diğer fonksiyonlar müşterinin sorusunu ("hangi banka daha ucuz?") yanıtlar;
# bu blok BANKANIN sorusunu yanıtlar. Aynı çıkarım verisi, tersinden okunmuş.
#
# Delta aritmetiği ARAYÜZDE DEĞİL burada durur. Fark hesabı yönü bilmek
# zorundadır ("düşük iyi" alanda daha küçük değer avantajdır) ve bu bilgi
# `_LOWER_IS_BETTER` kümesinde yaşar. Aynı kararı istemcide ikinci kez
# uygulamak, bugün iki kez düzeltilen hatanın (`masraf_durumu` sıfır sayımı,
# aralık ucu seçimi) tam kalıbıdır: ilke bir yolda doğru, diğerinde eskimiş.

#: Delta durumları. `eksik_urun` ile `eksik_veri` BİLEREK ayrıdır — biri
#: bankanın o ürünü sunmadığını, diğeri çıkarımın alanı bulamadığını söyler ve
#: ikisini tek etikette toplamak, olmayan bir ürün eksikliği iddia etmektir.
DELTA_KINDS = (
    "eksik_urun", "eksik_veri", "daha_iyi", "daha_kotu",
    "esit", "kiyaslanamaz", "rakip_yok",
)


def delta_between(field_name: str,
                  mine_key: Optional[float],
                  rival_key: Optional[float],
                  mine_bazi: Optional[str] = None,
                  rival_bazi: Optional[str] = None
                  ) -> tuple[str, Optional[float], Optional[float]]:
    """İki sıralama anahtarı arasındaki farkı YÖNE ve BAZA göre yorumlar.

    Dönüş: ``(kind, abs_diff, rel_pct)``.

    Taraflardan biri sayıya indirgenemiyorsa (aralık, zaman-koşullu oran,
    farklı para birimi) fark **hesaplanmaz** ve `kiyaslanamaz` döner. Yaklaşık
    bir fark üretmek, CLAUDE.md §17'nin yasakladığı uydurma sıralamadır.

    `mine_bazi` / `rival_bazi` oranın bazıdır (`'aylik'` | `'yillik'` |
    `None`). İKİSİ DE biliniyor ve FARKLIYSA fark hesaplanmaz: aylık %1,89 ile
    yıllık %24,0 arasındaki "%1.170 daha iyi" cümlesi, birimi görmezden gelen
    bir aritmetiktir (bkz. "Baz kapısı" bloğu). Baz çevrilmez ve tarafların
    biri bilinmiyorsa **varsayılmaz** — kapı yalnız ölçülmüş bir farkta kapanır.

    Bu kontrol `rank()`in baz kapısıyla ÜST ÜSTE gelir ve bilerek öyledir:
    `/bank-delta` anahtarları `comparable` satırlardan alıyor, yani oradan
    zaten geçmiş olurlar; ama `delta_between()` doğrudan da çağrılabilen genel
    bir işlevdir ve tek başına da adil kalmalıdır.

    Kontrol ALAN BAĞIMSIZDIR — `rank()`inkinden geniştir. `rank()` alan başına
    kanonik bir baz okur (`KANONIK_ORAN_BAZI`) ve o sözlükte olmayan alanda
    çalışmaz; burada ölçülen tek şey ÇAĞIRANIN iki taraf için farklı birim
    bildirmiş olmasıdır. Bu bildirime rağmen fark üretmek hiçbir alanda doğru
    olmaz, reddetmek ise hiçbir alanda yanlış olmaz.

    Göreli fark rakibin değerine oranlanır ve rakip 0 ise **hesaplanmaz**:
    sıfıra bölme tanımsızdır ve 0 burada gerçek bir üründür ("masrafsız",
    "vade farksız"), eksik veri değil.
    """
    if mine_key is None or rival_key is None:
        return "kiyaslanamaz", None, None

    benim_baz = oran_bazi_dogrula(mine_bazi)
    rakip_baz = oran_bazi_dogrula(rival_bazi)
    if benim_baz is not None and rakip_baz is not None and benim_baz != rakip_baz:
        return "kiyaslanamaz", None, None

    fark = mine_key - rival_key
    if fark == 0:
        return "esit", 0.0, 0.0

    dusuk_iyi = field_name in _LOWER_IS_BETTER
    daha_iyi = fark < 0 if dusuk_iyi else fark > 0
    goreli = (None if rival_key == 0
              else abs(fark) / abs(rival_key) * 100)
    return ("daha_iyi" if daha_iyi else "daha_kotu"), abs(fark), goreli
