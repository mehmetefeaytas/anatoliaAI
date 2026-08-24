---
title: "Katılma hesabı kâr payı oranı korpusta yoktu (veri eksikliği, hata değil)"
tags: [sorun, chatbot, katilma-hesabi, kar-payi, veri-kapsami]
source: "kullanıcı raporu (2026-08-24, canlı chatbot çıktısı)"
date: 2026-08-24
status: stable
---

# Katılma hesabı kâr payı oranı korpusta yoktu

## Belirti

Canlı çıktı:

```
"Katılım hesabında en iyi kar payı oranını hangi banka veriyor"
    → kaynaklı bir sıralama üretilemedi
```

## Kök neden — bu bir çıkarım hatası DEĞİL

Kampanya korpusu katılma hesabı getirisini **hiç yayınlamıyor**. Bankalar bu
oranı kampanya metninde değil **haftalık oran tablolarında** duyurur; kampanya
sayfaları finansman ürünlerini (konut, taşıt, ihtiyaç) anlatır.

Yani kural hattı da LLM katmanı da kaçırmamıştı: çıkarılacak değer belgede
yoktu. Halüsinasyon yasağı ([[bilgi-cikarimi]]) gereği sistem doğru davranıp
çekimser kalmıştı — eksik olan **veri kaynağıydı**.

Aynı ayrım daha önce de karşımıza çıktı: `#1212` belgesinde kâr payı oranı
değeri gerçekten yayınlanmıyordu ([[kiyas-cevabinda-iki-gosterim-hatasi]]).

## Çözüm — yeni bir veri kaynağı, yeni bir cevap yolu

[[tkbb-kar-payi-veri-seti]] hasat edildi (iki uç: 2012–2025 tarihsel arşiv +
içinde bulunulan hafta). Chatbot'a `katilma_orani` yolu eklendi
(`app/src/chatbot/katilma_orani.py`), `terminoloji`den sonra ve yapısal sorgu
yolundan ÖNCE.

Yol, **hesap izini ZORUNLU** tutar: "katılma/katılım hesabı", "vadeli hesap"
gibi bir iz yoksa devreye girmez. Bu olmadan "konut finansmanı kâr payı oranı"
gibi ALAN soruları bu yola düşer ve yapısal sorgu yolunun kaynaklı DEĞER
üretme işini çalardı — [[terim-sorusuna-sozlukten-cevap-verilmiyordu]]
sayfasındaki aynı ders.

Cevap: banka başına en iyi satır, vade ve para birimi süzgeci, getiri/pay
ayrımı ([[katilma-orani-iki-ayri-buyukluk]]), dönem tarihi, kaynak satırı ve
kâr-zarar ortaklığı uyarısı.

## İki tuzak — ikisi de testle yakalandı

### 1. Türkçe ünsüz yumuşaması deseni kaçırıyordu

`_HESAP_IZI` yalnız `hesab` kökünü arıyordu; *"vadeli **hesap** kâr payı
oranları"* sorusu eşleşmiyordu. Kök iki biçimde geçiyor: "vadeli hesaP" ama
"katılma hesaBı". Desen `hesa[bp]` yapıldı.

### 2. Jargon kapısı 'mevduat' desenini yakaladı — ve haklıydı

`_HESAP_IZI` "vadeli mevduat" ifadesini de tanıyor, çünkü kullanıcı
alışkanlıkla böyle sorabilir. Ama "mevduat" katılım bankacılığında yanlış
terimdir ve `scripts/jargon_lint.py` onu ihlal saydı.

Ayrım şu: bu bir **girdi deseni**, çıktı metni değil. Yanlış terimi ANLAYIP
doğrusuyla ("Katılma hesabı") cevaplamak tam olarak terminoloji hedefidir
(CLAUDE.md §12). Satır içi `# jargon-lint: ok` pragması ile muaf tutuldu —
kapı gevşetilmedi, tek satır işaretlendi.

## Kalan sınır — açıkça yazılıyor

- **2026 tarihsel veri yok.** Arşiv Mayıs 2025'te duruyor; güncel uç yalnız
  içinde bulunulan haftayı veriyor. Haziran 2025 – Ağustos 2026 arası hiçbir
  uçta yok.
- **Adil Katılım** TKBB veri setinde hiç yok; **BankAsya** kapalı.
- Dashboard (web) bu veriyi henüz göstermiyor; yalnız chatbot kullanıyor.
- Tarihsel arşiv (210.474 kayıt) hiçbir kod yolunda okunmuyor — trend/dönemsel
  kıyas için duruyor.

## İlgili dosyalar

- `app/src/chatbot/katilma_orani.py` — yeni
- `app/src/chatbot/bot.py` — `katilma_orani` handler'ı, `kaynak_var` listesi
- `app/scripts/tkbb_guncel_hasat.py` · `tkbb_karpayi_hasat.py` — yeni
- `app/tests/test_chat_katilma_orani.py` (20) · `test_tkbb_hasat.py` (20)

## Sources

- Kullanıcı raporu, 2026-08-24 — canlı chatbot çıktısı
- [[2026-08-24-tkbb-kar-payi-veri-seti]] — hasadın dökümü

## Related

- [[tkbb-kar-payi-veri-seti]] — boşluğu kapatan kaynak
- [[katilma-orani-iki-ayri-buyukluk]] — cevabın şema kararı
- [[kiyas-cevabinda-iki-gosterim-hatasi]] — "değer belgede yok" ayrımının önceki örneği
- [[terim-sorusuna-sozlukten-cevap-verilmiyordu]] — alan sorularını çalmama kuralı
- [[kar-payi-orani]] — kavram
