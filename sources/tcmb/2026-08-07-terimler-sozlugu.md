---
title: "TCMB Terimler Sözlüğü — ikinci terminoloji otoritesi (314 terim)"
tags: [source, tcmb, terminoloji, konvansiyonel-bankacilik, capraz-analiz, veri-toplama]
source: "https://www.tcmb.gov.tr/wps/wcm/connect/tr/tcmb+tr/main+menu/banka+hakkinda/egitim-akademik/terimler+sozlugu/"
date: 2026-08-07
status: stable
---

# TCMB Terimler Sözlüğü — ikinci terminoloji otoritesi

## goal

Projeye **ikinci bir terminoloji otoritesi** kazandırmak. Elimizdeki tek sözlük
(mentörün 101 girdilik, avukat teyitli katılım finansı sözlüğü)
katılım tarafını tanımlıyor; karşı tarafı — konvansiyonel bankacılığın resmî
dilini — tanımlayan bir referansımız yoktu. Türkiye Cumhuriyet Merkez Bankası'nın
Terimler Sözlüğü bu boşluğu doldurur ve aynı zamanda projenin temel tezini
(*"konvansiyonel otorite katılım terminolojisini kapsamıyor"*) **sayıyla test
etmeye** imkân verir.

## what-was-done

**1. robots.txt doğrulaması (önce).** `https://www.tcmb.gov.tr/robots.txt`
→ HTTP 200, içeriğin tamamı iki satır:

```
User-agent: *
Disallow: */search+results
```

Terimler Sözlüğü yolu bu kalıba uymuyor → **kazıma izinli**. `Crawl-delay`
direktifi yok; [[CLAUDE.md]] §14 gereği yine de istekler arasında 3 sn beklendi.

**2. Toplama.** Sözlüğün tamamı **tek HTML sayfasında**, sunucu tarafında
üretiliyor — JavaScript ile yüklenen gizli bölüm yok. HTTP 200, 239 180 bayt.
Paylaşım bağlantısındaki alternatif URL (`.../Terimler+Sozlugu/Sozluk`)
byte-özdeş aynı içeriği döndürdüğü için kaydedilmedi.

**3. Ayrıştırma.** İç içe `div.block-collapse` yapısı: dış düğüm harf grubu
(A, B, C-Ç … Z), iç düğüm tek terim. Başlık biçimi `Türkçe Terim (English Term)`.
**314 terim** çıkarıldı; 312'sinde İngilizce karşılık var (Sukuk ve Samurai Bonds
hariç). **Eksik yok** — ham HTML'de 336 `block-collapse-title` düğümü var,
22'si harf başlığı, 314'ü terim; sayı birebir tutuyor. J/Q/W/X harf grupları
sayfada hiç yok (Türkçede bu harflerle başlayan terim bulunmuyor).

**4. Çapraz analiz.** İlk naif eşleştirme 18 kesişim verdi; bu sayı yanlış çıktı.
İki tuzak ölçüldü ve ayrıştırıldı: (a) `Riba` girdisinin `varyantlar` listesinde
birebir "faiz" yazılı olduğu için TCMB'nin "Faiz Oranı" başlığıyla eşleşiyor —
bu **kapsama değil çatışma**; (b) `en` alanı üzerinden eşleşme İngilizce
sahte-dost üretiyor (`Vekâlet`/Agency → Merkezi Kayıt Kuruluşu). Üç ayrı geçişe
bölündü: KAPSAMA / ÇATIŞMA / SAHTE-DOST.

Ölçülen ana sayılar:

