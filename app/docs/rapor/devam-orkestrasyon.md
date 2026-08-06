# Devam notu — terim sözlüğü + çok-ajanlı orkestrasyon

**Durum:** 2026-08-06 akşamı durduruldu. Dal `veri-toplama-genislemesi`,
ağaç temiz, 1359 test çıkış 0, ruff temiz, `jargon_lint` temiz.
Bu oturumda 5 commit: `472ccfe`, `ba274c8`, `4df7d3b`, `d845145`, `9fe6206`.

Plan dosyası: `~/.claude/plans/structured-mixing-harbor.md` (A–H fazları).

---

## İLK İŞ — yarım kalan tek şey

Orkestrasyon kolunun gold ölçümü **koştu ama sonuç ÜRETMEDİ**. 40 dakika
çalıştı, log 0 baytta kaldı, süreç durdurulunca tampon uçtu.

**Sebep:** Python stdout'u dosyaya yönlendirilince tamponlar. `-u` verilmemişti.

```bash
cd /Users/mehmetefeaytas/anatoliaaI/app
LLM_BACKEND=ollama OLLAMA_MODEL=qwen2.5:7b-instruct OLLAMA_NUM_CTX=16384 \
  nohup .venv/bin/python -u -m eval.run_eval \
      --gold data/gold/gold.v1.json --config orkestra --matcher both \
      > /tmp/eval_orkestra.log 2>&1 &
```

`-u` ZORUNLU. Ayrıca rapor `eval/reports/<zaman>/` altına da yazılıyor;
tampon uçsa bile oradan okunabilir — ama koşu bitmeden o da yazılmaz.

**Süre beklentisi:** tek belge uçtan uca 116 sn (3 LLM çağrısı) ölçüldü.
`reconcile` yalnız eksik alanları sorduğu için gold'da daha hızlı olmalı;
20 belge için kabaca 20–40 dk. Karşılaştırma kolu (`kural`) saniyeler sürer:

```bash
.venv/bin/python -m eval.run_eval --gold data/gold/gold.v1.json --config kural
```

