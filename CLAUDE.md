# Anatolia AI — Bilgi Arşivi (LLM-Wiki Vault)

Bu klasör **Anatolia AI** ekibinin kalıcı bilgi arşividir. Amaç: TEKNOFEST
**Türkçe Yapay Zeka Dil Ajanları Yarışması (2. Senaryo)** kapsamında geliştirilen
projeye ait tüm bilgiyi (kaynaklar, varlıklar, kavramlar, kararlar, sorunlar,
sentezler) zamanla bozulmayan, çapraz bağlı ve kaynaklı bir wiki olarak tutmak.

Bu dosya, vault üzerinde çalışan her LLM/insan için **işletim kılavuzudur**.
`llm-wiki` yaklaşımının Anatolia AI'a uyarlanmış halidir.

---

## Amaç

- Anatolia AI için **kalıcı bilgi arşivi**.
- Yarışma: TEKNOFEST Türkçe Yapay Zeka Dil Ajanları Yarışması — 2. Senaryo
  (katılım bankacılığı kampanya metinlerinden NLP ile finansal bilgi çıkarımı,
  karşılaştırma, dashboard + chatbot).
- Tüm bilgi tek bir doğruluk kaynağında toplanır; tekrar tekrar PDF/dosya okumak
  yerine bu wiki sorgulanır.

## Dil

- **Tüm sayfalar Türkçe** yazılır. İstisnasız.
- Teknik terimlerin Türkçesi tercih edilir; yaygın İngilizce terim parantez içinde
  verilebilir (ör. "bilgi çıkarımı (information extraction)").

## İsimlendirme (Naming)

- Tüm dosya adları **kebab-case** ve Türkçe.
- Türkçe karakterler sadeleştirilir: `ş→s, ç→c, ı/i→i, ğ→g, ü→u, ö→o`
  (ör. "Kâr Payı Oranı" → `kar-payi-orani.md`).
- Kaynak (source) sayfaları: `sources/<kaynak-klasoru>/YYYY-MM-DD-<slug>.md`.

## Klasör Yapısı

```
raw/            # Ham kaynaklar — DEĞİŞMEZ (immutable). Sadece sembolik link + oku.
  teknofest/    #   Yarışma belgeleri (şartname vb.)
  docs/         #   Diğer dokümanlar
sources/        # Her ham kaynağın işlenmiş (ingest) özeti
  teknofest/
entities/       # Somut şeyler: kurum, sistem, platform, bileşen, API, kişi, veri seti
concepts/       # Soyut kavramlar: yöntem, teknik, prensip, terminoloji
decisions/      # Atomik mimari/ürün kararları (her biri tek karar)
sorun/          # Sorunlar / problemler / düzeltmeler (kök neden + çözüm)
syntheses/      # Yüksek seviyeli sentez / genel bakış sayfaları
archive/        # Silinmeyen, geçerliliğini yitirmiş sayfalar buraya taşınır
index.md        # Tüm sayfaların kategorize edilmiş dizini
log.md          # Kronolojik ingest / değişiklik günlüğü
lint-report.md  # Tutarlılık denetimi raporu
CLAUDE.md       # Bu dosya
```

## Sayfa Formatı

Her sayfa şu yapıda olur:

```markdown
---
title: <İnsan-okur başlık>
tags: [tag1, tag2]
source: "[[YYYY-MM-DD-slug]]"   # türetildiği kaynak sayfası / raw dosyası
date: YYYY-MM-DD
status: stable | taslak | celiskili | arsiv
---

# <H1 başlık>

<içerik — kaynaklı, çapraz bağlı>

## Sources
- [[YYYY-MM-DD-slug]] — ilgili bölüm/sayfa referansı

## Related
- [[diger-sayfa]] — neden ilgili olduğu
```

`source` sayfa için tek kaynak, `## Sources` çoklu kaynak referansı içindir.
Çapraz bağlar Obsidian `[[wikilink]]` biçimindedir.