| Ölçüm | Sonuç |
|---|---|
| Gerçek kavramsal kesişim | **4 / 101** (Finansal kiralama, Sukuk, Kira sertifikası, + kısmî İpotek) |
| TCMB'de karşılığı olmayan katılım terimi | **94 / 101 (%93,1)** |
| Çekirdek 18 fıkhî terimden TCMB'de olmayan | **17 / 18 (%94)** — tek istisna Sukuk |
| "kâr payı" — TCMB'nin 314 başlık **ve** 314 tanım metninde | **sıfır** |
| "katılma hesabı" / "özel cari hesap" | **sıfır** |
| Doğrudan çatışma çifti | **24 çift, 19 ayrı katılım terimi** |
| TCMB'de `faiz` kökü | 11 başlık, 43 tanım metni |
| TCMB'de `kredi` kökü | 7 başlık, 26 tanım metni |
| Hedef korpusta isabet (389 katılım belgesi) | katılım sözlüğü **%55,4** — TCMB **%14,0** |

**5. Tezin dürüst sınırı.** *"TCMB katılım terminolojisini hiç kapsamıyor"*
ifadesi **savunulamaz**. TCMB'de İslami finansa değen 5 kayıt var (%1,6):
Sukuk, Kira Sertifikası, İslami Finansal Hizmetler Kurulu (IFSB), Uluslararası
İslami Likidite Yönetimi Kuruluşu (IILM) ve geçerken anan Parasal Sektör.
Savunulabilir ifade oransaldır: *"%1,6'sı değiyor; çekirdek 18 terimin 17'si ve
projenin merkezî terimi 'kâr payı' hiç geçmiyor."*

**6. Beklenmedik bulgu — TCMB bizi doğruluyor.** TCMB'nin kendi Sukuk tanımı
şunu yazıyor: *"Tahvil borca dayalı sertifika, sukuk ise varlığa dayalı
sertifika olarak nitelendirilebilir."* Bu, sözlüğümüzün `Sukuk` girdisindeki
`ayrim_notu` ile birebir aynı ayrımdır. Yani en güçlü ayrım kartlarımızdan biri
artık **düzenleyici otoritenin kendi metniyle** desteklenebilir.

## files-changed / touched

Oluşturulan:

- `app/data/terminology/tcmb-terimler.json` — 314 terim (`terim`, `tanim`,
  `ingilizce`, `kaynak_url`, `otorite_tipi: konvansiyonel`)
- `app/data/terminology/_tcmb_ham/terimler-sozlugu.html` — ham kanıt (239 KB)
- `app/data/terminology/_tcmb_ham/terimler-sozlugu.html.meta.json` — künye
  (kaynak_url, cekilme_tarihi, http_durum, sha256, robots_kontrol_sonucu)
- `app/scripts/tcmb_sozluk_ayristir.py` — HTML → JSON ayrıştırıcı
- `app/scripts/tcmb_capraz_analiz.py` — üç geçişli ölçüm aracı (yeniden üretilebilir)
- `app/docs/terminoloji-tcmb-capraz.md` — çapraz analiz raporu

Bahsi geçen ama **değiştirilmeyen** dosyalar:

- `app/data/terminology/katilim-terim-sozlugu.json` — karşılaştırma tarafı
- `app/src/domain/terminology.py` — `degildir` / `ayrim_notu` semantiği,
  kart önceliği, bağlam bütçesi
- `app/scripts/jargon_lint.py` — `YASAK_KOKLER`, `oneri_tablosu()`
- `app/src/chatbot/safety.py` — kapsam kapısı

## decisions

Bu ingest'ten çıkan ve `decisions/` altına açılması gereken karar:

- **TCMB sözlüğü katılım sözlüğüyle BİRLEŞTİRİLMEZ.** Üç ölçülmüş gerekçe:
  (1) TCMB kayıtlarında `degildir`/`ayrim_notu`/`risk_notu` alanı yok,
  `terminology.py::_kart_onceligi` bu alanlara göre sıraladığı için alansız
  314 kayıt gerçek ayrım kartlarını bağlam bütçesinden dışarı iter;
  (2) `jargon_lint.oneri_tablosu()` karşılıkları `degildir` alanından türetir,
  TCMB kayıtları hiçbir karşılık üretmez; (3) katılım sözlüğü zaten ~76 000
  karakter ve `OLLAMA_NUM_CTX` 8192 token — TCMB bütçeyi üçe katlar.

