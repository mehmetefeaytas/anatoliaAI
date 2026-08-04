# Devam notu — `split_trainable` kalıp ayıklaması

> 2026-08-04. İlgili: `scripts/split_trainable.py` · `tests/test_split_trainable.py`
> · `data/silver/split_report.md`

## Ne yapıldı

n-gram tabanlı çerçeve ayıklaması gerçek kampanya gövdesini yiyordu. Kök neden
eşiğin sayısı değil **kampanya şablonu**: bankalar aynı kampanyayı 3-6 varyantla
yayınlıyor (aynı metin, farklı tutar/marka/tarih), gövde cümleleri de "3 belgede
tekrar eden" hâle geliyor ve menüyle aynı kefeye düşüyordu.

Üç değişiklik:

1. `SIGNAL_MIN_FRACTION = 0.25` — oran/tutar/taksit/vade taşıyan n-gram ancak
   bankanın belgelerinin ≥%25'inde geçiyorsa çerçeve sayılır.
2. `core_text`te **koruma baskın** — korunan pencerenin kapsadığı sözcük, komşu
   çerçeve penceresi de kapsıyor olsa bile kalır.
3. `core_text` artık **noktalamayı koruyor** — `%2,05` ve `1.500,00 TL` biçimi
   çekirdekte görünür (eskiden `2 05` / `1 500 00 TL` oluyordu).

## Ölçüt

Bir belge, ham metninde **belge-özgü** finansal sinyal taşıyıp `core_text`inde
hiç finansal sinyal kalmıyorsa "içerik kaybetmiş" sayılır.

- **Finansal sinyal:** `%\d` · `\d+ TL/₺/TRY` · `taksit` · `vade`. Keyfî değil;
  CLAUDE.md §9'un sayısal kanonik alanlarıyla birebir örtüşüyor
  (`kar_payi_orani`, `finansman_tutari`, `vade_ay`, `taksit_sayisi`).
- **Belge-özgü:** sinyali taşıyan 8-gram, bankanın belgelerinin %10'undan
  azında geçiyor. Bu şart olmadan ölçüt yanlış pozitif üretiyor: Akbank'ın her
  sayfasında (63/64) açılan "Masraf ve Maliyet Oranları / % 0" modalı site
  kromudur, atılması doğrudur ama naif ölçüt onu "kayıp" sayıyordu.

## Sayılar (öncesi → sonrası)

| Korpus | Belge | İçerik kaybeden | Çerçeve sızıntısı | Çekirdek <12 sözcük | Atılan sözcük |
|---|--:|--:|--:|--:|--:|
| `data/raw` | 1684 | **312 → 21** | 61 → 70 | 138 → 28 | %49,0 → %43,3 |
| `data/raw-classic` | 709 | **54 → 4** | 12 → 12 | 16 → 15 | %71,9 → %69,4 |

Çerçeve sızıntısı = çekirdeğinde çerez/KVKK/aydınlatma-metni ifadesi kalan
belge sayısı (site kromu ayıklanamamış demektir).

## Açık kalanlar

1. **Kalan 25 belge** (21 `data/raw` + 4 `data/raw-classic`) hâlâ içerik
   kaybediyor. Yoğunlaştığı yer: `vakif-katilim` (11) ve `yapi-kredi` (4).
   Bunlar `<slug>.txt` / `<slug>-2.txt` NEAR-DUPLICATE çiftleri; iki belge
   gövdesinin tamamını paylaşıyor ve üçüncü bir kardeşle birlikte df 3'e
   çıkıyor. Doğru çözüm eşik değil **yakın-mükerrer tespiti** (shingle
   Jaccard) olabilir: çift üyelerinden biri `R_MUKERRER` sayılırsa diğerinin
   gövdesi çerçeveye gitmez.
2. **`vakif-katilim` sızıntısı 40 → 49.** Bankanın kromu belgelerinin
   %25'inin altında tekrar ettiği için sinyalli krom parçaları korunuyor.
   Zararı sınırlı (çekirdekte fazla metin, eksik metin değil) ama izlenmeli.
3. **`.gitignore` güncellenmedi.** `data/silver/trainable.jsonl` orada "BİLİNEN
   KUSURLU" gerekçesiyle listelenmiş. Kusur ölçülerek daraltıldı; gerekçe
   metninin güncellenmesi veya dosyanın depoya alınıp alınmayacağı kararı ayrı
   bir iş — bu oturumda `.gitignore`a dokunulmadı (dosya başka bir agent'ın
   kapsamındaydı).
4. **`data/raw` için yeniden üretim yapılmadı.** Betiğin varsayılanı
   `data/raw-classic`; `data/raw` ölçüldü ama `trainable.jsonl`ı üretilmedi.
   Gerekirse: `--docs data/raw --out-dir <ayrı klasör>`.
