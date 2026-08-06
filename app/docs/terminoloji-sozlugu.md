# Katılım finansı terim sözlüğü — köken ve kullanım

**Dosya:** `data/terminology/katilim-terim-sozlugu.json`
**Kaynak:** Mentör Cavide Hanım (eski bankacı; chatbot ve çok-ajanlı sistem
deneyimi), 2026-08-06 tarihli e-posta.
**Doğrulama:** Terimlerin hukuki ayrımları mentörün avukat eşi tarafından
gözden geçirildi (Osmanlıca/fıkhî muamelat dili).
**Birincil standart kaynakları (girdilerin `kaynak` alanında):** AAOIFI Şer'i
Standartları, TKBB Katılım Finans Standartları, 5411 sayılı Bankacılık Kanunu,
SPK III-61.1 Kira Sertifikaları Tebliği, Türk Borçlar Kanunu, Türk Medeni
Kanunu, 6361 sayılı Kanun, SEDDK katılım sigortacılığı düzenlemeleri.

Sözlük **101 girdi** taşır. Bütünlük denetimi: mükerrer `id` yok, `iliskili`
alanındaki tüm çapraz referanslar çözülüyor, 15 alanın 14'ü tüm girdilerde dolu
(`risk_notu` yalnız 20 riskli girdide bulunur, bu kasıtlıdır).

---

## Neden replace değil, enjeksiyon

Mentörün maili, ilk aksiyon planındaki *yasak/karşılık tablosu* yaklaşımını
açıkça reddediyor:

> "Bunları LLM'e system prompta vermek mantıklı. Birebir değiştirmek anlamda
> bozukluk yaratıyor. Eşim avukat, ona danıştım, iyi Osmanlıca bilir,
> Türkçeleri aynı anlamı replace ile taşımıyor. O sebeple böyle bir kapsamlı
> analiz vermek gerekiyor. Bir de dönüşte atıyorum fon ya da bono yazmak da
> yanlış. Yine bunların jargonla cevap oluşturmak doğrusu."

Bu bir teori değil, bizim kendi ölçtüğümüz bir kusurun genellemesi.
`src/chatbot/safety.py` KAPI 1 kök tabanlı değiştirme yapıyordu ve gerçek
korpusta çöktüğü nokta bulundu: bankaların eğitim sayfaları iki kavramı
**karşılaştırıyor** —

    "Kâr Payı ile Faiz Arasındaki Farklar"

Kör değiştirme bunu "Kâr Payı ile Kâr Payı Arasındaki Farklar" yapıyordu.
`_CONTRAST_REPLACEMENTS` bu tek vaka için yazıldı. Sözlüğün `degildir` ve
`ayrim_notu` alanları aynı sorunun **101 terimlik genel çözümüdür**: bir
terimin ne OLMADIĞI ve ayrımın nerede durduğu makine-okunur biçimde yazılı.

Bu yüzden tablo bir *dönüşüm kuralı* değil, kendi çıktımız için bir *tespit
hedefi* olarak kalır (`scripts/jargon_lint.py`); sözlük otoritedir.

## Neden tümü prompt'a konulamaz

Sözlük **76 200 karakter**. `OLLAMA_NUM_CTX` 8192 token; Türkçe metinde bu
kabaca 25–30 bin karaktere denk gelir. Sözlüğün tamamı sistem prompt'una
sığmaz — üstelik Ollama varsayılan bağlamı **baştan sessizce kırpar**, yani
taşma sistem prompt'unu yok ederek sessizce niteliği düşürürdü.

Bu yüzden `src/domain/terminology.py::relevant_terms()` deterministik bir
yönlendiricidir: belgede **fiilen geçen** terimler seçilir, kart olarak
(~8 kart ≈ 3 000 karakter) enjekte edilir. Kart alan sırası
`kanonik → degildir → ayrim_notu → risk_notu`; `tanim` en sona düşer, çünkü
modelin bilmediği şey tanım değil **ayrımdır**.

## Sözlüğün beslediği yerler

| Tüketici | Kullanılan alanlar | Amaç |
|---|---|---|
| Çıkarım sistem prompt'u (`llm/schema.py`) | `degildir`, `ayrim_notu` | alan karışmasını önlemek |
| Gümüş etiketleyici/denetleyici (`silver/prompts.py`) | aynı | sınıf sınırları |
| Chatbot sentezi (`chatbot/rag.py`) | `kanonik`, `ayrim_notu` | jargona uygun cevap |
| Chatbot kapsam sözlüğü (`chatbot/safety.py`) | `kanonik`, `varyantlar`, `halk_dili` | haksız çekimserliği azaltmak |
| RAG sorgu genişletme | `halk_dili` | kullanıcının günlük dilini kanonik terime bağlamak |
| Çıktı bekçisi | `degildir`, `risk_notu` | "sukuk = tahvil/bono" gibi ihlalleri yakalamak |

## Sözlüğün taşıdığı üç tuzak sınıfı

**1. Anlam çakışması** — aynı kelime iki farklı şey: `katilim-fonu` (mevzuatta
mevduat karşılığı ↔ günlük dilde faizsiz yatırım fonu), `havale` (para
transferi ↔ borcun nakli), `zimmet` (borç sorumluluğu ↔ ceza hukukundaki
zimmet suçu). Bağlam ayrılmadan cevap verilmemeli.

**2. Tersine dönen ekler** — `muaccel` / `müeccel` tek harf farkla taban tabana
zıt; `adem-i ifa` olumsuzluk taşır; `gayri kabili rücu` / `kabili rücu`
önekiyle tersine döner. Normalizasyon bu ekleri silmemeli.

**3. Değişken rakamlar** — `tmsf` sigorta limiti ve `nisap` dönemsel olarak
güncellenir. `risk_notu` modelin sabit rakam söylemesini yasaklar.

## Yayın notu

Sözlük şartname §9 gereği teslimden önce depoya girecektir; erken yayınlamanın
jüriye faydası yok, rakibe faydası var. Yayın kademesi: **teslime yakın**
(bkz. push politikası).
