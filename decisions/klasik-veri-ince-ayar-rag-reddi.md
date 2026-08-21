---
title: "Karar: klasik banka verisi ince ayar ve RAG kaynağı olarak reddedildi"
tags: [decision, veri, fine-tune, rag, terminoloji, olcum]
source: "[[2026-08-06-mentor-terim-sozlugu]]"
date: 2026-08-07
status: stable
---

# Karar: klasik banka verisi ince ayar ve RAG kaynağı olarak reddedildi

**Karar:** Klasik (katılım olmayan) bankaların korpusu (`data/raw-classic/`, 724
belge) **LLM ince ayarında (fine-tune) kullanılmaz** ve **RAG erişim kaynağı
olarak indekslenmez**. Katılım bankacılığı sorularının hem eğitim hem erişim
kaynağı yalnızca kendi katılım korpusumuzdur (`data/raw/`; karar tarihinde 1759, 2026-08-21 ölçümünde **2.706 kazınmış belge** — PDF hasadıyla büyüdü).

## Bağlam

Klasik korpus zaten toplanmış durumda ve gümüş etiketleme hattını besliyor.
"Madem veri var, LLM'i onunla da eğitelim / chatbot ona da baksın" önerisi doğal
biçimde ortaya çıktı. Öneri ölçülerek reddedildi.

Terim dağılımı (terimi içeren **belge oranı**):

