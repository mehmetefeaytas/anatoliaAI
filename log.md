# Anatolia AI — Günlük (Log)

Kronolojik ingest / değişiklik günlüğü. En yeni en üstte.

## [2026-08-25] doc | teslim-dokumanlari-yeni-veri-koluyla-tazelendi

Teslim dokümanları yeni veri koluyla eşitlendi (kod değişmedi):

- **README.md** — "Ölçülebilir Durum" tablosuna iki satır: yayımlanan finansman
  oranı (154 kayıt · 7 banka) ve katılma segment kırılımı (247 kayıt · 2 banka).
- **app/docs/PROJE-DOKUMANTASYONU.md** §3 — yeni alt bölüm *"Finansman
  oranları — bankaların kendi yayınları"*; katılma bölümüne Vakıf Katılım
  satırı, robots/elle indirme gerekçesi ve segment ayrımı eklendi; "bilinen
  boşluklar ②" iki bankaya güncellendi.
- **app/docs/sunum/anatolia-ai-sunum.html** — bayat sayılar tazelendi:
  %5,4 → **%6,1**, 146 → **164** belge, 7.032 → **7.049** alan.
- **Kanıt kapısı sapması kapatıldı:** PDF aslı sayısı üç belgede 999 yazıyordu,
  ölçülen değer **1.000** (`find data/raw -name '*.pdf' | wc -l`). README.md,
  app/README.md ve app/data/raw/README.md düzeltildi.

Kalan sapma (kapatılmadı, çünkü ölçüm koşumu gerektirir): `test_toplanan`
README'de 3.948, kapının ölçtüğü değer **4.027** — `python -m scripts.test_ozeti`
yeniden koşulmalı; aynı koşum `test_gecti` / `test_atlandi` kanıtlarını da
tazeler.

Dokunulan dosyalar: `README.md` · `app/README.md` · `app/data/raw/README.md` ·
`app/docs/PROJE-DOKUMANTASYONU.md` · `app/docs/sunum/anatolia-ai-sunum.html` ·
`sorun/kampanya-metninde-olmayan-oran-banka-yayinindan.md` (yeni) ·
`sources/teknofest/2026-08-25-yayimlanan-finansman-oranlari.md` (yeni) ·
`index.md` · `log.md`

## [2026-08-25] ingest + feature | yayimlanan-finansman-oranlari

Kampanya korpusunda `kar_payi_orani` belgelerin yalnız **%6,1'inde** (164 /
2.708) dolu ve şartname §5.7'nin birinci kıyas ölçütü tam bu alana dayanıyor.
Önce bunun bir çıkarım kusuru olup olmadığı ölçüldü — değildi
([[kampanya-metninde-olmayan-oran-banka-yayinindan]]):

- EVREN `llm-large`, 60 aday belge → **0 kabul**
- yerel `qwen2.5:7b`, 30 belge → **0 kabul** (24 Ağustos ölçümü)
- metnin kendisi: yakalanmayan yüzdelerin çoğu *gecikme kâr payı formülü*
  ("en yüksek cari kâr payı oranlarının %50 fazlası"), kampanyanın oranı değil

