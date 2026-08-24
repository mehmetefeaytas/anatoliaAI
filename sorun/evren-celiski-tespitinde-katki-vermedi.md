---
title: "EVREN çelişki tespitinde katkı vermedi (ölçüldü, yol kapatıldı)"
tags: [sorun, olcum, celiski, evren, reddedilen-yol, yenilikcilik]
source: "ölçüm (2026-08-24, EVREN llm-large, 230 belge)"
date: 2026-08-24
status: stable
---

# EVREN çelişki tespitinde katkı vermedi

## Soru

Kural hattı çelişki tespitinde çok titiz (üç savunma katmanı: kapsam,
kıyaslanabilirlik, normalizasyon) ve ilkesi net: *"hayalet çelişki on gerçek
çelişkiden çok zarar verir"*. LLM bir dördüncü katman olabilir mi — ya
kuralın kaçırdığını bulur ya da bulgularını doğrular?

## Mevcut durum — ölçüldü

1.726 kampanya belgesinde kural hattı **20 çelişki** buluyor:

| tip | sayı | LLM yargısı anlamlı mı? |
|---|---|---|
| `suresi_dolmus_kampanya` | 17 | **hayır** — deterministik tarih karşılaştırması |
| `celisen_tutar_bandi` | 2 | evet |
| `celisen_kampanya_bitisi` | 1 | evet |

Yani **doğrulama** fikri baştan uygulanamaz: LLM yargısının anlamlı olduğu
küme 3 bulgudan oluşuyor ve bu örneklemde istatistiksel bir şey ölçülemez.

## Arama denemesi — 230 belge, sıfır bulgu

Kalan soru: EVREN kuralın KAÇIRDIĞINI bulur mu? Kısıtlı çıktı (`maxItems: 3`)
ve **kanıt kapısı** ile ölçüldü — LLM'in gösterdiği iki ifadenin İKİSİ de
belgede geçmeli, yoksa hayalet sayılır:

| örneklem | kanıtlı çelişki | hayalet | çağrı hatası |
|---|---|---|---|
| 30 belge | 0 | 0 | 0 |
| 200 belge | **0** | **0** | 0 |

EVREN hiçbir iddia üretmedi — ne doğru ne yanlış. Çağrılar başarılıydı.

## Yorum

Korpusta çelişki oranı zaten çok düşük (%1,2). 200 belgede beklenen bulgu
~2,3 ve LLM 0 buldu; yani ölçüm "LLM kötü" demiyor, **"bu iş için ek bir kol
gerekmiyor"** diyor.

Prompt bilinçli olarak muhafazakârdı (*"emin değilsen boş liste; şüpheli bir
çelişki kaçırılmıştan daha zararlıdır"*) — modülün kendi ilkesiyle aynı.
Gevşetmek hayalet üretirdi ve o, kural hattının 20 gerçek bulgusunu
gölgeleyecek bir maliyet.

**Karar: yol kapatıldı.** Çelişki tespiti kural hattında kalıyor.

## Ölçüm sırasında düzeltilen üç kendi hatam

1. `repo.get_campaign()` **yok**; ölçüm betiğim `except Exception: continue`
   ile hatayı yutup "1726 belgede 0 çelişki" yazdı. Sessiz yutma, ölçümü kör
   etti.
2. `VLLMClient.extract_json` yok — metot `generate(system, user, schema)`.
3. `base_url` sonuna `/v1` eklemek URL'i `/v1/v1/` yapıyor → HTTP 404.

Üçü de aynı sınıfta: **hatayı yutan ölçüm, yanlış sonucu doğru gibi
gösteriyor.** Aynı desen `llm_bosluk_doldur.py`de de vardı ve orada BOŞ DÖNÜŞ
sayacıyla kapatıldı.

## Sources

- `app/src/comparison/contradiction.py` — kural hattı ve üç savunma
- `GET /contradictions` — 20 bulgunun tip dağılımı
- Ölçüm betiği: kanıt kapılı çelişki arama, 30 + 200 belge

## Related

- [[llm-yalniz-kural-bosluklarini-doldurur]] — LLM'in İŞE YARADIĞI yer
- [[ssb-evren-cikarim-servisi]] — ölçülen servis
- [[urun-baglami-alan-duzeyinde-tasinmali]] — aynı gün ölçülen desen genişletmesi
