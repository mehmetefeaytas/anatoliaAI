# API katmanının kademeli bölünmesi — bağımlılık matrisi ve plan

**Tarih:** 2026-08-19
**Tetikleyen:** değerlendirmede `api/main.py`'nin "kod yapısının modüler ve
okunabilir olması" maddesini ihlal ettiği işaretlendi.
**Durum:** 1.–5. adım uygulandı; kalan 1 adım aşağıda sıralı.
**Ölçülen ilerleme:** `main.py` 2.505 → **1.044 satır** (%58 küçüldü);
uç sayısı 32'de sabit, 3.150 test yeşil.

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
- [x] **4. Kıyas uçları** → `api/routers/kiyas.py`. **UYGULANDI.**
      `/compare`, `/urun-tablosu`, `/bank-delta`, `/scoring`, `/advantageous`
      (701 satır — en büyük grup). Sonuç: `main.py` 2.102 → **1.309 satır**;
      router 807 satır, yeni `api/yardimcilar.py` 147 satır. Beş uç TestClient
      ile 200 döndü, uç sayısı 32'de kaldı.

      **İkiye bölünmedi** — plan bunu öneriyordu ama `/scoring` gövdesinde
      `compare(field=field, type=type)` çağrısı var: sıralamayı tek doğruluk
      kaynağından alsın diye kendi tablosunu kurmuyor. İki modüle ayırmak o
      çağrıyı bir HTTP isteğine ya da üçüncü bir ortak katmana çevirmek
      demekti; ikisi de aynı kararı iki yerde yaşatırdı.

      **YENİ KARAR — durum parametre, saflık import.** Önceki adımlarda her
      bağımlılık factory PARAMETRESİ olarak geçiyordu. Bu adımda kıyas uçları
      altı durumsuz yardımcıyı birden kullanıyordu (`span_info`,
      `scoring_direction`, `_en_iyi_taraf`, `VALID_INTENTS`,
      `VALID_PER_BANK`, `_ROW_TOKEN_SEP`) ve altısını parametre yapmak imzayı
      şişirip her çağrı yerinde aynı altı satırı tekrar yazdırıyordu. Ayrım
      şöyle netleşti: **çalışma-anı duruma bağlı olan parametre
      (`repo`, önbellekli closure yardımcıları), saf olan import.** Saf
      yardımcılar `api/yardimcilar.py`'ye çıktı — `main`in ALTINA değil
      YANINA, çünkü `main` router'ları import ediyor ve ters yön dairesel
      bağımlılık kurardı. Adlar `main` yüzeyinde de görünür kalıyor
      (`tests/test_api_sozlesme.py` `main.span_info` üzerinden erişiyor).

      Dört closure yardımcısı (`_field_rows`, `_kiyas_kapsami`,
      `_campaign_view`, `_campaign_contradictions`) `main`de KALDI ve
      parametre geçildi: `/chat`, `/extract`, `/contradictions*` ve
      `/campaigns/{id}/text` de onları kullanıyor.

      **DÖRDÜNCÜ DERS — kaynak-kodu denetleyen testler taşımada kırılır ve
      biri kapsamı sessizce daraltıyordu.** Yedi test düştü; hiçbiri davranış
      kırılması değildi:

      * `test_rank_girdi_paritesi.py` `TARANAN` listesinden `main.py`'yi
        okuyordu. Yol güncellendi. Bu test kendini korumuş: yanındaki
        `test_baska_cagiran_kalmadi` `src/` ağacını tarayıp `rank()` çağıran
        modül kümesini `TARANAN` ile karşılaştırıyor, yani yol güncellenmezse
        kör kalmıyor DÜŞÜYOR.
      * `test_compare_ortak_kapilar.py` `api_main.tekil_banka_urun` /
        `api_main.yon_zorla` adlarını yamalayarak uçların ortak kapıyı
        gerçekten çağırdığını ölçüyordu. Adlar artık `routers/kiyas.py`
        global'lerinden çözülüyor; yama `api_main` üzerinde kalsaydı uç
        yamalanmamış gerçek fonksiyonu çağırır ve testler **sessizce yeşil**
        kalırdı — ölçmek istedikleri şeyi ölçmeden. Yama hedefi taşındı.
      * `test_api_celiski_source_url.py` yalnız `main.py`de
        `_campaign_contradictions(` çağrılarını sayıyordu (≥5 bekliyordu).
        Kusur burada YAPISALDI: her bölme adımı sayıyı düşürüyor, test
        kırılıyor, yol güncelleniyor ve **taşınmış çağrılar bir daha hiç
        denetlenmiyordu**. Kapsam `src/api/**/*.py` birleşimine çevrildi;
        artık bölmeden bağımsız.
