
## vade_ay: ürün vadesi olmayan zaman ifadeleri (2026-08-08)

Chatbot "en yüksek vade hangi bankada?" sorusuna **Ziraat Katılım, 360 ay**
diyor. Kaynak metin:

> "…uzun vadeli (**genelde 2-30 yıl**) yatırım yapmayı düşünen kişi ve
> kuruluşlar YP Sukuk tercih edebilir."

Bu bir **yatırımcı profili** tarifidir, ürün vadesi değil. Ayrıca aralığın
(2–30 yıl) yalnız üst ucu alınmış.

Aynı sınıftan ikinci vaka, korpusta 120 ay üreten kayıtlar arasında:

> "Gelecek **10 yılda** bankacılık sektöründe ürün, hizmet…"

Takvim yılı kusuruyla (kapatıldı: `_takvim_yili`) aynı aile: sayı bir vade
bağlamında DEĞİL ama vade sanılıyor.

**Neden şimdi yapılmadı:** kanıt n=1–2. "uzun vadeli" ifadesi anahtar kelime
kapısını geçiyor, yani basit bir anahtar-kelime kuralı bunu ayırmıyor.
Ayırt edici işaret parantez içi açıklama ve "yatırım yapmayı düşünen /
sektöründe" gibi ürün-dışı yüklem — n=2 üzerinde kural yazmak, ölçülmemiş
bir desene kural yazmak olur. Önce kanıt toplanmalı: korpustaki tüm
`vade_ay ≥ 120` kayıtları elle taranıp kaç tanesinin ürün vadesi olmadığı
sayılmalı.

Şimdilik meşru en yüksek vade **120 ay**dır ve 360'lık kayıt tek başınadır.

## hedef_kitle: regex biçimli bir alan değil (2026-08-12)

F1 **0,267** (P 0,333 · R 0,222 · TP 4 · FP 8 · FN 14 · uydurma 5). Yapısal
alanların en yüksek desteğine sahip (18) ve en kötü F1'i. İki hipotez
kuruldu, **ikisi de ölçülüp çürütüldü**; bu yüzden kural yazılmadı.

### Hipotez 1 — negasyon penceresi çıplak "değil"i kaçırıyor (ÇÜRÜTÜLDÜ: n=1)

Doğru tespit: pencere `geçerli değil` arıyor ama korpus "…sadece hoş geldin
kampanyası **değil**" diyor ve bu yakalanmıyor
(`hayat-finans--hesaplar-avantajli-hesap`, `yeni_musteri` uyduruyor).

Ama 1.780 belgede bu deseni taşıyan **1 belge** var. n=1 üzerinde kural
yazmak, ölçülmemiş bir desene kural yazmaktır (aynı disiplin `vade_ay`
girişinde de uygulandı).

### Hipotez 2 — segment araması UYGUNLUK cümlesine sınırlanmalı (ÇÜRÜTÜLDÜ)

Gold dayanaklarının 5/6'sı "Kampanyadan kimler faydalanabilir?" cümlesinde
duruyor, uydurmaların ikisi ise ürün-uygunluk listesinden geliyor (ziraat
"emekliler", kuveyt leasing "Serbest Meslek Sahipleri"). Kapı denendi:

    mevcut          : gold-değeri-olanda üretim 7, uydurma 5
    uygunluk-kapılı : gold-değeri-olanda üretim 2, uydurma 0

5 uydurmayı elemek için 5 doğru üretimi öldürüyor — net F1 DÜŞER. Takas
kabul edilemez.

### Asıl kök neden: alan açık-sınıf semantik yüklem istiyor

Değer üretilmeyen 6 belgenin gold dayanakları birbirinden farklı TÜRDE
yüklemler:

| dayanak | sinyal türü |
|---|---|
| "şahıs firmasına sahip eczaneler faydalanabilir" | meslek |
| "kartına sahip ancak henüz hiç harcama yapmamış müşteriler" | davranışsal |
| "Hadi Gold üyesi olmalısın" | program üyeliği |
| "riskli yapı olarak tespit edilen … malikleri" | hak sahipliği |
| "Sadece bireysel Hayat Finans müşterileri" | müşteri tipi |
| "nitelikli yatırımcı beyanı vererek" | yasal statü |

Sınırlı bir anahtar-kelime listesi bunları kapsamaz; alan "kimler
faydalanabilir" sorusunun CÜMLE düzeyinde cevabını ve onu 4 etikete
eşlemeyi gerektiriyor. Bu, kural katmanının değil LLM katmanının işi —
`reconcile()` boş alanları LLM'e gönderdiği için mimari yol AÇIK, ama
teslim edilen sistem varsayılan olarak kural-only koşuyor
(`LLM_BACKEND` boş).

**Sonraki tur için doğru iş:** kural genişletmek değil, (a) uygunluk cümlesi
tespitini LLM few-shot ile eşleştirmek, ya da (b) gold'a bu 6 desenden örnek
ekleyip alanı LLM kolunda ölçmek.
