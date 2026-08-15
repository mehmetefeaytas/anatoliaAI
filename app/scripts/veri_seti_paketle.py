"""Yayına hazır veri seti paketi — iki gold seti + sızıntısız bölme + dataset card.

İlgili: scripts/veri_seti_paketi.py (TEK gold setini `dist/` altına paketleyen
            eski araç; hâlâ kullanılıyor, bu betik onun yerine geçmez)
        scripts/veri_seti_yukle.py (bu paketi Hugging Face'e yükleyen araç)
        data/gold/ANNOTATION_GUIDE.md (pakete kopyalanır)
        data/gold/GOLD-ROUND1-RECALL.md (kullanım sınırı bölümünün üslup emsali)
        tests/test_veri_seti_paketle.py

## Neden ikinci bir paketleyici

`veri_seti_paketi.py` **tek** bir gold setini alır ve `dist/` altına belge
metinleriyle birlikte yayar. Bu betiğin sorduğu soru farklı: dışarıdan biri bu
veriyle **model eğitecekse** neye ihtiyacı var? Üç şey:

1. **JSONL** — satır başına bir kayıt; akış hâlinde okunabilir, `datasets`
   kütüphanesinin varsayılan biçimi.
2. **Sızıntısız bölme** — `train`/`val`/`test`. Aynı belgeyi hem eğitimde hem
   testte gören bir bölme, ölçümü sessizce şişirir ve bunu kimse fark etmez.
3. **Dürüst bir künye (dataset card)** — bu setin nasıl üretildiğini ve neyin
   ölçülemeyeceğini yazan bir belge.

## Sızıntı neden burada gerçek bir risk — ölçüldü

`gold.round1` ile `gold.v2` **5 `source_url`'ü paylaşıyor** (aynı `id`, farklı
`content_hash` — sayfa iki hasat arasında değişmiş). İki seti birleştirip
naif olarak (kayıt düzeyinde) bölseydik, o beş belgenin bir kopyası eğitime,
diğer kopyası teste düşebilirdi: neredeyse aynı metin, neredeyse aynı etiket.
Bu yüzden bölme **belge düzeyindedir**: `source_url` ya da `content_hash`
paylaşan kayıtlar tek bir gruba çekilir (birleşim-bul), gruplar bölünür.

Kapı testtedir: `tests/test_veri_seti_paketle.py::Sizinti`.

## Ham HTML neden yok

`app/.gitignore`'daki gerekçe aynen geçerlidir: ham HTML cache'i 366 MB
(`data/raw` toplamı 417 MB) ve bankaların sayfa şablonunu bire bir yeniden
dağıtmak veri setinin amacı değil. Pakete
**çıkarılmış metin** (`text`) ve **provenance alanları** (`source_url`,
`content_hash`) girer. Bu, "bu bilgiyi nereden aldınız" sorusunu cevaplamaya
yeter (`docs/legal_notes.md` §3.1).

## Çıktı dizini neden `.gitignore`'da

Paket türetilmiş veridir: `data/gold/*.json`'dan tek komutla yeniden üretilir
ve ~4 MB tutar. Her yeniden üretim git geçmişine yeni bir kopya eklerdi.
AMA `README.md` (dataset card) izlenir — gerekçe `.gitignore` girdisinde.

## Kullanım

    .venv/bin/python -m scripts.veri_seti_paketle
    .venv/bin/python -m scripts.veri_seti_paketle --cikti data/yayin/anatolia-ai-gold
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

VARSAYILAN_ROUND1 = "data/gold/gold.round1.json"
VARSAYILAN_V2 = "data/gold/gold.v2.json"
VARSAYILAN_CIKTI = "data/yayin/anatolia-ai-gold"
VARSAYILAN_KILAVUZ = "data/gold/ANNOTATION_GUIDE.md"

TOHUM = 42
ORANLAR = (0.70, 0.15, 0.15)
BOLME_ADLARI = ("train", "val", "test")

# Beklenen kayıt sayıları. Gold değişirse betik SESSİZCE farklı bir paket
# üretmemeli — kartın içindeki her sayı bu dosyalardan geliyor ve dışarıya
# yayımlanıyor. Uyuşmazlık uyarı basar, kapıyı testler kapatır.
BEKLENEN = {"gold.round1": 134, "gold.v2": 48}

# κ değerleri — kaynakları YANINDA yazılı. İkisi aynı şeyi ölçmüyor; kart
# bunu açıkça söylemek zorunda (bkz. `_kart` içindeki uyarı).
KAPPA = {
    "round0": {
        "deger": "0,302",
        "olcut": "Fleiss κ",
        "anotator": 4,
        "protokol": "v1",
        "hakemlik": "SONRASI",
        "rapor": "data/gold/iaa-raporu-round0-kalibrasyon-v1.md",
    },
    "round1": {
        "deger": "0,274",
        "olcut": "Cohen κ",
        "anotator": 2,
        "protokol": "v2",
        "hakemlik": "ÖNCESİ",
        "rapor": "data/gold/iaa_report_round1.md",
    },
}

# 12 alan + `campaign_type`. Adlar CLAUDE.md §9 ile birebir; kanonik biçimler
# ANNOTATION_GUIDE.md §4 ve `scripts/gold_schema.py`'den türetildi.
# `tests/test_veri_seti_paketle.py::Sema` bu listenin veriyle örtüştüğünü çitler.
# NOT: tip sütununda `|` KULLANILMAZ — markdown tablo hücresini böler.
# Birden çok biçim alan alanlarda ayraç olarak `·` kullanılıyor.
ALANLAR = (
    ("kar_payi_orani", "float · {min,max}",
     "yüzde işaretsiz ondalık (`%2,05` → `2.05`); aralıksa `{min,max}`"),
    ("finansman_tutari", "{value,currency}",
     "`{\"value\": 150000.0, \"currency\": \"TRY\"}` — binlik `.`, ondalık `,` çözülmüş"),
    ("vade_ay", "int", "ay cinsinden tam sayı (`1 yıl` → `12`)"),
    ("taksit_sayisi", "int", "taksit adedi, tam sayı"),
    ("tahsis_ucreti", "{value,currency} · float",
     "tutar ya da oransal ücret — **bu sette 0 pozitif örnek var** (bkz. Bilinen sınırlar)"),
    ("masraf_durumu", "{has_fee,amount}",
     "`masrafsız` → `{\"has_fee\": false, \"amount\": 0.0}`; negasyon yokluk DEĞİLDİR"),
    ("odul_miktari", "{value,currency}", "parasal ödül; puan/mil ise `alisveris_puani`"),
    ("indirim_orani", "float · {min,max}", "yüzde işaretsiz ondalık"),
    ("alisveris_puani", "{kind,value}",
     "`kind` ∈ {`points`, `tl`}; mil/puan gibi parasal olmayan ödüller burada"),
    ("kampanya_suresi", "str (ISO-8601)",
     "`YYYY-MM-DD` — aralık verilmişse **bitiş** tarihi alınır"),
    ("kampanya_kosullari", "list[str]",
     "belgede birebir geçen koşul cümleleri (serbest metin listesi)"),
    ("hedef_kitle", "list[str]",
     "kapalı etiket kümesinden çoklu seçim (aşağıda)"),
)
HEDEF_KITLE_ETIKETLERI = (
    "yeni_musteri", "mevcut_musteri", "maas_musterisi", "belirli_segment")
KAMPANYA_TURLERI = (
    "Finansman", "İhtiyaç Finansmanı", "Konut Finansmanı", "Taşıt Finansmanı",
    "Kart", "Alışveriş Puanı", "Yeni Müşteri", "Yatırım Ürünü")


def oku(yol: str) -> list[dict]:
    """Gold JSON dosyasını okur."""
    kayitlar = json.loads(Path(yol).read_text(encoding="utf-8"))
    if not isinstance(kayitlar, list):
        raise ValueError(f"{yol}: liste bekleniyordu, {type(kayitlar).__name__} geldi")
    return kayitlar


def jsonl_yaz(yol: Path, kayitlar: list[dict]) -> None:
    """Satır başına bir JSON nesnesi. `ensure_ascii=False` — Türkçe okunur kalsın."""
    yol.parent.mkdir(parents=True, exist_ok=True)
    with yol.open("w", encoding="utf-8", newline="\n") as h:
        for kayit in kayitlar:
            h.write(json.dumps(kayit, ensure_ascii=False, sort_keys=True) + "\n")


def _grup_anahtarlari(kayit: dict) -> list[str]:
    """Kaydı bir belgeye bağlayan anahtarlar.

    İkisi de kullanılır: `source_url` aynı sayfanın iki hasadını birleştirir,
    `content_hash` ise farklı URL altında duran aynı metni yakalar.
    """
    anahtarlar = []
    for alan in ("source_url", "content_hash"):
        deger = (kayit.get(alan) or "").strip()
        if deger:
            anahtarlar.append(f"{alan}={deger}")
    if not anahtarlar:
        # Anahtarsız kayıt kendi başına bir gruptur; `id` en son çare.
        anahtarlar.append(f"id={kayit.get('id')}")
    return anahtarlar


def grupla(kayitlar: list[dict]) -> list[list[int]]:
    """Belge düzeyinde gruplar — `source_url` ya da `content_hash` paylaşanlar birlikte.

    Birleşim-bul (union-find). Dönüş: kayıt indekslerinin listesi listesi,
    grup içinde ve gruplar arasında **kararlı** sırada (tohum bağımsız).
    """
    ebeveyn: dict[int, int] = {i: i for i in range(len(kayitlar))}

    def bul(x: int) -> int:
        while ebeveyn[x] != x:
            ebeveyn[x] = ebeveyn[ebeveyn[x]]
            x = ebeveyn[x]
        return x

    def birlestir(a: int, b: int) -> None:
        ka, kb = bul(a), bul(b)
        if ka != kb:
            ebeveyn[max(ka, kb)] = min(ka, kb)

    ilk_goren: dict[str, int] = {}
    for i, kayit in enumerate(kayitlar):
        for anahtar in _grup_anahtarlari(kayit):
            if anahtar in ilk_goren:
                birlestir(ilk_goren[anahtar], i)
            else:
                ilk_goren[anahtar] = i

    kovalar: dict[int, list[int]] = {}
    for i in range(len(kayitlar)):
        kovalar.setdefault(bul(i), []).append(i)
    # Kararlı sıra: grup içi indeks sırası, gruplar arası ilk indeks sırası.
    return [kovalar[k] for k in sorted(kovalar)]


def bol(kayitlar: list[dict], tohum: int = TOHUM,
        oranlar: tuple[float, float, float] = ORANLAR) -> dict[str, list[dict]]:
    """Belge düzeyinde 70/15/15 böler.

    Bölme **gruplar** üzerinde yapılır, kayıtlar üzerinde değil. Hedefler
    KAYIT sayısıyla ifade edilir (grup boyutları eşit değil), doldurma
    sırayla: train dolana kadar train, sonra val, kalan test.
    """
    gruplar = grupla(kayitlar)
    karisik = list(gruplar)
    random.Random(tohum).shuffle(karisik)

    toplam = len(kayitlar)
    train_hedef = round(toplam * oranlar[0])
    val_hedef = round(toplam * oranlar[1])

    bolmeler: dict[str, list[dict]] = {ad: [] for ad in BOLME_ADLARI}
    for grup in karisik:
        if len(bolmeler["train"]) < train_hedef:
            ad = "train"
        elif len(bolmeler["val"]) < val_hedef:
            ad = "val"
        else:
            ad = "test"
        for i in grup:
            kayit = dict(kayitlar[i])
            kayit["bolme"] = ad
            bolmeler[ad].append(kayit)
    return bolmeler


def sizinti_denetimi(bolmeler: dict[str, list[dict]]) -> list[str]:
    """Bölmeler arası belge sızıntısı arar. Boş liste = temiz.

    İki ayrı kapı: aynı `source_url` ve aynı `content_hash`. İkisi de ayrı
    ayrı raporlanır ki hangi eksende sızdığı görünsün.
    """
    ihlaller: list[str] = []
    adlar = list(bolmeler)
    for alan in ("source_url", "content_hash"):
        kumeler = {
            ad: {(k.get(alan) or "").strip()
                 for k in kayitlar if (k.get(alan) or "").strip()}
            for ad, kayitlar in bolmeler.items()
        }
        for i, a in enumerate(adlar):
            for b in adlar[i + 1:]:
                ortak = sorted(kumeler[a] & kumeler[b])
                for deger in ortak:
                    ihlaller.append(f"{alan} hem {a} hem {b} içinde: {deger}")
    return ihlaller


def _sayim(kayitlar: list[dict]) -> dict:
    """Bir gold setinin künye sayıları — hepsi veriden, hiçbiri elle."""
    return {
        "kayit": len(kayitlar),
        "zor": sum(1 for r in kayitlar if r.get("hard")),
        "hakemlenmis": sum(1 for r in kayitlar if r.get("adjudicated")),
        "absent": sum(len(r.get("absent_fields") or []) for r in kayitlar),
        "banka": len({r.get("bank_slug") for r in kayitlar if r.get("bank_slug")}),
        "belge": len({(r.get("source_url") or "").strip() for r in kayitlar}),
        "tur_etiketli": sum(1 for r in kayitlar if r.get("campaign_type")),
    }


def _alan_tablosu(hepsi: list[dict]) -> str:
    dolu, yok = Counter(), Counter()
    for r in hepsi:
        dolu.update((r.get("fields") or {}).keys())
        yok.update(r.get("absent_fields") or [])
    satirlar = [
        "| Alan | Tip | Kanonik biçim | Dolu | `absent` |",
        "|---|---|---|---:|---:|",
    ]
    for ad, tip, bicim in ALANLAR:
        satirlar.append(f"| `{ad}` | `{tip}` | {bicim} | {dolu[ad]} | {yok[ad]} |")
    return "\n".join(satirlar)


def _kart(round1: list[dict], v2: list[dict],
          bolmeler: dict[str, list[dict]], ihlaller: list[str]) -> str:
    """Dataset card. Her sayı veriden hesaplanır; κ'lar rapor dosyalarından alınır."""
    s1, s2 = _sayim(round1), _sayim(v2)
    hepsi = round1 + v2
    grup_sayisi = len(grupla(hepsi))
    tarih = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    k0, k1 = KAPPA["round0"], KAPPA["round1"]

    # Yüzdeler Türkçe ondalık ayracıyla — belgenin geri kalanı da öyle
    # (`0,302`, `%2,05`). Tek bir `69.8%` tutarsızlık olurdu.
    def _yuzde(pay: int) -> str:
        return f"%{100 * pay / len(hepsi):.1f}".replace(".", ",")

    bolme_satirlari = "\n".join(
        f"| `{ad}.jsonl` | {len(bolmeler[ad])} | "
        f"{len({(r.get('source_url') or '') for r in bolmeler[ad]})} | "
        f"{_yuzde(len(bolmeler[ad]))} |"
        for ad in BOLME_ADLARI
    )
    tahsis_absent = sum(
        1 for r in hepsi if "tahsis_ucreti" in (r.get("absent_fields") or []))
    sizinti_satiri = (
        "**0 ihlal** — hiçbir `source_url` ve hiçbir `content_hash` iki bölmede birden yok."
        if not ihlaller else
        "⛔ **%d İHLAL** — bu paket yayımlanabilir değildir:\n\n%s" % (
            len(ihlaller), "\n".join(f"- {i}" for i in ihlaller[:20]))
    )

    # YAML künyesi Hugging Face'in şart koştuğu biçimdir; olmadan dataset
    # viewer açılmaz ve sayfa boş görünür. `configs` bölmeleri ADLARIYLA
    # bağlar — `train`/`val`/`test` dosyalarımız kök dizinde olduğu için
    # otomatik keşif çalışmaz.
    #
    # `license: apache-2.0` deponun LİSANSIDIR; kaynak sayfaların telif
    # durumu ayrıdır ve `LISANS.md` içinde ayrıca yazılıdır. İkisini tek
    # satıra sıkıştırmak yanıltıcı olurdu.
    return f"""---
language:
  - tr
license: apache-2.0
pretty_name: Katılım Bankacılığı Kampanya Metinleri Altın Seti
size_categories:
  - n<1K
task_categories:
  - token-classification
  - text-classification
tags:
  - turkish
  - finance
  - participation-banking
  - islamic-finance
  - information-extraction
  - teknofest
configs:
  - config_name: default
    data_files:
      - split: train
        path: train.jsonl
      - split: validation
        path: val.jsonl
      - split: test
        path: test.jsonl
  - config_name: gold_round1
    data_files:
      - split: train
        path: gold.round1.jsonl
  - config_name: gold_v2
    data_files:
      - split: train
        path: gold.v2.jsonl
---

# Anatolia AI — Katılım Bankacılığı Kampanya Metinleri Altın Seti

**Paket tarihi:** {tarih} · **Lisans:** Apache-2.0 (anotasyon katmanı) — bkz. `LISANS.md`
**Dil:** Türkçe · **Alan:** katılım bankacılığı (faizsiz finans) kampanya metinleri
**Görev:** belgeden yapılandırılmış finansal bilgi çıkarımı + kampanya türü sınıflandırması

> ⚠️ **Bu setler MAKİNE anotasyonludur ve insan hakemliğinden GEÇMEMİŞTİR.**
> Ayrıntı aşağıda "Kim etiketledi" bölümünde. Bunu manşetten önce yazıyoruz
> çünkü sonradan öğrenilmesi, veri setinin bütün iddiasını çürütür.

---

## İçerik

| Dosya | Kayıt | Ne |
|---|---:|---|
| `gold.round1.jsonl` | {s1['kayit']} | inceleme kuyruğundan gelen **geniş** örneklem |
| `gold.v2.jsonl` | {s2['kayit']} | kasten **zor** seçilmiş küçük set |
| `train.jsonl` | {len(bolmeler['train'])} | iki setin birleşiminden, belge düzeyinde bölme |
| `val.jsonl` | {len(bolmeler['val'])} | " |
| `test.jsonl` | {len(bolmeler['test'])} | " |
| `ANNOTATION_GUIDE.md` | — | anotasyon protokolü: kararların nasıl verildiği |
| `LISANS.md` | — | lisans + veri kökeni |

Biçim **JSONL**: her satır bir JSON nesnesi, bir kayıt. Ham HTML **yoktur**;
pakette çıkarılmış metin (`text`) ve provenance alanları (`source_url`,
`content_hash`) bulunur.

---

## Alan şeması — 12 alan + `campaign_type`

{_alan_tablosu(hepsi)}

`hedef_kitle` kapalı etiket kümesi: {" · ".join(f"`{e}`" for e in HEDEF_KITLE_ETIKETLERI)}.

**`campaign_type`** — 13. alan, 8 sınıflı kapalı küme:
{" · ".join(f"`{t}`" for t in KAMPANYA_TURLERI)}.
Etiketli kayıt: `gold.round1` {s1['tur_etiketli']}/{s1['kayit']} ·
`gold.v2` {s2['tur_etiketli']}/{s2['kayit']}. Etiketsiz kayıtta alan `null`'dur —
"tür yok" demek değil, **karara bağlanmadı** demektir.

### Kayıt yapısı

| Anahtar | Anlamı |
|---|---|
| `id` · `bank_slug` · `source_url` · `content_hash` | kimlik ve provenance |
| `text` | belgeden çıkarılmış düz metin (ham HTML değil) |
| `fields` | karara bağlanmış alanlar → kanonik değer |
| `field_spans` | her alanın belgedeki **birebir** kanıt alıntısı |
| `absent_fields` | "kontrol ettim, bu belgede YOK" kararı verilen alanlar |
| `campaign_type` · `hard` · `hard_tags` | tür etiketi ve zor-vaka işaretleri |
| `annotators` · `adjudicated` · `notes` | anotasyon künyesi |

---

## Protokol v2 — boş `verdict` ne demek

Her iki set de **protokol v2** ile etiketlendi. Tek cümlelik farkı şudur:

> **Boş `verdict` = KARAR VERİLMEDİ, metrik dışıdır.**

Öncülü olan protokol v1'de boş hücre `ok` (onay) sayılıyordu — yani anotatör
bir hücreye hiç dokunmadığında **modelin çıktısı onaylanmış** kabul ediliyordu.
Bu, etiketi modele çapalar ve ölçümü sistematik olarak iyimser yapar. v2 bunu
tersine çevirdi: dokunulmayan hücre ölçüme hiç girmez.

Bunun veri setindeki karşılığı üç durumlu bir ayrımdır ve **karıştırılmamalıdır**:

| Durum | Kayıttaki karşılığı | Anlamı |
|---|---|---|
| değer var | `fields[alan]` dolu | anotatör bir değere karar verdi |
| **`absent`** | alan `absent_fields` içinde | **kontrol ettim, belgede yok** |
| karar yok | alan hiçbirinde geçmiyor | bakılmadı — **metrik dışı** |

`absent` ile "karar yok" aynı şey değildir. **Halüsinasyon oranının paydası
`absent` kümesidir**: model, anotatörün "yok" dediği bir alana değer üretmişse
uydurmuştur. `absent` taşınmazsa bu oran dışarıdan yeniden üretilemez —
bu yüzden alan pakette birinci sınıf vatandaştır.

`absent` kararı: `gold.round1` **{s1['absent']}** hücre · `gold.v2` **{s2['absent']}** hücre.

---

## Anotatörler arası uyum (κ) — iki tur, AYRI AYRI

⛔ **Aşağıdaki iki sayı simetrik değildir ve toplanamaz, kıyaslanamaz.**

| Tur | Ölçüt | Değer | Anotatör | Protokol | Hakemlik | Rapor |
|---|---|---:|---:|---|---|---|
| **round0** | {k0['olcut']} | **{k0['deger']}** | {k0['anotator']} | {k0['protokol']} | **{k0['hakemlik']}** | `{k0['rapor']}` |
| **round1** | {k1['olcut']} | **{k1['deger']}** | {k1['anotator']} | {k1['protokol']} | **{k1['hakemlik']}** | `{k1['rapor']}` |

Asimetri **üç** eksende birden:

1. **Hakemlik konumu.** round0'ın {k0['deger']}'si hakemlik **sonrası** bir
   durumdur (0,051 → 0,268 → {k0['deger']} ilerlemesi kayıtlıdır); round1'in
   {k1['deger']}'ü hakemlik **öncesidir**. Round1'in hakemlik sonrası
   tutarlılığı 0,844'tür — ama bu **bağımsız uyum değildir** ve manşet olarak
   kullanılmaz.
2. **Ölçüt.** Fleiss κ çok-anotatörlü, Cohen κ iki-anotatörlüdür. Farklı
   tahmin ediciler; aynı ölçekte okunamazlar.
3. **Protokol.** round0 **v1** (boş = onay, modele çapalı), round1 **v2**
   (boş = karar yok). Payda bile aynı değil.

Bu yüzden "v1'de {k0['deger']} → v2'de {k1['deger']}, uyum düştü" **yanlış bir
cümledir**; aynı şekilde "uyum düzeliyor" da yanlıştır. İki bağımsız ölçümdür.

**Eşik anotasyon BAŞLAMADAN ilan edilmişti** (`ANNOTATION_GUIDE.md` §7):
κ ≥ 0,80 kabul · 0,67 ≤ κ < 0,80 notla kabul · κ < 0,67 zorunlu hakemlik +
kılavuz revizyonu. **Her iki tur da eşiğin altında kaldı** ve ilan edilen
sonuç uygulandı (kılavuz v1→v2 revize edildi, hakemlik koşuldu). Sayıya
bakıp eşik değiştirilmedi.

---

## Kim etiketledi — makine anotatör, makine hakem

⛔ **İNSAN HAKEMLİĞİ YAPILMADI.** Bu, setin en büyük kısıtıdır ve gizlenmez.

| Set | Anotatör | Hakemlik |
|---|---|---|
| `gold.round1` | **makine** (A–D), protokol v2 | 🟠 **makine kör hakem** — {s1['hakemlenmis']} kayıt `adjudicated: true` |
| `gold.v2` | **makine** (M1–M4), her değer birebir alıntı kanıtıyla | ❌ hakemlik yok ({s2['hakemlenmis']} kayıt `adjudicated: true`) |

`gold.round1`'deki **{s1['hakemlenmis']} kayıtlık hakemlik MAKİNE hakemliğidir.**
Uyuşmazlıklar, yalnız kendi alanının kılavuz paragrafını gören ve birbirinden
habersiz çalışan **kör** hakemlerce karara bağlandı. Protokol, hakemin
taraflardan biriyle **hem karar hem değer** olarak örtüşmesini şart koşar;
üçüncü bir cevap çıkarsa **hiçbir tarafa dokunulmaz**.

`adjudicated: true` bayrağı **"hakemlikten geçti"** der — **"insan onayladı"
demez.** Anotasyon kanıt kapılıydı (her değer belgede birebir geçen bir
alıntıya bağlı, programatik doğrulandı), ama **kanıt kapısı insan hakemliğinin
yerine geçmez**.

---

## İki set KIYASLANAMAZ — ve birleştirilerek sunulmaz

| | `gold.v2` | `gold.round1` |
|---|---:|---:|
| kayıt | {s2['kayit']} | {s1['kayit']} |
| **zor vaka** | **{s2['zor']}** | **{s1['zor']}** |
| `absent` kararı (halüsinasyon paydası) | **{s2['absent']}** | **{s1['absent']}** |
| banka | {s2['banka']} | {s1['banka']} |
| 12-alan mikro-F1 (referans sistem) | 0,464 | 0,744 |
| halüsinasyon oranı | **0,047** | **0,433** |

`gold.v2`'nin {s2['zor']}/{s2['kayit']} kaydı **kasten zor** seçilmiştir
(koşullu aralık, format varyantı, çelişki, terminoloji tuzağı).
`gold.round1` ise inceleme kuyruğundan gelen **geniş** bir örneklemdir.
İkisi aynı sistemi ölçer ama **aynı soruyu sormaz**.

**round1'in 0,433'lük halüsinasyonu bir gerileme değil, SEÇİM ETKİSİDİR.**
round1'de bir hücre inceleme kuyruğuna **zaten model bir şey ürettiği için**
girer; yani o setin `absent` kümesi rastgele değil, düşmanca seçilmiş bir alt
kümedir. Payda {s1['absent']}'a düşünce oran şişer. Aynı sebeple bu iki setin
F1'lerini yan yana koyup "hangi set daha kolay" demek de yanıltıcıdır.

---

## Bölme — sızıntısız, belge düzeyinde, `seed={TOHUM}`

İki setin **birleşimi** ({len(hepsi)} kayıt) bölünür. Bölme birimi kayıt değil
**belge**dir: `source_url` ya da `content_hash` paylaşan kayıtlar tek gruba
çekilir ve grup bölünmez. Toplam {grup_sayisi} grup.

Bu gerekli, çünkü iki set **{len(round1) + len(v2) - grup_sayisi} `source_url`'ü
paylaşıyor** (aynı sayfa, iki farklı hasat → farklı `content_hash`). Kayıt
düzeyinde bölseydik o belgenin bir kopyası eğitime, diğeri teste düşerdi.

| Bölme | Kayıt | Tekil belge | Oran |
|---|---:|---:|---:|
{bolme_satirlari}

Hedef oran {int(ORANLAR[0] * 100)}/{int(ORANLAR[1] * 100)}/{int(ORANLAR[2] * 100)};
gerçekleşen oran grup boyutları yüzünden birkaç kayıt sapabilir — grup
bölünmesindense sapma tercih edilir.

Her kayıtta iki alan bulunur: `bolme` (train/val/test) ve **`kaynak_set`**
(`gold.round1` / `gold.v2`). Kaynak seti açıkça taşıyoruz çünkü iki set
kıyaslanamaz ve karıştırmayı önleyen bilgi örtük kalmamalı; **iki set kıyaslanamaz olduğu için** bölmeleri tek
bir homojen küme gibi raporlamayın.

### Sızıntı denetimi

{sizinti_satiri}

Denetim `scripts/veri_seti_paketle.sizinti_denetimi` ile yapılır ve
`tests/test_veri_seti_paketle.py` içinde çitlenmiştir — hem sentetik bir
sızıntı vakasıyla (denetim yakalıyor mu) hem de gerçek paketle (sıfır ihlal).

---

## Kullanım sınırı — ne söylenebilir, ne söylenemez

| Söylenebilir | Söylenemez |
|---|---|
| "{len(hepsi)} kayıtlık, alan başına birebir kanıt alıntılı bir Türkçe katılım bankacılığı çıkarım seti" | ❌ "insan anotasyonlu altın set" |
| "`gold.round1`'de {s1['hakemlenmis']} kayıt kör hakemlikten geçti" | ❌ "hakemlik tamamlandı / uyuşmazlıklar çözüldü" |
| "κ round0 = {k0['deger']} (hakemlik sonrası), round1 = {k1['deger']} (hakemlik öncesi)" | ❌ tek bir κ vermek ya da ikisini kıyaslamak |
| "halüsinasyon `absent` paydasıyla ölçülür" | ❌ iki setin halüsinasyon oranını yan yana koymak |
| "manşet metrik `gold.v2`'de verilir — zor olan" | ❌ iki seti birleştirip tek bir F1 ilan etmek |
| "`train`/`val`/`test` belge düzeyinde ve sızıntısızdır" | ❌ "bu bölme üzerinde eğitilen model gold kalitesinde etiket öğrenir" |

**Bu set bir REFERANS setidir, eğitim seti olarak tasarlanmamıştır.** Üzerinde
eğitim yapılırsa, ölçüm o modelin **insanla** değil **başka bir makineyle**
ne kadar örtüştüğünü ölçer. Bu ayrım raporda korunmalıdır.

---

## Bilinen sınırlar — biz söylüyoruz

- **İnsan hakemliği yok** (yukarıda). Kapatılması gereken en öncelikli açık budur.
- **`tahsis_ucreti` ölçülemiyor.** Her iki sette de **0 pozitif örnek** var;
  bu alanda precision/recall/F1 **tanımsızdır**. Alan şemada duruyor çünkü
  `absent` kararları (birleşimde {tahsis_absent} hücre) halüsinasyon paydasına giriyor.
- **`kampanya_kosullari` span/jeton F1'i metodolojik olarak yanıltıcıdır.**
  Serbest cümle listesi döndüren bir alanda aynı koşulu farklı sözcüklerle
  yazan iki anotatör bile birbirini "yanlış" bulurdu. Kalem düzeyi ölçüt
  (jeton-Jaccard) kullanın.
- **`campaign_type` eksik.** `gold.round1`'de {s1['kayit'] - s1['tur_etiketli']},
  `gold.v2`'de {s2['kayit'] - s2['tur_etiketli']} kayıtta tür karara bağlanmadı.
- **Kaynak sayfalar değişir.** `content_hash` anotasyon anındaki metni çapalar;
  bugün aynı `source_url`'e gidildiğinde farklı içerik gelebilir. Nitekim iki
  setin paylaştığı 5 belgede tam olarak bu olmuştur.
- **Küme temsil edici değildir.** `gold.v2` kasten zor kürlenmiştir,
  `gold.round1` model çıktısı olan hücrelere göre süzülmüştür. Hiçbiri Türkçe
  bankacılık metinlerinin ortalama zorluğunu temsil etmez.

---

## Köken ve toplama

Metinler Türkiye'de faaliyet gösteren **{max(s1['banka'], s2['banka'])} katılım
bankasının kamuya açık** kampanya ve ürün sayfalarından toplandı. Toplama
robots.txt kurallarına uyularak, kimliğini beyan eden bir tarayıcıyla
(`AnatoliaAI-Research/1.0`) ve alan adı başına 3 saniye aralıkla yapıldı.
Giriş gerektiren hiçbir alan, **hiçbir kişisel veri** toplanmadı.

Her kayıtta `source_url` ve `content_hash` (sha256) bulunur: "bu bilgiyi
nereden aldınız" sorusunun cevabı kayıtlıdır. Ayrıntı: `docs/legal_notes.md`.

---

## Yeniden üretim

```bash
cd app
.venv/bin/python -m scripts.veri_seti_paketle
```

Paket `data/gold/gold.round1.json` ve `data/gold/gold.v2.json`'dan türetilir;
bölme `seed={TOHUM}` ile deterministiktir — aynı girdi aynı bölmeyi verir.
"""


