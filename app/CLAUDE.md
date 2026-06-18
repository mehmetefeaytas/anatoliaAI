# CLAUDE.md — Anatolia AI Yarışma Çözümü (kod projesi)

> Bu dosya Claude Code'un her oturumda okuduğu proje bağlamıdır. Buradaki kurallar
> bağlayıcıdır. Bir şey belirsizse, varsayım yapmadan önce sor.
>
> Bu dosya, ilk taslak planın (`v1`) üzerine yapılan **5 kritik mimari kararla**
> kesinleşmiş halidir (`v2`). Değişikliklerin gerekçeleri ilgili bölümlerde
> `[KARAR vN]` etiketiyle işaretlidir. Bilgi arşivi (vault) bir üst dizindedir:
> `../` (entities/, concepts/, decisions/, sorun/, syntheses/).

---

## 1. Proje Özeti

TEKNOFEST 2026 **Türkçe Yapay Zekâ Dil Ajanları Yarışması — 2. Senaryo**
(Bilişim Vadisi yürütücülüğünde) için NLP çözümü.

**Amaç:** Türkiye'deki katılım bankalarının (faizsiz finans) resmî sitelerindeki
kampanya/ürün metinlerini topla → doğal dildeki finansal bilgileri otomatik çıkar
→ standart formata normalize et → kampanya türlerini sınıflandır → bankaları
karşılaştırılabilir hale getir → **dashboard + chatbot** ile sun.

**Kritik kısıt (pazarlık dışı):** tamamen **on-premise** çalışabilmeli, **tamamen
açık kaynak** (Apache-2.0), **hiçbir ücretli API/servis/yazılım yok**, **internetsiz
çalışmalı**. Kısıtı ihlal eden kod önerme.

**Değerlendirme ağırlıkları (önceliklendirme):**
- Model Başarısı ve Anlamlandırma — **%30** (en yüksek)
- Fonksiyonellik ve Senaryo Kapsamı — %20
- Teknik İmplementasyon ve Mimari — %20
- On-Prem Uygulanabilirlik — %20
- Yenilikçilik ve Yaratıcılık — %10

Öncelik sırası: doğruluk/sağlamlık (%30) > uçtan uca çalışma > temiz mimari >
on-prem ispatı > ekstra özellikler.

---

## 2. Geliştirme vs. Teslim Ortamı `[KARAR — Colab/on-prem ayrımı]`

İki ortam **ayrıdır**, karıştırma:

- **Geliştirme/eğitim:** Colab Pro+ (A100/H100). Ağır deney, sınıflandırıcı
  eğitimi, model nicemleme (quantization) burada yapılır.
- **Teslim/demo:** **on-prem + offline**. Teslim edilen sistem Colab'a **bağlı
  olamaz**. Dağıtım: **nicemlenmiş (AWQ/GGUF 4-bit) model + Docker ile offline**.

LLM kritik yolda olmamalı: demo donanımında çalışmazsa **Ollama** yedeği veya
"LLM kapalı" modu devreye girsin (bkz. §3, §11).

---

## 3. Mimari: "Önce Kural, Sonra LLM" Hibrit

Çıkarım üç katman + uzlaştırma (reconciliation):

1. **Kurallar/Regex (deterministik, birincil)** — sayısal/yapısal alanlar: kâr
   payı oranı, tutar, vade, taksit, tarih, masraf. Yüksek güvenle çıkan alanı
   LLM'e **gönderme**.
2. **GLiNER2 (tamamlayıcı) + fine-tune BERTurk (yalnızca 8-sınıf sınıflandırma)** —
   `[KARAR v2-#2]` GLiNER birincil değil tamamlayıcıdır; Türkçe finans terimlerinde
   sıfır-atış performansı belirsiz. NER fine-tune YAPMA (overfit riski).
3. **Yerel LLM + kısıtlı JSON decoding (guided_json)** — yalnızca kuralların
   kaçırdığı örtük/bulanık ifadeler ("ilk 3 ay ödemesiz", "masrafsız", dolaylı oran).

**Uzlaştırma:** kural çıktısı varsa onu tercih et → boşlukları LLM ile doldur →
her alana `confidence` + `source_span` ekle. Alan gerçekten yoksa **`null` + düşük
güven** döndür; **ASLA değer uydurma** (halüsinasyon en büyük risk).

Veri akışı:
```
scrape → clean (trafilatura) → preprocess (TR-aware) → extract (3 katman) →
reconcile → normalize (canonical) → store (PostgreSQL) → compare/rank →
dashboard + HİBRİT chatbot (text-to-SQL + RAG)
```

---