Bilgi o belgelerde yok; bankalar onu **hesaplama araçlarında** yayımlıyor.
Dört yeni adaptör yazıldı (`ZiraatKatilimAdapter`, `HayatFinansAdapter`,
`DunyaKatilimAdapter`, `TomKatilimAdapter`); finansman oranı taşıyan banka
sayısı **3 → 7**, toplam **154 kayıt** (Dünya 56 · Emlak 42 · Ziraat 31 ·
Albaraka 16 · Hayat Finans / Kuveyt Türk / T.O.M. 3'er).

**Kayıtlar `extracted_fields`e YAZILMIYOR.** Banka düzeyinde yayımlanmış bir
oranı belirli bir kampanyanın alanına yazmak, o belgenin söylemediğini ona
atfetmek olurdu; kapsama sayısı yalan söylemeye başlardı. Kaynak ayrı, etiket
ayrı, görünüm ayrı — [[katilma-orani-iki-ayri-buyukluk]] kararının aynısı.

**Vakıf Katılım segment oranları.** Banka oranı yalnız robots-engelli PDF'te
yayımlıyor (`/documents/` yolu `robots.txt`'te açıkça kapalı). Şartname §5.1
gereği PDF **elle** indirildi; `scripts/vakif_paylasim_pdf.py` yalnız yerel
dosyayı okuyor, ağa çıkmıyor. **103 kayıt · 13 segment · TRY/USD/EUR/XAU.**
Segment ayrımı gerçek: 250–99.999 TL → %85, 100.000+ → %90. Kuveyt Türk'ün 144
kaydıyla birlikte segment verisi artık **iki bankada**
([[merkezi-veri-segment-ayrimini-gizliyor]]).

**Üç yüzey:** `GET /finansman-oranlari` ucu, *Karşılaştırma* sekmesinde
dördüncü görünüm, sohbette `finansman_orani` yolu. Sohbette bu yol **yedek**,
ön alma değil: ilk denemede yapısal sorgudan önce koşuyordu ve dört testi
düşürdü (tek banka soruları, takip zinciri, güvenlik seti C03'ün yasakladığı
ikame). Doğru yer yapısal sorgunun sonrası — korpus bir şey bulduysa o kazanır,
çünkü kanıtı belgenin span'i.

**Yan bulgu — Türkçe İ.** `"TAŞIT".casefold()` "taşit" veriyor, "tasit" değil.
Ziraat Katılım ürün adlarını tamamen büyük harfle yayımladığı için bankanın
bütün taşıt ürünleri kampanya türü eşlemesinden sessizce düşüyordu.
`tr_fold_ascii()`e geçildi; Ziraat artık taşıt sıralamasının başında (%3,29).

Dokunulan dosyalar:
- `app/src/scraping/rates.py` — dört yeni adaptör
- `app/src/domain/yayimlanan_oran.py` — yeni
- `app/src/api/routers/finansman_orani.py` — yeni · `src/api/main.py`
- `app/src/chatbot/finansman_orani.py` — yeni · `bot.py` · `terim_cevabi.py`
- `app/web/app/components/FinansmanOranPanel.tsx` — yeni ·
  `ComparePanel.tsx` · `lib/api.ts`
- `app/scripts/vakif_paylasim_pdf.py` — yeni · `scripts/baslat.sh` (`.env`)
- `app/data/raw/<banka>/rates/quotes.jsonl` (4 yeni banka) ·
  `vakif-katilim/rates/vakif-paylasim-pdf.jsonl`
- `app/tests/test_yayimlanan_oran.py` · `test_rates_yeni_adaptorler.py` ·
  `test_vakif_paylasim_pdf.py`
- `sources/teknofest/2026-08-25-yayimlanan-finansman-oranlari.md` (yeni),
  `sorun/kampanya-metninde-olmayan-oran-banka-yayinindan.md` (yeni),
  `index.md`, `log.md`

## [2026-08-24] fix | panel-dort-ariza

Kullanıcı raporu dört arıza bildirdi; dördü de ölçüldü ve düzeltildi.

**1. Chatbot yanlış yola gidiyordu.** *"Katılım bankalarındaki kâr payı oranı
ne kadar"* RAG'a düşüyor ve uzak model kaynaksız bir paragraf üretiyordu
(*"kesin bir değeri vermek mümkün değil"*), oysa 9 bankanın TKBB oranı elimizde
duruyordu. `katilma_sorusu_mu` hesap izini ZORUNLU tutuyordu; soruda "hesap"
sözcüğü hiç geçmiyor. Kurum yolu eklendi (`_KURUM_IZI` + ürün izi YOKSA) ve
cevaba ayrım notu kondu: bu tablo katılma hesabının oranı, finansman ürününün
değil. Cevap 15,5 sn'lik belirsiz paragraftan anlık kaynaklı tabloya döndü.

**2. Çelişki Tespiti 47 sn sürüyor ve 500 dönüyordu.** Ayrıntı:
[[celiski-tespiti-yavasti-ve-500-donuyordu]]. Önbellek + kilit + kalıcı
artefakt; soğuk uç 47,9 sn → 0,001 sn, bulgu sayısı değişmedi (20).
21 Ağustos'ta aynı belirti "yanlış alarm" diye kapatılmıştı; o teşhis
düzeltildi.

**3. Banka sayfası paydaya sözleşme katıyordu.** Ayrıntı:
[[banka-sayfasi-paydaya-sozlesme-katiyordu]]. «93 belge · %15 kapsama»
cümlesinde 93 tüm belgeler, %15 ise 51 kampanya belgesi üzerindendi. Payda
kıyas evreniyle eşitlendi; çıkarılan sözleşme sayısı satırda yazılıyor.

**4. Katılma Oranları ayrı sekmeydi.** Karşılaştırma sekmesinin görünüm
anahtarına üçüncü seçenek olarak taşındı — sorduğu soru aynı, kaynağı farklı
ve fark seçeneğin adında yazıyor.

**Yan bulgu:** ekran çekimi koşumu canlı tazeleme tetiklemiş ve 72 ham dosyanın
provenance damgalarını silmişti; geri alındı ve tekrarı engellendi
([[ekran-cekimi-ham-veriyi-yeniden-topladi]]).

**Ölçülüp eklenmeyen:** yerel model (qwen2.5:7b) ile boşluk doldurma sondajı
30 belgede **0 kabul** verdi. İki kabul kapısı çalıştı; model kapılardan geçen
hiçbir aday üretemedi. EVREN anahtarı olmadan bu yol kapalı.

Dokunulan dosyalar: `src/chatbot/katilma_orani.py` · `src/api/routers/denetim.py`
· `src/api/main.py` · `src/comparison/celiski_artefakti.py` (yeni) ·
`scripts/celiski_tarama.py` (yeni) · `tests/test_celiski_artefakti.py` (yeni) ·
`web/app/components/{ComparePanel,BankaSayfasi}.tsx` · `web/app/page.tsx` ·
`docs-ekran/ekran_cek.py` · `sorun/` (3 yeni sayfa) · `index.md`

## [2026-08-24] feature | katilma-oranlari-panel-yuzeyi

Katılma oranları chatbot'ta cevaplanıyordu ama panelde hiç yoktu; senaryo
dashboard ile chatbot'u BİRLİKTE istiyor (CLAUDE.md §5) ve sohbette görünen
bir sıralamanın ekranda bulunamaması kapsam kaybıydı.

`GET /katilma-oranlari` ucu (`src/api/routers/katilma.py`) ve «Katılma
Oranları» sekmesi (`web/app/components/KatilmaPanel.tsx`) eklendi. İki
büyüklük panelde de ayrı tutuluyor: büyüklük bir SÜZGEÇ, kolon değil
([[katilma-orani-iki-ayri-buyukluk]]). Süzgeç seçenekleri veriden türetiliyor;
boş sonuç `veri_yok: true` ile "oran sıfır" değil "veri toplanmadı" olarak
gösteriliyor.

Tarayıcıda doğrulandı: sekme açıldı, tablo render edildi, oran TR biçiminde
(`%42,79`), vade her satırda yazılı.

**Tarihsel arşiv için trend analizi YAPILMADI** — CLAUDE.md §18 trend
analizini bilinçli olarak elemiş durumda (bütçe üç hedefe yığılıyor). Arşiv
kaynağı kırılgan olduğu için depoda duruyor.

Dokunulan dosyalar:
- `app/src/api/routers/katilma.py` — yeni
- `app/src/api/main.py` — router kaydı
- `app/web/app/components/KatilmaPanel.tsx` — yeni
- `app/web/app/page.tsx` — sekme, TabKey, soru kümesi eşlemesi
- `app/web/app/lib/api.ts` — `KatilmaOranlari` tipi + `katilmaOranlari()`
- `app/tests/test_api_katilma.py` (17 test)
- `sorun/katilma-hesabi-orani-korpusta-yoktu.md`,
  `sources/teknofest/2026-08-24-tkbb-kar-payi-veri-seti.md`,
  `entities/tkbb-kar-payi-veri-seti.md`, `log.md`

Ölçüm: **3.859 test / 0 hata / 53 atlanan** · web 224/224 · ruff temiz ·
`next build` başarılı · vault 0 kırık link.

## [2026-08-24] ingest + feature | tkbb-kar-payi-veri-seti

Kullanıcı raporu: *"Katılım hesabında en iyi kâr payı oranını hangi banka
veriyor"* cevaplanamıyordu. Kök neden bir çıkarım hatası DEĞİL — kampanya
korpusu katılma hesabı getirisini hiç yayınlamıyor; bankalar bu oranı haftalık
oran tablolarında duyuruyor ([[katilma-hesabi-orani-korpusta-yoktu]]).

TKBB'nin **iki ayrı** kâr payı ucu bulundu ve hasat edildi
([[tkbb-kar-payi-veri-seti]]):

- `karpayi.tkbb.org.tr` — 2012-01-02 → 2025-05-26, dört rapor, **210.474
  kayıt** (gzip 1,1 MB; düz hâli 89 MB). TLS sertifikası GEÇERSİZ, bu yüzden
  hasat `--sertifika-atla` bayrağını açıkça ister.
- `veri-petegi.tkbb.org.tr` — Turboard paneli, içinde bulunulan hafta, **245
  kayıt**. `X-CSRFToken` başlığı zorunlu.

**2026 tarihsel veri YOK**: arşiv Mayıs 2025'te duruyor ve form yıl listesi de
2025 ile bitiyor (iki bağımsız kanıt). Güncel uç haftalık olarak devam ediyor.

Üç bağımsız kaynak aynı değeri verdi (Albaraka TL paylaşımı 90/90/92/93): iki
uç + Albaraka'nın kendi PDF'i. Ayrıca sertifika doğrulanmadan alınan değerler
kullanıcının tarayıcısından gelenlerle **7/7 banka birebir** uyuştu.

Chatbot'a `katilma_orani` yolu eklendi; getiri ile pay ayrı sıralanıyor
([[katilma-orani-iki-ayri-buyukluk]]). Güncel sonuç (2026-08-24, TL): 1 ay
T.O.M. %42,79 · 6 ay Hayat Finans %41,28 · 12 ay Albaraka %40,85.

Dokunulan dosyalar:
- `app/scripts/tkbb_karpayi_hasat.py` — yeni (tarihsel, gzip)
- `app/scripts/tkbb_guncel_hasat.py` — yeni (güncel hafta)
- `app/src/chatbot/katilma_orani.py` — yeni
- `app/src/chatbot/bot.py` — `katilma_orani` handler'ı + `kaynak_var`
- `app/.gitignore` — düz tarihsel arşiv kalıbı
- `app/data/raw/<banka>/rates/tkbb-karpayi.jsonl.gz` (9) · `tkbb-guncel.jsonl` (9)
- `app/tests/test_chat_katilma_orani.py` (20) · `app/tests/test_tkbb_hasat.py` (20)
- `sources/teknofest/2026-08-24-tkbb-kar-payi-veri-seti.md`,
  `entities/tkbb-kar-payi-veri-seti.md`,
  `decisions/katilma-orani-iki-ayri-buyukluk.md`,
  `sorun/katilma-hesabi-orani-korpusta-yoktu.md`, `index.md`, `log.md`

Ölçüm: **3.842 test / 0 hata / 53 atlanan**, ruff temiz, jargon kapısı temiz
(ihlal 0, muaf 46), vault 0 kırık link.

## [2026-08-24] fix | terminoloji-yolu

Kullanıcı raporu: *"Murabaha ne demek"* → "Bu bilgi verimde yok."
**Oysa veri vardı** — `data/terminology/katilim-terim-sozlugu.json` 101 terim
için tam kayıt tutuyor (tanım, sade anlatım, resmî karşılık, karıştırılmamalı,
risk notu ve **kaynak**: Murabaha → AAOIFI Şer'i Standart No. 8).
`domain/terminology.py` bu sözlüğü çıkarım ve güvenlik katmanlarında zaten
kullanıyordu; yalnız chatbot cevap üretimi ona hiç bakmıyordu
([[terim-sorusuna-sozlukten-cevap-verilmiyordu]]).

`src/chatbot/terim_cevabi.py` yazıldı, `bot.py`'ye KATALOG seviyesinde
bağlandı (`handler="terminoloji"`). Doğrulandı: Murabaha ✓, Riba ✓, Muşaraka ✓
cevaplanıyor; *"Kuveyt Türk kâr payı oranı nedir"* doğru şekilde
`structured`'a gidiyor. Bu, `rag_eval`'in "müşaraka nedir → isabetsiz"
bulgusunu da açıklıyor: terim vardı, bakılmıyordu.

**Uzak model DEĞİL sözlük** — bilinçli: terim tanımını modele ürettirmek
kaynaksız bir iddia olurdu (§19). Sözlük AAOIFI/BDDK kaynağı taşıyor ve
`risk_notu` gibi alanlar hiçbir genel modelin üretemeyeceği kurum bilgisidir.

**İki tuzak ölçülerek bulundu:**

1. **Çıktı koruması sözlük tanımını bozuyordu.** `Riba` kaydının resmî Türkçe
   karşılığı **"Faiz"**tir (riba yasaklanan şeydir); `sanitize_output` onu
   "Kâr payı" yapıyor ve tanım TERSİNE dönüyordu. `guard_output(...,
   alinti=True)` eklendi — yalnız `handler == "terminoloji"` için, model
   çıktısı için asla.
2. **Terim yolu alan sorularını çalınca GÜVENLİK açığı doğuyordu.** "Bu
   üründe masraf durumu nedir, faiz uygulanır mı?" sorusu `nedir` kalıbıyla
   terim yoluna gidiyor, alıntı modu post-filter'ı atlıyor ve kaynaktaki
   yasak terim sızıyordu (`test_safety.py` yakaladı). `_ALAN_IZLERI` alan
   adlarıyla genişletildi; ayrım "oranı" sözcüğünde: "kâr payı ne demek"
   terim sorusudur, "kâr payı ORANI nedir" alan sorusudur.

**Kalan sınır:** "Finansman ne demek" hâlâ cevaplanmıyor — sözlük katılım
bankacılığına ÖZGÜ terimleri içeriyor, genel bankacılık terimlerini değil.
`tcmb-terimler.json` (314 terim, tanımlı, kaynak URL'li) kapsam dışında;
şeması farklı ve katılım bağlamında `degildir`/`risk_notu` karşılıkları yok.

Dokunulan dosyalar:

- `sorun/terim-sorusuna-sozlukten-cevap-verilmiyordu.md` — yeni
- `index.md` · `log.md`
- `app/src/chatbot/terim_cevabi.py` — yeni
- `app/src/chatbot/bot.py` — `terminoloji` handler, `alinti=True`
- `app/src/chatbot/safety.py` — `guard_output(..., alinti=...)`
- `app/tests/test_chat_terim_cevabi.py` — yeni, 13 test

Test durumu: **3.749 geçti · 53 atlandı · 0 hata** · ruff temiz.

## [2026-08-24] fix | kiyas-gosterim-hatalari-ve-urun-baglami

Kullanıcı raporundan çıkan **üç hata** teşhis edildi; ikisi düzeltildi, biri
kısmen (uyarı düzeyinde) kapatıldı. Üçünün de **EVREN'le ilgisi yoktu** —
kullanıcının "belki EVREN çözer" varsayımı ölçümle yanlışlandı.

**1. Vade `%120` olarak basılıyordu.** Bileşik "en avantajlı" cevabı satırları
BOYUT BOYUT topluyor (vade, masraf, ödül…) ama `RankRow` hangi alandan
geldiğini taşımıyordu; arayüz her satırı SORGUNUN alanıyla biçimlemek zorunda
kalıyordu (`kar_payi_orani` bir oran alanı olduğu için `120` → `%120`).
Hata SEÇİCİYDİ: masraf ve ödül sözlük dallarına düştüğü için doğru
görünüyordu. Zincirin tamamı düzeltildi: `RankRow.field` →
`replace(x, field=field)` → `bot.py` kaynak sözlüğü → `ChatPanel.tsx`.
5 test.

**2. "en düşük" ile "en yüksek" AYNI cevabı veriyordu.** Birincil alan o
ailede kıyaslanabilir değil — ve bu bir VERİ GERÇEKLİĞİ: `#1212` (Albaraka)
metninde kâr payı oranı DEĞERİ yayınlanmıyor (metin taranarak doğrulandı;
ödeme planındaki "Kâr Payı" kolonu tutar, oran değil). Kural hattı
kaçırmamış. Alan kıyaslanamaz olunca bileşik skora düşülüyor ve bileşik skor
TEK YÖNLÜ. Düşmek doğru, SÖYLEMEMEK yanlıştı: `_yon_uyarisi` eklendi. 6 test.

**3. Konut kıyasında "200 TL ödül" ilgisiz bir üründen geliyordu.** `#761` bir
akademisyen paketi; gerçekten konut finansmanına değiniyor ama fatura ve kart
avantajlarını da içeriyor. Belgeye TEK ürün ailesi atanıyor ve o belgeden
çıkan TÜM alanlar o aileye sayılıyor
([[urun-baglami-alan-duzeyinde-tasinmali]]).

EVREN ile 45 belgede etiket denetimi yapıldı: birincil aile uyumu **%78**,
uyuşmazlıkların **yarısı** gerçek hata değil (mevcut etiket EVREN'in
`tum_aileler` listesinde), **çok ürünlü belge %18**. Yani toplu yeniden
etiketleme için gerekçe zayıf; asıl sorun çok-ürünlülük. Kural tabanlı
`_cok_urunlu_mu` + uyarı yazıldı (belge DIŞLANMIYOR, belirsizlik söyleniyor);
`#761` ✓ işaretleniyor, `#626` ✓ işaretlenmiyor. Kapsam sınırı yazılı: kural
%9, EVREN %18 — kural EVREN'in yarısını yakalıyor. 7 test.

**`belge_turu` süzgeci eklendi ve ölçüldü — fark YOK.** Banka hedeflemede
süzgeçsiz vektör 43/55 (%78), `kampanya` süzgeçli 43/55, `kampanya+sozlesme`
43/55. Sözleşme baskınlığı bu soru tipinde sorun değil; onu içerik
sorularında görmüştük ve o tip için altın etiketli set yok. Süzgeç kodda
opsiyonel duruyor, açmak için ölçülmüş gerekçe yok. 11 test.

**Dördüncü kez kendi ölçüm kurgumda hata:** etiket denetiminin ilk koşumu
45 belgeden yalnız 20'sini ölçebildi (%56 hata). Neden: ölçüm şemasındaki
`tum_aileler` dizisine `maxItems` koymamışım — kısıtlı decoding diziyi
sonlandırmıyor, model aynı değeri tekrarlayıp `max_tokens`'ı dolduruyor ve
JSON kesiliyor. Düzeltince 45/45, 0 hata. **Projenin kendi şeması bu tuzağı
zaten biliyor** (`hedef_kitle` maxItems=4, `kampanya_kosullari` maxItems=12) —
hata yalnız benim test şemamdaydı.

Dokunulan dosyalar:

- `sorun/kiyas-cevabinda-iki-gosterim-hatasi.md` — yeni
- `decisions/urun-baglami-alan-duzeyinde-tasinmali.md` — yeni
- `index.md` · `log.md`
- `app/src/comparison/compare.py` — `RankRow.field`
- `app/src/chatbot/structured.py` — `field` damgası, `_yon_uyarisi`,
  `_cok_urunlu_mu`, `_cok_urunlu_uyarisi`
- `app/src/chatbot/bot.py` — kaynak sözlüğünde `field`
- `app/src/chatbot/rag.py` — `belge_turu` süzgeci, `SUZGEC_DERINLIK_KATI`
- `app/web/app/components/ChatPanel.tsx` — satırın kendi alanıyla biçimleme
- `app/tests/` — `test_chat_kaynak_alan_bilgisi.py` (5),
  `test_chat_yon_uyarisi.py` (6), `test_kiyas_cok_urunlu_uyarisi.py` (7),
  `test_rag_belge_turu_suzgeci.py` (11) — yeni

## [2026-08-24] duzeltme | 262k-baglam-iddiasi-geri-cekildi

"262k bağlam net kazanç" iddiası **geri çekildi**; hata bizim ölçümümüzdeydi
ve iki katmanlıydı.

1. **Alan anahtarı sayıldı, dolu değer değil.** Şema her alanı döndürür ve boş
   olanı `{"value": null, ...}` biçiminde verir — boş bir sözlük olmadığı için
   "dolu" sayıldı. "Tam metinde 12 alanın tamamı" bulgusu bu yüzden şişmişti.
2. **Karşılaştırma yanlıştı.** Kırpık-vs-tam, LLM kolunun KENDİ İÇİNDE
   kıyasıdır. Kural hattı regex tabanlı ve metnin TAMAMINI tarıyor; kırpma
   (`OLLAMA_NUM_CTX=8192`) yalnız LLM yolunu etkiliyor. Nitekim 245 uzun
   belgenin **243'ünde kural hattı zaten alan bulmuş** (741 alan) — o belgeler
   boş değildi.

Doğru ölçüm (6 en uzun belge, dolu DEĞER sayımı): kural **24** alan, EVREN
(262k) **10** alan, ortak 10, EVREN'in ekstrası **0**. Bir belgede EVREN hiç
alan bulamadı, kural 5 buldu.

**Sonuç:** bu kalem üretime alınmamalı. Uzun bağlam bir yetenek olarak duruyor
(45.959 token sorunsuz işlendi) ama çıkarım işimizde karşılığı yok — §3-c'deki
tool_calling bulgusuyla aynı yön: EVREN'in çıkarım kolu kural hattının altında
ve bu bir yapılandırma eksiği değil.

Dokunulan dosyalar:

- `app/docs/evren-servisi.md` §9 — yeniden yazıldı
- `entities/ssb-evren-cikarim-servisi.md` — 262k satırı ✓✓ → ✗
- `log.md`

## [2026-08-24] olcum | evren-buyuk-erisim-testi-ve-guvenceler

**Büyük erişim testi (255 soru).** `rag_eval`'in 25 sorusu karar için
yetersizdi; iki bölümlü, otomatik altın etiketli bir test kuruldu ve iki soru
tipi **zıt yönde** sonuç verdi:

| kol | özet-tabanlı (n=200) | banka hedefleme (n=55) |
|---|---|---|
| keyword | **MRR 0,774** | 23/55 (**%42**) |
| vector | MRR 0,559 | **43/55 (%78)** |
| hibrit (RRF) | MRR 0,761 · **R@10 %92,5** | 39/55 (%71) |

A bölümündeki keyword üstünlüğü YAPAY (sorgular belgenin kendi özetinden
türetiliyor, kelime örtüşmesi şişiyor). B bölümü gerçek kullanıma yakın ve
orada vektör kolu keyword'ü %42 → %78 ile geçiyor. Hiçbir tek kol iki tipte de
iyi olmadığı için `HybridRetriever` yazıldı
([[hibrit-erisim-rrf-ile-birlestirilir]]) — RRF ile, skor toplamıyla DEĞİL
(kolların ölçekleri farklı; toplam biri ötekini ezer). Üretim varsayılanı
bilerek `keyword` kaldı: ham vektör aramasında uzun sözleşmeler baskın
çıkabiliyor.

**Gömme uzay uyumu — kritik doğrulama.** `embeddings` tablosu EVREN ile
dolduruldu ama teslimde sorgular yerel bge-m3 ile gömülecek. Aynı metin iki
uçla gömülüp karşılaştırıldı: **kosinüs 0,99993** (çapraz kontrol 0,436).
Uzaylar ayrışmıyor — tablo geçerli, kademe güvenli. Yan kanıt: erişim testi
sırasında EVREN düştü, log'a `gomme kademesi dustu -> siradaki` yazıldı ve
yerel model devraldı; ölçüm bozulmadı.

**Prefix caching ÖLÇÜLDÜ: 5,1×.** İlk deneme 4.823 token'lık bağlamla
yapılmıştı ve fark gürültü seviyesinde çıkmıştı. 45.959 token'lık gerçek
sözleşmeyle: ilk çağrı 3,86 sn, sonrakiler 0,75/0,73/0,78 sn. Dokümantasyonun
4,8× iddiası doğrulandı. Alan başına çağrı modunda aynı belge 12 kez
gönderildiği için kazanç doğrudan oradadır.

**Model adı doğrulaması — tuzak kapatıldı.** `GET /v1/models` listesine karşı
bir kerelik kontrol. Liste alınamazsa koşum DURMAZ (güvence, ön koşul değil);
açık `transport` ile kapanır (test izolasyonu); anahtarsız yerel uçta kapalı.
Canlı doğrulandı. 9 test.

**Özet yenileme koşuldu (kısmi).** 973 özet yenilendi, 7 aynı kaldı, 1.699
üretilemedi (`llm_hatasi` 1.695 — DNS kesintisi, `bos_cikti` 4). **Veri kaybı
YOK:** güvenli döngü gereği yeni özet üretilemeyen belgede eskiye
dokunulmadı; boşalan özet 0, sayı kapısına takılan 0. Yedek:
`data/ozet-yedek-20260824-evren-oncesi.json`. Kalan için koşum sürüyor.

**Görsel boşluk ölçümü.** 40 sayfada 75 kampanya/banner görseli, 42'sinin alt
metni BOŞ — yani içeriği hiç bilinmiyor. Potansiyel kapsam boşluğu var ama
görseller indirilmemiş; gerçek kazanç ölçülmedi.

**Teslim erişimi (takım beyanı).** Yarışma anında EVREN erişimi olacağı
bildirildi ve belgeye işlendi — şu ayrımla: neyin açılacağına ÖLÇÜM karar
verir, erişimin varlığı değil. Çıkarım kolu kural hattının altında olduğu için
orada açılmıyor.

Dokunulan dosyalar:

- `decisions/hibrit-erisim-rrf-ile-birlestirilir.md` — yeni
- `index.md` · `log.md`
- `app/src/chatbot/rag.py` — `HybridRetriever`, `hibrit` modu
- `app/src/extraction/llm/clients.py` — model adı doğrulaması
- `app/tests/test_rag_hibrit_retriever.py` (10) ·
  `app/tests/test_llm_model_dogrulama.py` (9) — yeni
- `app/docs/evren-servisi.md` §6/§8/§14 · `app/.env.example`
- `data/demo.db` — 973 özet yenilendi · `data/ozet-yedek-*.json` — yedek

Test durumu: **3.705 geçti · 53 atlandı · 0 hata** · ruff temiz.

## [2026-08-24] ingest | evren-resmi-dokumantasyon-ve-tool-calling

`https://evren-teknofest.ssyz.org.tr` okundu ve **üç yeteneği yanlış test
ettiğimiz** ortaya çıktı. Düzeltilen her biri yeni bir kapı açtı.

| konu | ilk denememiz | doğrusu | sonuç |
|---|---|---|---|
| şema kısıtı | `response_format` → HTTP 500 | **tool calling** | ✓ 12 alanın tamamı |
| görüntü | `vlm` → *"At most 0 image(s)"* | **`llm-large`** (max 2 görüntü) | ✓ tabloyu okudu |
| sparse/ColBERT | `/v1/embeddings` → 501 | **`/pooling/<alias>`** | ✓ çalışıyor |

**En değerli bulgu — `tool_calling` modu.** `json_schema` ve
`structured_outputs` karmaşık şemamızda HTTP 500 veriyor, `guided_json` kısıtı
sessizce yok sayıyor. Elde yalnız kısıtsız yollar kalmıştı ve ablasyon tam bu
yüzden "gerçek şema kısıtı hiç devreye girmedi" uyarısı taşıyordu. Tool calling
ile **aynı şema kabul edildi**; yani uç şemayı derleyebiliyor, kabul etmediği
şey `response_format` sarmalayıcısıydı. Mod `STRUCTURED_MODES`'a kısıt gücüne
göre eklendi (`guided_json` → **tool_calling** → `json_object`) ve
`_yanit_metni` yazıldı: tool calling'de çıktı `tool_calls[0].function.arguments`
içinde gelir, `content` boş kalır — yalnız `content`e bakan okuyucu çıkarımı
sessizce kaybederdi. 10 test.

**Ve hipotez çürüdü.** Ablasyon raporlarındaki "gerçek şema kısıtı hiç
devreye girmedi" uyarısı bir hipotez taşıyordu; kısıt devreye sokulup **aynı
gold'da** ölçüldü (`gold.v1`): `json_object` ile llm **0,331**, `tool_calling`
ile **0,304** (hibrit 0,510 → 0,483). Kısıt kaliteyi artırmadı, hafifçe
düşürdü — ama uydurmayı (23→18) ve yanlış pozitifi (46→41) azalttı, yani
kısıtlı model daha muhafazakâr. Sonuç: EVREN çıkarım kolunun kural hattımızın
altında kalması bir yapılandırma eksiği DEĞİL; fark modelin Türkçe finansal
çıkarım kabiliyetinde. `evren` kademesinin teslimde kapalı kalması kararı
güçlendi.

**Görüntü (vision) çalışıyor:** `llm-large` panel kıyas tablosunu ekran
görüntüsünden doğru okudu (Emlak %0 · Türkiye Finans %1,9 · Kuveyt Türk %3,49;
konut %1,69/%1,89/%3,85–3,95/%2,95), 5,7 sn. Taranmış sözleşme sayfaları ve
görsel afişler için açık bir kapı.

**Özet yenileme — üçüncü ve doğru ölçüm (25 kampanya, gerçek hat, 6 ölçüt):**
doğruluk %100 vs %100 · kapsama **%21 vs %15** · ondalık-nokta ihlali **5 vs 5
(eşit)** · uzunluk 1,58× · retrieval R@1 %88 vs %92. İkinci karşı gerekçe
(Türkçe biçim) de çürüdü. Kazanç kapsamada (%40 rölatif), kayıp retrieval'da
bir belge. Net etki marjinal; karar ürün tercihi olarak bırakıldı.

**TUZAK kaydedildi:** bilinmeyen model adı sessizce kabul ediliyor
(`llm-buyuk-yanlis-ad` → HTTP 200). `EVREN_MODEL` yanlış yazılırsa koşum
farklı modelle yapılır ve artefakt yanlış adı raporlar. Açık kalem: model adı
`/v1/models` listesine karşı doğrulanabilir.

**Ölçülemeyen:** prefix caching (belge 4,8× diyor; 4.823 token'lık bağlamda
fark gürültü seviyesinde çıktı, `prompt_tokens_details: None`).

Dokunulan dosyalar:

- `app/src/extraction/llm/clients.py` — `tool_calling` modu, `TOOL_ADI`,
  `_yanit_metni`, kısıt probunda `tool_calls` tanıma
- `app/tests/test_llm_tool_calling.py` — yeni, 10 test
- `app/tests/test_llm_client.py` · `test_llm_kisit_probu.py` — mod dedektörleri
- `app/docs/evren-servisi.md` — §3-c (tool calling), §10 (doğru ölçüm), §14
  (resmi dokümantasyon bulguları) → 15 bölüm
- `app/.env.example` — mod listesi
- `entities/ssb-evren-cikarim-servisi.md` — yanlış bilgiler düzeltildi

Test durumu: **3.683 geçti · 53 atlandı · 0 hata** · ruff temiz.

## [2026-08-24] fix | ozet-sayi-kapisi

Özet hattına **sayı doğrulama kapısı** eklendi
([[ozet-sayisal-degeri-denetleyen-kapi-yoktu]]): özetteki her finansal sayı
kaynak metinde bulunmak zorunda. Alfabe ve terminoloji kapılarının eşi; sebep
kodu `sayi_dogrulanmadi`, kalıcı değil (sıcaklık merdiveninde yeniden denenir).

**Ölçülen etki:** ilk regex tarih tuzağına düştü ve 2.676 özetten 114'ünü
(%4,3) düşürdü — hepsi TARİHTİ, yani hiç uydurma yakalamadan geçerli özetleri
eliyordu (`01.04.2025` içindeki `4.202` parçası "binlik gruplu sayı" sanılıyordu).
`(?!\d)` sıkılaştırmasıyla **9'a (%0,34)** indi ve dokuzu da elle doğrulandı,
gerçekti: id=1123 özette `%50` derken kaynakta yalnız `300 TL` var, id=2528
özette `5000 TL` derken kaynakta `5001 TL`. Dokuzu düşürüldü (`ozet_sebep`
yazıldı) ve EVREN ile yeniden üretildi (15,4 sn); korpus artık kapıdan **0
ihlalle** geçiyor.

**Geri çekilen iddia:** kapı, EVREN'in özet yenilemede %16 doğrulanamayan sayı
ürettiği ölçümünden doğmuştu. O ölçüm YANLIŞTI — prompt bizim basit test
prompt'umuzdu, projenin `SISTEM_PROMPT`'u değil. Gerçek hatla 14/14 özet
ihlalsiz üretildi (sıcaklık merdiveni kapalıyken de aynı, yani merdiven
kurtarmıyor). "EVREN sayı uyduruyor" iddiası geri çekildi ve özet yenileme
kararı yeniden açıldı.

Dokunulan dosyalar:

- `sorun/ozet-sayisal-degeri-denetleyen-kapi-yoktu.md` — yeni
- `entities/ssb-evren-cikarim-servisi.md` · `index.md` · `log.md`
- `app/src/summarize/ozet.py` — `_sayi_ihlali`, `SEBEP_SAYI`, `_basamaklar`
- `app/tests/test_ozet_sayi_kapisi.py` — yeni, 11 test + 7 alt test
- `app/tests/test_ozet_alfabe.py` · `app/tests/test_ozet_dil_temizligi.py` —
  fikstürler kapıyı hesaplayacak şekilde güncellendi (davranış değişmedi)
- `app/docs/evren-servisi.md` §10 — yanlış iddia düzeltildi
- `data/demo.db` — 9 ihlalli özet düşürüldü ve yeniden üretildi

Test durumu: **3.673 geçti · 53 atlandı · 0 hata** · ruff temiz.

## [2026-08-24] ingest | evren-gomme-ve-otomatik-ozet

EVREN'in tüm yetenekleri gerçek korpusla sınandı ve **işe yarayanlar
kullanıma alındı**. Ölçüm hem kazançları hem kayıpları verdi.

**Kullanıma alındı:**
- **Gömme yolu açıldı** ([[gomme-yolu-evren-ile-acildi]]). `embeddings` tablosu
  BOŞTU (`sentence-transformers` kurulu değildi) ve chatbot'un anlamsal kolu
  hiç devrede değildi. `EvrenEmbedder` + `KademeliEmbedder` yazıldı (22 test);
  2708/2708 kampanya, **51.556 chunk**, 647 sn, 0 hata. `eval/rag_eval.py`'ye
  `--vektor` kolu eklendi: banka hedefleme **8/10 → 10/10**, toplam isabet
  21/25 → **23/25**. Üretim varsayılanı (`RAG_RETRIEVER=keyword`) bilerek
  DEĞİŞMEDİ — ham vektör aramasında uzun sözleşmeler baskın çıkabiliyor.
- **Yedek yol kuruldu:** `sentence-transformers==6.0.0`, SBOM tazelendi, sürüm
  pinlendi (requirements.txt'teki notun kendi talimatı), lisans kapısı GEÇTİ.
  `requirements-api.txt` onu hâlâ bilerek dışlıyor (imaj boyutu).
- **Başlatma kademesi:** `scripts/baslat.sh` artık `LLM=0|1|yerel|evren`
  seçiyor ve seçimi EKRANA BASIYOR. `LLM=1` + anahtar → EVREN, Ollama hiç
  başlatılmaz.
- **Tazeleme → otomatik özet:** `alt_akis_kur(..., yeniden_ozetle=...)`.
  Bayat özet düştükten sonra özetleme işi tetiklenir; bloklamaz, düşerse
  tazelemeyi HATA'ya çevirmez. Kapı: `TAZELEME_SONRASI_OZET=0`.
- **Eksik özetler:** 71 özetsiz belgeden 39'u EVREN ile üretildi (65 sn).
  Kalan 32 dürüst gerekçeyle üretilemedi (`metin_bos` 29, `bos_cikti` 2,
  `terminoloji_ihlali` 1).
- **262k bağlam:** korpustaki 245 belge 8k sınırını aşıyor. Ölçüldü —
  321.782 karakterlik sözleşmede kırpık sürüm 0 alan, TAM metin 12 alanın
  tamamı (ücret tabloları belgenin sonunda).

**Ölçüldü ve REDDEDİLDİ:**
- `rerank` — gerçek korpusta MRR 0,68 → 0,29; her pasaj uzunluğunda kayıp.
- `vlm` — görüntü desteği kapalı (`At most 0 image(s)`).
- `bge-m3-sparse` / `bge-m3-colbert` — HTTP 501, uç yok.
- `guard` — bizim enjeksiyon kapımızla anlamlı fark yok (5/26 vs 4/26; yanlış
  alarm ikisinde de 0/23). İlk koşumdaki "%100" tamamen ağ hatasıydı.
- `llm-fast` — `llm-large`'dan yavaş.
- **Özet yenileme** — EVREN özetleri iki kat zengin ama %16'sı doğrulanamayan
  sayı taşıyor (mevcut %0) ve Türkçe ondalık ayırıcıyı bozuyor. Kendi
  ölçütümüzdeki hata da düzeltildi: ilk koşum `%3.54` ile `%3,54`yi farklı
  saydığı için oran %23 çıkmıştı.

Dokunulan dosyalar:

- `decisions/gomme-yolu-evren-ile-acildi.md` — yeni
- `entities/ssb-evren-cikarim-servisi.md` · `index.md` · `log.md`
- `app/src/rag/embedding.py` — `EvrenEmbedder`, `KademeliEmbedder`, fabrika
- `app/src/tazeleme_sonrasi.py` — `yeniden_ozetle` kancası
- `app/src/api/main.py` — kancanın bağlanması (geç bağlama)
- `app/src/summarize/ozet_isi.py` — LLM notu EVREN'i de anıyor
- `app/scripts/baslat.sh` — `LLM=0|1|yerel|evren` kademe seçimi
- `app/eval/rag_eval.py` — `--vektor` kolu
- `app/requirements.txt` · `app/docs/sbom.json` · `app/docs/LISANSLAR.md`
- `app/.env.example` — gömme kademesi + otomatik özet notları
- `app/docs/evren-servisi.md` — §8–§13 (14 bölüm)
- `app/tests/test_rag_evren_embedder.py` — yeni, 22 test
- `app/tests/test_tazeleme_sonrasi.py` — +4 test

Test durumu: **3.662 geçti · 53 atlandı · 0 hata** · ruff temiz · lisans kapısı GEÇTİ.

## [2026-08-24] ingest | ssb-evren-cikarim-servisi

SSB'nin TEKNOFEST 2026 kapsamında **tüm takımlara ücretsiz** açtığı EVREN
çıkarım servisi (8×H200, 10 model, kotasız) ingest edildi ve **canlı ölçüldü**.
Ölçüm hem servisi hem kendi kodumuzu sınadı.

**Servis:** OpenAI-uyumlu uç, `llm-large` = Qwen3.5-122B-A10B (262k bağlam),
`logprobs` var, `bge-m3-embed` **1024 boyut** (gömme katmanımızla birebir),
`rerank` ucu çalışıyor. `vlm`/`guard`/`router`/sparse/colbert ve izole Qdrant
sınanmadı.

**Bizde bulunan gerçek hata:** yetenek pazarlığı bir modu "çalışıyor" saymak
için yalnız HTTP 200'e bakıyordu. EVREN `guided_json`'u tanıyıp 200 dönüyor ama
kısıtı **sessizce yok sayıyor** (prob yanıtı `'P'` = "Pong!"); pazarlık o modu
seçiyor, çıktı serbest metin geliyor, üst katmanda "LLM alan bulamadı" olarak
görünüyordu. Prob artık kısıtın uygulandığını da sınıyor; araya `json_object`
modu eklendi.

**Ölçüm (gold.v2, 48 kayıt, strict):** kural **0,570** · llm (EVREN) 0,329 ·
hibrit 0,556. McNemar p=0,00051 → kural anlamlı biçimde kazanıyor. Alan başına
çağrı (tek alanlık şema → `json_schema` kısıtı gerçekten çalışıyor) **aynı
gold'da kazandırmadı**: `gold.v1`'de llm 0,331 → 0,323 ve çağrı 40 → 413.
Yani kısıtın devreye girmesi tek başına yetmiyor; darboğaz başka yerde.

**Karar:** EVREN teslim yoluna **bağımlılık değil kademe** olarak konur
(`LLM_BACKEND=evren,ollama`); düşerse yerel yol, o da düşerse kural-only
devralır. Fallback gerçek koşumla kanıtlandı. Şartname §5.9 (on-prem %20)
korunuyor, §5.10 ihlali yok (servis ücretsiz ve yarışmanın kendisi); anahtar
repoya girmiyor.

Dokunulan dosyalar:

- `sources/teknofest/2026-08-24-ssb-evren-cikarim-servisi.md` — yeni
- `entities/ssb-evren-cikarim-servisi.md` — yeni
- `decisions/evren-opsiyonel-kademe-olarak-entegrasyon.md` — yeni
- `sorun/pazarlik-http-200-kisit-uygulanmadi.md` — yeni
- `decisions/on-premise-calistirilabilir-mimari.md` — geri link
- `decisions/demo-onceden-doldurulmus-db.md` — geri link
- `concepts/bilgi-cikarimi.md` — geri link
- `index.md`, `log.md`
- `app/src/extraction/llm/cascade.py` — yeni (kademe zinciri)
- `app/src/extraction/llm/clients.py` — bearer başlığı, kısıt probu, `json_object`
- `app/src/extraction/llm/extractor.py` — `LLM_BACKEND` kademe listesi
- `app/tests/test_llm_{bearer,kisit_probu,cascade,zincir_fabrikasi}.py` — yeni, 42 test
- `app/tests/test_llm_deadline.py` — taklit imzası genişletildi
- `app/docs/evren-servisi.md` — yeni (ölçüm + kapsam sınırları)
- `app/docs/SARTNAME-UYUM.md` — §5.10 satırı EVREN alanını açıkça anıyor
- `app/.env.example` — EVREN bloğu (anahtar boş), kademe zinciri notları

Test durumu: **3.636 geçti · 53 atlandı · 0 hata** (önce +42 test).

## [2026-08-21] lint | tam-denetim

Tam lint (mekanik + semantik) koşuldu, `lint-report.md` baştan yazıldı (önceki
rapor 2026-06-16 tarihliydi ve 37 sayfalık vault'u anlatıyordu).

Mekanik: 59 içerik sayfası, 498 wikilink, **kırık link 0** (bugünkü düz-metne
indirme doğrulandı), orphan 6 (index.md sayılınca 4), `taslak` 3, frontmatter'ı
eksik 1 (`archive/_plan-rakip-ustunluk`), duplicate title 0, log kronolojisi
doğru, bayat (90+ gün) sayfa yok. Bugün eklenen 4 sayfa dizinde ve çift yönlü
bağlı — doğrulandı.

Semantik: (1) `decisions/ner-fine-tune-yerine-kural-few-shot` (`stable`) ile
`sources/docs/2026-08-05-ablasyon` ("hibrit KAYBETTİ", kural 10-1, p=0,0117)
arasında **işaretlenmemiş çelişki**; (2) "hibrit" terimi çıkarım ve chatbot
için iki farklı anlamda kullanılıyor; (3) korpus büyüklüğü 5 farklı değerle
geçiyor (güncel DB 2.708; bayat: 1759 iki `stable` sayfada, 849, 1.774, 1.782);
(4) 3+ sayfada geçip sayfası olmayan kavramlar: gold küme (9), RAG (8), F1 (7),
Ollama (6), ablasyon (5); (5) index.md'de 3 drift (Archive "boş" diyor ama
sayfa var; yarım-ingest notu "linkler kırık" derken artık kırık yok).

Kural gereği **hiçbir düzeltme yapılmadı**; 10 önerilen aksiyon raporda sıralı.

Dokunulan dosyalar:
- lint-report.md (baştan yazıldı)
- log.md (bu giriş)

## [2026-08-21] ingest | inceleme-duzeltmeleri-vault

21 Ağustos sunum kararı ve iki teknik sorun (+ bir yanlış alarm) vault'a
işlendi; üç yarım-ingest kaynak sayfasındaki kırık wikilinkler düz metne
indirildi ve sayfalar taslak statüsüne alındı; log.md kronolojisi onarıldı
("en yeni en üstte" beyanına uygun sıraya getirildi); kök CLAUDE.md'ye
klasör şeması ekleri, isimlendirme kapsam daraltması, app/docs ↔ vault sınırı
bölümü ve CLAUDE/AGENTS ikizlik kuralı yazıldı; izlenen dosyalardaki
`invariants.md` atıflarına vitrin-dalı notu, HF veri seti kartına kesit
uyarısı eklendi.

Dokunulan dosyalar:
- log.md (kronoloji onarımı: 2026-08-05 girişi doğru yerine, iki 2026-08-21
  girişi en üste taşındı + bu giriş)
- decisions/juri-sunumu-bes-slayt.md (yeni)
- sorun/turkce-buyuk-harf-yerel-duyarliligi.md (yeni)
- sorun/sunum-slayt-sigdirma-olcek-cokusu.md (yeni)
- sorun/next-dev-proxy-econnreset-yanlis-alarmi.md (yeni)
- index.md (son güncelleme tarihi + 4 yeni sayfa dizine eklendi)
- sources/docs/2026-08-05-ablasyon.md (23 kırık link düz metne; status: taslak)
- sources/docs/2026-08-03-anatolia-ai-teknik-rapor.md (23 kırık link düz
  metne; status: taslak; invariants vitrin-dalı notu)
- sources/docs/2026-07-31-offline-kanit.md (26 kırık link düz metne;
  status: taslak)
- sources/tcmb/2026-08-07-terimler-sozlugu.md (köşeli parantezli CLAUDE.md
  wikilink'i → düz metin)
- app/docs/rapor/banka-siteleri-veri-kaynagi-haritasi.md (3 göreli-yollu
  wikilink slug biçimine çevrildi)
- CLAUDE.md ve AGENTS.md (yukarıdaki kılavuz güncellemeleri; ikiz tutuldu,
  tek fark satır 63)
- app/docs/kod-haritasi/testler.md · app/docs/rapor/NOTEBOOKLM-YUKLEME.md
  (invariants.md atıfına vitrin-dalı notu)
- app/data/yayin/anatolia-ai-gold/README.md (kesit uyarısı, 2026-08-15
  paketi vs 2026-08-21 gold onarımı)

## [2026-08-21] duzeltme | gold derleme komutu bulundu, tahkim CSV'lere tasindi

Aynı gün açtığım `sorun/gold-round1-csvden-yeniden-uretilemiyor` sayfasının
teşhisi YANLIŞTI. Gold kaynaktan üretilebiliyor; eksik olan hangi ön-anotasyon
havuzunun kullanıldığı bilgisiydi: `--pre data/gold/preannotations.v2.json`.
Ben üç kombinasyon deneyip 57 kayıtta kalınca kusur ilan etmişim; 4. tur
Teknik Mimari jürisi dördüncü havuzu deneyip 134'e ulaşmış.

Gerçek boşluk ikincisiydi ve kapandı: HAKEM-05 + S1 kararları (27 satır)
kaynak CSV'lere yazıldı. Beşi YENİ SATIR olarak eklendi — o belgelerde
`finansman_tutari` inceleme kuyruğuna hiç girmemişti çünkü model o alanda bir
şey üretmemişti; kuyruk model çıktısına göre kuruluyor, yani modelin görmediği
alanda anotatörün kararını kaydedecek yer yoktu.

Yol boyunca kendi hatamı buldum: S1 betiğinde `r.setdefault("fields", {}) or {}`
yazmışım. Boş sözlükte `or` kopuk bir sözlük döndürüyor ve yazılan değer
kayboluyor. `lc-waikiki` kaydı bu yüzden boş kalmış. Bir denetim bunu "support
daralması" diye okumuştu; onarımdan sonra gerçek sayı 22 -> 18 (17 değil).

Ölçüm: round1 manşet 0,793 -> 0,795 · finansman_tutari F1 1,000 destek 18.

Dokunulan dosyalar:
- sorun/gold-round1-csvden-yeniden-uretilemiyor.md (teşhis düzeltildi)
- index.md · README.md (derleme komutu + sayılar)
- app/data/gold/review/round1_{A,B,main_C,main_D}.csv (27 satır)
- app/data/gold/gold.round1.json (kaybolan hücre onarıldı)

## [2026-08-21] sorun | gold.round1 kaynaktan yeniden üretilemiyor

4. tur Yenilikçilik jürisi bir sözümüzü tutmadığımızı buldu: HAKEM-05 paketinde
"bu boşluk `sorun/` altına yazılmalı" yazmışız ve yazmamışız. Bulgu haklıydı,
sayfa açıldı.

Ölçüm: `gold.round1.json` 134 kayıt taşıyor, dört anotasyon CSV'sinden derleme
yalnız 57 veriyor. Düşen 77'nin kırılımı: 46 `D`, 30 `A`+`B`, 1 `D`+`HAKEM-04`.
İki aday kök neden var ve ikisi de kayıtsız — derleme komutu hiçbir yerde yazılı
değil, ve CSV'ler gold üretildikten sonra iki turda (hakemlik, şema onarımı)
değişti.

Bu turda kapatılmadı ve sebebi yazılı: iş ölçüm tabanına dokunuyor, yanlış
sırada yapılırsa `gold.round1` ölçümleri (0,793 / 0,284) yeniden üretilemez
hâle gelir. Çevrimiçi süreç 26 Ağustos'ta bitiyor.

Dokunulan dosyalar:
- sorun/gold-round1-csvden-yeniden-uretilemiyor.md (yeni)
- index.md (Sorunlar bölümü)
- log.md (bu giriş)

## [2026-08-21] karar | jüri sunumu 15 slayttan 5 slayta indirildi

Şartname §10 sunum süresini **4 dakika** veriyor. 16 Ağustos'ta üretilen 15
slaytlık sunum o sürede sunulamıyordu; sahnede konuşulan bir ikna metni değil,
okunan bir savunma dokümanı gibi davranıyordu. Yerine yönetici seviyesinde
**5 slaytlık** bir sunum yazıldı. Hedef kitle karma: teknik jüri + katılım
bankacılığı uzmanları + banka yöneticileri.

**Eski sürüm silinmedi** (HARD RULE 3): `app/docs/archive/sunum-15-slayt-2026-08-21.html`,
başında neden arşivlendiği ve bilinen iki sapması yazılı. Savunma derinliği
(κ asimetrisi, ölçüp geri adım atılan kararlar, halüsinasyon payda tanımı)
konuşmacı notlarındaki **jüri soru bankasına** taşındı.

### Ölçüp düzelttiğimiz üç sapma

| Sapma | Kanıt | Ne yapıldı |
|---|---|---|
| Eski deck slayt 03 manşeti **%3,9** diyor, kendi kanıt satırı **146 / 2.708** diyor | 146/2708 = **%5,39** (`select count(distinct campaign_id) … kar_payi_orani`) | yeni deck **%5,4** yazıyor |
| `docs-ekran/ss/*.png` kareleri **1.774 belge** rozetiyle çekilmiş (12 Ağu) | `data/demo.db` bugün **2.708** belge · 7.032 alan | sunum kareleri canlı arayüzden **yeniden çekildi**; betik her koşumda rozeti okuyup teyit ediyor |
| Eski deck slayt 14 tam yığın ağsız kanıtı «sıradaki» sayıyor | tam yığın **3/3 koşum · 39/39 adım · 0 beklenmedik** ölçülmüş | yeni deck kazanılmış kanıt olarak yazıyor |

### Ölçüp slayttan ÇIKARDIĞIMIZ iki iddia

- **«758 PDF»** — kaynağı `docs/rapor/aile-kapsami-hasadi.md` (hasat raporu, 758
  benzersiz PDF · 5.410 sayfa). `kanit_tazeligi` kapsamında değil ve DB'de
  `.pdf` biten kayıt **969**; iki farklı tanım. Slayta konmadı.
- **«masrafsız denip aynı metinde tahsis ücreti belirtilmesi»** — dedektörün en
  bilinen kuralı ve panelin kendi giriş metninde «en güçlü örnek» diye
  adlandırılıyor, ama **bugünkü korpusta ateşlenmiyor**. 20 bulgunun dağılımı:
  17 süresi dolmuş kampanya · 2 çakışan tutar bandı · 1 çelişen bitiş tarihi.
  Slayt 5 bu yüzden gerçekten var olan bulguyu alıntılıyor (Kuveyt Türk · Taşıt
  Finansmanı · belge #801). Kural var, bulgu bugün yok; ikisi karıştırılmadı.

### Yol boyunca kapatılan iki teknik sorun

- **Türkçe büyük harf.** `text-transform:uppercase` yerel-duyarlıdır; dosya
  `<meta charset>` ile başladığı için örtük `<html>`'in `lang`'i yoktu ve mono
  etiketler «ÜRETIMDE», «BIÇIM VARYANTI», «KURUM IÇINDE» diye basılıyordu.
  Deck'in kendi betiği artık `kok.lang = "tr"` veriyor; PDF/PPTX de doğru
  eşlemeyi alıyor. **Arşivlenen 15 slaytlık sürümde bu hata duruyor.**
- **Sığdırma.** `uret-sunum.py` taşan slaytı tek katsayıyla küçültüyor. İlk
  taslakta beş slaytın beşi de taşıyordu ve ölçek 0,75'e kadar düşüyordu —
  tipografi okunmaz oluyordu. İçerik, beş slayt da **1080px'e kendi başına**
  sığana kadar sıkıştırıldı (taşma raporu boş). Tasarım sistemine üç yoğun
  yerleşim değiştiricisi eklendi (`.zaman.sik`, `.akis.dar`, `.kart.sik`).
- **Yanlış alarm:** çelişki sekmesi çekim sırasında «Sunucu 500 döndü» bastı.
  Ürün hatası değil: API'yi Next dev sunucusu ayaktayken yeniden başlatınca
  proxy ölü keep-alive soketini yeniden kullanıyor (`ECONNRESET`). Web
  sunucusu tazelenince geçti; not `docs/sunum/ekranlar/README.md`'de.

### Dokunulan dosyalar

- `app/docs/sunum/anatolia-ai-sunum.html` — **yeniden yazıldı** (5 slayt; tasarım
  sistemi arşivlenen sürümden birebir devralındı, sıfırdan tasarım yapılmadı)
- `app/docs/sunum/anatolia-ai-sunum.pdf` · `.pptx` — yeniden üretildi
  (5 sayfa / 5 slayt, 1440×810 pt, metin katmanı vektör)
- `app/docs/archive/sunum-15-slayt-2026-08-21.html` — **yeni** (taşınan eski deck)
- `app/docs/sunum/cek-juri-4dk.py` — **yeni**; deck'in kareleri için hedefli
  Playwright betiği. `docs-ekran/ekran_cek.py` 42 kareyi birden çekip
  `manifest.json`'la eşleşmek zorunda olduğu için o hat tetiklenmedi.
  40 zor vakayı tarayıp en çok alan çıkanı kendisi seçiyor
  (ölçüt kasten «en çok alan», «en az uyuşmazlık» değil).
- `app/docs/sunum/gom-ekranlar.py` — **yeni**; kareleri HTML'e yerinde gömer,
  `--denetle` ile bayat kare bildirir
- `app/docs/sunum/ekranlar/` — **yeni**; 12 kare + kullanılmayan adayların
  gerekçesini yazan README
- `app/docs/sunum/juri-4dk-konusmaci-notlari.md` — **yeni**; slayt başına
  konuşma notu, ⟨kes⟩ işaretli süre payı, kriter eşleşme tablosu, 10 soruluk
  jüri bankası
- `app/docs/SARTNAME-UYUM.md` — satır 10/11 (15 sayfa/slayt → 5) ve slayt
  sayısı notu gerçekle eşlendi; sayım bağımsız yeniden yapıldı
- `app/docs/rapor/sunum-ve-demo-plani.md` — §C'ye «bu iskelet bayattır» notu

`uret-sunum.py`, `docs-ekran/*` ve `manifest.json` **değişmedi**.

### Doğrulama

- `python -m scripts.kanit_tazeligi` → **15 iddia · 0 sapma · 0 kanıt eksik**
- taşma raporu boş · PDF **5** sayfa · PPTX **5** slayt · `zipfile.testzip()` hatasız
- PDF metin katmanı 4.387 karakter, `â 2` (mojibake yok)
- deck açık ve koyu temada render edildi; yatay kaydırma yok

## [2026-08-10] bakım | index.md ve log.md geriye dönük tamamlandı

İki ingest (2026-08-06 mentör terim sözlüğü, 2026-08-07 TCMB) **5 sayfa üretmiş
ama ne `index.md`'ye ne `log.md`'ye işlenmişti.** CLAUDE.md "Workflow: INGEST"
adım 8-9 ikisinin de her ingest sonrası güncellenmesini şart koşuyor; kural
yazılıydı, uygulanmamıştı. Bu girdi ve aşağıdaki iki ingest girdisi o boşluğu
geriye dönük kapatır.

Ölçüm (dosya sistemi ↔ index.md karşılaştırması, 2026-08-10):
- vault'ta 53 sayfa, index.md'de 45 → **8 sayfa dizinde yok**
- aynı 8 slug `log.md`'de de **0 kez** geçiyor (eksik küme ikisinde birebir aynı)
- 8'in **5'i** iki ingest'e ait ve bu turda eklendi
- 8'in **3'ü** (`sources/docs/` altındaki offline-kanit, teknik-rapor, ablasyon)
  yarıda kalmış bir ingest'e ait — **bilerek eklenmedi**, kullanıcı kararı
  bekliyorlar

Dokunulan dosyalar:
- index.md (Sources'a 2, Concepts'e 1, Decisions'a 2 girdi; `Son güncelleme`
  2026-08-07 → 2026-08-10; yarım ingest için açıklayıcı not)
- log.md (bu girdi + iki ingest girdisi)

Notlar:
- Sayfaların **içeriğine dokunulmadı**; yalnız dizin ve günlük kaydı.
- Silme/taşıma yapılmadı (hard rule #3).
- `lint-report.md` hâlâ 2026-06-16 tarihli ve "0 kırık link" diyor; yarım
  ingest'in ~45 kırık wikilink'i ondan sonra birikti. Lint yeniden koşturulmadı
  — bu turun kapsamı dışında, açık uç olarak kalıyor.

## [2026-08-07] ingest | tcmb-terimler-sozlugu

Kaynak: `sources/tcmb/2026-08-07-terimler-sozlugu.md` (TCMB Terimler Sözlüğü,
314 terim). Projeye **ikinci ve karşıt** bir terminoloji otoritesi kazandırdı:
elimizdeki tek sözlük katılım tarafını tanımlıyordu, konvansiyonel bankacılığın
resmî dilini tanımlayan referans yoktu. Aynı zamanda projenin temel tezini
(*"konvansiyonel otorite katılım terminolojisini kapsamıyor"*) sayıyla test
etmeye imkân verdi.

Ölçüm (üç geçişli çapraz analiz — KAPSAMA / ÇATIŞMA / SAHTE-DOST):
- gerçek kavramsal kesişim **4 / 101**
- TCMB'de karşılığı olmayan katılım terimi **94 / 101 (%93,1)**
- çekirdek 18 fıkhî terimin **17'si** TCMB'de yok (tek istisna Sukuk)
- "kâr payı", "katılma hesabı", "özel cari hesap" → 314 başlık ve 314 tanım
  metninde **sıfır**
- doğrudan çatışma: **24 çift, 19 ayrı katılım terimi**
- hedef korpusta isabet (389 katılım belgesi): katılım sözlüğü %55,4, TCMB %14,0

Dokunulan dosyalar:
- **sources/tcmb/** 2026-08-07-terimler-sozlugu.md (oluşturuldu)
- index.md (Sources bölümüne eklendi — 2026-08-10'da, geriye dönük)

Kod tarafı (app/, ayrı depo alanı):
- data/terminology/tcmb-terimler.json (314 terim), _tcmb_ham/ (ham HTML + künye)
- scripts/tcmb_sozluk_ayristir.py, scripts/tcmb_capraz_analiz.py (oluşturuldu)
- docs/terminoloji-tcmb-capraz.md (üretildi)

Notlar:
- **Tezin dürüst sınırı yazıldı:** "TCMB katılım terminolojisini hiç kapsamıyor"
  savunulamaz — 5 kayıt (%1,6) İslami finansa değiyor. Savunulabilir ifade
  oransaldır.
- Beklenmedik bulgu: TCMB'nin kendi Sukuk tanımı ("tahvil borca dayalı, sukuk
  varlığa dayalı sertifika") sözlüğümüzün `ayrim_notu` alanıyla birebir aynı
  ayrımı yapıyor — ayrım kartı artık düzenleyici metinle desteklenebilir.
- Bu ingest **türev sayfa üretmedi**; çıkan iki karar (TCMB birleştirilmez;
  rolü karşıt-otorite referansı) hâlâ `decisions/` altında sayfası olmayan
  **açık uçtur**.
- Çift yönlü bağ eksik: kaynak sayfa `[[katilim-finans-terimleri]]`,
  `[[terim-sozlugu-enjeksiyon-replace-degil]]` ve
  `[[katilim-bankaciligi-terminoloji-farkliligi]]`e link veriyor ama o
  sayfalarda karşı-link yok (hard rule #6). Açık uç.

## [2026-08-07] belge | klasik-banka-korpusu "YARIŞMA KAPSAMI DIŞI" etiketlendi

`app/data/raw-classic/` (11 klasik banka, 724 belge) yarışma veri seti sanılma
riski taşıyordu: dizin `data/raw`ın hemen yanında duruyor, aynı hasat betiği
üretiyor ve içinde Akbank/Garanti/İş Bankası gibi tanınmış banka adları var.
TEKNOFEST jürisi bunu şartname §5.1 kapsamının parçası sayarsa veri seti yanlış
değerlendirilir. Korpusa ve vault'a açık kapsam-dışı etiketi eklendi.

Ölçüm (2026-08-07, tahmin YOK — hepsi bu oturumda koşuldu):

- `find app/data/raw-classic -name '*.txt' | wc -l` → **724** belge
- `git ls-files data/raw-classic | wc -l` → **1461** izlenen dosya
- 724 `.meta.json` dosyasının tamamında `scraped_at` = **2026-08-04** (tek tur)
- `app/data/raw`: **1761** `.txt`; bunun 2'si banka kökündeki demo fikstürü
  (`kuveyt-turk/konut.txt`, `turkiye-finans/tasit.txt`) → **1759** kazınmış
- Terim kapsama oranı (`.txt` küçük harfe indirilip alt dizge araması):
  klasik korpus `faiz` **%70,2** (508/724), `kâr payı` %0,3 (2/724), fıkhî
  terim (murabaha·icara·mudarebe·muşareke·karz-ı hasen·sukuk·katılma
  hesabı·tekafül) **%0,0** (0/724); katılım korpusu `faiz` **%7,3** (128/1759),
  `kâr payı` **%18,1** (319/1759)
- `app/data/silver/silver.jsonl` `wc -l` → **505** gümüş kayıt
  (`silver_report.json`: 608 öneri → 505 gümüş, 100 red)

Dokunulan dosyalar:

- **entities/** klasik-banka-korpusu.md (oluşturuldu)
- **entities/** veri-seti.md (`## Related` altına çift yönlü bağ eklendi —
  kapsam içi/dışı ayrımı vurgulandı)
- index.md (Entities bölümüne eklendi, son güncelleme tarihi 2026-08-07)

Kod tarafı (app/, ayrı depo alanı):

- **app/data/raw-classic/README.md** (oluşturuldu) — kapsam dışı uyarı bloğu,
  toplama gerekçesi, nerede KULLANILIR / KULLANILMAZ, ölçülmüş terim dağılımı
  tablosu + ölçüm komutu, `data/raw` ile fark tablosu
- **app/data/raw/README.md** (oluşturuldu) — kapsam İÇİ korpus tanımı +
  `../raw-classic/README.md`e karşı-referans
- **app/data/raw-classic/_collection_report.md** (başa kapsam uyarısı bloğu
  eklendi; dosyanın kalanına dokunulmadı)

Notlar:

- `_collection_report.md` otomatik üretilir ("Elle düzenlemeyin"). Eklenen blok
  bir HTML yorumuyla işaretlendi: `python -m src.scraping.harvest` yeniden
  koşarsa blok silinir, geri eklenmelidir. Aynı raporun gövdesindeki 288
  belge / 5 banka sayıları **tek turun** sayılarıdır; korpus toplamı 724/11 —
  bu da rapor başına not düşüldü.
- Kapsam dışılık kodda zaten beyan edilmişti (`config/banks-classic.yaml` "NE
  İÇİN VAR" bloğu; `scripts/split_trainable.py` "Bu araç ne YAPMAZ";
  `scripts/build_silver.py` sıfır-kesişim mesajı) ama **korpus dizininin
  kendisinde** hiçbir işaret yoktu — dizine bakan biri kodu okumuyordu.
- Tasarımın özü kayda geçirildi: gümüş hat klasik veride EĞİTİR, altın hat
  katılım verisinde ÖLÇER; ayrıklık kasıtlıdır ve terminoloji aktarımını
  sınanabilir kılar (`app/CLAUDE.md §12`).
- Aynı gün alınan [[klasik-veri-ince-ayar-rag-reddi]] kararıyla aynı ölçümlere
  dayanır ve onu tamamlar: o karar korpusun ince ayar/RAG kaynağı olmasını
  reddeder, bu belge korpusun kapsam dışılığını dizinin kendisinde ilan eder.

## [2026-08-07] karar | klasik-veri-ince-ayar-rag-reddi

"Klasik (katılım olmayan) banka verisiyle LLM ince ayarı ve RAG yapma" fikri
ölçümle **reddedildi** ve gerekçesiyle kalıcı kayda geçirildi.

Ölçüm: klasik korpusun (724 belge) **%70,2'si "faiz"** içeriyor, fıkhî terim
oranı %0,0 (murabaha/icare/mudaraba/müşaraka/katılma hesabı hepsi sıfır).
Yarışma korpusunda (1759 belge) ise "faiz" yalnız %7,3, kâr payı %18,1.

Dört gerekçe: (1) ters register — bu veriyle ince ayar, yasakladığımız sözlüğü
öğretir; (2) **seyreklik** (asıl teknik gerekçe) — fıkhî terimler katılım
korpusunda da nadir (murabaha %1,9, icare %0,6, mudaraba %0,5); %0,6
sıklığındaki terim ince ayarla öğrenilmez, enjekte edilir; (3) RAG'de olgusal
yanlışlık — katılım sorusuna kaynak göstererek Akbank/Garanti pasajı basmak;
(4) yanlış halkaya yatırım — kural 0,677 / orkestra 0,672 / hibrit 0,575, yani
LLM katmanı şu anda zarar veriyor.

Kararın sınırı açıkça yazıldı: klasik veri **gümüş eğitimde geçerlidir ve
kullanılıyor** (505 kayıt, 8 sınıf) — orada aktarılan terminoloji değil ürün
ailesi yapısıdır; ayrıklık kasıtlıdır (klasikte eğit, katılımda ölç). RAG'in
kendisi de reddedilmiyor; reddedilen klasik korpusun RAG kaynağı olmasıdır —
doğru kaynak `app/data/raw/*/docs/` bölümüdür (fıkhî terim yoğunluğu %42,0).

Dokunulan dosyalar:
- **decisions/** klasik-veri-ince-ayar-rag-reddi.md (oluşturuldu)
- index.md (Decisions bölümüne eklendi)
- **app/docs/rapor/** karar-bekleyenler.md ("Kapanmış kararlar" bölümüne bir
  madde eklendi)

Notlar:
- Fıkhî terimler korpusa eşit dağılmıyor: `docs` %42,0, `products` %16,3,
  `live` %4,8, `archive` %1,5. RAG önceliği bu yüzden `docs/` bölümüne verilir.
- Karar dar kapsamlıdır; ne ince ayarın tümünü ne RAG'in kendisini reddeder.

## [2026-08-06] ingest | mentor-terim-sozlugu

Kaynak: `sources/mentor/2026-08-06-mentor-terim-sozlugu.md`. Mentör (eski
bankacı; chatbot ve çok-ajanlı sistem deneyimi) ilk mentörlük toplantısında
konuşulan terminoloji sorunu üzerine yazılı görüş ve **101 girdilik
yapılandırılmış katılım finansı sözlüğü** gönderdi (avukat teyitli).

Mailin özü tek cümlede: **terimi replace etme, LLM'e analizi ver.**

> "Birebir değiştirmek anlamda bozukluk yaratıyor… Türkçeleri aynı anlamı
> replace ile taşımıyor. O sebeple böyle bir kapsamlı analiz vermek gerekiyor."

Dokunulan dosyalar:
- **sources/mentor/** 2026-08-06-mentor-terim-sozlugu.md (oluşturuldu)
- **concepts/** katilim-finans-terimleri.md (oluşturuldu)
- **decisions/** terim-sozlugu-enjeksiyon-replace-degil.md (oluşturuldu)
- **decisions/** orkestrasyon-yetki-asimetrisi.md (oluşturuldu)
- index.md (Sources/Concepts/Decisions bölümleri — 2026-08-10'da, geriye dönük)

Notlar:
- İki karar çıktı ve ikisi de ölçüme dayanıyor: (1) sözlük **enjekte** edilir,
  kör replace yapılmaz; (2) orkestrasyonda **ajanlar önerir, hakem yalnız
  reddeder** — ablasyon (n=20, bootstrap 1000) hibrit kolun kural kolundan daha
  kötü olduğunu ölçtüğü için LLM ajanlarına yazma yetkisi verilmedi.
- Aynı kaynağa dayanan `klasik-veri-ince-ayar-rag-reddi` kararı ertesi gün
  (2026-08-07) ayrı bir "karar" girdisiyle zaten işlenmişti; bu ingest'in
  **kendisi** ve diğer üç türev sayfası işlenmemişti — bu girdi onu kapatıyor.
- `sources/mentor/2026-08-06-mentor-terim-sozlugu.md` frontmatter'ında `source:`
  alanı **yok** (diğer tüm kaynak sayfalarında var). İçeriğe dokunulmadığı için
  düzeltilmedi; açık uç.

## [2026-08-05] karar | masrafsizlik-celiskisi-kapsam-testi

Yenilikçilik hedefi #2'nin ("masrafsız deyip tahsis ücreti alanı yakala") nasıl
uygulanacağı ölçümle karara bağlandı. Naif tasarım ("tarifede ücret varsa
çelişki") ölçüldüğünde çöktü: korpustan çıkan 33 ilan edilmiş tahsis ücreti
kaydının 30'u tam olarak %0,5 — BDDK'nın konut finansmanı üst sınırı, yani
sektörde fiilen tek fiyat. Naif test her masrafsızlık kampanyasını çelişki
sayardı ve meşru muafiyetleri sahtekârlık gibi gösterirdi.

Karar: test **kapsam** testidir. Muafiyet bir koşula bağlıysa (`kosullu_muafiyet`)
çelişki değildir ama karşılaştırma tablosunda "masrafsız" yazılamaz — koşullu
ifade gösterilir. Koşul yoksa (`kapsamsiz_iddia`) insan hakemliğine gider.

Dokunulan dosyalar:
- **decisions/** masrafsizlik-celiskisi-kapsam-testi.md (oluşturuldu)
- **concepts/** urun-karsilastirma.md ("En Düşük Masraf" kriteri tek sayıya
  indirilemez notu + çift yönlü bağ)
- index.md (Decisions bölümüne eklendi)

Kod tarafı (app/, ayrı depo alanı):
- scripts/crosscheck_fees.py, tests/test_crosscheck_fees.py (oluşturuldu)
- data/gold/fee_crosscheck.csv, .md (üretildi)
- docs/rapor/zor-vaka-kurleme.md ("KURULDU" bölümü — açık uç kapandı)

Notlar:
- Bu bir belgeler ARASI kontroldür. Belge İÇİ çelişki korpusta pratik olarak yok
  (13 adayın 12'si ücret tarifesiydi), o yüzden gold `celiskili` etiketiyle
  aranamaz — ayrı betiğe ait.
- Yan bulgu: Türkiye Emlak Katılım taşıt tahsis ücretini bir formda %0,5,
  diğerinde %0,1 ilan ediyor (bankanın kendi içinde tutarsızlığı).

## [2026-07-27] kod+yöntem | Gün 1c: Veri modeli, gerçek güven, 12/12 alan, değişmez denetimi

Üç blok iş yapıldı. Sonuncusu bir **yöntem değişikliğidir** ve kalan 29 günün
verimini doğrudan etkiler.

### 1. Veri modeli (sonraki her katman buna bağlanacağı için önce)

- `ExtractedField`'a `span_start`/`span_end` eklendi. `source_span` yalnızca
  ±40 karakterlik bir pencere METNİydi ve orijinalde güvenilir bulunamıyordu;
  dashboard'daki kaynak vurgulaması (yenilikçilik hedefi #1) kesin offset ister.
  `verify_span(text)` kendi kendini denetler.
- `confidence` sabit 0.95'ti. Sabit skor kalibre edilemez (ECE tek bin'e düşer),
  abstain eşiği ayrım yapamaz, jüriye savunulamaz. `rules/confidence.py` eklendi:
  tetikleyici yakınlığı + makullük + belirsizlik + aralık cezasından hesaplanır.
  Ölçülen ayrım: ideal 0.95, aralık 0.90, belirsiz 0.85, makul dışı 0.50.
  Skorlar **kalibre edilmemiştir** (yalnız sıralayıcı); `confidence_source`
  alanında işaretli.

### 2. Kural katmanı 7/12 → 12/12 alan

§5.3'ün "Kampanya Bilgileri" ve "Hedef Kitle" kolonları tamamen boştu; §5.7'nin
"En Yüksek Ödül Miktarı" kriteri cevaplanamıyordu. Eklenen 5 çıkarıcının her
biri bir ayırt etme tuzağı çözüyor (koşul/ödül, indirim/puan, oran/adet,
segment/negasyon).

### 3. YÖNTEM: değişmez (invariant) denetimi

Bugün bulunan **beş hatanın hiçbiri çökme değildi** — hepsi sessizce yanlış
değer üretiyordu. Bu, asıl riskin "model yeterince iyi değil" değil
**"kendinden emin çöp üretiliyor ve fark edilmiyor"** olduğunu gösteriyor.

`eval/properties.py` — girdinin anlamını değiştirmeyen dönüşümler çıktıyı
değiştiriyorsa doğru cevabı bilmeden hata olduğu kesindir. Dolayısıyla
**gold etiketi gerekmez**:

| Değişmez | Yakalayacağı hata |
|---|---|
| P1 span bütünlüğü | vurgulanan yer ≠ raporlanan değer |
| P2 ortografik değişmezlik | **H1** (ALL-CAPS işaret ters çevirme) |
| P3 alakasız ekleme | **hayali 31 TL ücret** |
| P4 cümle sırası | **H2** (çelişkinin sıraya bağlılığı) |

Bugünkü beş hatanın **dördü** bunlarla otomatik yakalanırdı.

Bu, gold set kritik yolda beklerken (anotasyon insan işi, yavaş) anote
**edilmemiş** 150–250 belgede hemen hata avlar. Kritik yolu kısaltmaz ama
paralel bir kalite hattı açar.

META test eklendi: her zaman geçen bir denetleyici işe yaramaz. `tr_fold`
düzeltmesi geçici geri alındığında denetleyicinin gerçekten ihlal ürettiği
doğrulanıyor (`masraf_durumu` has_fee False→True). Bu test geçmezse diğer
"0 ihlal" sonuçları anlamsızdır.

### Bu bloklarda bulunan gerçek hatalar (hepsi düzeltildi)

1. **Sahte aralık:** `"kâr payı oranı %1,89 ile 120 aya kadar"` →
   `{min: 1.89, max: 120.0}`. 'ile' bağlacı aralık ayırıcı sanılıyor, bir
   VADE oran üst sınırı olarak karşılaştırma tablosuna yazılıyordu.
   İlk düzeltme denemesi regex geri izlemesiyle atlatıldı (`"36"`dan `"3"`),
   `(?![\d.,])` ile sayının tamamının tüketilmesi zorlandı.
2. **Fiil negasyonu eksikti:** `normalize_fee_status` yalnızca sıfat
   biçimlerini biliyordu. `"Yıllık kart ücreti alınmaz. Kampanya 31 Aralık
   2026..."` → `{has_fee: True, amount: 31.0}` — hem negasyon kaçıyor hem
   tarihten **hayali ücret** uyduruluyordu. `NEGATION_RE` tek doğruluk
   kaynağına alındı + ücret penceresi cümle sınırında kesiliyor.
3. **Koşul/geçerlilik karışması:** tek başına "geçerli" tetikleyicisi her
   belgedeki *"Kampanya <tarih> tarihine kadar geçerlidir"* cümlesini koşul
   sanıyordu (zaten `kampanya_suresi` yakalıyor). Her belgede yanlış pozitif.
4. **is_plausible yalnız min'e bakıyordu** — bozuk aralıkları makul gösteriyordu.

Dokunulan dosyalar:
- `app/src/schemas.py` (span offsetleri, confidence_source, verify_span)
- `app/src/extraction/rules/confidence.py` (yeni)
- `app/src/extraction/rules/extract.py` (5 yeni alan, offsetler, düzeltmeler)
- `app/src/normalization/normalize.py` (NEGATION_RE, fiil negasyonu)
- `app/src/extraction/rules/synonyms.py` (NEGATION_RE yeniden ihracı)
- `app/src/preprocessing/clean.py` (tr_upper)
- `app/eval/properties.py` (yeni, CLI dahil)
- `app/tests/{test_confidence_span,test_kampanya_alanlari,test_properties}.py` (yeni)

Test durumu: **129 test yeşil** (85 → 129), tamamen offline.

Açık uçlar (değişmedi): gerçek scraping, gold set 3→250, LLM'in Colab'da ilk
kez çalıştırılması. Bunlar kritik yolda ve insan katılımı gerektiriyor.

## [2026-07-27] sorun+kod | Gün 1b: Çelişki tespiti canlandırıldı (H2)

Bağlam: `contradiction.detect()`'in birincil kuralı `masrafsiz_ama_ucret` hem
`masraf_durumu` hem `tahsis_ucreti` alanını istiyor. Kural katmanı
`tahsis_ucreti` alanını hiç üretmediği için bu kural **bugüne kadar hiç
tetiklenemedi** — yani `decisions/daraltilmis-yenilikcilik-hedefleri.md`'deki
yenilikçilik hedefi #2 ölü kodmuş.

Yapılanlar:
- `extract_tahsis_ucreti()` eklendi. `masraf_durumu`'ndan **bağımsız** koşar.
  Negasyon ("alınmaz", "talep edilmez", "yoktur") → `{value: 0.0}`, yani
  "bilgi yok" değil "ücret sıfır" (§5.5 "masrafsız finansman" yorumu).
- `synonyms.py`'ye `NEGATION_RE` eklendi (sözcük listesi değil desen — fiil
  çekimlerini yakalasın diye).

Bu sırada bulunan iki hata:

1. **Binlik ayırıcı / cümle sonu karışması.** Cümlecik ayırıcı naif olarak
   `[.;\n]` üzerinden bölüyordu; `.` Türkçede aynı zamanda binlik ayırıcı
   olduğu için `"1.500,00 TL"` ifadesi `"1"`de kesilip **1500 yerine 1.0**
   üretiliyordu. Düzeltme: `(?<!\d)[.;](?!\d)` — rakamlar arasındaki noktada
   bölme.

2. **Çelişki tespiti yazım sırasına bağlıydı.** `extract_masraf` `re.search`
   (yalnız ilk eşleşme) kullanıyordu:
   - `"Masrafsızdır. Tahsis ücreti 500 TL."` → çelişki yakalanıyor ✓
   - `"Tahsis ücreti 500 TL. Masrafsızdır."` → **kaçıyordu** ✗

   Düzeltme: `finditer` ile tüm masraf bahisleri taranır. `masraf_durumu` artık
   kampanyanın **iddiasını** taşır — metinde herhangi bir yerde "masrafsız"
   iddiası varsa `has_fee=False` döner; gerçekte ücret olup olmadığını
   `tahsis_ucreti` söyler, uyuşmazlığı `contradiction.detect()` yakalar.
   Böylece her iki yazım sırası ve ALL-CAPS çalışıyor, yanlış pozitif yok.

**Değerlendirme semantiği bulgusu (H3'ün somut kanıtı):** yeni alan eklenince
eval `tahsis_ucreti` için P=0.00, FP=1 raporladı. İnceleyince görüldü ki bu
**doğru bir çıkarım**: gold kayıt #1'in metni birebir "Tahsis ücreti 500 TL"
diyor, ama gold `fields` sözlüğü bu alanı hiç anote etmemiş. Yani doğru çıkarım
yanlış pozitif sayılıyordu. Gold kaydı düzeltildi.

Bu, gold formatının **"gerçekten yok" ile "anote edilmemiş"i ayırt edemediğini**
gösteriyor — `absent_fields` alanı olmadan precision tanımsız, halüsinasyon
oranı ölçülemez. Gold şema göçü (İH2b) sırasında bu ayrım eklenecek.

Dokunulan dosyalar:
- `app/src/extraction/rules/extract.py` (extract_tahsis_ucreti, extract_masraf)
- `app/src/extraction/rules/synonyms.py` (NEGATION_RE)
- `app/data/gold/gold.sample.json` (kayıt #1'e tahsis_ucreti eklendi)
- `app/tests/test_contradiction.py` (yeni — 13 test)

Test durumu: **85 test yeşil** (72 → 85).

UYARI: eval şu an MICRO F1 = 1.00 raporluyor ama gold set **3 kayıt** —
istatistiksel olarak anlamsız, yalnızca "regresyon yok" demek. Gerçek sayı
gold set 150–300'e çıkınca (İH2b) üretilecek; o zamana kadar hiçbir yerde
başarı iddiası olarak kullanılmayacak.

## [2026-07-27] sorun+kod | Gün 1: Türkçe küçük-harf hatası (H1) + lisans denetimi

Bağlam: Yarışmanın çevrimiçi süreci bugün başladı (Kick Off; 26 Ağustos'a kadar
30 gün). Kod tabanı denetlenirken, gerçek veriye geçildiğinde sistemi sessizce
bozacak bir hata bulundu ve düzeltildi.

**Bulunan hata (H1):** Python'un `str.lower()` metodu Türkçe için hatalıdır —
`'TAŞIT'.lower()` → `'taşit'` (I→i, olması gereken ı) ve `'ÜCRETSİZ'.lower()`
→ `'ücretsi̇z'` (İ→i + U+0307 birleşen nokta). Banka sitelerindeki başlıklar
büyük harflidir; kod tabanındaki 7 çağrı yeri etkileniyordu. Bugüne kadar
görülmemesinin tek sebebi test fixture'larının küçük harfle yazılmış olması.

Ölçülen etki (gerçek ALL-CAPS banka metniyle, önce/sonra):

| | önce | sonra |
|---|---|---|
| kampanya türü sınıflandırma | `None` (tamamen kaçırıldı) | `Taşıt Finansmanı` |
| `masraf_durumu` | `has_fee: True` (**işaret ters**) | `has_fee: False` |

İkincisi bir kaçırma değil **yanlış değer**: "ÜCRETSİZ" yazan metni sistem
"masraf var" diye okuyordu ve bu değer karşılaştırmaya akıp §5.7 "En Düşük
Masraf" kriterinde bankayı yanlış sıralardı.

Çözüm: `preprocessing/clean.py`'ye `tr_fold()` (TR-doğru küçük harf, **uzunluk
koruyan** → source_span offset'leri güvenli) ve `tr_fold_ascii()` (+ diakritik
sadeleştirme) eklendi. Tüm eşleşme sözlükleri modül yüklenirken katlanmış
görünüme çevriliyor (`FOLDED_TYPE_HINTS`, `_FOLDED_FREE_TOKENS` vb.);
varyantlar frozenset ile tekilleştirildiği için mükerrer sayım yok.

Diğer Gün 1 kalemleri:
- `docs/model-license-audit.md` açıldı (şartname §5.10 kanıt katmanı).
  Trendyol-LLM-8B-T1 **BLOKE** — taban model zinciri doğrulanmadan kullanılamaz
  (Llama tabanlıysa Community License → §5.10 ihlali). Birincil model Qwen3-8B.
- `trafilatura` opsiyonele alındı: kendi yorumunda "GPLv3+" yazıyordu, Apache-2.0
  ile dağıtımda uyumsuz. Kod onsuz çalışıyor (`strip_html` fallback). Lisansı
  doğrulanana kadar teslim imajına girmiyor.
- `gliner` ve `zeyrek` yorum satırına alındı — kod tabanında sıfır referansları
  var; §9 "bağımlılıkların eksiksiz listesi" şartı yanıltıcı olmasın diye.
- `requirements-api.txt` ayrıldı (ince teslim imajı).
- `Dockerfile.api` düzeltildi: elle paket listesi yerine requirements dosyası,
  offline env bayrakları, ve `eval/` + `tests/` imaja dahil edildi — bunlar
  olmadan `docker run --network none ... unittest` kanıt koşusu imkânsızdı.
- `VLLMClient` varsayılan portu 8000 → 8001 (8000 API'nin kendi portuydu).

Dokunulan dosyalar:
- `app/src/preprocessing/clean.py` (tr_fold, tr_fold_ascii)
- `app/src/extraction/rules/synonyms.py` (katlanmış görünümler)
- `app/src/extraction/ner/classifier.py`, `app/src/extraction/rules/extract.py`
- `app/src/normalization/normalize.py`, `app/src/chatbot/router.py`
- `app/src/extraction/llm/clients.py`, `app/Dockerfile.api`
- `app/requirements.txt`, `app/requirements-api.txt` (yeni)
- `app/docs/model-license-audit.md` (yeni)
- `app/tests/test_turkish_fold.py` (yeni — 18 regresyon testi)

Test durumu: **72 test yeşil** (54 → 72), tamamen offline, 0,01 sn.

Açık uçlar:
- trafilatura lisansı doğrulanacak (ağ gerekli)
- Trendyol-LLM-8B-T1 taban model zinciri doğrulanacak
- Kalan 6 çıkarım alanı (`tahsis_ucreti` dahil) henüz yok → çelişki tespiti (H2)
  hâlâ tetiklenemiyor

## [2026-06-16] kod | app/ uçtan uca çekirdek inşa edildi

Bağlam: Kararlaştırılan v2 mimarisine göre `app/` altındaki tüm katmanlar kuruldu;
ağır modeller (vLLM/BERTurk) bu ortamda çalışamadığı için her katman **gerçek
kütüphane yolu + offline fallback** ile yazıldı. Tüm sistem modeller olmadan da
uçtan uca koşar (on-prem/offline kanıtı).

Kurulan katmanlar (hepsi test edildi):
- preprocessing, normalization (oran/para/vade/tarih/TR-sayı/aralık/negasyon)
- extraction: rules (birincil), llm (guided_json + vLLM/Ollama + Null-fallback),
  reconcile (kural birincil), ner/classifier (kural-ipucu + BERTurk yolu)
- db (SQLite offline + Postgres/pgvector şema), comparison (adil-kıyas) +
  contradiction (yenilikçilik), chatbot (router + yapısal sorgu + RAG)
- scraping (config-driven banks.yaml + offline fixtures), pipeline, api (FastAPI),
  web (Next.js dashboard+chatbot), eval (run_eval + ablation)

Doğrulama:
- **54 birim/entegrasyon testi, tamamı offline yeşil.**
- 10 banka config'ten yüklendi; 3 fixture uçtan uca işlendi.
- Chatbot doğru yönlendirdi: "en düşük kâr payı" → Kuveyt Türk %1,89 (yapısal),
  "taşıt koşulları" → RAG. Ablasyon dürüst rapor (LLM offline notu).

İlgili kararlar: [[hibrit-chatbot-text-to-sql-rag]],
[[ner-fine-tune-yerine-kural-few-shot]], [[zor-anlama-vakalari-merkezi]],
[[daraltilmis-yenilikcilik-hedefleri]], [[demo-onceden-doldurulmus-db]].

## [2026-06-16] karar | kod-projesi-mimari-v2 (5 kritik karar)

Bağlam: Önceki oturumda kullanıcının paylaştığı kod projesi planı (`CLAUDE.md v1`)
değerlendirildi; kazandıran 5 mimari değişiklik kararlaştırıldı ve `app/CLAUDE.md`
(v2) yazıldı. Bu kararlar şartname kaynağına dayanır.

Dokunulan dosyalar:

- **app/CLAUDE.md** (oluşturuldu — kod projesinin v2 operasyon kılavuzu)
- **decisions/** hibrit-chatbot-text-to-sql-rag.md,
  ner-fine-tune-yerine-kural-few-shot.md, demo-onceden-doldurulmus-db.md,
  zor-anlama-vakalari-merkezi.md, daraltilmis-yenilikcilik-hedefleri.md (oluşturuldu)
- index.md (Decisions bölümüne 5 yeni karar eklendi)
- entities/chatbot.md, syntheses/teknik-cozum-mimarisi.md (geri-bağlantı eklendi)
- _oturum-devir.md (oluşturuldu — eski `anatoliaal` oturumunun bağlam devri)

Notlar:
- Kararların 5'i de şartname değerlendirme ağırlıklarına (%30 model başarısı, %20
  fonksiyonellik, %20 on-prem, %10 yenilikçilik) dayandırıldı.
- Sıradaki adım: deterministik kural/normalizasyon katmanı + eval harness (kod).

## [2026-06-16] ingest | teknofest-tyda-sartname-2-senaryo

Kaynak: `raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf`
(sembolik link → TEKNOFEST TYDA Şartname 2. Senaryo, 25 sayfa, ~36k karakter).
Tek pass kurulum + ilk ingest.

Dokunulan dosyalar:

- **sources/teknofest/** 2026-06-16-teknofest-tyda-sartname-2-senaryo.md (oluşturuldu)
- **entities/** teknofest.md, bilisim-vadisi.md, bddk.md,
  turkiye-acik-kaynak-platformu.md, t3kys-basvuru-sistemi.md, github.md,
  chatbot.md, dashboard.md, veri-seti.md, katilim-bankalari.md (oluşturuldu)
- **concepts/** katilim-bankaciligi.md, kar-payi-orani.md, nlp.md,
  bilgi-cikarimi.md, metin-siniflandirma.md, kampanya-turleri.md,
  veri-on-isleme.md, veri-normalizasyonu.md, yapilandirilmis-veri-formati.md,
  on-premise-uygulanabilirlik.md, acik-kaynak-yaklasimi.md, web-scraping.md,
  urun-karsilastirma.md (oluşturuldu)
- **decisions/** on-premise-calistirilabilir-mimari.md,
  apache-2-acik-kaynak-lisansi.md, python-tabanli-veri-toplama.md,
  dashboard-ve-chatbot-arayuzu.md, bddk-listesi-veri-kaynagi-kapsami.md,
  yapilandirilmis-veri-formati-zorunlulugu.md (oluşturuldu)
- **sorun/** standart-veri-formati-eksikligi.md,
  katilim-bankaciligi-terminoloji-farkliligi.md, farkli-ifade-bicimleri.md,
  manuel-karsilastirma-zorlugu.md (oluşturuldu)
- **syntheses/** yarisma-genel-bakis.md, teknik-cozum-mimarisi.md,
  teslim-ve-degerlendirme-rehberi.md (oluşturuldu)
- index.md, lint-report.md (güncellendi/oluşturuldu)

Notlar:
- Çelişki tespit edildi (demo videosu süresi 5 dk vs 1 dk) →
  teslim-ve-degerlendirme-rehberi.md içinde `## ÇELİŞKİ` ile işaretlendi.
- Slug çakışması düzeltildi: decisions kararı
  `yapilandirilmis-veri-formati-zorunlulugu` olarak adlandırıldı (concept
  `yapilandirilmis-veri-formati` ile çakışmaması için).
