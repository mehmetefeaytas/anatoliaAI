# API katmanının kademeli bölünmesi — bağımlılık matrisi ve plan

**Tarih:** 2026-08-19
**Tetikleyen:** değerlendirmede `api/main.py`'nin "kod yapısının modüler ve
okunabilir olması" maddesini ihlal ettiği işaretlendi.
**Durum:** 1.–3. adım uygulandı; kalan 3 adım aşağıda sıralı.

## Sorun — ölçülmüş hâli

```
src/api/main.py            2.505 satır
  └── build_app()          1.914 satır   (satır 586–2499)
        └── 32 uç nokta    hepsi closure üzerinden paylaşılan duruma bağlı
```

Bu, projenin geri kalanıyla çelişiyor: `extraction/`, `normalization/`,
`comparison/`, `db/` ayrı ayrı test edilebilir katmanlar, ama API tek dosyada.
Karşılaştırma için harici bir referans: benzer kapsamdaki bir rakip
uygulamanın `api/main.py`'si 797 satır — yani bu yalnız bizim iç
standardımıza göre değil, alanın pratiğine göre de büyük.

## Neden naif taşıma davranışı bozar

Uç noktalar `build_app()` içinde tanımlı çünkü closure üzerinden **10 paylaşılan
nesneye** erişiyorlar:

| Closure değişkeni | Ne | Kaç uç noktada |
|---|---|---|
| `repo` | depo (SQLite/Postgres) | 9 |
| `llm` | çıkarım LLM'i | 3 |
| `bot` | chatbot | 1 |
| `clf` | tür sınıflandırıcı | 1 |
| `gunluk_yazici` | denetim günlüğü | — (dolaylı) |
| `_view_cache`, `_contra_cache`, `_blok_cache`, `_cerceve_cache` | istek-arası önbellek | 1+ |
| `app` | FastAPI örneği | 32 |

Önbellekler kritik: modül seviyesine çıkarılırsa **süreç ömrü boyunca
paylaşılan** duruma dönüşürler ve test izolasyonu bozulur. Bu yüzden bölme,
önbellekleri `build_app()` kapsamında bırakıp router'lara **parametre olarak**
geçirmek zorundadır.

## Uç nokta bağımlılık matrisi

Ölçüldü (19 Ağu 2026). "satır" = uç noktanın kendi gövdesi, docstring dahil.

| Uç nokta | Satır | Closure bağımlılığı |
|---|---:|---|
| `/health` | 11 | repo, llm |
| `/banks` | 37 | repo |
| `/campaigns` | 68 | repo |
| `/search` | 78 | repo |
| `/stats` | 49 | repo, llm |
| `/fields` | 15 | — |
| `/campaigns/{id}/text` | 61 | — |
| `/compare` | 236 | — |
| `/urun-tablosu` | 93 | — |
| `/bank-delta` | 220 | repo |
| `/scoring` | 72 | — |
| `/advantageous` | 81 | — |
| `/chat` | 75 | repo, bot |
| `/zor-vakalar` | 5 | — |
| `/extract` | 121 | repo, llm, clf, `_view_cache` |
| `/refresh*` (5 uç) | 88 | repo (yalnız cancel) |
| `/summaries*` (5 uç) | 70 | — |
| `/log` | 68 | — |
| `/admin/*` (4 uç) | 20 | — |
| `/contradictions*` (2 uç) | 39 | repo |

Toplam 32 uç nokta. Yarıdan fazlası **hiç closure kullanmıyor** — yani
taşınmaları düşünüldüğü kadar riskli değil; asıl dikkat gerektiren tek uç
`/extract` (dört bağımlılık, önbellek dahil).

## Plan — sıra bilinçli

Sıra "en düşük dairesel-import riski" ilkesine göre kuruldu. Her adımda tam
test paketi (3.142 test) koşulur ve ayrı commit atılır; yarım kalan bir adım
bırakılmaz.

- [x] **1. Sunum sabitleri** → `api/sabitler.py`.
      Hiçbir şey import etmedikleri için dairesel bağımlılık riski sıfır.
      `FIELD_LABELS` taşındı (9 kullanım), ad `main`'de yeniden ihraç edildi
      çünkü `zor_vaka.liste()` onu `main.FIELD_LABELS` olarak okuyor.