## 4. Çıkarım Modeli `[KARAR v2-#2 — fine-tune dağılımı]`

- **NER / alan çıkarımı:** kural + few-shot LLM. Fine-tune YOK.
- **Kampanya türü sınıflandırması (8 sınıf):** BERTurk fine-tune YAPILABİLİR —
  dengeli 150–300 örnekle yeterli.
- Anotasyon bütçesinin çoğu **gold/eval setine** gider, NER eğitimine değil.

---

## 5. Hibrit Chatbot `[KARAR v2-#1 — saf RAG DEĞİL]`

Senaryonun kalbi karşılaştırma: *"hangi bankada en düşük kâr payı?"*, *"36 ay vade
veren konut finansmanları"* — bunlar **toplama/sıralama** soruları. Saf semantik RAG
(bge-m3 + pgvector) bunlara zayıf cevap verir.

**Doğru mimari — router'lı hibrit:**
- **Sayısal/karşılaştırmalı sorular →** `extracted_fields` tablosu üzerinde
  **text-to-SQL / yapısal sorgu**.
- **Koşul/açıklama soruları →** RAG.
- Bir **router** soruyu sınıflandırıp doğru yola gönderir.

Bu, hem fonksiyonellik (%20) hem model başarısı (%30) puanını yükseltir.

---

## 6. "Zor Anlama" Vakaları — Mimarinin Merkezi `[KARAR v2-#4 — %30 burada kazanılır]`

Normalizasyon ve çıkarım bu vakaları **açıkça** ele almalı:
- Aralık: `%1,99–%2,49`
- Zaman-koşullu oran: `ilk 6 ay %0`
- Aylık vs. yıllık baz
- TR sayı formatı: `1.500,00` (binlik `.`, ondalık `,`)
- Negasyon: `masrafsız` ≠ "değer yok" (masraf = 0 demek)

Gold sette ayrı bir **"zor vakalar" alt kümesi** kürle; ablasyonda hibridin
**özellikle orada** kazandığını göster. Jüri için en ikna edici artefakt budur.

---

## 7. Teknoloji Yığını

Bileşeni izinsiz değiştirme; alternatif için önce gerekçe sun.

| Katman | Araç | Not |
|---|---|---|
| LLM (ana) | **Trendyol-LLM-8B-T1** (Qwen3-8B tabanlı, Apache-2.0) | Yapısal çıktı için saf **Qwen3-8B** alternatif |
| LLM servis | **vLLM** (`guided_json`) | Demo yedeği: **Ollama**; nicemleme: AWQ/GGUF 4-bit |
| Sınıflandırma | **BERTurk** (`dbmdz/bert-base-turkish-cased`) fine-tune (8 sınıf) | |
| NER (tamamlayıcı) | **GLiNER2** | Halüsinasyon yapamaz, CPU dostu, ikincil |
| Embeddings | **BAAI/bge-m3** | Çok dilli, 8192 token |
| DB + Vektör | **PostgreSQL + pgvector** | |
| Backend | **FastAPI** (Python 3.11+) | |
| Frontend | **Next.js + React** (TypeScript) | |
| Scraping | `requests`+`BeautifulSoup`, `Playwright` (JS), `trafilatura` (temiz metin) | |
| TR morfoloji | **Zemberek** (JPype) veya **Zeyrek** (saf Python) | |
| Orkestrasyon | **Docker Compose** | Tek komut, offline, anahtarsız |

**Lisans tuzağı:** Gemma lisanslı (WiroAI-9b, Gemma-2/3) ve Llama community
license modellerini KULLANMA. Yalnızca **Apache-2.0 / MIT** ağırlıklar.

---

## 8. Repo Yapısı

```
app/
├── CLAUDE.md
├── LICENSE                      # Apache-2.0 (zorunlu)
├── README.md                    # kurulum + çalıştırma adımları
├── docker-compose.yml           # postgres + vllm/ollama + api + web
├── .env.example                 # API anahtarı YOK; sadece local config
├── config/
│   └── banks.yaml               # banka → base_url → kampanya yolları (config-driven)
├── data/
│   ├── raw/                     # ham HTML + scrape timestamp
│   ├── processed/               # temizlenmiş metin
│   └── gold/                    # altın test seti (anotasyonlu) + zor-vaka alt kümesi
├── src/
│   ├── scraping/                # banka başına collector'lar
│   ├── preprocessing/           # TR normalize, lemmatize, segment
│   ├── extraction/
│   │   ├── rules/               # regex + normalizasyon sözlüğü (BİRİNCİL)
│   │   ├── ner/                 # GLiNER (tamamlayıcı) + BERTurk sınıflandırıcı
│   │   ├── llm/                 # prompt + guided_json şemaları
│   │   └── reconcile.py         # 3 katmanı birleştir
│   ├── normalization/           # canonical units (oran, TRY, ay, ISO tarih)
│   ├── comparison/              # ranking motoru + adil-kıyas garantisi
│   ├── rag/                     # chunk → embed → retrieve → generate
│   ├── chatbot/                 # router + text-to-SQL + RAG (HİBRİT)
│   ├── api/                     # FastAPI endpoint'leri
│   └── db/                      # şema, migration, repository
├── web/                         # Next.js dashboard + chatbot UI
├── eval/
│   ├── run_eval.py              # P/R/F1, macro-F1, normalizasyon doğruluğu, kappa
│   └── ablation.py              # kural-only vs LLM-only vs hibrit
└── docs/                        # mimari diyagram, veri akışı, sunum
```

