# Yapılacaklar — 2026-08-14 · çevrimiçi teslime **12 gün**

Bu liste **bugünkü** durumu yansıtır. Önceki sürüm 8 Ağustos'tu ve FAZ 1–2–3
tamamlandığı için büyük bölümü bayatladı. `yapilacaklar-envanteri.md` (3 Ağustos)
tam envanterdir ama daha da bayattır; çeliştiğinde **bu dosya geçerlidir**.

| | Tarih | Kalan |
|---|---|---|
| Bugün | 14 Ağustos 2026 | — |
| Çevrimiçi süreç bitişi | 26 Ağustos 2026 | **12 gün** |
| Final (Bilişim Vadisi, fiziksel) | 27–28 Ağustos 2026 | 13–14 gün |

Sıralama ölçütü: şartname ağırlığı × açığın büyüklüğü × geri alınamazlık.
Model Başarısı %30 · Fonksiyonellik %20 · Teknik %20 · On-Prem %20 · Yenilik %10

**S** = sende (insan işi) · **B** = bende (kodlanabilir)

---

## 0. ŞU AN AÇIK — bir sonraki oturumun ilk işi

| # | iş | kim | kanıt |
|---|---|---|---|
| **0.1** | **8 dosya commit edilmemiş** — LLM çıkarım/özet token bütçesi ayrıştırması (`butceyle()`, `num_predict=1536`, çift anahtarlı önbellek, orkestratör `summary()` alanı) | B | `git status --short` → 8 `M`; `pytest tests/test_llm_client.py tests/test_llm_cikti_siniri.py` → **68 geçti** |
| **0.2** | **6 commit push edilmemiş** — son push 13 Ağu 13:30 | B | `git log origin/main..HEAD` → 6 |

İş bitmiş ve testleri yeşil; eksik olan tek şey commit + push. Şartname §20
haftalık güncelleme istiyor, bu yüzden 0.2 bekletilemez.

---

## 1. FAZ 0 — repo temizliği · **HİÇ UYGULANMADI** 🔴

Plan 12 Ağustos'ta yazıldı, yalnız **G0.6 (kırık link kapısı)** uygulandı.
Geri kalanı duruyor. Jüri repoyu 2 dakika inceleyecek; şu an sinyal gürültüye
gömülü.

| # | iş | hedef | ölçülen (14 Ağu) | kim |
|---|---|---|---|---|
| 1.1 | G0.1 — LLM talimat dosyalarını izlemeden çıkar (`git rm --cached`, diskten silme) | 0 | **2 izli** | B |
| 1.2 | G0.2 — iç çalışma dökümlerini çıkar | ≤ 70 `.md` | **188 izli** | B |
| 1.3 | G0.3 — eski eval snapshot'ları (son iki koşu kalır) | ≤ 10 dosya | ölçülmedi | B |
| 1.4 | G0.4 — kök dizin ekran görüntüleri | 0 PNG | **9 PNG** | B |
| 1.5 | G0.7 — wiki dizinlerini izlemeden çıkar (karar verilmiş: **tam temizlik**) | 0 | **59 izli** | B |
| 1.6 | G0.5 — `.gitignore` konsolidasyonu, temiz klonda `git status` boş | boş | — | B |
| ✅ | G0.6 — kırık link kapısı | — | `59b9159` ile kapandı | — |

**Sıra:** 1.1–1.4 ayrık dosya kümeleri (paralel güvenli) → 1.5 → 1.6 → G0.6
kapısını tekrar koş. G3.4 (tek teknik doküman) **zaten yazıldı** (`97cd423`),
yani 1.5'in karşılığı hazır — wiki'yi çıkarmanın önündeki engel kalktı.

---

## 2. Şartname zorunlulukları — yapılmazsa puan yanar 🔴

