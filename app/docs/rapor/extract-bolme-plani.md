# Kural katmanının kademeli bölünmesi — sorumluluk haritası ve plan

**Tarih:** 2026-08-20
**Tetikleyen:** değerlendirmede `src/extraction/rules/extract.py`nin depodaki
**en büyük tekil dosya** (~3.700 satır) olduğu, "alan-bazlı modüllere
bölünmeli" diye isim isim işaretlendi (Teknik İmplementasyon %20, eylem
maddesi #1).
**Emsal:** `docs/rapor/api-bolme-plani.md` — `src/api/main.py` 2.505 → 887
satıra bölündü ve o turda Teknik Mimari puanı 77 → 86 çıktı. Aynı kalıp
(gerekçeli sorumluluk bölüşümü, kademeli adım, her adımda tam test) burada
da uygulandı.
**Durum:** **TAMAMLANDI.**
**Ölçülen sonuç:** `extract.py` (cephe) 3.707 → **200 satır**; kural
katmanı 12 yeni modüle dağıtıldı, en büyüğü (`kosullar.py`) 648 satır —
1.200 satır tavanının belirgin altında. 3.278 test yeşil (değişmedi),
eval kapıları AÇIK ve dört ölçüt (ikili/kalem/yapısal/makro mikro-F1)
**birebir aynı**.

## Neden bu bölme GÜVENLİYDİ — aynı turda büyük bir F1 kazancı vardı

Bölmeden hemen önce bu dosyada yapısal mikro-F1 0,698 → 0,823'e çıkarılmıştı.
Bu, bölmeyi riskli değil TERSİNE ÖLÇÜLEBİLİR kıldı: iki regresyon kapısı
(`eval/esikler.json`, `eval/esikler-round1.json`) bugün ölçülenin hemen
altına çekilmiş durumdaydı, 3.278 testlik paket ve 1.782 belgelik
değişmez denetimi (`eval.properties`) her adımı anında doğrulayabiliyordu.
Sonuç: bölme bitene kadar **tek bir metrik bile kımıldamadı** (aşağıya
bakın) — beklenen tam da buydu, çünkü bu saf bir refaktördü.

## Sorun — ölçülmüş hâli

```
src/extraction/rules/extract.py   3.707 satır
  └── 12 alan çıkarıcısı           extract_kar_payi, extract_vade,
                                    extract_tutar, extract_taksit,
                                    extract_masraf, extract_tahsis_ucreti,
                                    extract_kampanya_suresi,
                                    extract_odul_miktari,
                                    extract_indirim_orani,
                                    extract_alisveris_puani,
                                    extract_hedef_kitle,
                                    extract_kampanya_kosullari
  └── 1 çapraz-alan yöntemi        oran tablosu ayrıştırma
                                    (parse_rate_table / extract_from_rate_table)
  └── paylaşılan yardımcılar       _field, _window, _cumle_kapsami,
                                    _kanit_araligi, _truncate_at_next_column,
                                    _SAYI_BASI, _PARA_IFADESI
```

`entities/`, `normalization/`, `comparison/` gibi katmanlar zaten ayrı ayrı
test edilebilir modüllerdi; kural katmanı tek dosyada kalmıştı — API
bölmesinden önceki `main.py` durumunun aynısı.

## Sorumluluk haritası — hangi alan hangi yardımcıyı kullanıyor

Haritanın kendisi **tahminle değil `grep -n` ile her yardımcının çağrı
noktaları taranarak** çıkarıldı (bkz. aşağıdaki "Yöntem" bölümü). Sonuç:

