---
title: "TKBB kâr payı veri seti — iki uç, tarihsel arşiv + güncel hafta"
tags: [kaynak, tkbb, kar-payi, katilma-hesabi, veri-toplama, olcum]
source: "https://tkbb.org.tr/veripetegi-detay/40 · https://karpayi.tkbb.org.tr/veri/karpaylari"
date: 2026-08-24
status: stable
---

# TKBB kâr payı veri seti

## goal

Katılma hesabı kâr payı oranlarını **her banka için** bulmak. Tetikleyici,
canlı chatbot çıktısıydı: *"Katılım hesabında en iyi kâr payı oranını hangi
banka veriyor"* sorusu cevaplanamıyordu ([[katilma-hesabi-orani-korpusta-yoktu]]).

## what-was-done

TKBB'nin **iki ayrı** kâr payı ucu bulundu ve ikisi de hasat edildi:

| uç | kapsam | erişim | sonuç |
|---|---|---|---|
| `karpayi.tkbb.org.tr` | 2012-01-02 → **2025-05-26** | TLS sertifikası GEÇERSİZ | 210.474 kayıt |
| `veri-petegi.tkbb.org.tr` | içinde bulunulan hafta | sertifika geçerli, CSRF ister | 245 kayıt |

Tarihsel uç dört rapor sunuyor (`sheetIndex` 0–3): dağıtılan kâr payı, kâr
paylaşım, ve ikisinin ara ödemeli hesap karşılıkları. Tek istekte 4 vade × 4
para birimi (16 kolon) dönüyor.

Güncel uç bir **Turboard** panelidir; veri iframe içindeki panelin
`/api/v1/data/` çağrılarından gelir ve `X-CSRFToken` başlığı ZORUNLUDUR
(başlıksız HTTP 400).

### Güncel oranlar — 2026-08-24 haftası, TL, dağıtılan kâr payı (%)

| banka | 1 ay | 3 ay | 6 ay | 12 ay |
|---|---|---|---|---|
| T.O.M. | **42,79** | 42,74 | 39,00 | — |
| Hayat Finans | 37,81 | 39,31 | **41,28** | 39,82 |
| Albaraka | 31,35 | 32,22 | 36,85 | **40,85** |
| Dünya | 33,24 | 34,20 | 35,50 | 39,62 |
| Kuveyt Türk | 33,00 | 34,42 | 35,74 | 39,33 |
| Türkiye Emlak | 30,63 | 33,64 | 35,15 | 38,51 |
| Vakıf | 31,50 | 32,78 | 33,85 | 36,90 |
| Ziraat | 28,01 | 28,65 | 29,64 | 31,88 |
| Türkiye Finans | 28,18 | 28,66 | 29,27 | 31,18 |

## ÜÇ BAĞIMSIZ KAYNAK AYNI DEĞERİ VERDİ

Albaraka TL kâr **paylaşım** oranı (90/90/92/93) üç ayrı yoldan doğrulandı:

1. Güncel uç (`veri-petegi`, Turboard paneli)
2. Tarihsel uç (`karpayi`, `sheetIndex=1`)
3. Albaraka'nın kendi PDF'i (`kar-paylasim-oranlari-09-07-25.pdf`, 9 Tem 2025)

Ayrıca tarihsel uçtan `-k` ile alınan ilk hafta değerleri, kullanıcının kendi
tarayıcısından (sertifika uyarısını kabul ederek) aldığı değerlerle **7/7 banka
birebir** uyuştu. Sertifika doğrulanamadı ama İÇERİK doğrulandı.

## files-changed / touched

- `app/scripts/tkbb_karpayi_hasat.py` — yeni (tarihsel, gzip yazar)
- `app/scripts/tkbb_guncel_hasat.py` — yeni (güncel hafta)
- `app/src/chatbot/katilma_orani.py` — yeni (cevap üretimi)
- `app/src/chatbot/bot.py` — `katilma_orani` handler'ı
- `app/data/raw/<banka>/rates/tkbb-karpayi.jsonl.gz` — 9 banka, 1,1 MB
- `app/data/raw/<banka>/rates/tkbb-guncel.jsonl` — 9 banka, 152 KB
- `app/src/api/routers/katilma.py` — yeni (panel ucu)
- `app/web/app/components/KatilmaPanel.tsx` — yeni; `page.tsx`, `lib/api.ts`
- `app/tests/test_chat_katilma_orani.py` (20), `test_tkbb_hasat.py` (20),
  `test_api_katilma.py` (17)

## decisions

- [[katilma-orani-iki-ayri-buyukluk]] — getiri ile pay ayrı sıralanır

## issues

- [[katilma-hesabi-orani-korpusta-yoktu]] — boşluğun kendisi

## open-threads

- **2026 tarihsel veri yok — ama bu bir eksik DEĞİL.** Arşiv tamamlanmış
  dönemleri yayınlıyor ve 2026 henüz sürüyor (kullanıcı bilgisi, 2026-08-24);
  form yıl listesinin 2025'le bitmesi de bununla tutarlı. Bankaların farklı
  tarihlerde durması (Albaraka 2024-09, Türkiye Finans 2025-05) bildirim
  sıklıklarının farklı olmasından. Güncel uç içinde bulunulan haftayı
  veriyor; iki uç arasındaki ARA DÖNEM (Haz 2025 – Ağu 2026) hiçbir uçta
  bulunmuyor.
- **BankAsya** tarihsel uçta boş yanıt veriyor (kapalı banka), **Adil Katılım**
  veri setinde hiç yok.
- Panel `sheetIndex=2/3` (ara ödemeli hesap) tarihsel uçta hasat edildi; güncel
  uçta karşılığı aranmadı.
- Dashboard (web) tarafı bu veriyi henüz göstermiyor; yalnız chatbot kullanıyor.

## Sources

- `https://tkbb.org.tr/veripetegi-detay/40` — Veri Peteği, "Kar Payı Oranları"
- `https://karpayi.tkbb.org.tr/veri/karpaylari` — tarihsel arşiv
- `https://www.albaraka.com.tr/documents/.../kar-paylasim-oranlari-09-07-25.pdf`
- Kullanıcı raporu, 2026-08-24 — tarayıcı ağ kaydı ve yapıştırılan tablolar

## Related

- [[tkbb-kar-payi-veri-seti]] — hasat edilen varlık
- [[kar-payi-orani]] — kavram; bu kaynak onun katılma hesabı ayağını besliyor
- [[chatbot]] — veriyi kullanan bileşen
- [[2026-08-25-yayimlanan-finansman-oranlari]] — kardeş veri kolu: finansman
  oranları, bankaların kendi yayınlarından
