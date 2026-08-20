"""Kural tabanlı (deterministik) alan çıkarımı — CEPHE (façade).

İlgili kararlar:
- ../../decisions/ner-fine-tune-yerine-kural-few-shot.md  (kurallar birincil)
- ../../concepts/bilgi-cikarimi.md
- docs/rapor/extract-bolme-plani.md  (bu cepheye nasıl varıldığının planı)

## Bu dosya neden artık kısa

`extract.py` tek başına ~3.700 satırlık tek bir dosyaydı (12 alan
çıkarıcısı + tüm yardımcıları). 2026-08-20'de alan bazında modüllere
bölündü — sorumluluk haritası ve her sınırın gerekçesi `docs/rapor/
extract-bolme-plani.md`de ve her yeni modülün kendi başlığında yazılı.

Bu dosya artık İKİ ŞEYDEN sorumlu, üçüncüsünden DEĞİL:

  1. **Geriye dönük uyum cephesi.** `from src.extraction.rules.extract
     import extract_kar_payi, ...` biçimindeki HER mevcut çağrı yeri
     (30+ test dosyası + `scripts/`, `eval/`, `src/comparison/`,
     `src/extraction/reconcile.py`) değişmeden çalışmaya devam etmeli.
     Aşağıdaki içe aktarmalar bu yüzden `as isim` biçiminde: bu, ruff'a
     (F401) ve okuyucuya "bu bilerek yeniden ihraç ediliyor" sinyalini
     verir — aksi halde "kullanılmayan import" göründüğü için birileri
     silmeye kalkabilir ve geriye dönük uyum sessizce kırılır.
  2. **Uzlaştırma mantığı (`extract_all`).** On iki alan çıkarıcısını
     hangi SIRAYLA çağıracağını, oran tablosunun ne zaman öncelikli ne
     zaman yedek olacağını (`_TABLO_YEDEK_ALANLARI`), tahsis ücretinin
     tabanını (`extract_tutar` çıktısı) nasıl bulacağını ve kabuk
     (komşu kampanya) süzgecini nerede uygulayacağını bilen TEK yer
     burasıdır. Bu mantık alan modüllerinin HİÇBİRİNE ait değil — birden
     çok alanı aynı anda görmesi gerekiyor, dolayısıyla doğal yeri
     cephenin kendisi.

Her çıkarıcı bir ExtractedField döndürür: canonical_value + confidence + source_span.
Bulamazsa alanı hiç üretmez (None döner) — boşluğu LLM katmanı doldurur.
Halüsinasyon yasağı: değer uydurma.
"""

from __future__ import annotations

from ...schemas import ExtractedField
from . import confidence as C
from ._ortak import _PARA_IFADESI as _PARA_IFADESI
from ._ortak import _truncate_at_next_column as _truncate_at_next_column
from .alisveris_puani import _PUAN_SAYI_RE as _PUAN_SAYI_RE
from .alisveris_puani import extract_alisveris_puani as extract_alisveris_puani
from .hedef_kitle import _gezinme_seridi as _gezinme_seridi
from .hedef_kitle import extract_hedef_kitle as extract_hedef_kitle
from .kabuk import kabuk_baslangici
from .kar_payi import extract_kar_payi as extract_kar_payi
from .kar_payi import paylasim_cifti_araliklari as paylasim_cifti_araliklari
from .kosullar import _kosul_degil as _kosul_degil
from .kosullar import _yalnizca_tarih_gecerliligi as _yalnizca_tarih_gecerliligi
from .kosullar import extract_dipnotlar as extract_dipnotlar
from .kosullar import extract_kampanya_kosullari as extract_kampanya_kosullari
from .masraf import extract_masraf as extract_masraf
from .odul_indirim import extract_indirim_orani as extract_indirim_orani
from .odul_indirim import extract_odul_miktari as extract_odul_miktari
from .tablo import _ORAN_TABLOSU_BASLIK_RE as _ORAN_TABLOSU_BASLIK_RE
from .tablo import RateRow as RateRow
from .tablo import extract_from_rate_table as extract_from_rate_table
from .tablo import parse_rate_table as parse_rate_table
from .tahsis_ucreti import extract_tahsis_ucreti as extract_tahsis_ucreti
from .tarih import extract_kampanya_suresi as extract_kampanya_suresi
from .tarih import kampanya_tarih_araligi as kampanya_tarih_araligi
from .tutar import extract_taksit as extract_taksit
from .tutar import extract_tutar as extract_tutar
from .vade import MAKS_VADE_AY as MAKS_VADE_AY
from .vade import extract_vade as extract_vade

