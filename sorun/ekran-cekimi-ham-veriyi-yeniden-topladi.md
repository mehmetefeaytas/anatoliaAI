---
title: "Ekran görüntüsü almak ham arşivi yeniden topladı ve provenance damgalarını sildi"
tags: [sorun, ekran-goruntusu, ham-veri, provenance, celiski, otomasyon]
source: "ölçüm — app/data/gunluk/islem-gunlugu.jsonl (2026-08-24), git diff"
date: 2026-08-24
status: stable
---

# Ekran görüntüsü almak ham arşivi yeniden topladı

## Belirti

45 sayfalık panel PDF'i için kareler yeniden çekildikten sonra `git status`
**72 ham veri dosyasını değişmiş** gösterdi:

```
 M app/data/raw/vakif-katilim/live/detay-bu-yol-indirime-gider.txt.meta.json
 M app/data/raw/adil-katilim/live/katilim-bankaciligi.txt.meta.json
 … (72 dosya, 433 ekleme, 624 silme)
```

## Kök neden — ölçüldü, tahmin edilmedi

`app/data/gunluk/islem-gunlugu.jsonl` iki gerçek tazeleme çağrısı kaydetmiş ve
ikisi de tarayıcıdan (`127.0.0.1`) geliyor, testten değil:

```
19:39:07  POST /refresh  202  banka=adil-katilim   hedef=data/raw/adil-katilim/live
19:39:45  POST /refresh  202  banka=vakif-katilim  hedef=data/raw/vakif-katilim/live
```

Zaman damgaları `docs-ekran/ekran_cek.py` koşumuyla örtüşüyor.

Betik Veri Tazeleme sekmesinde **«Şimdi tazele»**ye basıyor. O düğme tek başına
zararsız: yalnız ön izlemeyi açıyor ve ön izleme ucu **ağa çıkmıyor**
(`routers/isler.py::refresh_preview` — *"ön izlemenin kendisi ağ gerektirseydi,
'internet var mı' sorusunu sormanın maliyeti yine internet olurdu"*).

Tehlike ön izlemenin AÇIK KALMASI. Kip pencere ekranı kaplarken betiğin bir
sonraki adımı başka bir sekmeye tıklıyor ve o tıklama pencerenin onay düğmesine
düşüyor. Yani kare almak, canlı toplama başlatıyor.

## Neden bu sadece "veri tazelendi" değil

Yeniden toplama meta dosyasını sıfırdan yazıyor ve **türetilmiş provenance
alanlarını taşımıyor**:

| alan | önce | sonra |
|---|---|---|
| `scraped_at` | 2026-08-03T16:52 | 2026-08-24T19:40 |
| `campaign_status` | `expired` | **yok** |
| `expiry_stamp` | ifade + alıntı + span | **yok** |
| `reextracted_at` | 2026-08-04T13:48 | **yok** |
| `extraction_result` | `degisim_yok` | **yok** |

`expiry_stamp` bir kanıt kaydıdır: *"Kampanya Süresi Dolmuştur"* ifadesinin
belgede tam olarak nerede geçtiğini (`span_start`, `span_end`) ve hangi alıntıyla
işaretlendiğini tutar. [[celiski-tespiti]] taramasının **20 bulgusundan 17'si**
`suresi_dolmus_kampanya` türünde ve bu damgadan besleniyor.

Yani ekran görüntüsü almak, ekranın gösterdiği kanıtı siliyordu.

## Çözüm

1. **Geri alındı.** `git checkout -- app/data/raw`; damgaların yerinde olduğu
   doğrulandı (`expiry_stamp: VAR`, `campaign_status: expired`).
2. **Kip pencere kapatılıyor.** Kare alındıktan hemen sonra `Escape` ve
   «Vazgeç» — sonraki tıklama onay düğmesine düşemez.
3. **Sessiz kalmasın diye kapı.** `_ham_veri_bozulmadi_mi()` koşum sonunda
   `git status --porcelain app/data/raw` bakıyor; boş değilse kaç dosyanın
   değiştiğini, muhtemel sebebi ve geri alma komutunu yazıyor. Betik bir kapı
   değil uyarıcı: `git` yoksa sessizce atlıyor.

## Kalan risk

Uyarı koşum SONUNDA basılıyor, yani hasar önce oluyor. Daha güçlü bir çözüm
ekran çekimi yığınını **geçici bir `RAW_DIR`** ile başlatmak olurdu; o zaman
tazeleme ateşlense bile depo dokunulmaz kalır. Yapılmadı çünkü `baslat.sh`
`RAW_DIR`'i sabit veriyor ve teslime beş gün var; uyarı, sessiz bozulmayı
görünür kılmaya yetiyor.

## İlgili dosyalar

- `docs-ekran/ekran_cek.py` — kapatma adımı + `_ham_veri_bozulmadi_mi()`
- `app/src/api/routers/isler.py` — `refresh_preview` (ağa çıkmaz), `refresh_start`
- `app/data/gunluk/islem-gunlugu.jsonl` — kanıtın kendisi

## Sources

- `app/data/gunluk/islem-gunlugu.jsonl` satır 3316 ve 3347 — iki `POST /refresh`
- `git diff app/data/raw` (2026-08-24) — 72 dosya, silinen alanlar

## Related

- [[celiski-tespiti-yavasti-ve-500-donuyordu]] — aynı oturumda, aynı sekmenin
  başka bir arızası
- [[bilgi-cikarimi]] — provenance'ın hizmet ettiği kavram