| Alan / modül | Satır (yeni) | Kullandığı paylaşılan yardımcı | Kimseyle paylaşmadığı kendine özgü mantık |
|---|---:|---|---|
| `kar_payi.py` | 567 | `_field`, `_window`, `logger` | paylaşım oranı ayrımı, yabancı kavram, ceza bağlamı, türev oran, bozuk hesaplama aracı (5 süzgeç, hiçbiri paylaşılmıyor) |
| `vade.py` | 388 | `_field`, `_window`, `_cumle_kapsami`, `logger` | takvim-yılı reddi, "X aya kadar + finansman ürünü" yapı tetikleyicisi, işlenmiş-örnek süzgeci |
| `tutar.py` | 348 | `_field`, `_window`, `_CUMLE_SINIRI_RE` | finansman tutarı aralık/toplam-azami/ters-sıra kalıpları + taksit sayısı (ikincisi hiçbir şey paylaşmıyor, ölçek gerekçesiyle burada) |
| `masraf.py` | 322 | `_field`, `_window`, `_cumle_kapsami`, `_kanit_araligi`, `_truncate_at_next_column`, `logger` | alan-dışı özne süzgeci, muafiyet kalıbı |
| `tahsis_ucreti.py` | 258 | `_field`, `_window`, `_truncate_at_next_column`, `_SAYI_BASI`, `_PARA_IFADESI` | oransal ücret hesap katmanı (`_ucret_degeri`), tek modülde |
| `tarih.py` | 171 | `_field`, `_window` | kanun atfı reddi, gün-gün aralığı, başlangıç/bitiş rolü |
| `tablo.py` | 403 | `_field`, `_window` | ÇAPRAZ ALAN — dört alana (`kar_payi_orani`, `vade_ay`, `finansman_tutari`, `masraf_durumu`) birden üretim yapar |
| `odul_indirim.py` | 160 | `_field`, `_window`, `_PARA_IFADESI` | ödül retoriği süzgeci, indirim aralığı |
| `alisveris_puani.py` | 157 | `_field`, `_window`, `_SAYI_BASI` | puan/oran ikili şeması, gezinme-şeridi/SSS süzgeci |
| `hedef_kitle.py` | 162 | `_field`, `_window` | 4-segment çok-etiketli sınıflandırma, gezinme şeridi |
| `kosullar.py` | 648 | `_field`, `_window`, `ihtar_mi` (mevcut `ihtar.py`) | 11 "koşul DEĞİL" süzgeci + dipnot çıkarımı (tek tüketicisi olduğu için BİRLİKTE) |
| `_ortak.py` (yeni) | 318 | — | `_field`/`_window`/`logger` + kanıt-aralığı ailesi + `_SAYI_BASI`/`_PARA_IFADESI` |
| `extract.py` (cephe) | 200 | tümü | `extract_all` uzlaştırması: tablo önceliği, tahsis tabanı bağı, kabuk süzgeci |

`kabuk.py` ve `ihtar.py` zaten ayrı modüldü (önceki turda çıkarılmıştı);
bu bölme onlara dokunmadı, yalnızca `extract.py`nin geri kalanını böldü.

## Paylaşım YARDIMCI düzeyinde, ALAN MANTIĞI düzeyinde değil

`_ortak.py`ye giden her ad **≥2 alan modülü tarafından fiilen çağrıldığı
ölçülerek** seçildi — hiçbiri "belki paylaşılır" tahminiyle taşınmadı:

