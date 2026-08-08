---
title: "Mentör maili: katılım finansı terim sözlüğü (mentör)"
tags: [source, mentor, terminoloji, prompt, chatbot]
date: 2026-08-06
status: stable
---

# Mentör maili: katılım finansı terim sözlüğü

## goal

Mentör (eski bankacı; chatbot ve çok-ajanlı sistem deneyimi), ilk
mentörlük toplantısında konuşulan terminoloji sorunu üzerine yazılı görüş ve
**101 girdilik yapılandırılmış bir katılım finansı sözlüğü** gönderdi.

## what-was-done

Mailin özü tek cümlede: **terimi replace etme, LLM'e analizi ver.**

> "Bunları LLM'e system prompta vermek mantıklı. Birebir değiştirmek anlamda
> bozukluk yaratıyor. Eşim avukat, ona danıştım, iyi Osmanlıca bilir,
> Türkçeleri aynı anlamı replace ile taşımıyor. O sebeple böyle bir kapsamlı
> analiz vermek gerekiyor. Bir de dönüşte atıyorum fon ya da bono yazmak da
> yanlış. Yine bunların jargonla cevap oluşturmak doğrusu. Ona da dikkat etmek
> lazım."

İki ayrı iddia var ve ikisi de bağlayıcı:

1. **Girdi tarafı** — yasak/karşılık tablosuyla kör değiştirme anlamı bozar;
   doğru yöntem sözlüğü sistem prompt'una vermektir.
2. **Çıktı tarafı** — modelin ürettiği cevapta "fon", "bono", "tahvil" gibi
   konvansiyonel karşılıklar kullanmak da yanlıştır; cevap jargonla kurulmalı.

Sözlüğün alan şeması: `id, kanonik, tip, kategori, resmi_tr, en, varyantlar,
halk_dili, tanim, sade_aciklama, degildir, ayrim_notu, iliskili, kaynak,
risk_notu`. Kritik olan iki alan **`degildir`** (terimin ne OLMADIĞI) ve
**`ayrim_notu`** (ayrımın nerede durduğu) — mailin istediği "kapsamlı analiz"
tam olarak bunlar.

Terimlerin hukuki ayrımları mentörün avukat eşi tarafından gözden geçirildi.
Kaynaklar girdi başına yazılı: AAOIFI Şer'i Standartları, TKBB Katılım Finans
Standartları, 5411 sayılı Bankacılık Kanunu, SPK III-61.1, Türk Borçlar
Kanunu, Türk Medeni Kanunu, 6361 sayılı Kanun, SEDDK.

## files-changed / touched

- `app/data/terminology/katilim-terim-sozlugu.json` (sözlüğün kendisi)
- `app/docs/terminoloji-sozlugu.md` (köken belgesi)
- `app/src/domain/terminology.py` (yükleyici, yönlendirici, kart, bekçi)
- `app/scripts/jargon_lint.py`
- `app/src/chatbot/safety.py` (kapsam kapısı genişletildi)

## decisions

- [[terim-sozlugu-enjeksiyon-replace-degil]]

## issues

- [[katilim-bankaciligi-terminoloji-farkliligi]] — bu mail o sorunun
  otoriter çözümünü getiriyor.

## open-threads

- Mentörden ayrıca **multi-agent prompt'ları ve hakem (judge) prompt'u**
  bekleniyor; geldiğinde `app/src/extraction/llm/agents.py` içindeki `J`
  rolüne takılacak.
- Mentöre gönderilecek: iki temsili kirli metin, kullanılan model +
  kuantizasyon + temperature, doküman kesiti, şu anki prompt, alan şeması.

## Sources

- Mentörün 2026-08-06 tarihli e-postası (ekli JSON sözlük dahil)

## Related

- [[katilim-finans-terimleri]] — sözlüğün kavram sayfası
- [[terim-sozlugu-enjeksiyon-replace-degil]] — mailden çıkan karar
- [[orkestrasyon-yetki-asimetrisi]] — mailin multi-agent önerisinin uygulaması
