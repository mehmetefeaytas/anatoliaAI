---
title: "Lint Raporu"
tags: [lint, rapor]
date: 2026-06-16
status: stable
---

# Lint Raporu — 2026-06-16

Otomatik denetim. **Düzeltme yapılmamıştır**, yalnızca bulgular raporlanmıştır
(CLAUDE.md Lint workflow kuralı gereği).

## Özet metrikler

- İçerik sayfası: **37** (index/log/CLAUDE/lint hariç)
- Toplam giden wikilink: **308**
- Çözümlenen (geçerli hedefli) çapraz referans: **305**
- Orphan (gelen linki olmayan) sayfa: **0**
- Gerçek kırık link: **0**

## 1. Çelişkiler

- **Demo videosu süresi tutarsızlığı** — şartname s.14 "maksimum 5 dakika" derken
  s.19 "demo videosu süresi 1 dakika" der. `## ÇELİŞKİ` başlığıyla işaretlendi ve
  yorumlandı: [[teslim-ve-degerlendirme-rehberi]] (`status: celiskili`). Kaynak
  içi çelişki olduğundan vault'ta gizlenmeden korunmuştur.

Başka içsel çelişki tespit edilmedi (tek kaynak ingest edildiği için kaynaklar
arası çelişki yok).

## 2. Orphan sayfalar

- **Yok.** Tüm 37 içerik sayfasının en az bir gelen wikilink'i var.

## 3. Eksik / kırık çapraz referanslar

- Gerçek kırık link **yok**.
- Tarayıcı CLAUDE.md içinde 3 "kırık" hedef bildirdi: `YYYY-MM-DD-slug`,
  `diger-sayfa`, `wikilink`. Bunlar **format örneği placeholder**'larıdır, gerçek
  link değildir → **yok sayıldı**, düzeltme gerekmez.

## 4. Kendi sayfası olmayan kavramlar

Şartnamede geçen ve henüz ayrı sayfası olmayan, ileride sayfa açılabilecek
kavram/varlıklar (eksiklik değil, kapsam notu):

- **Müşteri segmentleri** (yeni/mevcut/maaş müşterisi) — şu an
  [[bilgi-cikarimi]] içinde alan olarak geçiyor; ayrı sayfa açılabilir.
- **Finansman maliyeti / katılım fonu / masrafsız finansman / avantajlı
  finansman** — şu an [[katilim-bankaciligi]] ve [[kar-payi-orani]] içinde
  tanımlı; her biri atomik concept sayfasına bölünebilir.
- **Mentörlük programı** — [[yarisma-genel-bakis]] içinde geçiyor; ayrı entity
  gerekmiyor.
- **Turnitin / intihal kontrolü** — Katılım Şartları'nda geçiyor; düşük öncelik.

## 5. Öneriler (uygulanmadı)

- İkinci bir kaynak ingest edildiğinde (ör. örnek kampanya verisi, mimari notlar)
  yukarıdaki bölünmeler değerlendirilebilir.
- `status: celiskili` olan [[teslim-ve-degerlendirme-rehberi]] çelişki, resmî
  bilgilendirme maili geldiğinde güncellenmeli.