---

## 9. Veri Modeli (PostgreSQL)

```sql
banks(id, name, slug, website_url, bddk_active)
campaigns(id, bank_id, raw_text, clean_text, source_url, scraped_at, campaign_type)
extracted_fields(id, campaign_id, field_name, raw_value, canonical_value,
                 confidence, source_span, extractor)  -- extractor: 'rule'|'ner'|'llm'
embeddings(id, campaign_id, chunk_text, vector)  -- pgvector
```

Temel alanlar: `kar_payi_orani`, `finansman_tutari`, `vade_ay`, `taksit_sayisi`,
`tahsis_ucreti`, `masraf_durumu`, `kampanya_turu`, `odul_miktari`, `indirim_orani`,
`alisveris_puani`, `kampanya_suresi`, `kampanya_kosullari`, `hedef_kitle`.

---

## 10. Normalizasyon Kuralları (canonical)

Senaryoda açıkça ödüllendiriliyor; titizlikle uygula:
- **Oran:** `%2,05` / `% 2.05` / `2.05%` → decimal `2.05`
- **Para:** `500 TL` / `500₺` / `500 Türk Lirası` → `{value: 500, currency: "TRY"}`
- **Vade:** `12 ay` / `1 yıl` → ay (int) `12`
- **Tarih:** her biçim → ISO-8601 (`2026-12-31`)
- **TR sayı:** `1.500,00` → `1500.00` (binlik `.`, ondalık `,`)
- **Eşanlamlılar:** kâr payı ≈ getiri oranı; finansman ≈ kredi; vade ≈ ödeme süresi
  ≈ geri ödeme süresi; masrafsız ≈ ücretsiz ≈ dosya masrafı yok

---

## 11. Demo Stratejisi `[KARAR v2-#3 — canlı LLM/scrape'e bağlama]`

4 dakikalık sunumda yerel 8B LLM + canlı scraping = donma riski.
- **Önceden scrape + önceden çıkarım** yap, DB'yi doldur. Demo doldurulmuş DB'den okur.
- Tek bir örnek için **"canlı çıkarım" butonu** bırak (çalıştığını ispatlar).
- Gerisini cache'den göster. Offline-hazırlık on-prem %20 puanını güçlendirir.

---

## 12. Domain Bilgisi — Faizsiz Finans

Katılım bankacılığı terminolojisi konvansiyonelden farklıdır; doğru yorum %30'un kalbi:
- **kâr payı (oranı)** = faiz yerine; murabahada önceden ilan edilen kâr marjı
- **finansman** = kredi yerine (konut, taşıt, ihtiyaç finansmanı)
- murabaha, icara (leasing), mudarebe, muşareke, karz-ı hasen, sukuk, katılma
  hesabı vs özel cari hesap, tahsis ücreti, vade farkı

**8 kampanya türü (sınıf etiketleri):** Finansman, İhtiyaç Finansmanı, Konut
Finansmanı, Taşıt Finansmanı, Kart, Alışveriş Puanı, Yeni Müşteri, Yatırım Ürünü.

---

## 13. Hedef Bankalar (BDDK Liste 77)

Adil · Albaraka Türk · Dünya · Hayat Finans · Kuveyt Türk · T.O.M. · Türkiye Emlak ·
Türkiye Finans · Vakıf · Ziraat Katılım.

**Liste değişebilir** (İktisat, Halk, Katılımevim vb.). Scraper'ı `config/banks.yaml`
ile **config-driven** tut — yeni banka tek satır (yenilikçilik puanı). Build'de
güncel listeyi doğrula: https://www.bddk.org.tr/Kurulus/Liste/77

---

## 14. Scraping Kuralları (etik + sağlam)

