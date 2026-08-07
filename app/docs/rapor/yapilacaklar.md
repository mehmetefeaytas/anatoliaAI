# Yapılacaklar — 2026-08-07 · teslime **19 gün**

Bu liste **bugünkü** durumu yansıtır. `yapilacaklar-envanteri.md` (3 Ağustos,
62 KB) tam envanterdir ama bayattır; buradaki maddelerle çeliştiğinde **bu
dosya geçerlidir**.

Sıralama ölçütü: TEKNOFEST ağırlıkları × şu anki açık.
Model Başarısı %30 · Fonksiyonellik %20 · Teknik %20 · On-Prem %20 · Yenilik %10

**S** = sende (insan işi, ben yapamam) · **B** = bende (kodlanabilir)

---

## 0. Senin kararını bekleyen — hiçbiri ilerleyemez

| # | karar | dosya |
|---|---|---|
| **K-1** | Çerçeve ayıklaması: n-gram mı, blok mu, hiçbiri mi? | `karar-bekleyenler.md` |
| **K-2** | `DEFAULT_CONFIG` hâlâ `hibrit` — ölçüm kuralı 0,10 F1 önde gösteriyor | aynı |
| **K-3** | **77 commit push edilmedi.** Şartname §20 haftalık commit istiyor | aynı |
| **K-4** | Prompt-injection LLM modunda koşulsun mu (~10 dk) | aynı |

**K-3 en aciliyetlisi.** İki dosya (`yapilacaklar-envanteri.md`,
`banka-siteleri-veri-kaynagi-haritasi.md`) `0fcab79`'da zaten depo geçmişine
girdi; dalı olduğu gibi push etmek onları yayına sokar. Geçmişten çıkarmak
`git filter-repo` ister ve geri alınamaz. Karar senin.

---

## 1. Model Başarısı %30 — en ağır kalem

| | iş | kim | durum |
|---|---|---|---|
| 1.1 | **gold.v2 anotasyonu** — 48 belge, 10 banka, kör protokol | B | koşuyor |
| 1.2 | gold.v2 üzerinde kural / orkestra kollarını ölç, gold.v1 ile **ayrı ayrı** raporla | B | 1.1 bekliyor |
| 1.3 | **K-1'i geniş sette tekrarla** (temel / n-gram / blok) — n=20'de fark gürültüydü | B | 1.1 bekliyor |
| 1.4 | Bootstrap GA + McNemar bu tur için yeniden koşulmadı | B | 1.2 bekliyor |
| 1.5 | **κ için ikinci insan anotatör.** gold.v2 bunun yerine GEÇMEZ, önceliğini artırır | **S** | başlamadı |
| 1.6 | Ö1 üç kollu terim deneyi (temel / sadeleştirme / sözlük kartı) | B | kol hazır, koşulmadı |
| 1.7 | BERTurk ince ayarı (Colab) → kural temel çizgisi 0,700 / 0,762'yi geçerse al | **S** koşar, B hazırladı | defter hazır |

## 2. Fonksiyonellik %20 — Faz G dashboard

| | iş | kim |
|---|---|---|
| 2.1 | Kıyas tablosu — hangi bankada hangi oran | B |
| 2.2 | Chatbot arayüzü — **kaynak göstererek** cevap | B |
| 2.3 | Çelişki tespiti ekranı (mentör: "çarpıcı olabilir") | B |
| 2.4 | Banka içi delta ekranı — B2B konumlandırmayı taşır | B |
| 2.5 | Güven skorlarını ticari görünümden kaldır, jüri/geliştirici moduna al | B |
| 2.6 | **"0 = ürün yok, ceza değil"** arayüzde açıkça yazsın | B |

## 3. Şartname zorunlulukları — yapılmazsa puan yanar

| | iş | kim |
|---|---|---|
| 3.1 | **5 dakikalık demo videosu** + 1 dakikalık kısa versiyon | **S** |
| 3.2 | Jüri sunumu **PDF ve PPTX** olarak | **S** |
| 3.3 | Veri setini herkese açık yayınla + **açık lisans** ata | **S** + B |
| 3.4 | Haftalık commit etiketleri (`hafta-02`, `hafta-03`…) | **S** (K-3'e bağlı) |
| 3.5 | `assets/demo_backup.mp4` — canlı demo çökerse tek sigorta | **S** |
| 3.6 | Ağ kapalı uçtan uca demo provası (Wi-Fi kapalı + container ağı kesik) | B + **S** |

## 4. Mentör / insan işleri

| | iş | kim |
|---|---|---|
| 4.1 | **Cavide Hanım'a dönüş**: TCMB çapraz analizinin 19 terimlik `ayrim_notu` zenginleştirme önerisi onayını bekliyor | **S** |
| 4.2 | Samet Bey'in ödevi: problem / hangi sorun / farkımız / MVP / somut bitiş | **S** |
| 4.3 | 4 mentör toplantısı şartının tuttuğunu sekretaryaya doğrula | **S** |
| 4.4 | `iletisim@teknofest.org` — ücretli LLM sorusu; **yazılı cevap savunma olur** | **S** |

## 5. Teknik borç — ölçülmüş, kapatılmamış

| | iş | not |
|---|---|---|
| 5.1 | `data/demo.db` bayatlayabiliyor | 31 Tem'de kurulmuş, 3 Ağu'da korpus büyümüş, kimse fark etmemişti. Kurulum tarihi ile korpus tarihini karşılaştıran bir kapı gerekiyor |
| 5.2 | **Sözleşme PDF'leri kampanya gibi işleniyor** | Ölçüldü: 113 PDF belgesi (%6,4) kampanya olarak kayıtlı, **41'i kıyaslanabilir alan taşıyor** (oran/vade/tutar) ve karşılaştırma tablosuna giriyor. Akit metni kampanya değildir: erişimde (RAG) KALMALI, kıyasta OLMAMALI. Çözüm `campaigns` tablosuna `belge_turu` (kampanya/sözleşme) alanı ister — korpus yolundaki bölümden türetilir. Şema göçü + iki backend |
| 5.3 | `müşaraka` korpusta 3 belgede, hiçbiri tanım değil | veri boşluğu — kapatılacaksa hedefli toplama gerek |
| 5.4 | Güvenlik setinde 2 kayıt düşüyor (C05, K02) | ikisi de eski, bu turda gelmedi |
| 5.5 | `rakip-analizi.md` teslim öncesi tekrar koşulmalı | görülen depolar çalışma depoları, nihai teslim değil |
| 5.6 | `karz-ı hasen` tokenizasyonda `karz` + `ı` + `hasen` oluyor | tek harflik `ı` gürültü token; erişim skorunu bozabiliyor |

---

## Bu turda kapananlar (kayıt için)

- Klasik veriyle ince ayar / RAG **reddedildi**, gerekçesi kalıcı kayıtta
- Klasik korpus dizinin kendisinde **"YARIŞMA KAPSAMI DIŞI"** etiketli
- **TCMB Terimler Sözlüğü** (314 terim) karşıt-otorite referansı olarak eklendi;
  katılım terimlerinin **%93,1'i** TCMB'de yok — tezin ölçülmüş kanıtı
- RAG terim kapsaması **4/15 → 14/15** (korpus tazelendi + erişim eşiği oransal oldu)
- Gecikme cezası maddesinden kâr payı oranı çıkarma hatası kapatıldı (**15 → 1**)
- `demo.db` yeniden kuruldu: **849 → 1761 belge**
- Ölçüm seti için 48 belgelik tabakalı aday havuzu üretildi
