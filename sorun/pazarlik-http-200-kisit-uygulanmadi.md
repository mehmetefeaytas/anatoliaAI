---
title: "Yetenek pazarlığı «parametreyi tanıdım» ile «kısıtı uyguladım»ı ayırt etmiyordu"
tags: [sorun, llm, yapilandirilmis-cikti, pazarlik, sessiz-hata]
source: "[[2026-08-24-ssb-evren-cikarim-servisi]]"
date: 2026-08-24
status: stable
---

# Yetenek pazarlığı «parametreyi tanıdım» ile «kısıtı uyguladım»ı ayırt etmiyordu

## Belirti

[[ssb-evren-cikarim-servisi]] ucuna bağlanınca çıkarım hattı **hiç alan
bulamadı** gibi göründü. Oysa servis çalışıyordu, model Türkçe metni doğru
anlıyordu ve HTTP hatası yoktu.

## Kök neden

`VLLMClient.negotiate()` çalışan yapılandırılmış-çıktı (structured output)
modunu ölçerek bulur: her modu 1 token'lık gerçek bir istekle dener ve ilk
**HTTP 200** dönen modu seçip cache'ler. Buradaki örtük varsayım şuydu:

> Sunucu parametreyi kabul ettiyse kısıtı da uygular.

EVREN bu varsayımı kırdı. `guided_json` parametresini **tanıyor**, HTTP 200
dönüyor, ama kısıtı **hiç uygulamıyor**:

| İstek | Yanıt |
|---|---|
| `guided_json` + `max_tokens=1` | `'P'` |
| `guided_json` + `max_tokens=8` | `'Pong! 🏓\n\nHow'` |

Pazarlık `guided_json`'u seçti, gerçek çağrı serbest Türkçe metin döndürdü,
`parse.py` onu ayrıştıramadı ve hata üst katmanda "LLM alan bulamadı" olarak
göründü. Bu, `clients.py` modül docstring'inin **önlemek için yazıldığı** hata
sınıfının aynısıdır — yalnızca kılığı değişmişti: eskiden sunucu parametreyi
reddediyordu (400, görünür), şimdi sessizce yok sayıyor (200, görünmez).

## Çözüm (fix)

Prob artık kısıtın **uygulandığını** da sınıyor: kısıtlı decoding'de ilk token
`{` olmak zorundadır, kısıt yoksa model kendi cümlesine başlar.
`_kisit_uygulandi()` bunu okur; sınavı geçemeyen mod elenir ve
`negotiation_log`'a *"HTTP 200 ama kisit UYGULANMADI"* yazılır.

İki koruma bilerek eklendi:

1. **Muhafazakârlık.** Prob yanıtı **boşsa** mod elenmez. Bazı sunucular
   `max_tokens=1`'de boş içerik döndürür; kararsızlığı "kısıt yok" diye okumak
   çalışan bir modu eler ve sistemi gereksizce `prompt_only`a düşürür. Yanlış
   eleme, yanlış kabulden pahalıdır.
2. **`prompt_only` proba tabi değil.** Orada kısıt zaten yoktur, son çaredir;
   elenirse hiç mod kalmaz.

Ayrıca araya **`json_object`** modu eklendi (`response_format={"type":
"json_object"}`): şema kısıtı yok ama JSON kısıtı var. Mod zinciri artık
`json_schema → structured_outputs → guided_json → json_object → prompt_only`.

Kaçış kapısı: `VLLM_KISIT_PROBU=0`.

## Ölçülen etki

Düzeltme sonrası EVREN'de pazarlık doğru moda düşüyor ve ayrıştırma başarılı:

```
json_schema         HTTP 500
structured_outputs  HTTP 500
guided_json         HTTP 200 ama kisit UYGULANMADI
json_object         OK
```

Kalite kazancı ise **sıfır** ölçüldü: `prompt_only` ve `json_object` koşumları
birebir aynı F1 verdi. Gerekçe — model `temperature=0`'da zaten geçerli JSON
üretiyordu (şema yönergesi prompt'a gömülü); darboğaz JSON *biçimi* değil, şema
uyumu. Düzeltmenin değeri kalitede değil **dürüstlükte**: sistem artık hangi
kısıtla koştuğunu doğru raporluyor.

## Çözümün ikinci yarısı — `tool_calling` (24 Ağu, aynı gün)

Prob düzeltmesi doğru modu SEÇMEYİ sağladı ama elde kısıtlı bir mod yoktu:
`json_object` yalnız JSON biçimini kısıtlar, şemayı değil. Resmi dokümantasyon
okununca tool/function calling desteğinin yazılı olduğu görüldü ve denendi —
**aynı şema kabul edildi** (12 alan, 39 `anyOf`, 5.548 karakter; 12 alanın
tamamı doğru yapıda döndü). Yani uç şemayı derleyebiliyor; kabul etmediği şey
`response_format` sarmalayıcısıydı.

Mod `STRUCTURED_MODES`'a kısıt gücüne göre eklendi:
`guided_json → tool_calling → json_object`.

İki incelik ölçümle çıktı:

1. **Yanıt `content`te değil.** Tool calling'de çıktı
   `message.tool_calls[0].function.arguments` içine yazılır ve `content` boş
   kalır. Yalnız `content`e bakan okuyucu bunu "model boş cevap verdi" diye
   okur; `_yanit_metni` bu yüzden yazıldı.
2. **Prob 1 token istiyor ve tool çağrısı o tek token'da TAMAMLANMIYOR.**
   Sunucu `tool_calls`ı ayrıştıramıyor ve `content`e ham başlangıç işaretini
   (`<tool_call>`) bırakıyor. Prob onu `{` ile başlamadığı için eledi ve
   ablasyon **yine** kısıtsız `json_object` ile koştu — yani düzeltme olmadan
   bu modun hiçbir faydası görünmezdi. `_kisit_uygulandi` artık mod
   farkındadır: `tool_calling` modunda `tool_call` işareti kısıt kanıtıdır.

Canlı doğrulama: pazarlık `json_schema` 500 → `structured_outputs` 500 →
`guided_json` "kısıt uygulanmadı" → **`tool_calling` OK** sırasını izliyor;
12 dolu alan, 524 logprob.

Testler: `tests/test_llm_tool_calling.py` (13 test).

## Açık kalan

Şema desteği **alan bazında** değişiyor: alan başına çağrıda pazarlık
`json_schema`'yı seçiyor (tek alanlık şemada kısıt gerçekten çalışıyor) ama
`hedef_kitle` alanının şeması yine 500 veriyor. Pazarlık modu **istemci
başına** cache'liyor; bu varsayım da EVREN'de kırılıyor. Düzeltmenin iki yolu
var (şema-başına pazarlık, ya da o alanın şemasını sadeleştirme) ve ikisi de
ölçülmeden seçilmemeli.

## İlgili dosyalar

- `app/src/extraction/llm/clients.py` — `_kisit_uygulandi`, `negotiate`,
  `json_object` modu
- `app/tests/test_llm_kisit_probu.py` — 7 test (davranışın sözleşmesi)
- `app/.env.example` — `VLLM_KISIT_PROBU` notu

## Sources

- [[2026-08-24-ssb-evren-cikarim-servisi]] — ölçüm dökümü
- `app/docs/evren-servisi.md` §3-b, §3-b-2, §3-c

## Related

- [[ssb-evren-cikarim-servisi]] — hatanın açığa çıktığı servis
- [[evren-opsiyonel-kademe-olarak-entegrasyon]] — aynı çalışmanın kararı
- [[bilgi-cikarimi]] — kısıtlı çıktının hizmet ettiği kavram