- robots.txt'e **uy**; açıklayıcı User-Agent
- Rate-limit: domain başına 2–5 sn/istek
- Ham HTML'i timestamp + source_url ile **cache'le** (provenance)
- JS sayfaları için Playwright; içerik çıkarımı için trafilatura
- Site engelliyorsa: senaryonun izin verdiği **manuel toplama**ya düş, dokümana not et

---

## 15. Komutlar

```bash
docker-compose up                                   # offline, anahtarsız tüm sistem
python -m src.scraping.run --config config/banks.yaml
python -m src.extraction.run --input data/processed/sample.txt
python -m eval.run_eval --gold data/gold/           # P/R/F1, macro-F1, kappa
python -m eval.ablation                             # kural vs LLM vs hibrit
pytest
cd web && npm run dev
```

---

## 16. Değerlendirme Metodolojisi

150–300 kampanyalık **çift-anotasyonlu altın test seti** (+ zor-vaka alt kümesi).
Raporla:
- Alan bazında **precision / recall / F1**
- Sınıflandırma **accuracy + macro-F1** (8 tür)
- **Normalizasyon doğruluğu** (varyant → doğru canonical oranı)
- **Inter-annotator agreement (Cohen's kappa)** — gold setin güvenilirliği
- **Ablasyon tablosu:** kural-only vs LLM-only vs hibrit → hibridin (özellikle zor
  vakalarda) kazandığını kanıtla

Ablasyon tablosu jüri için en ikna edici tek artefakttır. Her özellikte eval'i tekrarla.

---

## 17. Karşılaştırma — Adil Kıyas Garantisi

- Yalnızca **aynı birime normalize** alanlar kıyaslanır.
- Koşullar farklıysa (örn. zaman-koşullu oran) **"doğrudan kıyaslanamaz"** işaretle,
  uydurma sıralama yapma.

---

## 18. Yenilikçilik — Daraltılmış 3 Hedef `[KARAR v2-#5]`

Trend analizi / çift dili **dağıtma**. Bütçeyi şu üçe yığ:
1. Alan bazlı **güven skoru + kaynak vurgulama** (açıklanabilirlik)
2. **Bankalar arası çelişki tespiti** ("masrafsız" deyip tahsis ücreti alanı yakala —
   jüride çok güçlü)
3. **Config-driven banka onboarding**

---

## 19. Kod Konvansiyonları

- **Dil:** kod/değişken İngilizce; yorum/docstring Türkçe olabilir; kullanıcıya
  dönük tüm metinler (dashboard, chatbot) Türkçe.
- **Python:** type hints zorunlu, Pydantic şema, `ruff` + `black`, tek-sorumluluk.
- **LLM çıktısı:** her zaman `guided_json` / Pydantic ile zorunlu — serbest metin
  parse etme.
- **Modülerlik:** her katman bağımsız test edilebilir (Teknik İmplementasyon %20).
- **Halüsinasyon yasağı:** bilgi yoksa `null`.
- **Gizli bilgi yok:** repoda API anahtarı/kişisel/müşteri verisi olmasın.

---

## 20. Uyumluluk Kontrol Listesi (her commit)

- [ ] LICENSE = Apache-2.0 mevcut
- [ ] Ücretli API/servis/yazılım YOK
- [ ] Yalnızca Apache/MIT lisanslı model ağırlıkları
- [ ] İnternetsiz `docker-compose up` çalışıyor
- [ ] Kod yarışma döneminde yazıldı (Turnitin kontrolü var)
- [ ] Haftalık commit; etiketler: `BilisimVadisi2026` + `Türkiye Açık Kaynak Platformu`
- [ ] README'de tam kurulum + çalıştırma + veri seti indirme linki

---

## 21. Sık Hatalar — Kaçın

- Ücretli API/yazılım (diskalifiye riski)
- LLM çıktısını serbest metin parse etmek (her zaman guided JSON)
- Eksik bilgiyi doldurmak için değer uydurmak
- Tek seferlik scraper (config-driven yap)
- Çalışmayan/tekrar üretilemeyen repo (`docker-compose up` ile gelmeli)
- Değerlendirmeyi sona bırakmak (gold seti ilk iki haftada kur)
- Canlı LLM/scrape'e bağlı demo (önceden doldur — §11)
- GitHub'a geç yükleme / haftalık commit'i atlamak

---

## 22. Çalışma Tarzı

- Büyük değişiklikten önce kısa plan sun, sonra uygula.
- Bağımlılık eklemeden önce lisansını kontrol et (Apache/MIT/GNU dışıysa sor).
- Her özellik için test + (mümkünse) eval güncellemesi.
- Belirsizlikte varsayım yapma; sor.
</content>
</invoke>
