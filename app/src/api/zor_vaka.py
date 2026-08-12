"""Zor vaka tezgâhı — altın kümedeki ZOR belgeleri servis eder ve model
çıktısını altın değerle KARŞILAŞTIRIR.

İlgili: ./main.py (`GET /zor-vakalar`, `POST /extract` içindeki `gold` bloğu)
        ../../web/app/components/ExtractLive.tsx (ekran)
        ../../scripts/gold_schema.py (`HARD_TAGS` — taksonominin tek kaynağı)
        ../../eval/matchers.py (`strict_match` / `tolerant_match`)
        CLAUDE.md §6 (zor anlama vakaları), §16 (değerlendirme), §11 (canlı yol)

## Bu modülün varlık sebebi — ölçülen kusur

"Canlı Çıkarım" ekranı 313 satırlık bir GELİŞTİRİCİ formuydu: bir metin kutusu,
aşağı akışta hiçbir karşılığı olmayan serbest bir banka etiketi ve dört ADET
ELLE YAZILMIŞ örnek metin (`ExtractLive.tsx:32-60`). O dört metin korpustan
gelmiyordu; yani ekran "sistem çalışıyor" diyordu ama "sistem GERÇEK ve ZOR
veride çalışıyor" demiyordu — üstelik iddianın doğruluğunu kontrol edecek bir
referans da yoktu. Kendi yazdığın metinden kendi çıkardığın değer, hiçbir şeyin
kanıtı değildir.

Oysa malzeme hazırdı ve hiçbir uç ona dokunmuyordu (ölçüldü: `grep gold
src/api/*.py` → sıfır): altın kümede **48 belge**, bunların **40'ı zor**
işaretli, gerçek korpus metniyle. Zor etiket dağılımı:

    format_varyant   25      kosullu_aralik   12      terminoloji   12
    eksik_bilgi       9      celiskili         4      (çok etiketli)

Her belge ayrıca ALTIN değerleri taşır (`fields`), her değerin metinde birebir
geçen bir alıntısını (`field_spans`), ve "anotatör baktı, bu belgede YOK"
kaydını (`absent_fields`). Yani ekranın sağ sütununu dolduracak referans zaten
vardı.

## Karşılaştırmayı neden SUNUCU yapıyor

Model çıktısıyla altın değeri eşleştirmek bir DOĞRULUK kararıdır ve bu projede
o kararın tek bir sahibi var: `eval/matchers.py`. Aynı kararı arayüzde ikinci
kez (TypeScript'te) yazmak, bu depoda altı kez tekrarlayan «aynı bilgi iki
yerde» kusurunu yeniden üretirdi — ve en kötü biçiminde: ekran, ölçüm
raporundan FARKLI bir "doğru" tanımı kullanırdı. Jüriye gösterilen tablo ile
rapordaki F1, sessizce ayrışırdı.

## Neden İKİ eşleştirme modu birlikte

`strict_match` kanonik biçimi birebir arar; `tolerant_match` sayıda %1 göreli
tolerans tanır, liste sırasını önemsemez ve altın bir ARALIKSA aralığın içine
düşen skalere kısmi kredi verir. Tek başına gevşek raporlamak "toleransı sonuç
iyi görünene kadar mı büyüttünüz" sorusunu davet eder; tek başına katı
raporlamak `1.8900000000000001` gibi biçim gürültüsünü gerçek hata sayar.
İkisini birlikte göstermek farkın kendisini bir bulguya çevirir: `esdeger`
sayısı "kaç hata anlam değil biçim hatası" sorusunun cevabıdır.

## Neden `fabricated` ayrı bir durum

`absent_fields` "anotatör kontrol etti, bu belgede YOK" demektir. Model orada
bir değer üretirse bu bir yanlış değer değil, bir UYDURMADIR — ve projenin
merkezindeki iddia (değer uydurmuyoruz) tam olarak bu sayıyla ayakta durur.
Ekranda ayrı bir kutu hak eder; ortalama bir "yanlış" sayacının içinde
kaybolmamalı.

Altın kümede hiç değerlendirilmemiş alan (ne `fields` ne `absent_fields`
içinde) `out_of_scope`'tur ve METRİK DIŞIDIR: orada model ne üretirse üretsin
doğru ya da yanlış diyemeyiz, çünkü referans yok. Boş bir hücreyi "uyuşmazlık"
gibi göstermek, olmayan bir hata icat etmek olurdu.
"""

