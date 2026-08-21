"""Kıyas uçları — CEPHE: uç kayıtları + sıralama kapı çekirdeği.

`api/main.py`'den taşındı (19 Ağu 2026, kademeli bölmenin 4. adımı), ardından
807 satırdan bu cepheye + 7 modüle BÖLÜNDÜ (21 Ağu 2026). Gövdeler ve uç
docstring'leri BİREBİR taşındı; davranış değişikliği yok.

## Bölmenin ekseni: uç SÖZLEŞMESİ / uç GÖVDESİ / paylaşılan KATMAN

Dosya satır sayısına göre kesilmedi. Sınırlar sorumluluğa göre çizildi:

    kiyas.py                   CEPHE — 5 uç kaydı + sıralama kapı çekirdeği
    kiyas_alan_kiyasi.py       /compare       (tek alan, çok banka — denetim yüzeyi)
    kiyas_sartname_tablosu.py  /urun-tablosu  (kolon şeması — sıralama YOK)
    kiyas_banka_deltasi.py     /bank-delta    (aile × alan ızgarası, delta türü)
    kiyas_skor_aciklamasi.py   /scoring       (SÖZELLEŞTİRME — hesaplama YOK)
    kiyas_bilesik_skor.py      /advantageous  (alanlar ARASI ağırlıklı skor)
    kiyas_toplama.py           KATMAN — alan × kampanya toplama (3 uç paylaşır)
    kiyas_kanit_satiri.py      KATMAN — kanıtlı satır biçimleri (2 uç paylaşır)

Beş uç aynı veriyi paylaşıyor ama **beş farklı soruyu** yanıtlıyor (müşterinin
sorusu / şartnamenin tablosu / bankanın sorusu / "neden bu sıra?" / bileşik
skor); her uç kendi modülünde. İki karar ise gerçekten PAYLAŞILIYORDU ve
paylaşıldığı hâlde iki-üç yerde yazılıydı — onlar katman modülü oldu.

## Niçin sıralama çekirdeği CEPHEDE kaldı — üç denetim kapısı bu dosyayı adıyla sabitliyor

Bu, bölmeye direnen tek parça ve direnci gerçek. Üç kapı sıralama yolunu
`src/api/routers/kiyas.py` dosyasına ADIYLA bağlıyor:

1. **`tests/test_rank_girdi_paritesi.py::test_baska_cagiran_kalmadi`**
   `src/` altında `rank()` çağıran dosyaların KÜMESİNİ sabitliyor
   (`{kiyas.py, chatbot/structured.py}`). Çağrıyı yeni bir modüle taşımak
   kümeyi büyütür ve kapıyı düşürür — kapının amacı tam olarak bu: `rank()`
   çağıranlar SAYILABİLİR kalsın, çünkü her çağıran dört kapı alanını
   taşımak zorunda ve alanı taşımayan çağıran SESSİZCE ödüllendiriliyor.
2. **`...::test_compare_ucu_DENETLENIYOR`** bu dosyada EN AZ İKİ `rank()`
   girdi sözlüğü olmasını istiyor; denetim kapsamı sessizce daralırsa düşer.
3. **`tests/test_compare_ortak_kapilar.py`** `kiyas.tekil_banka_urun` ve
   `kiyas.yon_zorla`'yı uygulama KURULDUKTAN SONRA yamalıyor ve çağrıldığını
   sayıyor. Yani ortak kapı adları BU modülün global'lerinden, istek anında
   çözülmek zorunda. Çağrıyı başka modüle taşımak, yamanın hiç görülmemesine
   yol açar.

Üçünün ortak mesajı aynı: **sıralama kapılarının beslendiği yer tek ve
denetlenebilir olmalı.** Bu yüzden `siralanmis_satirlar` ve
`delta_siralamasi` burada; ama artık `router_kur`un içinde gömülü closure
değil, MODÜL DÜZEYİNDE saf fonksiyonlar — depoyu, closure'ları, isteği
tanımıyorlar. Bölmenin kazancı burada da var: çekirdek test edilebilir hâle
geldi.

## Bağımlılıkların ikiye ayrılması (`api/yardimcilar.py`'nin kuralı)

* **Durumlu → parametre.** `repo` ve dört closure yardımcısı (`field_rows`,
  `kiyas_kapsami`, `campaign_view`, `campaign_contradictions`) `main`de
  KALIYOR: `/chat`, `/extract`, `/contradictions*` ve `/campaigns/{id}/text`
  de onları kullanıyor. Cephe onları ilgili uç modülüne DAĞITIR — hangi ucun
  neye ihtiyacı olduğu artık `router_kur` gövdesinde tek bakışta okunuyor.
* **Saf → import.** `span_info`, `scoring_direction`, `_en_iyi_taraf` ve
  kıyas sabitleri `api/yardimcilar.py`'de; her modül ihtiyacını import eder.

## Taşımanın dört dersi (önceki adımlardan, tekrar edilmesin diye)

1. `from __future__ import annotations` yüzünden anotasyonlar dizedir ve
   FastAPI onları uç fonksiyonunun TANIMLANDIĞI modülün global'lerinden
   çözer. Uçlar artık kendi modüllerinde tanımlı, dolayısıyla `Optional` her
   uç modülünde import edilmek zorunda — biri eksik kalsa o uç 422 verirdi.
2. Uç fonksiyonunun docstring'i `/openapi.json`'un `description` alanıdır,
   yani KAMUYA açık sözleşme metni. Bu yüzden docstring gövdeyle birlikte
   taşındı ve uç fonksiyonu kendi modülünde TANIMLANIP buradaki router'a
   kaydediliyor: `description` yine FastAPI'nin kendi yolundan
   (`inspect.cleandoc(__doc__)`) üretiliyor, elle `description=` verilmiyor.
   `/openapi.json` birebir aynı kalıyor — ölçüldü.
3. Uçlar AYNI SIRAYLA kaydedilir (`/compare`, `/urun-tablosu`,
   `/bank-delta`, `/scoring`, `/advantageous`): `/openapi.json`'daki `paths`
   sözlüğünün anahtar sırası kayıt sırasıdır.
4. `app.routes` bir `include_router`'lı uygulamada uç yollarını LİSTELEMEZ.
   Uç sayısını ölçen her yer `app.openapi()["paths"]` kullanmak zorunda
   (`tests/test_api_gunluk.py`, `.github/workflows/ci.yml`).
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ...comparison.compare import RankRow, rank, tekil_banka_urun, yon_zorla
from ..yardimcilar import _ROW_TOKEN_SEP
from . import (
    kiyas_alan_kiyasi,
    kiyas_banka_deltasi,
    kiyas_bilesik_skor,
    kiyas_sartname_tablosu,
    kiyas_skor_aciklamasi,
)


# --------------------------------------------------------------------------- #
# Sıralama kapı çekirdeği — niçin bu dosyada kaldığı modül başlığında yazılı
# --------------------------------------------------------------------------- #
def siralanmis_satirlar(
    rows: list[dict],
    field: str,
    *,
    intent: Optional[str],
    per_bank: str,
    kapsam: list[dict],
) -> tuple[dict[tuple[Any, Any], dict], list[RankRow]]:
    """`/compare`'in sıralaması: `rank()` girdisi + üç ortak kapı.

    `(kaynak, ranked)` döner. `kaynak` `(campaign_id, source_span)` -> ham
    depo satırı eşlemesidir; sunum katmanı sıralama satırından kaynağa
    dönmek için onu kullanır.

    Girdi sözlüğü `compare.RANK_KAPI_ALANLARI`'nın TAMAMINI taşımak zorunda:
    kapılar eksik alanda **sessizce kapanır** ve alanı taşımayı unutan çağıran
    ödüllendirilir (test yeşil kalır, ekran yanlış sıralar). Bu tuzağa bu
    depoda ÜÇ kez düşüldü; `tests/test_rank_girdi_paritesi.py` bu sözlüğü AST
    üzerinden denetler ve denetim yalnız bu dosyayı okur.

    Ortak kapıların adları (`yon_zorla`, `tekil_banka_urun`) bilerek MODÜL
    global'lerinden çözülüyor: `tests/test_compare_ortak_kapilar.py` onları
    uygulama kurulduktan sonra yamalayıp çağrıldığını sayıyor.
    """
    # Satır kimliğini `bank` alanına gömen token hilesi KALDIRILDI.
    # Yazıldığında gerekliydi: `rank()` girdideki ek alanları `RankRow`a
    # taşımıyordu ve kaynak satıra dönmenin başka yolu yoktu. Artık
    # `campaign_id` ile `campaign_type` taşınıyor.
    #
    # Hile yalnız gereksiz değil, ENGELDİ: paylaşılan sunum kapısı
    # `tekil_banka_urun()` `(bank, campaign_type)` çiftine bakar; her
    # satırın `bank`ı benzersiz bir token olsaydı hiçbir şey tekilleşmez,
    # uç nokta da kuralı kendi gövdesinde ikinci kez yazmak zorunda
    # kalırdı — bu depoda beş kez pahalıya mal olmuş "aynı karar iki
    # yerde" hatası.
    kaynak: dict[tuple[Any, Any], dict] = {}
    rank_input: list[dict] = []
    for r in rows:
        # Anahtar (kampanya, kanıt penceresi): `query_fields()` bir alan
        # için kampanya başına tek kayıt döndürür (ölçüldü, data/demo.db:
        # 5455 satırda mükerrer (alan, kampanya) çifti YOK) ve pencere
        # aynı kampanyada bile ayırt edicidir. İlk kayıt kazanır.
        kaynak.setdefault((r["campaign_id"], r["source_span"]), r)
        rank_input.append({
            "bank": r["bank"],
            "bank_name": r["bank_name"],
            "canonical_value": r["canonical_value"],
            "source_span": r["source_span"],
            "campaign_id": r["campaign_id"],
            "campaign_type": r["campaign_type"],
            # Çıkarımın KENDİ güveni sıralamaya girer (`compare.rank()`
            # `ASGARI_GUVEN` kapısı). Alan taşınmazsa kapı sessizce
            # kapalı kalırdı ve tablo, çıkarıcının zaten zayıf
            # işaretlediği bir değeri "en düşük" diye basardı.
            "confidence": r.get("confidence"),
            # Kampanyanın geçerlilik damgası (`compare.rank()` süre
            # kapısı). Aynı gerekçe: alan taşınmazsa kapı sessizce kapalı
            # kalır ve kapanmış bir kampanya, bugün başvurulabilecek
            # tekliflerin ÜSTÜNDE görünür.
            "campaign_status": r.get("campaign_status"),
            # Ham değer (`compare.rank()` KOŞUL kapısı). Kapı, koşulun
            # orana bağlı olup olmadığını ham değerin kanıt penceresindeki
            # KONUMUNA bakarak anlar; alan taşınmazsa konum bilinemez ve
            # kapı sessizce kapalı kalır.
            #
            # ÖLÇÜLDÜ (2026-08-11): tam olarak bu oldu. Kapı eklendi,
            # testleri geçti, `rank()` doğrudan çağrıldığında çalıştı — ama
            # `/compare` yanıtında "Mobilden yeni müşterilere özel %0"
            # satırları hâlâ `comparable=True` dönüyordu. Yukarıdaki iki
            # yorum aynı tuzağı zaten iki kez anlatıyordu; üçüncüsü de
            # aynı biçimde düştü.
            "raw_value": r.get("raw_value"),
            # Oranın bazı (`compare.rank()` BAZ kapısı). Çıkarım katmanı
            # alanı henüz üretmiyor ve `.get()` `None` döndürüyor — kapı
            # o hâlde ateşlenmez, çünkü bilinmeyen baz varsayılmaz. Alan
            # buraya ŞİMDİDEN taşınıyor: yukarıdaki üç yorumun anlattığı
            # tuzak tam olarak "kapı eklendi, alan taşınmadı, kapı
            # sessizce kapalı kaldı" biçiminde üç kez tekrarlandı.
            "oran_bazi": r.get("oran_bazi"),
        })

    # Sıralama → istenen yön → banka × ürün ailesi başına tek satır.
    # Üçü de `comparison/compare.py`'nin ortak kapıları; chatbot'un yapısal
    # yolu (`chatbot/structured.py`) BİREBİR aynı çağrıları yapar ve
    # ayrışmayı `tests/test_chatbot_kiyas_paritesi.py` kilitler.
    ranked: list[RankRow] = yon_zorla(
        rank(rank_input, field, kapsam=kapsam), field, intent)
    if per_bank == "best":
        ranked = tekil_banka_urun(ranked)
    return kaynak, ranked


def delta_siralamasi(aile_satirlari: list[dict], alan: str) -> list[tuple]:
    """`/bank-delta`'nın sıralaması: `rank()` girdisi + token geri eşleme.

    `(kaynak_kayit, RankRow)` çiftlerini döndürür. Token hilesi TAMAMEN bu
    fonksiyonun içinde yaşıyor — gömülmesi ve sökülmesi yan yana duruyor,
    yani `_ROW_TOKEN_SEP` başka hiçbir dosyada geçmiyor.

    Dört kapı `/compare` ile aynı gerekçelerle beslenir; farkı, buradaki
    sözlüğün `bank` alanına satır indeksi gömmesi. Bu ikinci `rank()` çağrı
    yeri `tests/test_rank_girdi_paritesi.py::test_compare_ucu_DENETLENIYOR`
    tarafından ayrıca sayılıyor.
    """
    siralanmis = rank([
        {"bank": f"{i}{_ROW_TOKEN_SEP}{r['bank']}",
         "bank_name": r["bank_name"],
         "canonical_value": r["canonical_value"],
         "source_span": r["source_span"],
         # Güven kapısı burada da geçerli: delta paneli
         # `comparable` bayrağına bakıyor ve düşük güvenli bir
         # değerle fark hesaplamak, o farkı uydurmak olurdu.
         "confidence": r.get("confidence"),
         # Süre kapısı da geçerli, aynı gerekçeyle: kapanmış bir
         # kampanyayla "rakipten %10 daha iyisiniz" demek, artık
         # kimseye verilmeyen bir teklife dayanan bir iddiadır.
         "campaign_status": r.get("campaign_status"),
         # Koşul kapısı da geçerli: "mobilden yeni müşterilere
         # özel %0" ile hesaplanmış bir delta, herkesin
         # alamayacağı bir orana dayanan bir farktır.
         "raw_value": r.get("raw_value"),
         # Baz kapısı da geçerli: yıllık ilan edilmiş bir oranla
         # aylık bir orandan çıkarılan fark, birimi görmezden
         # gelen bir aritmetiktir.
         "oran_bazi": r.get("oran_bazi")}
        for i, r in enumerate(aile_satirlari)
    ], alan)

    # Sıralama satırını kaynak kayda geri bağla. Token'daki indeks
    # `aile_satirlari` içindeki konumdur (bkz. `_ROW_TOKEN_SEP`).
    return [
        (aile_satirlari[int(x.bank.split(_ROW_TOKEN_SEP, 1)[0])], x)
        for x in siralanmis
    ]


# --------------------------------------------------------------------------- #
# Cephe — uç kayıtları ve bağımlılık dağıtımı
# --------------------------------------------------------------------------- #
def router_kur(
    repo: Any,
    *,
    field_rows: Callable[..., list[dict]],
    kiyas_kapsami: Callable[..., list[dict]],
    campaign_view: Callable[[int], Optional[dict]],
    campaign_contradictions: Callable[..., list],
):
    """Kıyas uçlarını taşıyan `APIRouter`'ı kurar.

    İmza `main.py`'nin çağrısıyla BİREBİR aynı kaldı: bölme `main.py`'ye
    tek satır değişiklik getirmiyor. Gövde artık yalnız iki şey yapıyor —
    router'ı açmak ve her uç modülüne İHTİYACI OLAN bağımlılıkları vermek.
    Hangi ucun neyi kullandığı bu listeden okunuyor; eskiden hepsi tek bir
    closure kapsamında ortaklaşmıştı ve `/scoring`'in `/compare`'e bağlı
    olduğu ancak 570 satır aşağıda görülüyordu.

    `fastapi` import'u fonksiyon içinde: paket kurulu değilse
    `main.build_app()` zaten anlaşılır bir hata veriyor ve bu modülün
    import edilmesi tek başına çökmemeli (çekirdek kural/normalizasyon
    katmanı saf stdlib ile çalışır).
    """
    from fastapi import APIRouter

    r = APIRouter()

    # KAYIT SIRASI SÖZLEŞMEDİR: `/openapi.json`'daki `paths` anahtar sırası
    # buradan gelir (modül başlığı, 3. ders).
    compare = kiyas_alan_kiyasi.uc_ekle(
        r,
        field_rows=field_rows,
        kiyas_kapsami=kiyas_kapsami,
        campaign_view=campaign_view,
        campaign_contradictions=campaign_contradictions,
        siralanmis_satirlar=siralanmis_satirlar,
    )
    kiyas_sartname_tablosu.uc_ekle(
        r, field_rows=field_rows, kiyas_kapsami=kiyas_kapsami)
    kiyas_banka_deltasi.uc_ekle(
        r, repo,
        field_rows=field_rows,
        campaign_view=campaign_view,
        campaign_contradictions=campaign_contradictions,
        delta_siralamasi=delta_siralamasi,
    )
    # `/scoring` sıralamayı `/compare`'in KENDİSİNDEN alır — tek doğruluk
    # kaynağı. Bağımlılık burada AÇIKÇA bağlanıyor.
    kiyas_skor_aciklamasi.uc_ekle(r, compare=compare)
    kiyas_bilesik_skor.uc_ekle(r, field_rows=field_rows)

    return r