def _lisans(round1: list[dict], v2: list[dict]) -> str:
    bankalar = sorted({r.get("bank_slug") for r in round1 + v2 if r.get("bank_slug")})
    return f"""# Lisans ve Veri Kökeni

## Anotasyon katmanı — Apache-2.0

Bu paketteki **anotasyon katmanı** (alan değerleri, kanıt alıntıları,
`absent` kararları, zor-vaka etiketleri, kampanya türü etiketleri, bölme
tanımı ve bu belgeler) Anatolia AI ekibinin ürünüdür ve **Apache License
2.0** altında paylaşılır. Tam metin: `LICENSE` (depo kökü).

    Copyright 2026 Anatolia AI

TEKNOFEST 2026 Türkçe Yapay Zekâ Dil Ajanları Yarışması — 2. Senaryo
(Bilişim Vadisi yürütücülüğünde) kapsamında üretilmiştir.

## Kaynak metinler — telif ilgili bankalara aittir

`text` alanındaki metinler Türkiye'de faaliyet gösteren katılım bankalarının
**kamuya açık** kampanya ve ürün sayfalarından derlenmiştir. Bu metinlerin
telif hakkı **ilgili kurumlara aittir**; pakette yalnızca **araştırma ve
değerlendirme** amacıyla, kaynağı gösterilerek yer alırlar.

Kaynak kurumlar (`bank_slug`): {" · ".join(f"`{b}`" for b in bankalar)}

## Ne yayımlanıyor, ne yayımlanmıyor

| Yayımlanıyor | Yayımlanmıyor |
|---|---|
| çıkarılmış düz metin (`text`) | **ham HTML** |
| `source_url` · `content_hash` (sha256) | site şablonu, CSS, betik, görsel |
| anotasyon katmanının tamamı | ücret tarifesi / bilgi formu PDF asılları |

**Ham HTML bilinçli olarak dışarıda bırakılmıştır.** Gerekçe `app/.gitignore`
içinde yazılıdır ve burada aynen geçerlidir: ham HTML cache'i **366 MB**
(`data/raw` toplamı 417 MB) ve bankaların sayfa şablonunu bire bir yeniden
dağıtmak bu veri setinin amacı değildir. Metin + URL + içerik özeti, kaydın
kaynağını doğrulamaya yeter.

## Toplama uyumu

- **robots.txt'e uyuldu.** `Disallow` uygulandı; `*` joker ve `$` çapası
  desteklenen kendi REP ayrıştırıcımızla (`src/scraping/robots.py`).
- **Kimlik beyan edildi:** `AnatoliaAI-Research/1.0 (+TEKNOFEST 2026;
  arastirma amacli)`.
- **Hız sınırı:** alan adı başına sabit 3,0 saniye. Yeniden deneme yok.
- **Kişisel veri yok.** Giriş gerektiren hiçbir alan taranmadı; toplanan şey
  bankanın zaten kamuya ilan ettiği pazarlama duyurusudur. KVKK anlamında
  işlenen veride kişisel veri bulunmamaktadır.

## Kapatılmamış kalemler — dürüst liste

`docs/legal_notes.md` §4, bugün **açık** olan kalemleri listeler. Bu veri
setini ilgilendiren ikisi:

1. **Kullanım koşulları (ToS) incelenmedi.** Yalnızca robots.txt ele alındı.
   robots.txt **teknik** bir izindir; telif ve kullanım koşulları **hukuki**
   izindir. İkisi aynı şey değildir ve biz bugün yalnızca birincisini
   karşıladığımızı iddia ediyoruz.
2. **Korpusun yeniden dağıtımı ayrıca değerlendirilmelidir** — telif, metnin
   kendisindedir. Anotasyon katmanının Apache-2.0 olması, kaynak metinlerin
   lisansını değiştirmez.

Ticari kullanım düşünüyorsanız bu iki kalem sizin tarafınızda kapatılmalıdır.

## Model ağırlıkları

Bu paket **model ağırlığı içermez**. Projede kullanılan ağırlıkların lisans
denetimi: `docs/model-license-audit.md` (yalnız Apache-2.0 ve MIT; Gemma ve
Llama community license altındaki modeller bilinçli olarak reddedilmiştir).

## Atıf

    Anatolia AI (2026). Katılım Bankacılığı Kampanya Metinleri Altın Seti.
    TEKNOFEST 2026 Türkçe Yapay Zekâ Dil Ajanları Yarışması — 2. Senaryo.
"""