| # | iş | kim | durum |
|---|---|---|---|
| **2.1** | **Veri seti yayını** + açık lisans → README linkini güncelle | **S** + B | Paket tek komuta indi (`dbcc54`), **yükleme yapılmadı**. README hâlâ *"yükleme tamamlandığında buraya eklenecektir"* (satır 270). Şartname s.18 zorunlu teslim. G3.1 gold büyümesini bekliyordu — artık beklememeli, v2 ile yayınlanıp v3 gelince güncellenebilir |
| **2.2** | **5 dk demo videosu** + 1 dk kısa versiyon | **S** | Çekim listesi hazır (`sunum-ve-demo-plani.md`, `d244127`). **Çekim yapılmadı.** En uzun süren kalem — bugün başlamalı |
| **2.3** | **Jüri sunumu PDF + PPTX** | **S** | İskelet hazır (aynı belge). Materyal yok |
| **2.4** | `assets/demo_backup.mp4` — canlı demo çökerse tek sigorta | **S** | yok |
| **2.5** | Haftalık commit etiketi (`yayin/hafta-05`) | B | `yayin/hafta-04` var; yeni kademe gerekiyor |
| ✅ | Ağ kapalı uçtan uca prova | — | G4.4 koşuldu (`0154651`) — README'nin ilk bloğu temiz makinede düşüyordu, düzeltildi |

---

## 3. Model Başarısı %30 — ölçülmüş açıklar

| # | iş | kim | durum |
|---|---|---|---|
| **3.1** | **Gold 48 → 74 anotasyonu** | **S** | Dağıtım paketi hazır (`preannotations.v3.json`, `ab870d1`), örnekleyicideki tekillik kusuru düzeltildi. **`gold.v3.json` yok — anotasyon yapılmadı.** Bittiğinde eval + ablasyon + CI eşikleri yeniden koşulur |
| **3.2** | **κ yeniden ölçümü** (`round1_v2`) | **S** | Fleiss κ **0,302** ilan edildi; ilan edilmiş eşik gereği (κ<0,67 → zorunlu hakemlik + kılavuz revizyonu) kılavuz v1→v2 revize edildi ve 123 uyuşmazlık listelendi. **v2 turu doldurulmadı** — yani düzeltmenin işe yarayıp yaramadığı ölçülmedi. `ee7884d` doldurulmamış turun κ=1,000 vermesini kapattı, açığı kapatmadı |
| 3.3 | `tahsis_ucreti` ölçülebilir hale gelsin | **S** | gold.v2'de **0 kayıtta dolu** → F1 matematiksel olarak imkânsız. Çözüm kod değil, 3.1'de gold'a örnek eklemek. Yenilikçilik kartı (çelişki tespiti) buna bağlı |
| 3.4 | `hedef_kitle` F1 0,267 | B | İki hipotez kuruldu, **ikisi de ölçülüp çürütüldü** (`ebec263`, `BACKLOG.md`). Kök neden: alan açık-sınıf semantik yüklem istiyor — kural katmanının işi değil. Doğru iş: (a) LLM few-shot ile eşleştir, ya da (b) gold'a 6 desenden örnek ekleyip **LLM kolunda** ölç |
| 3.5 | `vade_ay` 0,545 (hedef 0,70) · `indirim_orani` 0,400 (hedef 0,50) | B | Kalan 3 FP'nin üçü de **semantik ayrım** istiyor (örnek metni, hak sahipliği koşulu, tablo ilk satırı) — regex ile kapanmaz. Düşük getiri; 3.1'den sonra yeniden değerlendir |
| 3.6 | Güven kalibrasyonu ECE **0,306** | B | Ölçüldü, **düzeltilmedi**. 0,90+ bandı %94,9 güven ilan edip %45,2 doğru — model en emin olduğu yerde en çok yanılıyor. Sıcaklık ölçekleme uygulamak **üretim davranışını değiştirir**, ayrı bir karardır. Sunumda "ölçtük ve kötü çıktı, gizlemiyoruz" olarak anlatılıyor — bu savunulabilir bir duruş |
| ✅ | Ablasyon (kural vs LLM vs hibrit vs orkestra) | — | **dördüncü kez** kural katmanı önde (`b05b0f0`, qwen2.5). Jüriye anlatılacak en güçlü tek bulgu |

---

## 4. Mentör / insan işleri

