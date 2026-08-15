# `gold.round1.recall.json` — künye ve KULLANIM SINIRI

> ⛔ Bu dosya `gold.round1.json`'un yerine geçmez. Manşet metrikler **insan
> gold'undan** (`gold.round1.json`) verilir. Bu dosya yalnız **recall
> ölçülebilirliği** için vardır ve LLM tarafından tamamlanmış hücreler içerir.

## Neden var — ölçülmüş boşluk

`gold_report_round1.md` şunu yazıyordu:

    12/12 alan karara bağlı (recall ÖLÇÜLEBİLİR): 0

134 kayıtlık gold'da **hiçbir kayıtta** 12 alanın hepsi karara bağlı değildi.
Yani elimizde precision vardı, recall yoktu. Değerlendirmenin %30'u "Model
Başarısı ve Anlamlandırma" ve recall o başlığın yarısıdır.

Sebep kapsama: anotatörler belge başına ortalama 1–2 alan karara bağladı
(dağılım: 7/12 bir belge, 5/12 bir belge, 4/12 altı belge, gerisi ≤3).

## Nasıl üretildi

1. Kapsaması **en yüksek 10 belge** seçildi (42 hücre zaten insan kararlıydı).
2. Kalan **78 hücre** iki ayrı Opus 5 oturumunda karara bağlandı. Her oturuma
   belge tam metni + kılavuzun karar sözlüğü, 12 alan tanımı ve sekiz kuralı
   gömülü verildi.
3. Kararlar `round1_recall_opus.csv`'ye yazıldı — **ayrı dosya**, `build_gold`
   anotatör adını `recall_opus` diye çıkarıyor, insan kararlarıyla karışmıyor.
4. Her hücrenin `note`'una `#recall-opus5` damgası düştü.

### Kapılar

- `verdict` dört değerden biri, `fix` ⇒ `gold_value` dolu ve `parse_gold_value`
  süzgecinden geçiyor, `fix` değilse boş, `note` zorunlu.
- **Birebir alıntı kapısı:** `kampanya_kosullari`'nda `fix` verilen her cümle
  belge metninde birebir (boşluk/tırnak normalize) geçmek zorunda.
  `silver_birlestir.dogrula` ile aynı ilke — belgede geçmeyen bir cümle ölçüme
  girerse çıkarıcıyı haksız yere yanlış gösterir.
- Değeri birebir doğrulanamayan iki `kampanya_kosullari` hücresi `unclear`'a
  çevrildi (metrik dışı), uydurma değer yazılmadı.
- 78/78 yazıldı, 0 red. Lint: 0 hata, 0 uyarı.

## Sonuç

| | insan gold | recall gold |
|---|---:|---:|
| kayıt | 134 | 134 |
| **12/12 kapsanan (recall ölçülebilir)** | **0** | **5** |
| kanıtlı alan | 129/148 | 133/157 |
| çelişki | 11 | 11 |

10 belgenin **hepsi** 12/12 karara bağlandı; 5'i tam ölçülebilir. Kalan 5'te
en az bir alan `unclear` — `unclear` metrik dışıdır, dolayısıyla o kayıtlar
"recall ölçülebilir" sayılmaz. Bu, ölçümün kendini kısıtlamasıdır, kusur değil.

### Eval (kural, strict)

| | insan gold | recall gold |
|---|---:|---:|
| mikro P / R / F1 | 0,732 / 0,757 / 0,744 | 0,682 / 0,739 / 0,709 |
| mikro yapısal F1 | 0,739 | 0,724 |
| TN (doğru sessizlik) | 34 | **93** |
| FP | 41 | 54 |
| FN | 36 | 41 |

Sayıların DÜŞMESİ beklenen ve doğru yöndür: karara bağlanan hücre sayısı
arttıkça daha çok hata ölçülür. TN'nin 34'ten 93'e çıkması, modelin doğru
sessizliğinin ilk kez sayılabildiğini gösterir.

## Ne söylenebilir, ne söylenemez

| Söylenebilir | Söylenemez |
|---|---|
| "10 belgede 12/12 kapsama sağlandı; recall ilk kez 5 kayıtta ölçülebilir" | ❌ "gold seti 134 kayıt, recall %73,9" |
| "eksik hücreler LLM ile tamamlandı, insan hücreleri dokunulmadan korundu" | ❌ manşet metrik olarak sunmak |
| "kural katmanı LLM'in etiketiyle eğitilmiş DEĞİLDİR; ölçüm kendi çıktısını doğrulamıyor" | ❌ "insan gold'u kadar güvenilir" |

Kural çıkarıcısı bu etiketlerle **eğitilmedi** — dolayısıyla BERTurk'ün
düştüğü tuzak (gümüşle eğit, altınla ölç) burada yoktur. Yine de LLM yazımı
bir referans, insan yazımı bir referansla aynı şey değildir; bu ayrım
raporda korunmalıdır.

## Sonraki adım

Bu 78 hücrenin **insan doğrulaması**, `#recall-opus5` damgası sayesinde tek
komutla süzülebilir. Doğrulanan hücreler insan gold'una taşınırsa dosya
gereksiz hâle gelir — hedef budur.

## Sources
- `data/gold/gold_report_round1_recall.md` — derleme raporu
- `data/gold/review/round1_recall_opus.csv` — kararlar
- `data/gold/ANNOTATION_GUIDE.md` §3 (karar sözlüğü), §4, §4.13