| terim | klasik korpus (724 belge) | yarışma korpusu (ölçüm tarihinde 1759 belge; 2026-08-21'de 2.706) |
|---|---|---|
| murabaha | %0,0 | %1,9 |
| icare | %0,0 | %0,6 |
| mudaraba | %0,0 | %0,5 |
| müşaraka | %0,0 | %0,3 |
| katılma hesabı | %0,0 | %11,6 |
| kâr payı | %0,3 | %18,1 |
| sukuk | %0,1 | %5,7 |
| "faiz" geçen belge | **%70,2** | %7,3 |

**Ölçüm notu:** [[klasik-banka-korpusu]] sayfası aynı korpusu bağımsız ölçtü ve
bazı katılım-korpusu değerlerinde farklı sonuç verdi (murabaha %1,8 / 31 belge,
sukuk %2,3 / 40 belge). Fark, terim eşleme yönteminden (alt dizge ↔ sözcük
sınırı) ve payda tanımından kaynaklanıyor olabilir. **Kararı etkilemez:** her iki
ölçümde de klasik korpustaki fıkhî terim oranı %0,0, katılım korpusundaki oran
ise tek haneli yüzdelerde — yani seyreklik gerekçesi (Gerekçe 2) her iki sayı
kümesiyle de aynı sonucu verir.

## Gerekçe 1 — ters register (yasakladığımız sözlüğü öğretir)

Klasik korpusun **%70,2'si "faiz" kelimesini içeriyor**; fıkhî terim oranı
pratikte **sıfır**. Bu veriyle ince ayar yapmak, modele tam olarak kullanmasını
**yasakladığımız** sözlüğü öğretmek demektir.

Bu, mentörün uyarısının ([[2026-08-06-mentor-terim-sozlugu]])
makine öğrenmesi karşılığıdır: "faiz"i çıktı tarafında yasaklayıp
([[terim-sozlugu-enjeksiyon-replace-degil]], `output_violations`) eğitim
tarafında %70 yoğunlukta beslemek kendi kendini bozan bir tasarımdır.

## Gerekçe 2 — seyreklik (asıl teknik gerekçe)

Ters register tek başına yasak sebebi değil; asıl teknik gerekçe **fıkhî
terimlerin katılım korpusunda da nadir olması**: murabaha %1,9, icare %0,6,
mudaraba %0,5.

**%0,6 sıklıktaki bir terim ince ayarla öğrenilmez; enjekte edilir.** Yani veri
sorununun çözümü daha çok metin değil, **doğru mekanizmadır**: 101 terimlik
sözlük + belgeye özel terim kartı (`app/src/domain/terminology.py`,
[[katilim-finans-terimleri]]). Bu zaten alınmış bir karardır
([[terim-sozlugu-enjeksiyon-replace-degil]]).

Fıkhî terimlerin bölüm bazlı yoğunluğu (yarışma korpusu) bunu doğruluyor —
terimler korpusa eşit dağılmıyor, **sözleşme/tarife belgelerinde toplanıyor**:

| bölüm | belge | fıkhî terim taşıyan | oran |
|---|---:|---:|---:|
| `docs` (sözleşme/tarife) | 112 | 47 | **%42,0** |
| `products` | 637 | 104 | %16,3 |
| `live` | 808 | 39 | %4,8 |
| `archive` | 201 | 3 | %1,5 |

En sık fıkhî terimler (belge sayısı): sukuk 100, istisna 50, vekâlet 37,
muaccel 36, murabaha 34, icare 11, karz-ı hasen 11, mudaraba 9, müşaraka 6,
vaad 6.

## Gerekçe 3 — RAG'de olgusal yanlışlık

RAG pasajı kullanıcıya **kaynak göstererek** basılır. Katılım bankası sorusuna
Akbank/Garanti pasajıyla cevap vermek yalnız terminolojik değil **olgusal olarak
da yanlıştır**: gösterilen ürün, gösterilen bankanın ürünü değildir. Hibrit
chatbotun ([[hibrit-chatbot-text-to-sql-rag]]) RAG kolu için bu, düzeltilemez bir
kaynak hatasıdır.

## Gerekçe 4 — yanlış halkaya yatırım

Ölçülen kol karşılaştırması (kural/strict, gold):

| kol | mikro-F1 |
|---|---|
| **kural** | **0,677** |
| orkestra | 0,672 |
| hibrit | 0,575 |

LLM katmanı şu anda **zarar veriyor**. En zayıf halka LLM'in katılım
terminolojisi bilgisi değil, LLM katmanının kendisidir; oraya veri yatırmak
yanlış halkaya yatırımdır. Ayrıca `app/CLAUDE.md` §4 alan çıkarımı için ince
ayarı **zaten yasaklıyor**, yalnız 8 sınıflı sınıflandırmaya izin veriyor
([[ner-fine-tune-yerine-kural-few-shot]]).

## Kararın sınırı

Bu karar dar kapsamlıdır; iki noktada **aşırı genellenmemelidir**:

1. **Klasik veri gümüş eğitim için geçerlidir ve kullanılıyor** — 505 kayıt,
   8 sınıf (`app/data/silver/silver.jsonl`, [[metin-siniflandirma]]). Orada
   aktarılan şey terminoloji değil **ürün ailesi yapısıdır** (konut / taşıt /
   ihtiyaç / kart / alışveriş puanı ayrımı bankacılık türünden bağımsızdır).
   Ayrıklık kasıtlıdır (`app/CLAUDE.md` §12): **klasikte eğit, katılımda ölç**.
2. **RAG'in kendisi reddedilmiyor** — reddedilen, klasik korpusun RAG kaynağı
   olmasıdır. Doğru kaynak kendi `app/data/raw/*/docs/` bölümümüzdür; fıkhî terim
   yoğunluğu orada **%42,0** ile en yüksektir.

## Alternatif — bunun yerine ne yapılacak

- Terminoloji **enjeksiyonla** taşınır: 101 terimlik sözlük + belgeye özel terim
  kartı ([[terim-sozlugu-enjeksiyon-replace-degil]]).
- RAG indeksi katılım korpusuyla, öncelik `docs/` bölümüne verilerek kurulur.
- Klasik korpus yalnız gümüş sınıflandırma eğitiminde kalır; ölçüm her zaman
  katılım korpusunda yapılır.

## Sources
- [[2026-08-06-mentor-terim-sozlugu]] — "faiz" sözlüğünün yasaklanması, çıktı
  tarafı bağlayıcılığı
- `app/data/raw-classic/_collection_report.md` — klasik korpusun toplanma raporu
- `app/docs/rapor/karar-bekleyenler.md` — K-2, kol bazlı mikro-F1 ölçümleri
- `app/CLAUDE.md` §4 (ince ayar dağılımı), §12 (alan bilgisi / ayrıklık)

## Related
- [[klasik-banka-korpusu]] — reddin konusu olan korpusun varlık sayfası
- [[terim-sozlugu-enjeksiyon-replace-degil]] — seyrek terimin doğru mekanizması
- [[ner-fine-tune-yerine-kural-few-shot]] — ince ayarın zaten daraltılmış kapsamı
- [[hibrit-chatbot-text-to-sql-rag]] — RAG kolunun kaynağını belirleyen karar
- [[katilim-finans-terimleri]] — 101 terimlik sözlüğün kavram sayfası
- [[katilim-bankaciligi-terminoloji-farkliligi]] — çözülmeye çalışılan sorun
- [[bddk-listesi-veri-kaynagi-kapsami]] — yarışma korpusunun kapsam kararı
- [[metin-siniflandirma]] — klasik verinin meşru kullanıldığı tek yer
- [[veri-seti]] — korpus varlığı
