---
başlık: Çelişki tespiti — kod yolu tutarsızlığı (kapatıldı)
durum: ölçüldü ve düzeltildi (2026-08-20)
girdi: scripts/celiski_canli.py (okundu, değiştirilmedi) + docs/rapor/celiski-canli-ornek.md
        + iki gerçek hasat turu (c3f3b90 2026-07-30/849 belge, e05bc83 2026-08-03/1635 belge)
        + güncel data/raw (1782 belge, tek anlık görüntü)
dosyalar: src/comparison/contradiction.py, tests/test_celiski_bitis_deseni.py
---

# Çelişki tespiti — kod yolu tutarsızlığı: `_END_PATTERNS` vs `extract_kampanya_suresi`

## 1. Bulgu (girdi, kendi ölçmedim)

`scripts/celiski_canli.py --fire-test` (başka bir ajanın çıktısı, bu raporda
yalnız okundu) şunu ortaya çıkardı: korpustaki 140 "aynı URL, farklı
content_hash" kaydından 49'unda bir finansal alan gerçekten değişmişti (40
`kampanya_suresi`). Bu 40 aday üretimdeki `detect_across()`'a verildiğinde
**yalnız 6'sı** `Contradiction(kind="capraz_kampanya_bitisi")` üretiyordu.
Kalan 34 ateşlenmiyordu çünkü `src/comparison/contradiction.py`'deki
`end_date_claims()`'in `_END_PATTERNS`'i, korpusta **en sık geçen** bitiş
biçimini yakalamıyordu: `"1 – 31 Ay YYYY tarihlerinde geçerlidir"` (gün-gün,
ortak yıl). Genel alan çıkarıcı `extract_kampanya_suresi`
(`src/extraction/rules/extract.py`, `kampanya_tarih_araligi()` üzerinden) bu
biçimi zaten yakalıyordu — iki kod yolu sessizce farklı sıkılıktaydı ve bu
fark hiçbir yerde yazılı değildi.

## 2. Niçin dar — bu gerekçe hâlâ geçerli, korundu

`contradiction.py`'nin kendi tasarım ilkesi (modül docstring'i, "sayı değil
doğruluk"): çelişki iddiası üretmek, alan çıkarmaktan DAHA YÜKSEK kesinlik
gerektirir — yanlış çelişki iddiası kullanıcıya "bu iki sayfa çelişiyor" diye
yanlış bilgi verir; bu, alanı `null` bırakmaktan daha kötü bir hatadır. Bu
yüzden `_END_PATTERNS` bilerek dar tutulmuştu (yalnız "kampanya" sözcüğü ≤80
karakter önde + "geçerli" ya da açık bir başlık). Bu gerekçe **hâlâ geçerli**;
karar bu ilkeyi terk etmek değil, ilkeyi bozmadan ÖLÇÜMLE DOĞRULANMIŞ ek
biçimler eklemekti.

## 3. Karar: GENİŞLET — iki sayı ile

Desen yazmadan önce 40 adayın hepsi tam korpustan (2465 belge, iki hasat turu
birleşik) çekildi; adayların gerçek metinleri okundu (bkz. §4 yöntem).
Ölçülen iki sayı:

- **34 ateşlenmeyen adaydan kaçı, deseni genişletsen DOĞRU çelişki üretir?**
  17/34 (idx 0,1,7,8,9,10,12,14,17,18,19,20,21,35,36,37,38 — bkz. §5 tablo).
  Tam korpusta (2465 belge, yalnız bu iki yeni desen) yeni desenler
  **97 + 14 = 111** belgede ateşledi; bunların **99'u** genel alan
  çıkarıcının kanonik değeriyle TUTARLIYDI.
- **Kaçı YANLIŞ çelişki üretir (banka tarih değiştirmemiş, çıkarım hatası)?**
  **0.** Genel çıkarıcıyla "tutarsız" görünen 12 belge TEK TEK elle
  doğrulandı — hepsinde YENİ DESEN doğruydu, genel çıkarıcının KENDİSİ
  yanlıştı (Ziraat Katılım sayfalarında "Diğer Kampanyalar" kenar çubuğundaki
  alakasız "Son Gün DD.MM.YYYY" tarihini yakalıyordu — bkz. §6). Sıfır gerçek
  yanlış-pozitif ölçüldü.

Bu iki sayı olmadan desen yazılmadı — önce tam korpus taraması yapıldı, sonra
karar verildi.

## 4. Yöntem (tekrar üretilebilir)

```bash
python3 -m scripts.celiski_canli --fire-test         # 40 adayın 6'sının ateşlediği patch-öncesi durum
python3 -m pytest tests/test_celiski_bitis_deseni.py -q
python3 -m pytest tests -q
```