from __future__ import annotations

import functools
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Optional

_KOK = Path(__file__).resolve().parents[2]
# `eval/` ve `scripts/` paket köküne göre çözülür. Aynı ekleme
# `eval/matchers.py` ve `scripts/gold_schema.py` başında da var; sunucu farklı
# bir çalışma dizininden ayağa kaldırıldığında (docker `WORKDIR`) bu satır
# olmadan eşleştiriciler bulunamaz ve karşılaştırma sessizce devre dışı kalırdı.
if str(_KOK) not in sys.path:
    sys.path.insert(0, str(_KOK))

from eval.matchers import strict_match, tolerant_match
from scripts.gold_schema import HARD_TAGS

#: Altın küme dosyası. Ortam değişkeniyle taşınabilir — ölçüm koşuları ve demo
#: aynı dosyayı göstermek zorunda değil.
GOLD_YOLU = os.environ.get("GOLD_PATH", str(_KOK / "data" / "gold" / "gold.v2.json"))

#: Zor etiketlerin kullanıcıya dönük Türkçe adı ve tek cümlelik tanımı.
#: Anahtarlar `scripts/gold_schema.HARD_TAGS` ile birebir aynı olmak ZORUNDA;
#: `etiket_ozeti()` bunu her çağrıda doğrular. Ham etiket (`format_varyant`)
#: jüriye hiçbir şey anlatmaz, açıklaması anlatır.
ETIKET_ADLARI: dict[str, tuple[str, str]] = {
    "terminoloji": (
        "Terminoloji",
        "Katılım bankacılığına özgü terim — kâr payı, katılma hesabı, "
        "murabaha, tahsis ücreti."),
    "format_varyant": (
        "Biçim varyantı",
        "Türkçe sayı, para ve tarih biçimleri: binlik ayracı nokta, ondalık "
        "ayracı virgül (1.500,00) ve noktalı tarih (31.12.2026)."),
    "eksik_bilgi": (
        "Eksik bilgi",
        "Sayı hiç verilmemiş, yalnızca niteleyici var (“avantajlı "
        "oranlarla”). Doğru davranış değer üretmemektir."),
    "celiskili": (
        "Çelişkili metin",
        "Belge kendi içinde çelişiyor — masrafsızlık iddiası ile tahsil "
        "edilen bir ücret aynı sayfada."),
    "kosullu_aralik": (
        "Koşullu / aralıklı",
        "Oran bir aralık ya da bir koşula bağlı: “%1,99 – %2,49”, "
        "“ilk 6 ay %0”. Tek sayıya indirmek bilgiyi bozar."),
    "tr_ortografi": (
        "Türkçe imla tuzağı",
        "İ/ı ayrımı, şapkalı harfler ve büyük harf blokları."),
}

#: Bir alanın altın küme karşısındaki durumu. Kimlikler İngilizce ve
#: SABİTTİR; Türkçe karşılıkları ekranda üretilir (`extractor`,
#: `confidence_source` alanlarıyla aynı desen).
DURUMLAR: tuple[str, ...] = (
    "match",            # katı eşleşme
    "equivalent",       # katı değil ama anlamca eşdeğer (tolerant)
    "mismatch",         # iki modda da eşleşmedi
    "missed",           # altında değer var, model bulamadı
    "fabricated",       # altında YOK, model değer üretti
    "correct_absence",  # altında YOK, model de üretmedi
    "unclear",          # anotatör karar veremedi — metrik dışı
    "out_of_scope",     # altın kümede bu alan hiç değerlendirilmedi
)

#: Önizleme uzunluğu — liste satırında belgeyi tanımaya yeter, metnin
#: tamamını iki kez göndermez.
ONIZLEME_SINIRI = 160


@functools.lru_cache(maxsize=4)
def _ham_kayitlar(yol: str) -> tuple[dict[str, Any], ...]:
    """Altın küme dosyasını BİR kez okur ve zor kayıtları döndürür.

    Dosya 311 KB; her istekte ayrıştırmak demonun her tıklamasına ölçülebilir
    bir gecikme eklerdi (CLAUDE.md §11 — demo donmamalı). Önbellek yola göre
    anahtarlanır, böylece testler farklı bir dosyayla koşabilir.

    Dosya YOKSA boş demet döner ve uç bunu açıkça söyler. Sahte bir vaka
    listesi üretmek, boş bir liste göstermekten kötüdür.
    """
    p = Path(yol)
    if not p.is_file():
        return ()
    veri = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(veri, dict):  # {"records": [...]} sarmalı da kabul
        veri = veri.get("records", [])
    if not isinstance(veri, list):
        return ()
    return tuple(k for k in veri if isinstance(k, dict))


