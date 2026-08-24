---
title: "TKBB Kâr Payı Veri Seti (iki uç)"
tags: [entity, tkbb, veri-kaynagi, kar-payi, katilma-hesabi]
source: "[[2026-08-24-tkbb-kar-payi-veri-seti]]"
date: 2026-08-24
status: stable
---

# TKBB Kâr Payı Veri Seti

Türkiye Katılım Bankaları Birliği'nin (TKBB) katılma hesabı oranlarını
yayınladığı **iki ayrı** uç. İkisi farklı sistemdir ve karıştırılmamalıdır.

## 1. Tarihsel arşiv — `karpayi.tkbb.org.tr`

- Kapsam **2012-01-02 → 2025-05-26**. Arşiv TAMAMLANMIŞ dönemleri yayınlıyor;
  2026'nın bulunmaması eksik değil, yıl henüz sürüyor (kullanıcı bilgisi).
  Bankaya göre bitiş farklı — bildirim sıklıkları farklı (Albaraka ve
  Emlak 2024-09-30, Kuveyt Türk ve Vakıf 2024-10-07, TOM ve Ziraat 2024-12-23,
  Hayat Finans 2025-05-05, Türkiye Finans 2025-05-26).
- Dört rapor: dağıtılan kâr payı, kâr paylaşım, ve ikisinin ara ödemeli hesap
  karşılıkları (`sheetIndex` 0–3).
- `POST /veriseti/profitReportDetail`, form gövdesi; tek istekte 4 vade × 4 para
  birimi.
- **TLS sertifikası geçersiz** (`ERR_CERT_DATE_INVALID`). Hasat bu yüzden
  `--sertifika-atla` bayrağını AÇIKÇA ister; bayrak yokken çalışmaz.
- Hasat: `app/scripts/tkbb_karpayi_hasat.py` → 210.474 kayıt, gzip 1,1 MB.

## 2. Güncel hafta — `veri-petegi.tkbb.org.tr`

- **Turboard** paneli; `tkbb.org.tr/veripetegi-detay/40` içinde iframe.
- İki bileşen: `DL-FFC6K484A682B8I` (dağıtılan kâr payı) ve
  `DL-0M0C2ABB615D062` (kâr paylaşım).
- `GET /api/v1/data/` + **`X-CSRFToken` başlığı zorunlu** (`/api/v1/auth/csrf/`
  ile alınır); başlıksız HTTP 400.
- Ölçüt kolonları `m0..m3` = TL, USD, EUR, Altın; vade kolonları Aylık / 3
  Aylık / 6 Aylık / Yıllık.
- Satırlarda **tarih YOK** — dönem istekteki hafta filtresinden gelir, bu
  yüzden kayıtta `period_date_kaynak: turetilmis` işaretlenir.
- Hasat: `app/scripts/tkbb_guncel_hasat.py` → 245 kayıt/hafta.

## Kapsanan bankalar

Dokuz banka: Albaraka, Dünya, Türkiye Emlak, Hayat Finans, Kuveyt Türk,
T.O.M., Türkiye Finans, Vakıf, Ziraat ([[katilim-bankalari]]).

**BankAsya** tarihsel uçta listede ama boş yanıt veriyor (kapalı banka).
**Adil Katılım** hiçbir uçta yok.

## Verinin kullanıldığı yerler

- **Chatbot** — `katilma_orani` yolu, banka başına en iyi satır sıralaması
- **Panel** — «Katılma Oranları» sekmesi, `GET /katilma-oranlari`

Tarihsel arşiv şu an hiçbir kod yolunda okunmuyor: trend analizi bilinçli
olarak elenmiş bir yol (CLAUDE.md §18). Arşiv yine de depoda duruyor çünkü
kaynak kırılgan.

## Güvenilirlik

Albaraka TL paylaşım oranı üç bağımsız kaynakta aynı çıktı (iki uç + bankanın
kendi PDF'i). Tarihsel uçtan sertifika doğrulanmadan alınan değerler,
kullanıcının tarayıcısından gelen değerlerle 7/7 banka birebir uyuştu — içerik
doğrulandı, sertifika değil.

## Sources

- [[2026-08-24-tkbb-kar-payi-veri-seti]] — hasadın tam dökümü

## Related

- [[katilma-orani-iki-ayri-buyukluk]] — verinin iki büyüklüğü ayrı tutulur
- [[katilma-hesabi-orani-korpusta-yoktu]] — bu kaynağın kapattığı boşluk
- [[katilim-bankalari]] — kapsanan kurumlar
- [[kar-payi-orani]] — kavramsal zemin
- [[chatbot]] — veriyi kullanan bileşen