- [x] **2. Katalog uçları** → `api/routers/katalog.py`. **UYGULANDI.**
      `/health`, `/banks`, `/campaigns`, `/search`, `/stats`, `/fields` —
      258 satır, bağımlılık yalnız `repo` + `llm`. Router bir **factory**
      olarak yazılır: `router_kur(repo, llm, *, otorite_sluglari) -> APIRouter`.
      `_otorite_kaynak_sluglari` ve `scoring_direction` taşınmadı, parametre
      geçildi — böylece `main` ↔ `routers` döngüsü hiç doğmadı.
      Sonuç: `build_app()` 1.914 → **1.668 satır**; router 321 satır.
      8 yeni test (`tests/test_api_router_katalog.py`) uçların artık
      `build_app()` kurmadan, sahte bağımlılıklarla sınanabildiğini kilitliyor.

      TAŞIMADA BİR KEZ KIRILDI — tekrarlanmasın: `Response` fonksiyon içine
      import edilince `GET /campaigns` her istekte **422** döndü.
      `from __future__ import annotations` tip anotasyonlarını dizeye çeviriyor
      ve FastAPI onları modül global'lerinden çözüyor; import fonksiyon içinde
      kalırsa `response: Response` çözülemiyor ve query parametresi sanılıyor.
      Aynı tuzak `main.py`'de daha önce yaşanıp yorumla işaretlenmişti; taşıma
      onu birebir tekrarladı. Kalan adımlarda `Response`/`Request` alan uçlar
      için önce modül-seviyesi import yazılacak.

      Ayrıca ölçüldü: FastAPI 0.141.1'de `include_router` ile eklenen uçlar
      `app.routes` listesinde GÖRÜNMÜYOR ama yönlendirme çalışıyor
      (TestClient ile 200 doğrulandı). Route sayısına bakarak "router
      bağlanmadı" sonucuna varmak yanlış olur.
- [x] **3. Arka plan işleri** → `api/routers/isler.py`. **UYGULANDI.**
      `/refresh*` + `/summaries*` (10 uç, 158 satır). Closure bağımlılığı
      neredeyse yok (`repo` yalnız 1 uçta); yöneticiler parametre geçildi.
      Sonuç: `build_app()` 1.668 → **1.533 satır**; router 238 satır.

      TAŞIMADA ÜÇ ŞEY ÖĞRENİLDİ — kalan adımlarda tekrarlanmasın:

      1. **Silinen blokta yalnız uç noktalar yoktu.** `ozet_isi =
         OzetYoneticisi(...)` ve `app.state.ozet_isi = ...` atamaları uçların
         ARASINDA duruyordu; naif kesme onları da götürdü ve `build_app()`
         `NameError` verdi. Kesmeden önce blok içindeki ATAMALAR taranmalı.
      2. **`app.state` bir TEST KANCASI.** Yöneticilere gövdeler
         `app.state.tazeleme` / `app.state.ozet_isi` üzerinden erişiyor ve
         kodda gerekçesi yazılı ("testler sahte bir iş geçirebilsin diye").
         Doğrudan parametreye çevirmek o kancayı kırardı; bu yüzden router
         factory'ye `app` referansı geçildi.
      3. **`app.routes` ile uç saymak yanlış ölçüt.** `tests/
         test_api_gunluk.py` eylem uçlarını `app.routes` üzerinden dolaşıyordu
         ve router'a taşınan uçları GÖRMEDİ ("eylem ucu kaybolmuş") — oysa
         uçlar çalışıyordu. `app.openapi()["paths"]` her iki durumda da tam
         listeyi veriyor (ölçüldü: 32 uç) ve test ona çevrildi. Aynı hata CI
         kapısında da yaşanmıştı; ölçüt artık iki yerde de FastAPI'nin iç
         yapısından bağımsız.

      Ayrıca `RefreshReq` pydantic modeli `main.py`'den buraya taşındı (tek
      kullanıcısı bu grup) ve `Request`/`BaseModel` modül seviyesinde import
      edildi — 2. adımdaki 422 tuzağının tekrarı önlendi.
- [ ] **4. Kıyas uçları** → `api/routers/kiyas.py`.
      `/compare`, `/urun-tablosu`, `/bank-delta`, `/scoring`, `/advantageous`
      (702 satır — en büyük grup). `/compare` tek başına 236 satır; bu adım
      kendi içinde ikiye bölünebilir.
- [ ] **5. Ajan uçları** → `api/routers/ajan.py`.
      `/chat`, `/extract`, `/zor-vakalar`. `/extract` önbellek paylaşıyor,
      bu yüzden EN SONA bırakıldı.
- [ ] **6. Denetim/yönetim** → `api/routers/denetim.py`.
      `/log`, `/admin/*`, `/contradictions*`.

Adım 2–6 tamamlandığında `build_app()` yalnız kurulum + `include_router`
çağrılarından oluşur (tahmini 120–150 satır).

## Neden kademeli, tek seferde değil

1.914 satırı tek commit'te taşımak, 3.142 testin hangi adımda kırıldığını
belirsizleştirir. Kademeli bölmede her adım kendi testiyle doğrulanır ve
gerektiğinde tek commit geri alınır.

Bu belge, işin yarım kalması hâlinde bir sonraki turun sıfırdan analiz
yapmasını da önler: matris yukarıda, sıra yukarıda, gerekçe yukarıda.
