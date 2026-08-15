# IAA raporu — YÖNLENDİRME (bu dosya artık ölçüm taşımaz)

> Elle yazıldı, `report_iaa.py` üretmez. Bu ad iki ayrı turun raporunu üst
> üste bindirdiği için emekliye ayrıldı; ölçümler aşağıdaki tur adlı
> dosyalarda. **Silinmedi** (HARD RULE: silme yok), çünkü ona işaret eden
> belgeler var; buraya gelen okuyucu doğru dosyaya yönlendirilir.

## Ne olmuştu — kök neden

`scripts/report_iaa.py` çıktıyı **hep aynı ada** yazıyordu. Round0'ın **v1**
turundan üretilen Fleiss κ = **0,302**'lik rapor, sonradan **v2** turundan
(260 satır paylaşıldı, **0 dolu karar**) üretilen raporla sessizce **EZİLDİ**.

Sonuç: dosya "ölçülemedi" diyordu; kök `README.md` dâhil altı belge ise
κ = 0,302 ilan edip kanıt diye tam da bu dosyayı gösteriyordu. İki sayı da
doğruydu — kaybolan şey **hangisinin hangi tura ait olduğuydu**, yani raporun
kanıt olma niteliğiydi.

Betik düzeltildi: çıktı adı artık turu içerir (`--tur` ya da CSV adlarından
türetme) ve var olan bir raporu FARKLI içerikle ezmek `--uzerine-yaz`
olmadan **hata** verir.

## Hangi κ hangi turdan

| Tur | Rapor | Anotatör | Ortak satır | Karar bulunmayan hücre | Metrik | κ |
|---|---|---|---:|---:|---|---:|
| round0 kalibrasyon **v1** | [`iaa-raporu-round0-kalibrasyon-v1.md`](iaa-raporu-round0-kalibrasyon-v1.md) | A, B, C, D | 260 | 0 | Fleiss | **0,302** |
| round0 kalibrasyon **v2** | [`iaa-raporu-round0-kalibrasyon-v2.md`](iaa-raporu-round0-kalibrasyon-v2.md) | v2_A…v2_D | 260 | 1040 | Fleiss | **ölçülemedi** |
| round1 (manşet) | [`iaa_report_round1.md`](iaa_report_round1.md) | A, B | 650 | 1004 | Cohen | **0,274** |
| round1 hakemlik SONRASI | [`iaa_report_round1_hakemlik_sonrasi.md`](iaa_report_round1_hakemlik_sonrasi.md) | A, B | 650 | 1004 | Cohen | 0,844 |

**Bu dosyanın eski içeriği** (round0 v2 turunun ölçümü) birebir
`iaa-raporu-round0-kalibrasyon-v2.md`'dedir ve o dosya CSV'lerden yeniden
üretilmiştir.

## Üç okuma kuralı

1. **Manşet κ'lar: round0 v1 = 0,302 · round1 = 0,274.** Bunlar bağımsız iki
   (ya da dört) yargının uyumudur ve yayımlanan değerlerdir.
2. **0,844 manşet değildir.** Kör hakemlik uyuşmazlıkları uzlaştırdıktan
   SONRA ölçülen gold tutarlılığıdır; bağımsız uyum değildir ve manşetin
   yerine konamaz (`scripts/hakemlik_uygula.py` modül başlığı; round0 emsali
   [`review/_kalibrasyon-sonucu.md`](review/_kalibrasyon-sonucu.md) §8, orada
   0,051 ve 0,268 yan yana yayımlandı).
3. **round0 v2 turu ölçüm vermez.** 260 satır paylaşıldı, tek hücre
   doldurulmadı. "Uyum yok" değil, "ölçüm yok" — o raporun söyleyebileceği
   tek şey budur.

## Yeniden üretim

```bash
.venv/bin/python -m scripts.report_iaa \
    data/gold/review/round0_kalibrasyon_{A,B,C,D}.csv \
    --tur round0-kalibrasyon-v1

.venv/bin/python -m scripts.report_iaa \
    data/gold/review/round0_kalibrasyon_v2_{A,B,C,D}.csv \
    --tur round0-kalibrasyon-v2
```
