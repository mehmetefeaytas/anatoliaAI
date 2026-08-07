# Ölçüm setini genişletme — n=20'den n=68'e

**Durum:** aday havuzu üretildi ve anotasyon koştu. Sonuç bölümü ölçüm
bittikçe doldurulur.

İlgili: `scripts/sample_gold_v2.py`, `data/gold/ANNOTATION_GUIDE.md`,
`docs/rapor/karar-bekleyenler.md` (K-1)

---

## Neden gerekliydi — üç somut kanıt

**1. Kararlar tek haneli sayılara dayanıyor.** K-1'de (çerçeve ayıklaması)
n-gram ile blok yaklaşımı arasındaki fark halüsinasyonda **5 kayıt**,
kaçırmada **2 alan**. F1 farkı 0,688 vs 0,687 — istatistiksel olarak yok.
Bu büyüklükte "kazanan" ilan etmek ölçüm değil, gürültü okumaktır.

**2. Gerçek bir hata sınıfı sette hiç iz bırakmadı.** Gecikme cezası
maddesinden kâr payı oranı çıkarma hatası, korpusta üretilen
`kar_payi_orani` kayıtlarının **%17,9'unu** etkiliyordu. Düzeltildikten
sonra gold mikro-F1'i **0,677'de sabit kaldı** — çünkü o 20 belgede tek bir
ceza maddesi yok. Ölçüm seti, sistemin en yaygın hatalarından birini
göremiyordu.

**3. Kapsama dar.** gold.v1: 7 banka, hepsi web sayfası, hiç PDF yok.
Korpusta 10 banka var; Ziraat Katılım (291 belge), Hayat Finans (48) ve
Adil Katılım (6) ölçümde **hiç temsil edilmiyordu**.

---

## Tasarım

### Örnekleme (`scripts/sample_gold_v2.py`)

- **48 yeni belge**, gold.v1'in 20'sine EK. Toplam **n=68** (3,4×).
- Tabakalı: 8 kampanya türü + sınıflandırılmamışlar; tür başına ~5 belge.
- Banka çeşitliliği gözetilir — **10 bankanın hepsi** temsil ediliyor.
- `content_hash` ile gold.v1'den ayrık: aynı belge iki kez ölçülmez.
- Kabuk belgeler elenir (uzunluk + sözcük çeşitliliği eşiği).
- **PDF yok.** Sözleşme PDF'leri farklı bir tür (akit, kampanya değil) ve
  alanların çoğu orada yapısal olarak yoktur. Karıştırmak iki seti
  kıyaslanamaz kılardı. Bu bir KAPSAM kararıdır; PDF'ler ayrı bir set
  olarak ele alınmalı (açık iş).
- Deterministik: sabit tohum (20260807) + kararlı sıralama.

### Anotasyon — dairesellik karşıtı protokol

Ölçüm setini sistemin çıktısına bakarak üretmek F1'i şişirir ve ölçümü
değersiz kılar. Bu yüzden anotasyon **kör** koştu:

| kural | gerekçe |
|---|---|
| `src/extraction/` okunmaz, koşulmaz | etiket sistemin kopyası olmasın |
| `preannotations*.json` değerlerine bakılmaz | aynı |
| her değer için **birebir alıntı** zorunlu (`field_spans`) | uydurmaya karşı mekanik koruma |
| alıntının metinde geçtiği programatik doğrulanır | iddia değil, kanıt |
| emin olunmayan alan hiçbir listeye girmez | tahmin metrik dışı |
| "yok" da bir karardır → `absent_fields` | halüsinasyon paydası |

Dört anotatör (M1–M4) ayrık 12'şer belge üzerinde bağımsız çalıştı.

### Statü — dürüstlük şartı

gold.v2 kayıtları `annotators: ["M1".."M4"]`, `adjudicated: false` taşır.
**gold.v1 ile aynı sayılmaz ve raporda birleştirilerek sunulmaz:**

- **gold.v1 (n=20)** — insan anotasyonlu, hakemlikten geçmiş. Birincil ölçüm.
- **gold.v2 (n=48)** — makine anotasyonlu, kanıt doğrulamalı, **insan
  hakemliği bekliyor**. İkincil / doğrulayıcı ölçüm.

Jüriye sunumda bu ayrım açıkça yazılır. İkisinin sonucu **aynı yönü**
gösteriyorsa bulgu güçlenir; **ayrışıyorsa** bu bir bulgudur ve saklanmaz.

κ (anotatörler arası uyum) için ikinci insan anotatör hâlâ gereklidir —
gold.v2 onun yerine geçmez, önceliğini artırır.

---

## Sonuçlar

_(anotasyon tamamlandıkça doldurulur)_

| ölçüm | gold.v1 (n=20) | gold.v2 (n=48) | birleşik (n=68) |
|---|---|---|---|
| kural / strict mikro-F1 | 0,677 | — | — |
| halüsinasyon | 0,096 | — | — |

### K-1 yeniden ölçümü

_(temel / n-gram / blok üç kolu geniş sette tekrarlanacak)_

---

## Tekrar üretim

```bash
.venv/bin/python -m scripts.build_demo_db --out data/demo.db --force
.venv/bin/python -m scripts.sample_gold_v2 --n 48 --parcala 4
# anotasyon -> data/gold/parca/etiket-*.json
.venv/bin/python -m eval.run_eval --gold data/gold/gold.v2.json --config kural
```