def _zor(kayitlar: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    """Yalnız zor işaretli kayıtlar. Etiketi olan kayıt zordur."""
    return [k for k in kayitlar if k.get("hard") or k.get("hard_tags")]


def yukle(yol: Optional[str] = None) -> tuple[dict[str, Any], ...]:
    """Tüm altın kayıtlar (zor olmayanlar dâhil) — sayaçlar için."""
    return _ham_kayitlar(yol or GOLD_YOLU)


def kayit(vaka_id: str, yol: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Kimliğiyle tek bir zor vaka kaydı; bilinmiyorsa `None`."""
    for k in _zor(yukle(yol)):
        if k.get("id") == vaka_id:
            return k
    return None


def etiket_ozeti(yol: Optional[str] = None) -> list[dict[str, Any]]:
    """Zor etiketler + her birinin belge sayısı, taksonomi sırasında.

    Sıra `HARD_TAGS`'ten gelir, sayımdan değil: jüri arka arkaya iki kez
    baktığında çiplerin yer değiştirmemesi gerekir.
    """
    sayac: dict[str, int] = {}
    for k in _zor(yukle(yol)):
        for etiket in k.get("hard_tags") or []:
            sayac[etiket] = sayac.get(etiket, 0) + 1
    cikti = []
    for etiket in HARD_TAGS:
        ad, aciklama = ETIKET_ADLARI.get(etiket, (etiket, ""))
        cikti.append({"etiket": etiket, "ad": ad, "aciklama": aciklama,
                      "adet": sayac.get(etiket, 0)})
    # Taksonomide olmayan bir etiket (ör. eski `legacy`) sessizce yutulmaz.
    for etiket, adet in sorted(sayac.items()):
        if etiket not in HARD_TAGS:
            cikti.append({"etiket": etiket, "ad": etiket, "aciklama": "",
                          "adet": adet})
    return cikti


def _alan_satiri(ad: str, etiketler: Mapping[str, str]) -> dict[str, Any]:
    return {"field": ad, "label": etiketler.get(ad, ad)}


def vaka_ozeti(k: dict[str, Any], etiketler: Mapping[str, str],
               banka_adlari: Mapping[str, str]) -> dict[str, Any]:
    """Tek bir zor vakanın liste kaydı — metin dâhil.

    Metin listede TAŞINIR çünkü çıkarım isteği metni gövdede gönderir: ekran
    seçilen vakayı ikinci bir çağrıyla çekseydi, jüri her tıklamada bir ağ
    turu daha beklerdi. Kırk belgenin toplamı ~160 KB'dır ve tek seferde,
    sekme açılışında gelir.
    """
    slug = k.get("bank_slug") or ""
    metin = k.get("text") or ""
    altin = k.get("fields") or {}
    kanitlar = k.get("field_spans") or {}
    belirsiz = set(k.get("unclear_fields") or [])
    return {
        "id": k.get("id"),
        "banka": slug,
        "banka_adi": banka_adlari.get(slug, slug),
        "kaynak_adresi": k.get("source_url"),
        "kampanya_turu": k.get("campaign_type"),
        "zor_etiketler": list(k.get("hard_tags") or []),
        "metin": metin,
        "metin_uzunlugu": len(metin),
        "onizleme": (metin[:ONIZLEME_SINIRI].rstrip() + "…"
                     if len(metin) > ONIZLEME_SINIRI else metin),
        "altin_alan_sayisi": len(altin),
        "altinda_yok_sayisi": len(k.get("absent_fields") or []),
        "belirsiz_alanlar": [_alan_satiri(a, etiketler) for a in sorted(belirsiz)],
        "kanitli_alanlar": sorted(set(altin) & set(kanitlar)),
    }


def liste(etiketler: Mapping[str, str], banka_adlari: Mapping[str, str],
          yol: Optional[str] = None) -> dict[str, Any]:
    """`GET /zor-vakalar` gövdesi."""
    tum = yukle(yol)
    zorlar = _zor(tum)
    return {
        "kaynak_var": bool(tum),
        "toplam_belge": len(tum),
        "zor_belge": len(zorlar),
        "etiketler": etiket_ozeti(yol),
        "vakalar": [vaka_ozeti(k, etiketler, banka_adlari) for k in zorlar],
    }


def _durum(alan: str, altin_var: bool, altin_deger: Any,
           model_var: bool, model_deger: Any,
           yok_mu: bool, belirsiz_mi: bool) -> tuple[str, str]:
    """Bir alanın durumu + gerekçesi.

    Gerekçe eşleştiricinin kendi cümlesidir ("para birimi farklı: 'TRY' !=
    'USD'"); ekranda uyuşmazlığın YANINDA durur ki tartışma veriyle yapılsın.
    """
    if belirsiz_mi:
        return "unclear", "Anotatör karar veremedi; bu alan ölçüm dışında."
    if altin_var:
        if not model_var:
            return "missed", "Altın kümede değer var, model bu alanı üretmedi."
        kati = strict_match(alan, model_deger, altin_deger)
        if kati.ok:
            return "match", ""
        gevsek = tolerant_match(alan, model_deger, altin_deger)
        if gevsek.ok:
            return "equivalent", gevsek.reason or "Biçim farklı, anlam aynı."
        return "mismatch", kati.reason
    if yok_mu:
        if model_var:
            return "fabricated", "Altın kümede bu alan YOK; üretilen değer uydurmadır."
        return "correct_absence", "Altın kümede yok; model de üretmedi."
    return "out_of_scope", "Altın kümede bu alan değerlendirilmemiş."


def karsilastir(k: dict[str, Any], model_degerler: Mapping[str, Any],
                etiketler: Mapping[str, str], alan_sirasi: list[str],
                *, metin_ayni: bool) -> dict[str, Any]:
    """Model çıktısını altın değerlerle alan alan karşılaştırır.

    `model_degerler`: alan adı → kanonik değer (yalnız model'in ÜRETTİĞİ
    alanlar). Üretilmeyen alan sözlükte HİÇ bulunmaz — `None` değeriyle
    bulunmakla karıştırılmamalı, çünkü kural katmanı bilinçli olarak `null`
    üretebilir.
    """
    altin = k.get("fields") or {}
    kanitlar = k.get("field_spans") or {}
    yoklar = set(k.get("absent_fields") or [])
    belirsizler = set(k.get("unclear_fields") or [])

    # Anotatör NOTLARI (`notes`) bilinçli olarak DIŞARIDA bırakıldı. Değerli
    # bir kayıt ama iç yazışma dilinde: anotasyon kılavuzunun bölüm
    # numaralarına, ham alan adlarına (`alisveris_puani`) ve etiket
    # hashtag'lerine atıf yapıyor. Ekrana basılsaydı jüri, ürünün içinden
    # geliştirme notu sızdığını görürdü — `tests/test_ic_referans_sizmasi.py`
    # tam olarak bu sınıf sızıntı için var. Değerin dayanağı zaten
    # `field_spans` alıntısıyla gösteriliyor.
    satirlar = []
    sayac = dict.fromkeys(DURUMLAR, 0)
    for alan in alan_sirasi:
        altin_var = alan in altin
        model_var = alan in model_degerler
        durum, gerekce = _durum(
            alan, altin_var, altin.get(alan), model_var, model_degerler.get(alan),
            alan in yoklar, alan in belirsizler)
        sayac[durum] += 1
        satirlar.append({
            "field": alan,
            "label": etiketler.get(alan, alan),
            "gold_value": altin.get(alan) if altin_var else None,
            "gold_present": altin_var,
            "gold_absent": alan in yoklar,
            "gold_span": kanitlar.get(alan),
            "status": durum,
            "reason": gerekce,
        })

    return {
        "id": k.get("id"),
        "bank": k.get("bank_slug"),
        "source_url": k.get("source_url"),
        "campaign_type": k.get("campaign_type"),
        "hard_tags": list(k.get("hard_tags") or []),
        # Gönderilen metin altın belgenin metniyle aynı mı. Jüri metni elle
        # değiştirdiğinde karşılaştırma hâlâ çizilir ama artık aynı belgenin
        # ölçümü DEĞİLDİR ve ekran bunu söylemek zorundadır.
        "text_matches": metin_ayni,
        "fields": satirlar,
        "summary": sayac,
    }