**Kapı (K3 kararı):** orkestrasyon `kural` kolunu geçemezse `DEFAULT_CONFIG`
kural kalır ve orkestrasyon ablasyon tablosuna ölçülmüş bir satır olarak
girer. Kazanan ilan etmek için |Δ| ≥ 0,05 gerekir (n=20'de altı gürültü).

Kıyas için mevcut sayılar (`docs/rapor/ablasyon.md`, n=20):

| kol | mikro-F1 | halüsinasyon |
|---|---|---|
| kural | 0,612 | 0,102 |
| hibrit | 0,575 | 0,163 |

---

## Bu oturumda tamamlananlar

### Faz A — terim sözlüğü altyapısı

- `data/terminology/katilim-terim-sozlugu.json` — 101 girdi, denetlendi
  (mükerrer id yok, `iliskili` çapraz referanslarının tümü çözülüyor).
- `src/domain/terminology.py` — yükleyici / deterministik yönlendirici /
  kart üreteci / çıktı bekçisi.
- `scripts/jargon_lint.py` + CI adımı.
- `src/chatbot/safety.py` kapsam kapısı sözlükle genişletildi.

**Ölçülmüş tasarım kararları** (tekrar tartışılmasın diye):

| Karar | Ölçüm |
|---|---|
| `halk_dili` kart seçiminde KULLANILMAZ | açıkken her belge `keyfiyet`/`tediye` çekiyor |
| `halk_dili` kapsam kapısında da KULLANILMAZ | yanlış pozitif 3/18 → 11/18 |
| üslup terimleri elenir | filtresiz koşuda en sık çekilen terim `isbu` çıktı |
| eş anlamlı çift katlanır | `sukuk`+`kira-sertifikasi` iki kart harcıyordu |
| jargon lint kapsamı dar | kör tarama 494 bulgu, `web/`de yalnız 1 gerçek ihlal |
| §5.5'in yalnız 2 kavramı eşlenir | diğer 3'ü fıkhî terim değil, sözlükte karşılığı yok |

### Faz B — orkestrasyon

`T0 yönlendirici → A1 sayısal ‖ A2 bağlamsal → K1 kanıt kapısı →
K2 kalem kapısı → J hakem`

Değişmez: **ajanlar önerir, hakem yalnız reddeder, reddedilen alan kural
değerine düşer.** En kötü hâl = kural-only. `test_EN_KOTU_HAL_kural_only`
bunu sabitliyor.

Hakem lastik damga değil — 5 kontrol vakasında 4/5. Kaçırdığı vaka
("Taşıt Rehin Tesis Ücreti" → tahsis ücreti) `_kalem_kapisi` ile mekanik
olarak kapatıldı.

### Faz C — kısmen

- **C1 bitti:** hata sınıfları adlandırıldı (kaçırma / yanlış çıkarım /
  halüsinasyon), üçü ayrı paydayla raporlanıyor.
  Kural kolunda ölçüldü: çıkarım hatası 0,369 [24/65] — **13 kaçırma,
  11 yanlış çıkarım**. Yani hataların neredeyse yarısı grounding.
- **C4 ölçüldü, UYGULANMADI:** yarışma korpusunun **%42,6'sı çerçeve**
  (8,3M → 4,7M karakter). Ama körlemesine uygulanamaz — 143 belge sinyal
  taşıdığı hâlde içeriğinin %75'inden fazlasını kaybediyor.

  Sebebi teşhis edildi: **sözleşme şablonlarında tekrar, gürültü değil
  içeriğin kendisi.** Albaraka'nın 110 bin karakterlik sözleşmeleri çekirdek
  metin olarak sayfa numarası döküntüsü bırakıyor. Varsayım `live/products`
  için doğru, `docs/` için ters dönüyor.

  Kayıpların 77'si tek bankada (Dünya Katılım) toplanmış — orayı ayrıca
  incelemeden genel uygulama yapılmamalı.

  **Doğru API uyarısı:** `boilerplate_shingles()` koruma kümesini atar;
  `boilerplate_sets()` kullanılıp `protected` `core_text`'e verilmeli.
  Bu fark tek başına içerik yiyen belgeyi 278'den 143'e indiriyor.

---

## Rakip analizi — `docs/rapor/rakip-analizi.md`

**gitignore'a alındı, ASLA push edilmez** (yayın kademesi 3).

En kritik üç bulgu:

1. **`YURDAKULOGLU/TEKNOFEST-2026-Katilim-Analiz`** bizim "kural birincil,
   LLM tamamlayıcı" tezimizin aynısını savunuyor. O argüman artık ayırt
   edici değil — farkımız argümanda değil, **onu ölçmüş olmamızda**.
   Ablasyon tablosu sunumun merkezine geçmeli.
2. **En büyük açığımız: prompt-injection güvenlik değerlendirmesi.**
   Rakipte 20/20 geçmiş, bizde sıfır. Finansal ajanda birinci sınıf jüri
   kriteri ve en ucuz kapatılabilir olanı.
3. **Config-driven scraping ayırt edici DEĞİL** — 4 rakipte var. On-prem,
   açık kaynak, Ollama, dashboard+chatbot da öyle. Sunumda bunlara ağırlık
   vermek zayıflık olur.

Rapor teslim öncesi tekrar koşturulmalı: görülen depolar takımların çalışma
depoları, nihai teslim sürümleri değil.

---

## Sıradaki işler (plan sırasıyla)

1. **Orkestrasyon ölçümünü tamamla** (yukarıdaki komut, `-u` ile).
2. **Ö1 üç kollu deney** — temel / sadeleştirme / sözlük kartı.
   `LLMOrchestrator(terim_karti=False)` ablasyon kolunu zaten açıyor.
3. **Prompt-injection değerlendirme seti** — rakip analizindeki en kritik açık.
4. **C4 boilerplate** — `live/products` için uygula, `docs/` hariç tut,
   Dünya Katılım'ı ayrıca incele.
5. **Faz D** — kampanya süresi aralığı, tahsis ücreti yüzde hesabı, dipnot
   çıkarımı.
6. **Faz F/G/H** — sunum belgeleri, dashboard, mentör mailleri.

## Tuzaklar

1. **`python -u`** — yönlendirilmiş çıktı tamponlanır; bu oturumda 40 dakika
   bu yüzden kayboldu.
2. `git add -A` ve düz `git commit` yasak — `git commit --only <yol>`,
   yeni dosya için önce `git add -N`.
3. Testin `OK` satırı ANSI renkli, grep'e takılmaz — **çıkış koduna bak**.
4. Ollama `num_ctx` varsayılanı 2048 ve taşmayı BAŞTAN kırpar; terim
   kartlarıyla birlikte bu sistem prompt'unu yok eder. Açıkça ver.
5. Daima `.venv/bin/python`; sistem `python3`'te `bs4` yok.
