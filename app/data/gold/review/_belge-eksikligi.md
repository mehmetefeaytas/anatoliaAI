# Belge metni eksikliği — `round2_zor_vaka` (kapandı)

**Tarih:** 2026-08-09
**Durum:** çözüldü — 32/32 metin üretildi, denetim kapısı kuruldu.
**İlgili:** `scripts/belge_metni_denetimi.py` ·
`tests/test_belge_metni_denetimi.py` · `docs/rapor/zor-vaka-kurleme.md`

---

## Belirti

`round2_zor_vaka.csv` **73 belge / 949 satır** içeriyordu; `belgeler/` altında
bu belgelerin **yalnız 41'inin** `.txt` dosyası vardı. Kalan 32 belgeyi
anotatör göremiyordu. Metni olmayan belgede verilebilecek tek dürüst cevap
"karar veremedim"dir, kova 4 (recall kontrolü) ise tam metin okunmadan
doldurulamaz — yani paket bu hâliyle yollansa 949 satırın büyük kısmı boş
dönecekti.

Diğer paketlerin hepsi (`round0_kalibrasyon_*` 8 dosya, `round1_A/B`,
`round1_main_C/D`) ölçüldü: **eksik yok, boş metin yok**. Sorun tek pakete
özgüydü.

## Kök neden

Metinleri yazan tek yer `scripts/to_review_csv.py:486-489`:

```python
docs_dir = out / "belgeler"          # out = --out-dir
for doc_id, doc in docs.items():
    (docs_dir / f"{doc_id}.txt").write_text(doc.get("text", ""), ...)
```

CSV'ler ve `belgeler/` **aynı** `--out-dir` altına yazılır; ikisi birbirinden
ayrıldığı anda paket sakatlanır. `docs/rapor/zor-vaka-kurleme.md` §"Tekrar
üretim" bölümündeki komut zor-vaka paketini **geçici bir dizine** üretiyor:

```bash
.venv/bin/python -m scripts.to_review_csv \
  --pre data/gold/preannotations.zor.json --out-dir <tmp> ...
```

Sonra `<tmp>` içinden `data/gold/review/` altına **yalnız CSV** taşınmış,
`belgeler/` geçici dizinde kalmış. Klasörde zaten duran 41 metin, önceki
turların (`preannotations.json` ve `preannotations.v2.json`) ürünüydü.

Ölçümle doğrulandı — 41 sayısı tesadüf değil, tam olarak eski turların
kesişimi:

| kaynak | toplam belge | round2 kapsamı |
|---|---:|---:|
| `preannotations.json` (v1) | 243 | 29 |
| `preannotations.v2.json` | 250 | 33 |
| birleşimi | — | **41** |
| `preannotations.zor.json` | 73 | 73 |

Yani eksik 32 belge, **yalnız zor-vaka paketine özgü** olanlardı. Hiçbiri
"kaynakta yok" değildi; `belge_turu` süzmesine de takılmamışlardı — üretim
kısmi kalmıştı.

Bu hatanın sessiz kalma nedeni, kimsenin bakmıyor olması: `lint_review_csv`
satır **biçimini** denetler, satırın anote **edilebilir** olup olmadığını
değil.

## Çözüm

`scripts/belge_metni_denetimi.py --uret`, eksik metinleri `data/demo.db`
`campaigns.raw_text` kolonundan **birebir** yazdı (özetleme/kırpma yok).

`doc_id` ham korpustan türetilir (`preannotate._unique_doc_id`), veritabanında
böyle bir kolon yok. Kimliği DB satırına bağlayan köprü — üretecin kendi
kullandığı köprü — ön-anotasyondaki `source_url`:

    doc_id → preannotations*.json[source_url] → campaigns.raw_text

Yazmadan önce iki bağımsız kaynak karşılaştırıldı: `campaigns.raw_text` ile
ön-anotasyondaki `text`. **73 belgenin 73'ünde birebir aynı** çıktılar, yani
kaynak seçimi sonucu değiştirmiyor. Ayrışan bir belge olsaydı yazılmayacaktı —
hangisinin doğru olduğunu betik bilemez ve tahmin etmez.

**Sonuç: 32 belge üretildi, 0 belge üretilemedi.** Mevcut hiçbir `.txt`
üzerine yazılmadı.

Biçim doğrulaması: üretim önce geçici bir dizinde prova edildi; çıkan 70
dosyanın 70'i ön-anotasyon metniyle bayt bayt aynıydı. Mevcut 41 dosyanın
38'i de aynı metni taşıyor (kalan 3'ü için aşağıya bakın).

## Kalıcı kapı

1. **Denetim betiği** — `scripts/belge_metni_denetimi.py`

   ```bash
   .venv/bin/python -m scripts.belge_metni_denetimi          # kapı
   .venv/bin/python -m scripts.belge_metni_denetimi --uret   # onarım
   ```

   `data/gold/review/round*.csv` içindeki her `doc_id` için
   `belgeler/<doc_id>.txt` var mı ve **dolu mu** diye bakar. Eksik varsa çıkış
   kodu 1.

   Boş dosya da eksik sayılır: anotatöre "bu alan metinde yok" dedirtir, o
   karar gold'a girer ve modelin doğru çıkarımını yanlış sayar. Eksik metin
   görünür bir engel, boş metin görünmez bir hatadır. `--uret` bu yüzden bir
   metni ancak kaynağından birebir okuyabildiğinde yazar.

2. **Test** — `tests/test_belge_metni_denetimi.py::DepoKapisiTest`
   deponun gerçek paketleri üzerinde koşar. Aynı hata tekrar edilirse
   `unittest` kırmızı yanar; teslimden sonra değil, commit'te.

## Açık uçlar (anotasyonu engellemiyor)

- **3 dosya bayat.** `kuveyt-turk--kampanyalar-kampanya-arsivi-2`,
  `vakif-katilim--detay-3-ay-ertelemeli-motosiklet-kampanyasi`,
  `vakif-katilim--detay-50000-tl-ihtiyac-finansmani-kampanyasi` — bu üç
  `.txt` v1 turundan kalma metni taşıyor, `preannotations.zor.json` ve
  `demo.db` ise güncel (tazelenmiş) metni gösteriyor. Fark küçük (22–241
  karakter). **Üzerine yazılmadı**: dosyalar mevcut ve dolu, üstelik bu üç
  belge zaten önceki turlarda anote edilmiş olabilir; tazelemenin
  anotasyonu bayatlatıp bayatlatmadığı ayrı bir karar
  (`_tazeleme.md` süreci).
- **Üretilemeyecek 3 belge var ama round2'de değiller.** Prova sırasında
  ölçüldü: `kuveyt-turk--kampanyalar-kampanya-arsivi-2` (turlar 2 farklı
  `source_url` gösteriyor) ve `turkiye-finans--kampanyalar-biten-kampanyalar`
  + `-2` (aynı URL 2 farklı `raw_text` taşıyor). Üçünün de `.txt`'si zaten
  mevcut olduğu için engel değil; ama o dosyalar bir gün silinirse
  `--uret` onları geri getiremez.

## Related
- [[zor-vaka-kurleme]] — paketin nasıl kürlendiği; §Tekrar üretim komutu
- [[_atama.md]] — `round2_zor_vaka` tek anotatörlü, κ üretmez
