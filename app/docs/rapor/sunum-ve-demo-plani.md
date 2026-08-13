# Sunum ve Demo Planı — 5 dk video · 1 dk demo · 4 dk sunum

**Hazırlık tarihi:** 13 Ağustos 2026
**Kapsam:** G4.2 (demo videosu) ve G4.3 (sunum materyali)
**Kural:** bu belgedeki her sayı ölçülmüştür ve kök `README.md`'nin
"Ölçülebilir Durum" tablosundaki komutla yeniden üretilir. Slayta girmeden önce
sayıyı **o gün** yeniden koşun; bayat sayı sunumda savunulamaz.

---

## Şartnamedeki süre çelişkisi

Şartname s.14 "en fazla 5 dakika", s.19 "1 dakika" diyor. Çelişki
`syntheses/teslim-ve-degerlendirme-rehberi.md`'de kayıtlı. **İkisi de
hazırlanır**; kısa olan uzunun kesitidir, ayrı çekim yapılmaz.

---

## Anlatının omurgası

Bu projenin rakiplerden ayrıldığı yer daha yüksek bir F1 değil — **ölçümün
dürüstlüğü**. Sunum bunun üzerine kurulur:

> "Tek bir parlak yüzde vermiyoruz, çünkü bir alanı kaçırmak ile uydurmak aynı
> hata değildir."

Rakip tek sayı gösterecek. Biz iki sayı, güven aralığı ve halüsinasyon oranı
göstereceğiz. Jüri karşısında güçlü olan bu.

---

## A) 5 dakikalık demo videosu — çekim listesi

Toplam 5:00. Süreler tavan; taşarsa §5 kısaltılır, §3 asla kısaltılmaz.

| # | Süre | Ekranda | Anlatım (özet) |
|---|---|---|---|
| 1 | 0:00–0:30 | Kapak + problem: üç banka sayfası yan yana, farklı ifadeler ("ilk 6 ay masrafsız", "%1,99–%2,49", "120 aya kadar") | Katılım bankacılığında bilgi doğal dilde ve kıyaslanamaz biçimde duruyor |
| 2 | 0:30–1:15 | Mimari şeması: toplama → temizleme → **kural (birincil)** → LLM (yalnız boşluk) → normalizasyon → DB → dashboard/chatbot | İki katman. LLM kritik yolda değil; kapalıyken sistem çalışır |
| 3 | 1:15–2:30 | **Dashboard**: kıyas tablosu, alan başına güven skoru, kaynak vurgulama; "doğrudan kıyaslanamaz" rozeti | Her değerin yanında nereden geldiği var. Koşullar farklıysa sıralama uydurmuyoruz |
| 4 | 2:30–3:30 | **Chatbot**: (a) kıyas sorusu → yapısal sorgu yolu, (b) koşul sorusu → RAG + kaynak, (c) **alan dışı soru → reddetme** | Üçüncüsü kasten: sistem bilmediğinde bilmediğini söylüyor |
| 5 | 3:30–4:15 | **Çelişki tespiti**: "masrafsız" diyen kampanya + tahsis ücreti kaydı yan yana | Bu bir kapsam testi: ücretin varlığı değil, kampanyanın hangi ücreti kapsadığını söylememesi |
| 6 | 4:15–4:45 | Terminalde `python -m eval.run_eval` koşuyor, rapor çıkıyor | Sayılar slayttan değil, komuttan geliyor |
| 7 | 4:45–5:00 | `docker-compose up` + ağ kapalı rozeti; Apache-2.0 | Tamamen on-prem, internetsiz, ücretli servis yok |

**Çekim kuralları**

- Demo **önceden doldurulmuş DB'den** okur (karar: `demo-onceden-doldurulmus-db`).
  4 dakikada yerel 8B LLM + canlı scraping donma riski taşır.
- Tek bir örnekte "canlı çıkarım" butonu gösterilir — çalıştığını ispatlar.
- Ekran kaydı 1080p, imleç vurgulu, ses ayrı kayıttan.
- Sayıların göründüğü her karede o sayı **o gün** koşulmuş olmalı.

---

## B) 1 dakikalık kısa demo — kesit

Uzun videonun §3 + §4c + §5'inden kurulur. Yeni çekim yok.

| Süre | İçerik |
|---|---|
| 0:00–0:20 | Dashboard kıyas tablosu + kaynak vurgulama |
| 0:20–0:40 | Chatbot: alan dışı soruya **cevap vermeme** |
| 0:40–1:00 | Çelişki tespiti kartı |