---

## Workflow: INGEST (kaynak işleme)

Yeni bir ham kaynak geldiğinde:

1. Kaynağı `raw/<kaynak-klasoru>/` içine **sembolik link** olarak bağla
   (`ln -s`). Orijinali asla taşıma/kopyalama/düzenleme.
2. Kaynağı oku, ana konuyu çıkar.
3. `sources/<kaynak-klasoru>/YYYY-MM-DD-<slug>.md` yaz. İçerik:
   - frontmatter
   - **goal** (kaynağın amacı)
   - **what-was-done** (ne anlatılıyor / ne yapıldı)
   - **files-changed / touched** (dokunulan veya bahsi geçen dosyalar)
   - **decisions** (çıkan kararlar → decisions/ linkleri)
   - **issues** (çıkan sorunlar → sorun/ linkleri)
   - **open-threads** (açık sorular / yapılacaklar)
   - `## Sources` (ham dosyaya referans)
4. Bahsi geçen her **entity** (kurum, sistem, dosya, fonksiyon, servis, API, kişi,
   veri seti) için `entities/` altında sayfa oluştur veya güncelle. **Çift yönlü
   link** kur (entity → source, source → entity).
5. Her **mimari/ürün kararı** için `decisions/` altında **atomik** (tek karar)
   sayfa.
6. Her **sorun/düzeltme** için `sorun/` altında sayfa: kök neden + çözüm (fix) +
   ilgili dosyalar.
7. Her **soyut kavram** için `concepts/` altında sayfa oluştur veya güncelle.
8. `log.md`'ye `## [YYYY-MM-DD] ingest | <slug>` girişi ekle; altında dokunulan
   tüm dosyaların listesi.
9. `index.md`'yi güncelle.

## Workflow: QUERY (sorgulama)

Bir soruya cevap ararken:

1. Önce `index.md`'den ilgili kategoriyi bul.
2. İlgili sayfayı oku; `## Related` ve `## Sources` üzerinden derinleş.
3. Bilgi eksikse **ham kaynağa** (raw/) git, ama önce wiki'yi tüket.
4. Cevabı her zaman bir kaynağa dayandır; kaynaksız cevap verme.

## Workflow: LINT (denetim)

Periyodik olarak `lint-report.md` üret:

- **Çelişkiler**: aynı konuda birbiriyle çelişen ifadeler.
- **Orphan sayfalar**: hiçbir sayfadan link verilmeyen sayfalar.
- **Eksik çapraz referanslar**: bahsi geçtiği halde linklenmemiş sayfalar.
- **Kendi sayfası olmayan kavramlar**: tekrar tekrar geçen ama sayfası olmayan
  kavram/varlıklar.

Lint **otomatik düzeltme yapmaz**, sadece raporlar.

---

## HARD RULES (asla ihlal edilmez)

1. **raw/ değişmezdir (immutable).** raw/ altına asla yazma, düzenleme, silme
   yapma. Sadece sembolik link oluştur ve oku.
2. **Kaynaksız iddia yasak.** Her bulgu/ifade ilgili kaynağa (`## Sources` veya
   `source`) referans vermek zorundadır.
3. **Silme yok.** Geçersiz/eski sayfa silinmez; `archive/` altına taşınır ve
   `status: arsiv` yapılır.
4. **Çelişkiler işaretlenir.** İki kaynak veya sayfa çelişiyorsa, ilgili sayfada
   `## ÇELİŞKİ` başlığı açılır; her iki taraf kaynağıyla yazılır, `status:
   celiskili` yapılır. Çelişki gizlenmez, silinmez.
5. **Atomiklik.** decisions/ ve concepts/ sayfaları tek bir karar/kavram içerir.
6. **Çift yönlü bağ.** Bir sayfa başka bir sayfadan bahsediyorsa, mümkünse her iki
   yönde de link kurulur.