| # | iş | kim |
|---|---|---|
| 4.1 | Mentöre dönüş: TCMB çapraz analizinin 19 terimlik `ayrim_notu` zenginleştirme önerisi onayı | **S** |
| 4.2 | Samet Bey'in ödevi: problem / hangi sorun / farkımız / MVP / somut bitiş | **S** |
| 4.3 | 4 mentör toplantısı şartının tuttuğunu sekretaryaya doğrula | **S** |
| 4.4 | `iletisim@teknofest.org` — ücretli LLM sorusu; **yazılı cevap savunma olur** | **S** |

---

## 5. Teknik borç — düşük öncelik, teslimi bloke etmiyor

| # | iş | not |
|---|---|---|
| 5.1 | `müşaraka` 3 belgede, hiçbiri tanım değil | veri boşluğu; hedefli toplama |
| 5.2 | Güvenlik setinde 1 kayıt düşüyor (29/30) | ilan edildi, teşhis açık |
| 5.3 | `rakip-analizi.md` teslim öncesi tekrar koşulmalı | rakip 11 Ağu'da 8 commit attı |
| 5.4 | `jargon_lint` `docs/*.md` kapsamı | jüriye giden raporda ihlal yok (denetlendi) → risk sınırlı |
| 5.5 | LLM özetlerinin tam korpusta üretimi | ~28 sn/belge, tam korpus ~13 saat. Kıyasta görünen alt küme üretiliyor; arayüz özet yoksa bölümü hiç göstermiyor (sahte özet basmıyor) |
| ~~5.6~~ | `build_summaries` parti sonunda yazıyor | **kapandı** — `--devam` ile kaldığı yerden sürüyor |
| ~~5.7~~ | gold id ayrışması (sessiz bozulma) | **kapandı** — `aa16505`, kanıt kapısı şemaya taşındı |

---

## Bu turda kapananlar (12–14 Ağustos, kayıt için)

- **FAZ 1** — `vade_ay` 0,133→0,545 · `kar_payi_orani` 0,500→0,800 ·
  `indirim_orani` 0,000→0,400 · yapılandırılmış mikro-F1 **0,646** ·
  halüsinasyon **0,059**
- **FAZ 2** — RAG eval modülü (`eval/rag_eval.py`), README ölçülebilir-durum
  tablosu, ölçüm metodolojisi vitrini, güvenlik ilanı 29/30
- **BM25** — sıralamada uygulandı, örtüşme sayımı **kapı** olarak korundu
  (banka hedefleme R@5 0,600→0,800; McNemar b=16 c=0, p=3,1e-05)
- **G3.2** kanıt zinciri — 48/48 kayıt ham arşive kadar izleniyor
- **G3.4** tek teknik doküman — karar gerekçeleri damıtıldı (wiki temizliğinin
  önkoşuluydu)
- **CI** — eval regresyon kapısı + Postgres/pgvector işi (53 atlanan test
  gerçekten koşuyor) + markdown link kapısı
- **demo.db** korpusla eşitlendi (1.782), özet kapsaması 1.759
- **Kalibrasyon** ölçümü yazıldı (ECE 0,306) — ölçülmemiş eşik kalmadı
- **İşlem günlüğü** — sisteme gelen her istek kalıcı kayda yazılıyor
- **Ollama** düşünme kipi kapatıldı (yeni modeller boş dönüyordu)

---

## Önerilen sıra (12 gün)

1. **Bugün:** 0.1 + 0.2 (commit/push) → FAZ 0 (1.1–1.6) → 2.5 yayın kademesi
2. **Bugün paralel (S):** 2.2 demo videosu çekimine başla · 3.1 gold anotasyonu
   dağıt · 4.4 TEKNOFEST'e yaz (cevap gecikir)
3. **15–18 Ağu:** 3.1 biter → eval/ablasyon/CI eşikleri yeniden koş → 2.1 veri
   seti yayını
4. **19–23 Ağu:** 2.3 sunum · 3.2 κ turu · 2.4 yedek video
5. **24–26 Ağu:** son ölçüm turu (sunumdaki her sayı o gün yeniden koşulur) ·
   temiz klon + offline prova tekrarı · son push