def paketle(round1_yolu: str = VARSAYILAN_ROUND1, v2_yolu: str = VARSAYILAN_V2,
            cikti: str = VARSAYILAN_CIKTI, kilavuz: str = VARSAYILAN_KILAVUZ,
            tohum: int = TOHUM) -> dict:
    """Paketi üretir. Dönüş: özet sözlüğü (sayılar + sızıntı ihlalleri)."""
    round1, v2 = oku(round1_yolu), oku(v2_yolu)
    # Kaynak set AÇIK bir alan olarak taşınır. `annotators` üzerinden de
    # çıkarılabilir (M1–M4 = v2, A–D = round1) ama bu, indiren kişinin BİZİM
    # anotatör adlandırmamızı bilmesini gerektirir. İki set kıyaslanamaz
    # olduğu için, karıştırmayı önleyen bilgi örtük kalmamalı.
    for kayit in round1:
        kayit["kaynak_set"] = "gold.round1"
    for kayit in v2:
        kayit["kaynak_set"] = "gold.v2"
    hepsi = round1 + v2
    bolmeler = bol(hepsi, tohum=tohum)
    ihlaller = sizinti_denetimi(bolmeler)

    out = Path(cikti)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    jsonl_yaz(out / "gold.round1.jsonl", round1)
    jsonl_yaz(out / "gold.v2.jsonl", v2)
    for ad in BOLME_ADLARI:
        jsonl_yaz(out / f"{ad}.jsonl", bolmeler[ad])

    kilavuz_yolu = Path(kilavuz)
    if kilavuz_yolu.is_file():
        shutil.copy2(kilavuz_yolu, out / "ANNOTATION_GUIDE.md")

    (out / "LISANS.md").write_text(_lisans(round1, v2), encoding="utf-8")
    (out / "README.md").write_text(
        _kart(round1, v2, bolmeler, ihlaller), encoding="utf-8")

    return {
        "dizin": str(out),
        "round1": len(round1),
        "v2": len(v2),
        "grup": len(grupla(hepsi)),
        "bolme": {ad: len(bolmeler[ad]) for ad in BOLME_ADLARI},
        "ihlaller": ihlaller,
        "kilavuz": kilavuz_yolu.is_file(),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Yayına hazır veri seti paketi (JSONL + sızıntısız bölme + kart).")
    ap.add_argument("--round1", default=VARSAYILAN_ROUND1)
    ap.add_argument("--v2", default=VARSAYILAN_V2)
    ap.add_argument("--cikti", default=VARSAYILAN_CIKTI)
    ap.add_argument("--kilavuz", default=VARSAYILAN_KILAVUZ)
    ap.add_argument("--tohum", type=int, default=TOHUM)
    a = ap.parse_args(argv)

    ozet = paketle(a.round1, a.v2, a.cikti, a.kilavuz, a.tohum)

    print(f"paket        : {ozet['dizin']}")
    print(f"gold.round1  : {ozet['round1']}")
    print(f"gold.v2      : {ozet['v2']}")
    print(f"belge grubu  : {ozet['grup']}")
    for ad in BOLME_ADLARI:
        print(f"{ad:<13}: {ozet['bolme'][ad]}")
    if not ozet["kilavuz"]:
        print("UYARI: ANNOTATION_GUIDE.md bulunamadı, pakete konmadı.")
    for ad, beklenen in BEKLENEN.items():
        gercek = ozet["round1"] if ad == "gold.round1" else ozet["v2"]
        if gercek != beklenen:
            print(f"UYARI: {ad} {beklenen} kayıt bekleniyordu, {gercek} geldi — "
                  "dataset card'daki sayılar değişti, kartı gözden geçir.")

    if ozet["ihlaller"]:
        # Sızıntılı bir bölmeyi yayımlamak, üzerinde ölçülen her sayıyı
        # geçersiz kılar. Paket yine üretilir ki sorun görünsün, kapı kapanır.
        print(f"sızıntı      : {len(ozet['ihlaller'])} İHLAL")
        for satir in ozet["ihlaller"][:20]:
            print(f"  - {satir}")
        print("HATA: bölmeler arası belge sızıntısı var — yayımlamadan önce düzelt.")
        return 1
    print("sızıntı      : 0 (temiz)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
