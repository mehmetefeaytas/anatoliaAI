# Round1 Gümüş Etiket Seti — künye ve SINIRLAR

> Üretildi: 2026-08-15 · Hat: `scripts/silver_parti_hazirla` → `silver_parti_bol`
> → (harici asistan oturumu) → `scripts/silver_birlestir`
> Çıktı: `round1_silver.jsonl` — **1.427 (belge, alan) kararı, 227 belge**

## ⛔ Bu set ALTIN DEĞİLDİR — ölçümde kullanılmaz

`eval/run_eval.py` gold'dan (`data/gold/gold.*.json`) okur, buradan **okumaz**
ve okumamalıdır. Bu setin etiketlerini üreten şey bir modeldir; aynı sistemi
onunla ölçmek modelin kendi çıktısıyla sınanması olur.

Bedeli bu projede ölçülmüştür: gold modelin çıktısına çapalıyken mikro-F1
**0,677**, kör protokolde **0,536** — aradaki 0,141 protokol artefaktıydı
(`../gold/ANNOTATION_GUIDE.md` §3.1). Gümüş etiketi gold'a karıştırmak bu
artefaktın daha büyüğünü üretir.

**Meşru kullanım:** sınıflandırıcı/çıkarıcı eğitimi, kapsama analizi, hata
kalıbı çıkarma, hakemlik önceliklendirme.
**Yasak kullanım:** P/R/F1 hesabı, κ hesabı, regresyon kapısı.

## Neden üretildi

Round1 turunda dört anotatör 1.795 hücreden **368'ini** karara bağladı
(%20,5). Kalan 1.427 hücre v2 protokolünde "karar verilmedi" sayılır ve gold'a
girmez. O hücreler boş kaldığı sürece recall ölçülemez ve sınıflandırıcı
eğitilemez.

Gümüş set bu boşluğu **ölçümü kirletmeden** doldurur: insan kararı olan hiçbir
hücre partiye alınmadı (tek bir anotatörün kararı bile varsa hücre insanındır).

## Ne var içinde

| verdict | adet | pay | anlamı |
|---|---:|---:|---|
| `ok` | 907 | %63,6 | model doğru — çoğu "doğru sessizlik" (model boş, metinde de yok) |
| `absent` | 263 | %18,4 | **halüsinasyon iddiası** — model değer üretti, metinde yok |
| `fix` | 230 | %16,1 | model yanlış/eksik; doğru değer yazıldı |
| `unclear` | 27 | %1,9 | metin gerçekten belirsiz; hakemliğe düşer |

- Ortalama güven: **0,809** · birebir alıntılı satır: **701/1.427**
- `absent` en çok: `masraf_durumu` (43), `finansman_tutari` (40), `hedef_kitle` (39)
- `fix` en çok: `kampanya_kosullari` (118) — tek başına düzeltmelerin yarısı

## Doğrulama kapıları (hepsi geçti)

`silver_birlestir` her kaydı gold'un süzgecinden geçirir:

- `verdict` dört değerden biri · `fix` ise `gold_value` dolu ve **kanonik**
  (`parse_gold_value`) · `ok`/`absent`/`unclear` ise boş
- `evidence` belge metninde **birebir** geçiyor (uydurma alıntı kapısı)
- her `(doc_id, field)` yalnız bir kez
- partide istenen hücrelerin tamamı karşılandı

Sonuç: **1.427 kabul · 0 red · 0 çift · 0 karşılanmayan.**

## Etiketleyicinin bulduğu model hata kalıpları

Bunlar gümüş etiketin yan ürünü ve çıkarıcıyı düzeltmek için doğrudan
kullanılabilir:

1. **Kabuk kirliliği** (`ANNOTATION_GUIDE` §4.13/8) — "İlginizi Çekebilir" /
   "Diğer Kampanyalar" bloklarından değer çekiliyor. Onlarca hücrede ölçüldü.
2. **KVKK/çerez metninden `masraf_durumu`** — aydınlatma metnindeki "ücretsiz
   sonuçlandırılmaktadır" cümlesi `{has_fee: false}` üretiyor.
3. **Eşik/ödül tutarının `finansman_tutari` sanılması** — sepet eşiği, ödül
   tutarı, hesaplama aracının slider üst sınırı.
4. **Örnek ödeme planından vade** — mevzuat gereği konan örnek tablodaki ay,
   ürünün ilan ettiği vade sanılıyor.
5. **Oransal ücretin TL'ye türetilmesi** — "binde 5" → `625 TL`; bu sayı
   metinde geçmiyor (§4.13/5 gereği `unclear` + `#oransal_ucret`).
6. **`kampanya_kosullari` kabuğu** — blog menüsü, SSS başlığı, yasal ihtar
   cümlesi koşul sanılıyor.

## Bilinen sınırlar

- **Tek etiketleyici.** Her hücreye bir model baktı; `build_silver`'ın üç oylu
  uzlaşma mekanizması (`src/extraction/silver/consensus.py`) bu turda
  kullanılmadı. Güven skoru bir model tahminidir, uyum ölçümü değildir.
- **Kılavuz boşlukları etiketlere yansıdı.** Etiketleyiciler bağımsız olarak
  aynı yerlerde tökezledi: ticari/tüzel segment için `hedef_kitle` karşılığı
  yok; "tek özne var ama 8 sınıfın hiçbiri uymuyor" durumunda `absent` dışında
  karşılık yok; ücret tarifesi/sözleşme PDF'lerinin tek özne testinden geçip
  geçmediği net değil. Aynı yerde bağımsız tökezleme kılavuz kusurudur
  (§4.13 girişi).
- **Kalite ölçümü ayrı yapıldı.** İnsanların hemfikir olduğu 60 hücrede kör
  test koşuldu: karar uyumu **%75,0**, değer uyumu **%71,7**. Ayrıntı ve 17
  uyuşmazlığın kırılımı: [KALITE-KOR-TEST.md](KALITE-KOR-TEST.md). Örneklem
  bilerek kolay tarafa yanlıdır (insanların uzlaştığı hücreler), bu yüzden
  sayı gümüşün genel doğruluğu değildir.

## Dosyalar

| Dosya | Ne |
|---|---|
| `round1_parti.jsonl` | etiketlenecek 227 belge / 1.427 hücre |
| `parca/kume_NN.jsonl` | metin hacmine göre dengelenmiş 10 küme |
| `parca/etiket_NN.jsonl` | küme başına ham etiket çıktısı |
| `round1_etiketler.jsonl` | pilot (4 belge / 21 hücre) |
| `round1_silver.jsonl` | **birleştirilmiş + doğrulanmış set** |
| `kalite_ornegi.jsonl` · `kalite_sonucu.jsonl` | kör kalite testi girdi/çıktı |
