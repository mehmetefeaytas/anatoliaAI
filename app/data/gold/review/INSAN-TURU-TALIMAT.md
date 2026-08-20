# İnsan Turu Talimatı — 1 sayfa, başlamadan önce okuyun

## Neden bu tur var

Jüri κ=0,700 ölçümünü doğruladı ama **kısmi kredi** verdi: gerekçe n=16 ve
ikinci etiketleyicinin bir **insan değil, bir LLM** olmasıydı (bkz.
`_kappa-ikinci-tur.md`). Model-model uyumu, gold'un insan yargısıyla
tutarlılığını kanıtlamaz. Bu turda **siz** ikinci etiketleyicisiniz — aynı 16
kaydı, LLM'in gördüğü şeyin AYNISINI görerek (yalnız belge metni, kılavuz)
bağımsız olarak etiketleyeceksiniz.

**Körleme zorunludur ve araç bunu garanti eder:** ekranda gold'un mevcut
değerini de, LLM'in ne karar verdiğini de GÖRMEYECEKSİNİZ — yalnız kampanya
metnini ve alan adını. Bu olmadan κ anlamsızdır; jüri bunu ilk sorar.

## Nasıl başlanır

Proje kökünden (`app/`):

```bash
.venv/bin/python -m scripts.ikinci_etiketleyici insan
```

Araç size sırayla 16 kaydı, her kayıtta 12 alanı tek tek soracak. Her alan
için:
- Kısa bir hatırlatma metni gösterilir (tam kural için parantez içindeki
  bölüme bakın: `data/gold/ANNOTATION_GUIDE.md`, özellikle **§4** — 12 alanın
  ne saydığı/saymadığı — ve **§4.13** — sekiz sık karışan sınır vaka).
- Değeri kılavuzdaki biçimde yazın (`%1,89`, `500 TL`, `31.12.2026`, `12 ay`
  gibi serbest Türkçe girişler de kabul edilir, araç kanonik biçime çevirir).
- Alan belgede yoksa **`yok`** yazın.
- `kampanya_kosullari` ve `hedef_kitle` **birden çok girişe** izin verir: her
  koşulu/etiketi ayrı satıra yazın, bitirince **boş satır** bırakın. Alan hiç
  yoksa tek satıra `yok` yazmanız yeterli.
- Yanlış biçimde bir şey yazarsanız araç NEDEN geçersiz olduğunu söyler ve
  aynı alanı tekrar sorar — ilerlemeniz kaybolmaz.

**Bu turda `unclear` seçeneği yoktur** — yalnız değer/`yok` ikilisi
sorulur, çünkü κ hesabı (`kappa` alt komutu) yalnız bu iki durumu
karşılaştırabiliyor. Gerçekten kararsızsanız kılavuzun (§3.4 mantığı)
işaret ettiği en olası kararı verin; bu, ölçümün bir sınırıdır, gizlenmiyor.

## Ne kadar sürer

**Tahmini ~60–90 dakika** (araç başlarken de bunu yazdırır). Dayanak:
`ANNOTATION_GUIDE.md` §1 — ön-anotasyon YOKKEN elle etiketleme belge başına
~5 dakika sürüyor; bu turda ön-anotasyon YOK (körleme gereği), 16 belge ×
~5 dk ≈ 80 dk. Ölçüm değil, kılavuzun kendi rakamından türetme.

## Yarıda kalırsa ne olur

**Hiçbir şey kaybolmaz.** Her alanı cevapladığınızda araç diske yazar. İster
bir kayıt ortasında, ister kayıtlar arasında durun — terminali kapatabilir,
bilgisayarı kapatabilirsiniz. Devam etmek için **aynı komutu tekrar
çalıştırın**:

```bash
.venv/bin/python -m scripts.ikinci_etiketleyici insan
```

Araç zaten tamamlanmış kayıtları atlar, yarım kalan kaydın kaldığınız
alandan devam eder. Baştan başlamak isterseniz (önerilmez — yaptığınız işi
siler):

```bash
.venv/bin/python -m scripts.ikinci_etiketleyici insan --bastan
```

## Bitirince

Çıktı `data/gold/review/ikinci-tur-insan.jsonl` dosyasına yazılmıştır. κ'yı
hesaplamak için (yalnız 16 kaydın **hepsi** tamamlandıktan sonra çalıştırın —
eksik kayıtla κ yanıltıcı olur):

```bash
.venv/bin/python -m scripts.ikinci_etiketleyici kappa \
    --girdi data/gold/review/ikinci-tur-insan.jsonl
```

Bu, `data/gold/review/_kappa-ikinci-tur-insan.md` raporunu üretir — LLM
turunun raporuna (`_kappa-ikinci-tur.md`) dokunmaz, ikisi yan yana durur.

## Bir şey karışırsa

Kararsız kaldığınız alanlar için `ANNOTATION_GUIDE.md`:
- **§3** — `ok`/`fix`/`absent`/`unclear` ayrımının mantığı (bu turda yalnız
  değer/`yok` sorulsa da, kararı VERİRKEN aynı mantığı kullanın).
- **§4** — alan alan ne sayılır/sayılmaz, sınır vakalar.
- **§4.13** — sekiz kapatılmış kural (ör. "bireysel müşteriler" segment
  değildir, ürün kısıtı segment değildir, tek özne yoksa `absent`).
- **§5** — kanonik değer biçimleri.