# Oran tablosundan gelen ama tekil çıkarıcıya ÖNCELİK bırakan alanlar.
# Gerekçe `extract_all` içinde, uygulandığı yerde.
#
# `vade_ay` buraya 2026-08-12'de EKLENDİ — ölçüldü (gold.v2, 48 kayıt):
# tablodan gelen vade, tablonun kendi DİLİMİ olduğu için kampanyanın vadesi
# değildi ve `extract_vade`'nin doğru cevabını 0,95 güvenle eziyordu:
#
#   turkiye-finans avantaj  tablo "1-3 0,00% ..." -> 3    | extract_vade 36 ✓
#   albaraka TOGG           tablo max            -> 99   | extract_vade 48 ✓
#
# İkisinde de gold, `extract_vade`'nin değeriyle birebir uyuşuyor. Tablo
# satırındaki vade `RateRow` içinde KALIR (kâr payını vadeye bağlamak için
# gerekli), yalnız `vade_ay` ALANI olarak dışa verilmesi yedeğe düşer —
# `extract_vade` sustuğunda yine devreye girer, yani bilgi kaybı yok.
_TABLO_YEDEK_ALANLARI = frozenset(
    {"masraf_durumu", "vade_ay", "finansman_tutari"})

# Tüm kural çıkarıcılar — sırayla denenir.
_EXTRACTORS = [
    extract_kar_payi,
    extract_vade,
    extract_tutar,
    extract_taksit,
    extract_masraf,
    extract_tahsis_ucreti,
    extract_kampanya_suresi,
    extract_odul_miktari,
    extract_indirim_orani,
    extract_alisveris_puani,
    extract_hedef_kitle,
    extract_kampanya_kosullari,
]