Kısa sürüme mimari ve eval koşusu **girmez**; onlar sunumun işi.

---

## C) 4 dakikalık sunum — slayt iskeleti

PDF + PPTX olarak teslim edilir (s.14).

| # | Slayt | Süre | Çekirdek mesaj |
|---|---|---|---|
| 1 | Kapak — takım, senaryo | 0:10 | — |
| 2 | Problem | 0:30 | Aynı bilgi, farklı ifade; manuel kıyas pratikte imkânsız |
| 3 | Mimari (tek şema) | 0:40 | Kural birincil, LLM tamamlayıcı, hepsi on-prem |
| 4 | **Ölçüm dürüstlüğü** ← ana farklılaştırıcı | 1:00 | Dört hata kovası (kaçırma / yanlış çıkarım / halüsinasyon / atlanan); iki mikro-F1 ve farkının açıklaması; belge düzeyi bootstrap |
| 5 | **Ölçüp geri adım attığımız yer** | 0:40 | Ablasyon hibridi yanlışladı (0,575 < 0,612, p=0,0117; halüsinasyon 0,163 vs 0,102). Sonucu düzeltmedik |
| 6 | Yenilikçilik: çelişki tespiti + güven/kaynak + config-driven banka | 0:30 | Üçü de ölçülebilir, üçü de demoda görünüyor |
| 7 | On-prem kanıtı | 0:20 | `--network none` içinde koşan kanıt paketi; Apache-2.0 zinciri köke kadar |
| 8 | Kapanış + demo geçişi | 0:10 | — |

**Slayt 4'ün tablosu** (sunum günü yeniden koşulacak):

| Ne | Değer |
|---|---|
| Yapılandırılmış alan mikro-F1 | 0,646 |
| 12-alan mikro-F1 | 0,452 [%95 GA 0,384–0,512] |
| Halüsinasyon oranı | 0,059 (yapısal kesitte 0,047) |
| RAG terim kapsama R@5 | 0,867 |
| Reddetme kararı doğruluğu | 30/30 |
| Güvenlik seti | 29/30 · aşırı red 0/6 |
| Anotatör uyumu | Fleiss κ 0,302 · Krippendorff α 0,620 / 0,787 |
| Test | 2.649 toplanan · 2.596 geçen |

---

## Jüri sorularına hazır cevaplar

**"F1'iniz rakibinkinden düşük."**
Farklı şey ölçüyoruz. Onlar 6 alanda, biz 12 alanda; gold setimizin 40/48'i
**kasten** zor vaka; halüsinasyonu ayrı paydayla sayıyoruz. Yapılandırılmış
alan kesitinde 0,646, tam kesitte 0,452 — ikisini de yayımlıyoruz ve farkını
README'de açıklıyoruz. Tek sayıya indirmek bu farkı gizlemek olurdu.

**"κ = 0,302 düşük değil mi?"**
Düşük ve bunu biz ilan ettik. Eşik anotasyon **başlamadan** açıklanmıştı
(0,67) ve ilan edilen sonuç uygulandı: zorunlu hakemlik, kılavuz v1→v2
revizyonu, 123 uyuşmazlığın tek tek listelenmesi. Sayıya bakıp eşik
değiştirmedik. Revizyon sonrası tur şu an sahada.

**"LLM'i neden daha çok kullanmıyorsunuz?"**
Kullanmayı denedik ve ölçtük: hibrit kol kural kolundan **kötü** çıktı, üstelik
halüsinasyonu %60 daha yüksekti. Ölçümü düzeltmek yerine kararı değiştirdik.

**"Veri seti nerede?"**
Paket tek komutla üretiliyor ve provenance kapısından geçiyor. Gold seti şu an
genişletildiği için yükleme tur bitiminde yapılacak — yarım gold yayımlamak,
indirilen kopyayı yanlış bırakır.

---

## Yapılacaklar (bu belge planı, çekimi değil)

- [ ] Ekran kaydı — dashboard, chatbot, çelişki kartı (docs-ekran/ PDF'i taslak olarak var)
- [ ] Seslendirme metni — yukarıdaki anlatım sütunundan tam cümlelere açılacak
- [ ] Slayt tasarımı — PDF + PPTX
- [ ] Sunum günü: bütün sayıları yeniden koş, slayt 4 ve 5'i güncelle
- [ ] `OFFLINE-KANIT.md` yeniden koşulsun (mevcut kanıt 31 Temmuz'dan)
