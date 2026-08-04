# Devam Durumu — internet kesintisi öncesi dondurulan hâl

**Tarih:** 2026-08-04, ~17:30
**Dal:** `veri-toplama-genislemesi`
**Neden var:** İnternet planlı olarak kesildi. Bu dosya, "başla" denildiğinde işin
**tam olarak nereden** devam edeceğini kaydeder. Tahmin yok; her sayı ölçüldü.

Teslime kalan: **22 gün** (son tarih 26 Ağustos 2026).

---

## 1. Ölçülmüş korpus durumu (dondurma anındaki)

| Ölçüm | Değer | Komut |
|---|---:|---|
| `data/raw` `.txt` belge | 1684 | `find data/raw -name '*.txt' \| wc -l` |
| ...300 karakterden kısa | 10 | aşağıdaki ölçüm betiği |
| ...600 karakterden kısa | 52 | aynı |
| ...1024 karakterden kısa | 226 | aynı |
| ...`content_status: kabuk` işaretli | 74 | aynı |
| `data/raw-classic` `.txt` belge | 724 | `find data/raw-classic -name '*.txt' \| wc -l` |
| Gümüş etiket (`silver.jsonl`) | 416 | `wc -l data/silver/silver.jsonl` |

### Kabuk belge dosyası — KAPANDI, ama kurtarmayla değil teşhisle

İki ayrı şey karıştırılmasın:

**(a) Gerçek bir regresyon vardı ve onarıldı.** Ağustos yeniden-hasadı mevcut
14 belgeyi bozmuştu (`eb67e65` 3232 bayt → `e05bc83` 306 bayt). Bunlar git
geçmişinden `.txt` + `.meta.json` **birlikte** geri alındı (`3fb361d`), yoksa
`content_hash` tutarsız kalırdı.

**(b) "Kabuk krizi"nin çoğu benim sezgiselimin YANLIŞ POZİTİFİYDİ.** 101 aday
deponun kendi Playwright fetcher'ı ile yeniden hasat edildi. Ölçülen sonuç:

| Bulgu | Adet |
|---|---:|
| Aday | 101 |
| Tarayıcı metni statikle **bayt-aynı** | 98 |
| **Sezgiselin yanlış pozitifi** (zaten tam içerikli, dokunulmadı) | 87 |
| Gerçekten gövdesiz, `kabuk` işaretlendi (8'i yeni) | 14 |
| Kurtarılan | **0** |

Kalan 14: turkiye-emlak-katilim 6, vakif-katilim 8, kuveyt-turk **0**.

- **Sezgiselim hatalıydı.** `"ana sayfa"` / `"müşteri ol"` sözcüklerini çerez
  bandı göstergesi saymıştım; oysa bu üç bankanın **her** sayfasındaki kırıntı
  yolu sözcükleri. Kuveyt Türk'ün 21/21'i yanlış pozitif çıktı (ör. 1182
  karakterlik tam kampanya metni).
- **Fetcher'da kusur yok.** Bu sitelerin gövdesi sunucuda render ediliyor;
  statik çekim zaten her şeyi alıyordu. MCP tarayıcısına bile gerek kalmadı.
- Kalan 14'te içerik **canlı sitede de yok** — `innerText` ile doğrulandı:
  yalnızca menü + başlık + kırıntı yolu. Akordeon/sekme tıklaması her sayfada
  aynı +358 karakterlik altbilgiyi getirdi. Değer uydurulmadı.

> **En kritik yakalanan tuzak:** `/kampanyalar/kampanya?slug=` adresi kampanya
> **listesine** yönleniyor ve 4166 karakter döndürüyor — yani "içerik
> kurtarıldı" gibi görünüyor. Koruma kapıları olmadan yeniden hasat **korpusu
> zehirlerdi**: her kabuk sayfaya, ait olmadığı liste metni yazılırdı.

**Sonuç ve karar:** bu bir çıkarım hatası değil, kaynağın kendi durumu.
`scrape_mode: static` **kasıtlı olarak korunuyor** — `js`'e çevirmek hasadı ~10x
yavaşlatır ve tek karakter kazandırmaz. Gerekçe `config/banks.yaml` içine
banka banka yazıldı, kanıt ise ilgili `.meta.json` dosyalarının
`recollection_result` alanlarında. 74 belge `content_status: kabuk` ile
**işaretli tutuluyor, silinmiyor** (CLAUDE.md: silme yok).

> Bu satırlar "denendi ve olmadı" bilgisini taşıdığı için değerli: yoksa bir
> sonraki oturum aynı 101 sayfayı tekrar tarayıcıyla hasat etmeye kalkar.

Ölçüm betiği (aynı sayıları üretmeli, yoksa bir şey değişmiş):

```python
import json, pathlib
raw = pathlib.Path("data/raw")
kisa = isaretli = 0
for t in raw.rglob("*.txt"):
    if len(t.read_text(encoding="utf-8", errors="replace")) < 600:
        kisa += 1
    m = t.with_suffix(".txt.meta.json")
    if m.exists() and json.loads(m.read_text()).get("content_status") == "kabuk":
        isaretli += 1
print(kisa, isaretli)
```

## 2. Gümüş sınıf dağılımı — Faz 3'ün kilidi burada

| Sınıf | Adet |
|---|---:|
| Kart | 144 |
| Alışveriş Puanı | 73 |
| İhtiyaç Finansmanı | 50 |
| Yatırım Ürünü | 48 |
| Yeni Müşteri | 41 |
| Finansman | 38 |
| **Konut Finansmanı** | **13** |
| **Taşıt Finansmanı** | **9** |

BERTurk ince ayarı (Faz 3) bu iki sınıf 20'ye ulaşmadan **yapılmayacak**;
8 sınıfın ikisi eğitilemezken makro-F1 yanıltıcı olur. Ulaşılamazsa ince ayar
atlanır ve gerekçe rapora yazılır — bu bir başarısızlık değil, ölçülmüş bir kısıt.

### Neden 13/9 hâlâ sabit — engel AĞ DEĞİL, BAĞIMSIZLIK

Belge tarafı ilerledi: `data/raw-classic` altına **106 yeni ürün belgesi** girdi
(10 banka, medyan 5509 karakter, 724 tekil `doc_id`, çakışma 0). Ama
`data/silver/` **hiç dokunulmadı**, çünkü belgeler etiketlenmedi.

İlk yazdığım gerekçe ("etiketleme ağ istiyor") **yanlıştı.** Etiketleyici repo
dışında ama JSONL sözleşmesiyle çalışıyor; bir oturum o rolü oynayabilir.
Gerçek engel bütünlük:

> Tek oturum hem **etiketleyici** hem **denetleyici** olursa üç oylu uzlaşma
> iki bağımsız oydan tek oya iner. `consensus.py` bu kipi adıyla anıyor:
> **"lastik damga"**. `VerifyVerdict.own_label`'ın ayrı bir alan olmasının tek
> sebebi bu kipi yakalamak.

Yani sahte bağımsız denetleyici üretmek 20 hedefini tutturur ama veri setinin
**kökenini savunulamaz** kılar (şartname §8). **İnternet gelse bile bu çözülmez
— ayrı bir oturum/model gerekiyor.** Etiketleme turu bu yüzden bilinçli olarak
yapılmadı.

**Projeksiyon (sonuç değil):** kural katmanı — deterministik, offline — 106 yeni
belgede **51 Konut / 36 Taşıt adayı** görüyor. Sınıf kurallarına göre düşecekler
(BES/hesap, sözlük, SSS, basın duyurusu, ticari) `devam-konut-tasit-hasati.md`
içinde tek tek sayıldı; düşüşlerden sonra ikisi de 20'yi rahatça geçiyor.
Gerçek sayı `merge` koşulunca `silver_report.json`'da çıkacak.

Hedefe henüz ulaşılmadı: **Konut 7, Taşıt 11 belge eksik** (etiketli sayıda).

---

## 3. Dondurulan üç agent

| Agent | Kapsam (yalnız bu yollar) | Bıraktığı devam notu |
|---|---|---|
| Kabuk hasadı | `data/raw/**`, `config/banks.yaml`, `src/scraping/fetcher.py` | `docs/rapor/devam-kabuk-hasati.md` |
| Konut/Taşıt hasadı | `data/raw-classic/**`, `config/banks-classic.yaml`, `data/silver/**` | `docs/rapor/devam-konut-tasit-hasati.md` |
| `split_trainable` onarımı | `scripts/split_trainable.py`, `tests/test_split_trainable.py` | `docs/rapor/devam-split-trainable.md` |

Üçü de **kendi yollarını adıyla** commit etmekle görevlendirildi. `git add -A`
hiçbirinde kullanılmadı — eşzamanlı yazan agent'ların yarım işini süpürürdü.

## 4. "başla" denince sıra

### Ağ gerektirenler (önce, çünkü kritik yolu bunlar tıkıyor)

1. Üç devam notunu oku, kaldığı URL listesinden hasadı sürdür.
2. ~~Kabuk belgeleri yeniden hasat et~~ — **YAPMA, kapandı.** Yukarıdaki (b)
   maddesi: 101 şüpheli denetlendi, kurtarılabilir değil. Tekrar denemek boşa
   ~10x yavaş bir hasat turu demek.
3. Konut/Taşıt: **hasat kısmı bitti** (106 belge geldi). Kalan iş etiketleme ve
   bu ağ işi değil — **ayrı bir oturum/model** açıp üç oylu turu koştur, aynı
   oturumda etiketleyici+denetleyici olma (lastik damga). Sonra `merge` koş ve
   gerçek sayıyı `silver_report.json`'dan oku.
4. `vakifkart.com.tr` + Kuveyt Türk / Türkiye Finans / Vakıf Katılım kart markası
   alanlarını bul (kuyruk maddesi 4). **Hiç başlanmadı** — ağ kesildiği için
   tarayıcı işi başlatılmadı.

### Ağ gerektirmeyenler (paralel yürüyebilir)

5. **Ön-anotasyonu tazele.** Satırların %28'i bayat; korpus da değişti, yani
   şimdi daha fazlası bayat. Kabuk hasadı bittikten SONRA koşulmalı, yoksa iki
   kez koşulur:
   ```
   .venv/bin/python -m scripts.preannotate
   .venv/bin/python -m scripts.to_review_csv
   .venv/bin/python -m scripts.lint_review_csv data/gold/review/*.csv   # 0 hata
   ```
6. 5 adet `evidence_weak` kaydı düzelt (`data/silver/silver.jsonl`,
   `scripts/resolve_queue.py:227`). B agent'ı aynı dosyaya yazdığı için
   **onun commit'inden sonra** yapılmalı.
7. Faz 2 — metrik hattı. Projenin **hâlâ tek gerçek metriği yok**:
   - LLM katmanını korpusta bir kez uçtan uca koştur (T-018/T-044)
   - ablasyon: kural-only / LLM-only / hibrit (T-014)
   - alan bazında P/R/F1 + makro-F1 (T-013)
   - halüsinasyon oranı, `absent` etiketlerinden (T-016)

### İnsan gerektirenler (teknik engel değil)

8. **Cohen/Fleiss κ** — kalibrasyon A dolu, B/C/D **boş**. İkinci anotatör şart;
   şartname §5.5'in "gold setin güvenilirliği" kanıtı bu sayı. Eşikler önceden
   ilan edildi: ≥0.80 kabul, 0.67–0.80 notla kabul, <0.67 zorunlu hakem turu.
9. Veri seti indirme linki (T-001), 5 dk + 1 dk demo videosu (T-002/003),
   sunum PDF/PPTX (T-004).
10. `iletisim@teknofest.org` — ücretli LLM'in tek seferlik kullanımı sorusu.
    Yazılı cevap savunma olur.

---

## 5. Kalibrasyon A — kapandı

45 satır 6 kusur sınıfında düzeltildi. Son hâl: linter **0 hata 0 uyarı**,
`build_gold` **20 kayıt** üretiyor, **14'ü 12/12 alan kapsamında**, 0 çelişki.
Biçim kararları `data/gold/review/_bicim-karti.md`'de; ilkesi şu: *şemaya sığanı
`gold_value`'ya, sığmayanı `note`'a yaz* — böylece bilgi kaybolmaz ve şema
genişlerse yeniden anotasyon gerekmez.

Anotasyon zamanı kapısı kalıcı: `scripts/lint_review_csv.py` + 30 test.
Çittiği üç **ölçülmüş** sessiz kayıp yolu:

1. Elektronik tablonun başa yazdığı sekme-adı satırı → `csv.DictReader` onu
   başlık sanıyor, **195 cevap görünmez** oluyor.
2. Tek değerli alana aralık → ayrıştırıcı ilk değeri alıyor, yani **başlangıç**
   tarihi bitiş alanına giriyor ve modelin doğru cevabı yanlışla değiştiriliyor.
3. Otomatik düzeltmenin `--`'yi em-dash'e çevirmesi → satır hiçbir belgeyle
   eşleşmiyor, `build_gold` sessizce atlıyor.

## 6. Yayın durumu

`origin/yayin/hafta-02` + `hafta-02` etiketi push edildi (T-007 karşılandı).
1314 dosya dışarıda bırakıldı, 3915 dosya yayında. Uzakta doğrulandı: 10 yasaklı
desenin **0**'ı sızdı, korpusun 1684 `.txt` dosyası gitti.

Push politikası üç kademe (gerekçesiyle `_plan`/plan dosyasında):
Kademe 1 şimdi (kod, korpus, anotasyon artefaktı) · Kademe 2 teslime yakın
(teknik rapor, yöntem belgeleri) · Kademe 3 hiç (zayıflık envanteri, keşif
haritası, iç araç promptu).

> `veri-toplama-genislemesi` dalı **olduğu gibi push EDİLMEZ**: Kademe 3
> dosyaları `0fcab79` commit'inde geçmişe girdi. Yayın her zaman ayrı dal olarak
> kurulur (git plumbing ile geçici indeks üzerinden — çalışan ağaca dokunmadan).

---

## 7. Tekrarlanmasın diye: ölçülmüş tuzaklar

1. **Sistem `python3` kullanmak.** `bs4` yok; `_extract_main_text` sessizce tüm
   HTML'i metin sanıyor. Bir kuru koşu 1569 belgenin 1418'ini yanlışlıkla
   "içerik kurtarıldı" raporladı. **Daima `.venv/bin/python`.**
2. **`git add -A`.** Eşzamanlı agent'ların yarım işini süpürür.
3. **Yeniden HASAT ≠ yeniden ÇIKARIM.** Hasat yeni dosya adı üretip anotasyon
   `doc_id` eşleşmesini bozuyor; bir turda 32 belgenin 10'u geçersiz kaldı.
   Yeniden çıkarım için `scripts/reextract_raw.py` (dosya adını korur).
4. **`belgeler/` kopyalarını `data/raw`'dan körü körüne tazelemek.** Bir kez
   3358 karakterlik gerçek içerik 287 karakterlik kabukla ezildi (git'ten geri
   alındı). Tazelemeden önce iki yönlü boyut karşılaştırması yap.
5. **`find -size -1k`.** Blok yukarı yuvarlar; `-1k` "0 bayt" demektir ve her
   zaman 0 sonuç verir. Karakter say (`-size -600c` veya Python).
6. **unittest `OK` satırını grep'lemek.** ANSI renk kodu başa geldiği için
   `^OK` tutmaz. **Çıkış koduna bak.**
7. **`content_hash`'i metni utf-8'e yeniden kodlayıp doğrulamak.** Meta'daki
   hash **orijinal yanıt baytları** üzerinde; Türk banka siteleri iso-8859-9
   servis ediyor. Bu yanlış denetim 85 belgeyi "bozuk" gösterdi. Yakalanma
   yöntemi öğretici: aynı denetim **commit'li** `live/` belgelerine kontrol
   grubu olarak uygulandı ve orada da %73 "bozuk" çıktı — yani hata denetimde.
   Bayt alanında 724/724 temiz. *Şüpheli bir ölçüm gördüğünde önce ölçümden
   şüphelen; bilinen-iyi bir küme üzerinde kontrol koş.*
8. **`grep -c '<etiket>' silver.jsonl` ile sınıf saymak.** `reason` alanı da
   sınıf adını içeriyor; grep 13 yerine 75 verir. JSONL'de sayım JSON
   ayrıştırıp `label` alanından yapılır.
9. **Paylaşımlı indeks.** `git add -A` yasağı yetmez: `git add <tek-dosya> &&
   git commit` de indeksin TAMAMINI alır ve eşzamanlı bir agent'ın hazırladığı
   dosyaları süpürür (bu oturumda `b50745a`'da oldu — 16 dosya yanlış commit'e
   girdi, kayıp yok ama gerekçe mesajı yanlış commit'te kaldı).
   **Çözüm: `git commit --only <yollar>`.**

## 8. Doğrulama komutları

```
.venv/bin/python -m unittest discover -s tests          # çıkış kodu 0
.venv/bin/python -m ruff check src/ scripts/ tests/     # temiz
.venv/bin/python -m scripts.lint_review_csv data/gold/review/*.csv   # 0 hata
.venv/bin/python -m scripts.build_gold --csv-dir data/gold/review    # derlenir
```