- **TCMB'nin projedeki rolü: karşıt-otorite referansı, terim kaynağı değil.**
  Birincil rol `jargon_lint` karşıt örnek havuzu (11 faiz + 7 kredi başlığı,
  43 + 26 tanım metni; ayrıca klasik korpusta geçip katılım korpusunda hiç
  geçmeyen 9 ayırt edici terim). İkincil rol `ayrim_notu` alıntı kaynağı
  (19 terim için otoriter karşı-tanım).

## issues

- **Sahte-dost tuzağı ölçüldü.** İki sözlük otomatik eşleştirilirse 11 katılım
  terimi yalnız İngilizce üzerinden yanlış eşleşiyor (Vekâlet/Agency → MKK,
  Tediye/Payment → 7 ödeme sistemi başlığı, Mahsup/takas → Swap, Arındırma →
  Mevsim ve Takvim Etkisinden Arındırma). İleride herhangi bir otomatik sözlük
  hizalaması yazılırsa bu tuzağa düşer.
- **Çelişkinin niteliği alışılmadık.** Bu, "iki kaynak aynı terimi farklı
  tanımlıyor" türü bir çelişki değil: TCMB, sözlüğümüzün *yasak* dediği
  kavramları **normatif ve nötr** tanımlıyor. TCMB "Tutsat (İpotek) Kredileri"
  maddesi konut finansmanını "ödünç verilerek" ve "sabit faizle" anlatır —
  murabaha temelli bir ürünü bu tanımla yorumlayan model doğrudan uyum ihlali
  üretir.

## open-threads

- Korpusta geçen **39 mezhep-nötr terimin** (IBAN, valör, akreditif, itfa,
  mutabakat…) `otorite_tipi: "notr"` yardımcı sözlüğe alınması **yapılmadı** —
  ayrı karar, ayrı commit gerektirir.
- `ayrim_notu` alanlarına TCMB alıntısı eklenmesi **yapılmadı**; sözlük mentör
  teyitli olduğu için alan düzenlemesinden önce **mentörün onayı**
  alınmalı.
- TCMB terimlerinin kalıcı ID'si veya sürüm etiketi yok; sayfa güncellenirse
  fark tespiti yalnız `.meta.json` içindeki SHA-256 ile yapılabilir. Periyodik
  yeniden çekme + hash karşılaştırması kurulmalı.
- Üçüncü bir otorite (BDDK veya TBB terimler sözlüğü) ile aynı ölçüm
  tekrarlanırsa sonucun genellenebilirliği test edilmiş olur.

## Sources

- TCMB Terimler Sözlüğü —
  `https://www.tcmb.gov.tr/wps/wcm/connect/tr/tcmb+tr/main+menu/banka+hakkinda/egitim-akademik/terimler+sozlugu/`
  (çekilme 2026-08-07, HTTP 200, 239 180 bayt,
  SHA-256 `ae1e00692de152aa52ba8ee6d66cb4f76229de540dccfeabfb89346bc17daaed`)
- Ham kanıt: `app/data/terminology/_tcmb_ham/terimler-sozlugu.html` + `.meta.json`
- Çapraz analiz raporu: `app/docs/terminoloji-tcmb-capraz.md`
- robots.txt: `https://www.tcmb.gov.tr/robots.txt` (HTTP 200, 2026-08-07)

## Related

- [[2026-08-06-mentor-terim-sozlugu]] — karşılaştırmanın diğer tarafı;
  101 terimlik katılım sözlüğünün geldiği mentör maili
- [[katilim-finans-terimleri]] — katılım sözlüğünün kavram sayfası
- [[terim-sozlugu-enjeksiyon-replace-degil]] — bu ingest o kararı **sınırlıyor**:
  enjeksiyon doğru yaklaşım ama TCMB sözlüğü enjekte edilecek malzeme değil
- [[katilim-bankaciligi-terminoloji-farkliligi]] — bu ingest o sorunun
  **niceliksel kanıtını** üretiyor (%93,1 kapsanmama, 17/18 çekirdek terim yok)