- `_field`/`_window`: 12/12 alan.
- `_cumle_kapsami`/`_cumle_araligi`: `vade`, `masraf`, `tahsis_ucreti`.
- `_kanit_araligi`: yalnız `masraf` ve `tahsis_ucreti` (ikisi de "kanıt
  tetikleyici sözcük değil onu taşıyan tümceciktir" disiplinini paylaşıyor).
- `_truncate_at_next_column`/`_COLUMN_HEADERS_RE`: `masraf` ve
  `tahsis_ucreti` (komşu tablo sütununu kesme koruması).
- `_SAYI_BASI`/`_PARA_IFADESI`: `tahsis_ucreti`, `odul_indirim`,
  `alisveris_puani` — üçü de "dilim alma, `search(text, pos, endpos)`
  kullan" kusurunu (bkz. `_ortak.py` başlığı) aynı iki sabitle önlüyor.

`tablo.py` hiçbir alan modülüne YERLEŞTİRİLMEDİ çünkü tek bir alana değil
bir ÇIKARIM YÖNTEMİNE karşılık geliyor ve dört alana birden üretim
yapıyor; herhangi birine konması diğer üçünü ondan import etmeye
zorlardı. Aynı gerekçe API bölmesinde `kiyas.py`nin `/scoring`'i
bölünmemiş bırakmasıyla aynı sınıftan: ortak bir çağrıyı iki modüle
bölmek aynı kararı iki yerde yaşatır.

## Yöntem — sıra ve doğrulama

1. **Taban ölçüldü ve yazıldı** (bölmeden önce): `pytest tests -q` →
   3.278 geçti / 53 atlandı; `eval.run_eval --config kural --esikler
   eval/esikler.json` → ikili mikro-F1 **0,5702**, kalem mikro-F1
   **0,6291**, yapısal mikro-F1 **0,8228**, makro-F1 **0,7646**; round1
   kapısı AÇIK; `ruff check .` temiz; `eval.properties` 0 ihlal.
2. **Sorumluluk haritası** her fonksiyon/sabit için `grep -n` ile çağrı
   noktası taranarak çıkarıldı (yukarıdaki tablo) — tahminle değil.
3. **Mekanik kesim.** Regex-ağır, Türkçe aksanlı içerik elle yeniden
   YAZILMADI: bir Python betiği (`split_extract.py` + `gen_modules.py`,
   geçici) kaynak dosyayı SATIR ARALIĞIYLA kesip yeni dosyalara yapıştırdı.
   Elle yazılan tek şey import blokları ve modül-başı gerekçe
   docstring'leriydi — transkripsiyon riski bu satırların dışına hiç
   taşmadı.
4. **Her adımdan sonra tam doğrulama**: `pytest tests -q`, iki eval
   kapısı, `ruff check .`, `eval.properties`. Hiçbiri geri alınmadı çünkü
   hiçbiri kırılmadı.

## İKİ ÖLÇÜLMÜŞ TUZAK — bölme başlamadan bulundu, aksi halde sessizce davranış değiştirirdi

### Tuzak #1 — aynı ad, iki tanım, yalnızca biri hiç canlı olmadı

`_CUMLE_SINIRI_RE` orijinal dosyada İKİ KEZ tanımlıydı: eski satır 987
(`r"[.!?;]\s+[A-ZÇĞİÖŞÜ]|\n"`) ve eski satır 1342
(`r"(?<!\d)[.;!?](?!\d)|\n"`, ondalık/binlik noktayı cümle sonu SAYMAYAN
sürüm). Python'da modül-düzeyi bir ad yeniden atandığında öncekini
tamamen ezer; fonksiyon gövdeleri adı ÇAĞRI ANINDA modül global'inden
okur, tanım sırasından değil. `extract_tutar` (kod sırasına göre İLK
tanımın hemen altında duruyordu) `_CUMLE_SINIRI_RE.search(gap)` çağırdığında
modül zaten TAM YÜKLENMİŞ oluyordu — yani her zaman İKİNCİ tanımı görüyordu.
Birinci tanım hiçbir çağrı yolunda asla gözlenmedi.

Bu, API bölmesindeki "`Response` fonksiyon içine import edilince 422
döndü" dersiyle AYNI SINIFTAN bir tuzak: tek dosyada gizli kalan bir isim
gölgelemesi, dosya bölününce ya YANLIŞ tarafa kopyalanıp davranışı
DEĞİŞTİRİRDİ (eğer `tutar.py` "kendi yakınındaki" ölü birinci tanımı
alsaydı) ya da fark edilmeden iki kez yaşardı. `grep -n _CUMLE_SINIRI_RE`
ile ikisinin de tüm okuma noktaları taranarak doğrulandı ve yalnız İKİNCİ
tanım `_ortak.py`ye taşındı; birinci sessizce düşürüldü — davranış
DEĞİŞMEDİ, çünkü zaten hiç yürütülmüyordu.

**Ders (kalan turlar için):** bir dosya bölünmeden önce
`grep -noE '^_[A-Za-z_0-9]+ = ' dosya | sort | uniq -c | awk '$1>1'` ile
tekrarlanan modül-düzeyi ad ataması taranmalı. Bu depoda yalnız BU isim
tekrarlıydı (doğrulandı); başka aday çıkmadı.

### Tuzak #2 — bir test logger ADINI tam dize olarak sabitliyor

`tests/test_kar_payi_bozuk_hesaplama_araci.py::test_ret_gerekcesi_loglanir`
`self.assertLogs("src.extraction.rules.extract", level=logging.DEBUG)`
çağırıyor. `assertLogs` verilen adın kendisinden ya da ondan TÜREYEN
(nokta ile ayrılmış alt) bir logger'dan gelen kaydı yakalar. Her yeni
modülde alışılmış `logging.getLogger(__name__)` kullanılsaydı,
`kar_payi.py`nin logger'ı `"src.extraction.rules.kar_payi"` olurdu —
bu, `"src.extraction.rules.extract"`in ne kendisi ne alt logger'ıdır
(KARDEŞ düğüm, ATA değil), dolayısıyla kayıt hiç yakalanmaz ve test
SESSİZCE değil AÇIKÇA kırılırdı (`assertLogs` eşleşme yoksa
`AssertionError` fırlatır).

Çözüm: `_ortak.py` logger'ı `__name__`e değil BİLE İSİM SABİT DİZEYE
bağladı (`logging.getLogger("src.extraction.rules.extract")`) ve her alan
modülü kendi logger'ını tanımlamak yerine bunu `_ortak`tan içe aktarıyor.
Böylece hangi modülde üretildiğinden bağımsız olarak TÜM `logger.debug(...)`
çağrıları aynı logger kimliğini taşıyor — bölmeden önceki tekil-dosya
davranışıyla birebir aynı.

**Ders:** bir dosya bölünürken `__name__` tabanlı logger'lar sessiz bir
kimlik değişikliğine yol açabilir; `assertLogs`/`caplog.at_level` ile
adı sabitlenmiş bir test varsa (kontrol: `grep -rn "assertLogs\|caplog"
tests/ | grep <eski-modül-yolu>`) logger kimliği bilerek sabitlenmeli.

## Geriye dönük uyum — cephe deseni

`extract.py` artık yalnız iki şeyden sorumlu: (1) geriye dönük uyum
cephesi, (2) `extract_all` uzlaştırma mantığı (tablo önceliği/yedeği,
tahsis tabanı bağı, kabuk süzgeci — bunlar birden çok alanı AYNI ANDA
görmesi gerektiği için hiçbir alan modülüne ait olamaz).

Geriye dönük uyum için tüm re-export'lar `from .modül import ad as ad`
biçiminde yazıldı (redundant alias). Bu, hem `ruff`a (F401: "kullanılmayan
import") hem okuyucuya "bu bilerek yeniden ihraç ediliyor" sinyali verir —
API bölmesinde `main.span_info` gibi adların neden `yardımcılar.py`den
yeniden ihraç edildiği notuyla aynı disiplin. 30+ çağrı yeri (test
dosyaları + `scripts/`, `eval/`, `src/comparison/scan.py`,
`src/extraction/reconcile.py`) `grep -rn "from.*rules\.extract import"`
ile taranıp her içe aktarılan ad tek tek doğrulandı;
`_gezinme_seridi`, `_kosul_degil`, `_yalnizca_tarih_gecerliligi`,
`_truncate_at_next_column`, `_PARA_IFADESI`, `_PUAN_SAYI_RE`,
`paylasim_cifti_araliklari`, `MAKS_VADE_AY`, `_ORAN_TABLOSU_BASLIK_RE`
gibi alt-çizgili "yarı-özel" adlar da dahil, hepsi cephede yeniden
ihraç ediliyor.

## Ölçülen sonuç — önce/sonra

| Ölçüt | Önce (taban) | Sonra (bölme bitti) |
|---|---:|---:|
| `pytest tests -q` | 3.278 geçti, 53 atlandı | 3.278 geçti, 53 atlandı (değişmedi) |
| ikili mikro-F1 (strict, tüm vakalar) | 0,5702 | 0,5702 |
| kalem mikro-F1 | 0,6291 | 0,6291 |
| yapısal mikro-F1 | 0,8228 | 0,8228 |
| makro-F1 | 0,7646 | 0,7646 |
| Regresyon kapısı (`esikler.json`) | AÇIK | AÇIK |
| Regresyon kapısı (`esikler-round1.json`) | AÇIK | AÇIK |
| `eval.properties --raw-dir data/raw` | 0 ihlal (1.782 belge) | 0 ihlal (1.782 belge) |
| `ruff check .` | temiz | temiz |
| `extract.py` (ve tüm alt modüller) en büyük dosya | 3.707 satır | 648 satır (`kosullar.py`), cephe 200 satır |

Dört F1 rakamı ve testler **birebir aynı** — beklenen sonuç, çünkü bu
saf bir kod-taşıma turuydu; hiçbir çıkarım kararı, eşik ya da regex
davranışı değiştirilmedi (yukarıdaki iki tuzağın ikisi de davranışı
KORUMAK için çözüldü, değiştirmek için değil).

## Neden `kosullar.py` (648 satır) daha fazla bölünmedi

`kampanya_kosullari` gold.v2'de en zayıf alandı (F1 0,204) ve bu yüzden
en çok "koşul DEĞİL" süzgecini taşıyor (11 sınıf: soru cümlesi, SSS
cevabı, yönlendirme, ürün tanımı, fıkıh/mevzuat, sorumluluk reddi, ödül
bildirimi, ürün özelliği, blok başlığı, site kromu, tarih-iskeleti).
Bu 11 süzgecin hepsi TEK bir karar fonksiyonunda (`_kosul_degil`)
birleşiyor ve TEK bir tüketicisi var (`extract_kampanya_kosullari`) —
aralarında ikinci bir çağrı grafiği kesişimi yok, dolayısıyla bölmek için
gerçek bir sınır yok. `extract_dipnotlar` de aynı gerekçeyle burada
kaldı: tek tüketicisi bu fonksiyon. 648 satır 1.200 tavanının belirgin
altında; "sınırı yapay olarak taşımak mimari değildir" ilkesi burada
zorla bölmemenin de gerekçesi.

## Sonraki tur için — bu belgenin kapsamı DIŞINDA

`_ortak.py`deki kanıt-aralığı ailesi (`_cumle_araligi`, `_cumle_kapsami`,
`_kanit_araligi`) yalnız 3 modül tarafından kullanılıyor; ileride yeni bir
alan aynı disiplini paylaşırsa (örn. yeni bir "kanal kısıtı" alanı)
`_ortak.py`ye eklenecek dördüncü tüketici olur. Bunun dışında bölme
kapsamı tamamlandı; yeni bir ölçülmüş sorun çıkmadan daha ince taneli bir
bölme (örn. `tutar.py`nin `extract_taksit`'i ayrı dosyaya çıkarmak)
önerilmiyor — aynı "ölçülmüş sorun çıkmadan yapılmaması daha iyi" ilkesi
API planının kapanışında da yazılı.