- [x] **5. Ajan uçları** → `api/routers/ajan.py`. **UYGULANDI.**
      `/chat`, `/extract`, `/zor-vakalar` (149 satır). Sonuç: `main.py`
      1.309 → **1.044 satır**; router 269 satır. Üç uç gerçek istekle
      doğrulandı (`/extract` `kar_payi_orani=1,89` + `vade_ay=120` döndürdü,
      `/chat` `handler=structured`), uç sayısı 32'de kaldı.

      **Önbellek endişesi gerçekleşmedi.** Plan `/extract`i "önbellek
      paylaşıyor" diye en sona bırakmıştı; gövdesi okunduğunda görüldü ki
      `/extract` hiçbir önbelleğe dokunmuyor — girdi metni istekten geliyor ve
      çıkarım her seferinde yeniden koşuyor (canlı çıkarım ucunun anlamı bu).
      Paylaşılan tek şey `_kaynaklari_zenginlestir` (yalnız `/chat`) ve o da
      parametre geçildi.

      **Gövde şemaları zorunlu olarak taşındı.** `ChatReq`/`ExtractReq` ve
      `Request` `main`de bırakılamazdı: `from __future__ import annotations`
      yüzünden anotasyonlar dizedir ve FastAPI onları ROUTER modülünün
      global'lerinden çözer — `main`de kalsalardı iki uç da gövdeyi hiç
      okumadan 422 verirdi. `main` yalnız `BaseModel`i tutuyor, çünkü
      `build_app()` pydantic yokluğunu onun `None` olmasıyla raporluyor.
      `Response` de `main`de kaldı (`GET /campaigns` başlığı için).

      **BEŞİNCİ DERS — fonksiyonu taşırken OKUDUĞU sabitleri de taşı.**
      `_guvenlik_ozeti` ilk denemede `yardimcilar.py`'ye taşındı ama okuduğu
      `GUVENLIK_KAPILARI` ve `GATE_LABELS` `main`de kaldı; sonuç dört
      `F821 Undefined name`. Kapı sabitleri fonksiyonun parçasıdır (ikisi
      `chatbot/safety.py`'den ithal edilen kapı kimliklerini Türkçe etikete
      bağlıyor) ve ayırmak aynı kararı iki modüle bölmek olurdu. Sabitler de
      taşındı; `tests/test_chat_guvenlik_yuzeyi.py` de `api_main.X` yerine
      `yardimcilar.X` okuyacak biçimde güncellendi — fonksiyonu kaynağından
      çekmek, `main` üzerinden yeniden ihraç edilmiş bir ada bağlanmaktan
      dürüsttür (o dolaylılık taşımayı gizlerdi).
- [ ] **6. Denetim/yönetim** → `api/routers/denetim.py`.
      `/log`, `/admin/*`, `/contradictions*`.

Adım 6 tamamlandığında `build_app()` yalnız kurulum + `include_router`
çağrılarından oluşur (tahmini 120–150 satır).

## Neden kademeli, tek seferde değil

1.914 satırı tek commit'te taşımak, 3.142 testin hangi adımda kırıldığını
belirsizleştirir. Kademeli bölmede her adım kendi testiyle doğrulanır ve
gerektiğinde tek commit geri alınır.

Bu belge, işin yarım kalması hâlinde bir sonraki turun sıfırdan analiz
yapmasını da önler: matris yukarıda, sıra yukarıda, gerekçe yukarıda.