def extract_all(text: str) -> list[ExtractedField]:
    """Metinden kural katmanının çıkarabildiği tüm alanları döndürür.

    Bulunamayan alanlar listelenmez (boşluk LLM'e bırakılır). Aynı alan birden
    çok kez yakalanırsa ilk (en yüksek güvenli) tutulur.
    """
    out: dict[str, ExtractedField] = {}
    # ORAN TABLOSU önce denenir: tablo varsa kâr payı/vade oradan gelir ve
    # tekil çıkarıcıların tablo gövdesinden yanlış değer devşirmesi engellenir
    # (tabloda onlarca sayı yan yana durur).
    tablo_yedek: dict[str, ExtractedField] = {}
    for f in extract_from_rate_table(text):
        if not f.is_present:
            continue
        if f.field_name in _TABLO_YEDEK_ALANLARI:
            tablo_yedek[f.field_name] = f
        else:
            out[f.field_name] = f

    # Oransal tahsis ücretinin TABANI belgenin finansman tutarıdır. İki alan
    # arasındaki bu bağ ancak burada — ikisi de görünürken — kurulabilir;
    # `extract_tahsis_ucreti` tek başına çağrıldığında tabanı bilmez ve
    # (doğru davranış olarak) hesap yapmaz.
    #
    # Taban MAKUL bir finansman tutarı olmak zorunda. Bu koruma olmadan ücret
    # tarifesi PDF'lerinde `extract_tutar`'ın yakaladığı çöp değerler
    # (0,27 TL / 1,04 TL / 2 TL) tabana geçiyor ve **0 TL tahsis ücreti**
    # üretiyordu — yani "ücretsiz" gibi görünen uydurma bir değer. Üç belgede
    # ölçüldü; makullük bandı (`confidence.PLAUSIBLE_RANGES`) üçünü de eler.
    tutar_alani = extract_tutar(text)
    taban = None
    if tutar_alani is not None and isinstance(tutar_alani.canonical_value, dict):
        aday = tutar_alani.canonical_value.get("value")
        alt, ust = C.PLAUSIBLE_RANGES["finansman_tutari"]
        if isinstance(aday, (int, float)) and alt <= aday <= ust:
            taban = float(aday)

    for fn in _EXTRACTORS:
        f = extract_tahsis_ucreti(text, taban) if fn is extract_tahsis_ucreti else fn(text)
        if f and f.is_present and f.field_name not in out:
            out[f.field_name] = f

    # Tablodan gelen YEDEK alanlar en sonda: tekil çıkarıcı sustuysa devreye
    # girerler. Ters sıra bilgi KAYBETTİRİRDİ — `extract_masraf` bu belgelerin
    # çoğunda TL tutarını da biliyor (`{"has_fee": true, "amount": 60}`),
    # tablodan gelen yedek ise yalnız "ücret var" diyebiliyor. Ölçüldü
    # (`data/demo.db`, 2026-08-09): 19 oran-tablolu belgenin 11'inde tekil
    # çıkarıcının değeri daha zengin, 8'inde hiç değer yok — yedek tam o
    # 8 belgede kazandırıyor.
    for ad, f in tablo_yedek.items():
        if ad not in out:
            out[ad] = f

    # TABLO HÜCRESİ TABLONUN TAMAMINI TEMSİL ETMEZ.
    #
    # `extract_vade` tetikleyiciye EN YAKIN sayıyı seçer ve oran tablosunun
    # başlığı "Vade" sözcüğüyle başladığı için en yakın sayı neredeyse her
    # zaman tablonun İLK SATIRIdır. Ölçülen hata (gold.v2 `kuveyt-turk--
    # kampanya-arsivi-kuveyt-turkten-avantajli-leasing-finansmani`):
    #
    #     "Vade TL Kar Oranı … 12 Ay 4.15 … 60 Ay 3.81"
    #     -> extract_vade 12 (ilk satır)          gold 60 (en uzun vade)
    #
    # Kılavuz ve `extract_from_rate_table` aynı sözleşmeyi paylaşıyor: tablodan
    # vade **en uzun** vadedir. Kapı bu yüzden ÇOK DAR: yalnız tekil
    # çıkarıcının değeri tablonun bir SATIR DEĞERİYSE (yani hücreden
    # devşirilmişse) ve tablo daha uzun bir vade biliyorsa tablo kazanır.
    #
    # ÇÜRÜTÜLEN ALTERNATİF (ölçüldü): `vade_ay`'ı `_TABLO_YEDEK_ALANLARI`dan
    # çıkarıp tabloyu KOŞULSUZ birincil yapmak. F1 0,800 -> 0,600 düştü, çünkü
    # iki belgede satır ayrıştırması vadeyi YANLIŞ okuyor ve doğru değer düz
    # metinde duruyor:
    #     albaraka TOGG        tablo 10  ("T10F" markasından)   metin 48  ✓
    #     turkiye-finans mobil tablo  3  (kolon kayması)        metin 36  ✓
    # Bu iki vaka dar kapıdan da GEÇMEZ: tablo maksimumu (10 / 3) tekil
    # çıkarıcının değerinden (48 / 36) küçük olduğu için kapı hiç açılmaz.
    tablo_vade = tablo_yedek.get("vade_ay")
    mevcut_vade = out.get("vade_ay")
    if (tablo_vade is not None and mevcut_vade is not None
            and mevcut_vade is not tablo_vade):
        satir_vadeleri = {r.vade_ay for r in parse_rate_table(text)}
        if (isinstance(mevcut_vade.canonical_value, int)
                and isinstance(tablo_vade.canonical_value, int)
                and mevcut_vade.canonical_value in satir_vadeleri
                and tablo_vade.canonical_value > mevcut_vade.canonical_value):
            out["vade_ay"] = tablo_vade

    # KABUK SÜZGECİ — kılavuz §4.13/8'in kod karşılığı. Tek noktada, çünkü
    # kural 12 alanın hepsi için aynıdır ve test edilecek tek bir sınır olmalı.
    # Değeri komşu kampanya listesinden devşiren alan bu belgeye ait değildir
    # (`src/extraction/rules/kabuk.py` — kuyruk kümesi tanımı).
    sinir = kabuk_baslangici(text)
    if sinir is not None:
        out = {ad: f for ad, f in out.items()
               if not (isinstance(f.span_start, int) and f.span_start >= sinir)}
    return list(out.values())