Tam-korpus tutarlılık taraması (bu raporun §3'teki 111/99/12 sayıları) iki
gerçek hasat turunun git blob'larından (`c3f3b90`, `e05bc83`) tüm 2465 belge
metnini çekip her adayda hem yeni desenleri hem `extract_kampanya_suresi`'i
çalıştıran, tek seferlik bir betikle üretildi (kalıcı script eklenmedi —
sahiplenilen dosya listesi `scripts/celiski_canli.py`'ye yazmayı yasaklıyor;
yöntem burada tarif edildi, sonuç `contradiction.py`'ye yorum olarak
işlendi).

## 5. Eklenen iki desen — hangi adayları kazandırdı

| Yeni desen | Çapa | Örnek (gerçek korpus) | Tam korpus: ateş/tutarlı |
|---|---|---|---:|
| "gün-gün ortak yıl" + geçerli | `kampanya...D1-D2 tarih(i\|leri)(nde\|arasında)...geçerli` | "Kampanya 1 – 31 Temmuz 2026 tarihlerinde geçerlidir" | 97 / 85 tutarlı, 12 tutarsız (hepsi oracle hatası, bkz. §6) |
| "Kampanya Dönemi:" başlığı | `kampanya dönemi:? D1-D2` (geçerli GEREKMİYOR, pattern3 ile aynı güven) | "Kampanya Dönemi: 16 Haziran - 31 Temmuz 2026" | 14 / 14 tutarlı, 0 tutarsız |

**Elenen üçüncü aday** — "Kampanya Koşulları" başlığı + gün-gün, "geçerli"
GEREKMİYOR: yalnız 3 ek aday kazandırıyordu (idx 25,27,30) ama başlığın
KENDİSİ (`"Kampanya Koşulları"`) sayfada birden çok kez tekrarlanabiliyor
(liste sayfası sinyali — bkz. §7); "geçerli" gibi ikinci bir doğrulama
olmadan bu başlık tek başına yeterince güvenilir bir çapa değil. Kazanç/risk
oranı düşük görüldü, EKLENMEDİ.

**Bilerek dar bırakılan (false negative, kabul edildi):** tek tam tarih +
"tarihine kadar" ama "geçerli" YOK ve "kampanya" sözcüğü de 80 karakter içinde
YOK (ör. "31 Temmuz 2026 tarihine kadar www.casper.com.tr..." — 7 aday, idx
26,28,29,31,32,33,34). Bu tam olarak modülün özgün "31 Ağustos'a kadar tahsil
edilmeli" yanlış-pozitif kaynağının şeklidir; iki çapadan biri bile yoksa
genişletilmedi.

## 6. Yan bulgu: genel çıkarıcının kendi hatası (bilgi amaçlı, düzeltilmedi)

Tutarlılık taramasındaki 12 "tutarsız" örnek incelenince şu ortaya çıktı:
`extract_kampanya_suresi`'in TEK-TARİH dalı, Ziraat Katılım'ın kart kampanyası
sayfalarında (ör. `kart-kampanyalari/kurban-bayramina-ozel-...`) sayfanın
KENDİ kampanyasının tarihini değil, sayfadaki **"Diğer Kampanyalar" kenar
çubuğunun** ilk "Son Gün DD.MM.YYYY" metnini yakalıyor — alakasız bir başka
kampanyanın bitiş tarihi. Bu `src/extraction/**` içinde, bu ajanın
sahiplenmediği bir dosyada; burada yalnız RAPORLANIYOR, dokunulmadı. Bu bulgu
aynı zamanda "iki kod yolu birbirinden bağımsız gelişti" tezini tersinden
doğruluyor: genel çıkarıcı bazen `contradiction.py`'nin sıkı deseninden DAHA
AZ güvenilir.

## 7. Ek olarak kapatılan, ÖNCEDEN VAR OLAN bir hata

Genişletme sırasında `_rule_conflicting_end_dates` (belge içi çelişki
kuralı) için bir liste-sayfası riski ölçüldü: T.O.M. Bank'ın
`kampanyalar.html` sayfası gibi, HER BİRİ kendi "Kampanya Koşulları"
başlığına sahip birden çok kampanyayı art arda listeleyen sayfalarda, genişleyen
desenler her kampanyanın kendi (gerçek) bitiş tarihini ayrı ayrı yakalayınca
belge tek bir kampanyaymış gibi "çelişen bitiş tarihi" sanılabiliyordu.

Bu, YENİ bir risk değil, **ÖNCEDEN VAR OLAN** bir hataydı: mevcut
`tests/test_contradiction_across.py::test_liste_sayfasi_tumu_icin_hukum_vermez`
testinin sentetik T.O.M. Bank metni, PATCH ÖNCESİ kodla bile (mevcut
`_END_PATTERNS`, pattern2 iki tam tarihi zaten yakalıyordu) sessizce bir
`celisen_kampanya_bitisi` hayaleti üretiyordu — o test yalnızca
`suresi_dolmus_kampanya` türünü kontrol ettiği için bu görünmüyordu. Genişleme
bunu gerçek korpusta (T.O.M. Bank'ın kendi sayfası) da tetikler hale
getirdiği için bu PR'da `_multiple_campaign_blocks()` koruması eklendi:
sayfada "Kampanya Koşulları" başlığı ≥2 kez geçiyorsa `_rule_conflicting_end_dates`
susar. Bu koruma `_looks_like_listing`'in YERİNE KULLANILMADI — o koruma tek
doğrulanmış belge-içi true-positive'te (Albaraka "Temmuz Ayına Özel Fatura
Kampanyası") de True döner ve onu susturur; ölçümle doğrulandı, testle
sabitlendi (`tests/test_celiski_bitis_deseni.py::TestCokluKampanyaBlogu`).

## 8. Ateşleme sayısı — önce / sonra

**Tarihsel diff korpusu (40 gerçek `kampanya_suresi` değişikliği adayı,
`scripts/celiski_canli.py --fire-test` ile):**

| | Önce (patch öncesi, belgelenmiş) | Sonra (bu PR) |
|---|---:|---:|
| Ateşleyen aday | 6 / 40 | **13 / 40** |

**Güncel tek-anlık-görüntü korpus (1782 belge, `python -m src.comparison.scan`):**

| Tür | Önce | Sonra |
|---|---:|---:|
| `capraz_kampanya_bitisi` | 0 | **6** |
| `suresi_dolmus_kampanya` | 10 | 13 (yan etki: aynı genişleyen `end_date_claims` `_rule_expired_but_published`'i de besliyor) |
| `celisen_kampanya_bitisi` | 1 | 1 (değişmedi — `_multiple_campaign_blocks` korumasıyla birlikte) |
| `celisen_tutar_bandi` | 4 | 4 (değişmedi, ilgisiz) |

Yeni 6 `capraz_kampanya_bitisi` bulgusunun 6'sı da Albaraka'nın "worldpuan"
ödül kampanyaları serisi (ör. `seturda-7500-tlye-varan-worldpuan`,
`_1`, `_2`, `_3` — bankanın KENDİ URL biçimi, aylık tekrar eden ayrı
sayfalar). **Dürüstlük notu (kapsam dışı, düzeltilmedi):** bunlar muhtemelen
gerçek "aynı anda çelişen iki iddia" değil, ART ARDA gelen aylık edisyonlar
(Mayıs/Haziran/Temmuz/Ağustos); `product_key()`'in sürüm-soneki kırpma mantığı
(`_1`/`_2`/`_3`'ü "aynı ürün" sayması) bu durumda ayrı, sıralı kampanyaları tek
gruba koyuyor. Bu, `product_key()`'in kendi tasarımına ait, bu PR'ın kapsamı
DIŞINDA bir sınır durumu — `_END_PATTERNS` genişlemesi bunu YARATMADI, yalnız
GÖRÜNÜR kıldı (önceden `end_date_claims` bu sayfalarda hiç ateşlemiyordu).
Takip kararı gerekiyor: `product_key()` sürüm-soneki kırpmasının ne zaman
"aynı sayfa yeniden tarandı" ne zaman "bankanın kendi ayrı sayfa serisi"
olduğunu ayırt etmesi gerekebilir — bu dosyanın (`contradiction.py`) sahibi
olarak öneriyorum ama bu PR'da UYGULAMADIM (kapsam: yalnız `_END_PATTERNS`).

## 9. Test paketi

- Yeni: `tests/test_celiski_bitis_deseni.py` — 13 test, hepsi pozitif +
  karşı-örnek çiftleri halinde (gün-gün deseni, Kampanya Dönemi başlığı,
  çoklu-kampanya-bloğu koruması). Hepsi geçiyor.
- Tam paket: `python -m pytest tests -q` → **3242 geçti, 1 BİLİNEN ve
  AÇIKLANMIŞ hata, 53 atlandı.**
  - Bilinen hata: `tests/test_contradiction_across.py::TestKorpusRegresyonu::test_hayalet_alarmi`
    — `GHOST_CEILINGS["capraz_kampanya_bitisi"]` tavanı 5, güncel korpus artık
    6 gerçek (hayalet değil, §8'de kanıtlı) bulgu üretiyor. Bu dosya bu
    ajanın sahiplenmediği bir dosya (`tests/test_contradiction_across.py`,
    yalnızca `src/comparison/contradiction.py` + yeni test dosyası +
    bu rapor yazma izni var); tavanın 5'ten örn. 12'ye (dosyanın kendi
    kuralı: "ölçülen değerin ~2 katı") çıkarılması gerekiyor. **Ana oturuma
    devrediliyor.**

## 10. Sonuç

Karar **genişletmekti**, dar tutmak değil — ama yalnız ölçümle doğrulanmış iki
biçimle (gün-gün+geçerli, Kampanya Dönemi: başlığı), sıfır ölçülen
yanlış-pozitifle. Üçüncü aday desen (Kampanya Koşulları başlığı, geçerli
gerektirmeyen) kazanç/risk oranı düşük görüldüğü için elendi — bu da
belgelendi. Süreçte, genişletmeden bağımsız, ÖNCEDEN VAR OLAN bir liste-sayfası
hatası bulundu ve kapatıldı. Kalan tek açık madde `GHOST_CEILINGS` tavanının
ana oturum tarafından güncellenmesi.
