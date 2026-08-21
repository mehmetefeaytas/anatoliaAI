# Kimlik Doğrulama — kurum kancası, kimlik sistemi değil

İlgili: `CLAUDE.md` §7 (teknoloji yığını), §11 (demo stratejisi), §20 (gizli bilgi yok)
Kod: `src/api/kimlik.py`, bağlama `src/api/main.py::build_app()`
Test: `tests/test_api_kimlik_dogrulama.py` (41 test)
Tarih: 2026-08-21

---

## 1. Neden bu belge var

21 Ağustos 2026'ya kadar API katmanında kimlik doğrulamaya dair **tek bir satır
yoktu**. Ölçülebilir hâli:

```
grep -rniE "api_key|authoriz|bearer|jwt|oauth" src/api/   ->  0 sonuç
```

Sistem "kurum sistemlerine entegre edilebilir" diye anlatılıyordu; ama bir
katılım bankasının kendi ağına koyacağı bir servisin **çağıranı ayırt
edememesi** mimari bir eksikliktir. Veri hassas olmasa bile `/refresh`
internete çıkan ve diske yazan bir **eylem** ucudur: kim tetiklediği
işlem günlüğünde görünür, ama *tetikleyebilen kim* sorusunun cevabı "ağa
erişebilen herkes"ti.

Bu belge o boşluğu kapatan kancayı, sınırlarını ve kurumun onu kendi kimlik
sistemine nasıl bağlayacağını anlatır.

---

## 2. Tehdit modeli — neyi çözer, neyi ÇÖZMEZ

Bu bir güvenlik ürünü değil; **tek bir katmanın** tek bir sorumluluğu.

### Çözer

| Tehdit | Nasıl |
|---|---|
| Kurum ağındaki yetkisiz bir istemcinin API'yi çağırması | Anahtar olmadan `/health` dışında hiçbir uç cevap vermez (401) |
| Panel/rapor tüketicisinin yanlışlıkla (ya da kasten) eylem tetiklemesi | Salt-okuma anahtarı `/refresh`, `/summaries/build`, `/admin/*` uçlarında 403 alır |
| Anahtar tahmini için yanıt süresi ölçmek | Karşılaştırma `hmac.compare_digest` ile ve **ilk eşleşmede kırılmadan** yapılır |
| Hangi anahtarın yanlış olduğunu deneme-yanılma ile bulmak | Tanımsız anahtar ile yanlış anahtar **aynı** cevabı alır; mesaj anahtarı içermez |
| Güvenliğin sessizce kapalı kalması | Doğrulama kapalıysa **açılışta uyarı** log'lanır |
| Anahtarın log/denetim kaydına düşmesi | Anahtar hiçbir yere yazılmaz — `__repr__` bile yalnız sayı gösterir (test edildi) |

### ÇÖZMEZ — açıkça

| Tehdit | Neden burada değil |
|---|---|
| Kullanıcı kimliği, oturum, parola, çoklu doğrulama | Kurumun dizin servisinin (LDAP/AD) işi; ürünün ikinci bir kimlik yüzeyi açması hem gereksiz hem denetim dışıdır |
| Anahtar döndürme (rotation), süre sonu, iptal listesi | Sır yönetimi kurumun kasasının (Vault/secret store) işi; ürün anahtarı okur, yönetmez |
| Kişi düzeyinde denetim izi ("hangi personel") | Anahtar bir **istemci** kimliğidir, kişi değil. Kişi düzeyi izleme geçit + kurum kimliğiyle yapılır |
| Taşıma güvenliği (şifreleme) | TLS sonlandırma ters vekil sunucunun işi. **Anahtar düz HTTP üzerinde gönderilirse ağı dinleyen okur** — bu kanca TLS'in yerine geçmez |
| Hız sınırlama, kaba kuvvet kilidi, IP listesi | Geçidin (gateway/WAF) işi; uygulama katmanında tekrarlamak iki yerde yarım çözüm üretir |
| Yetki devri, kaynak düzeyinde izin ("yalnız X bankası") | Bugün gerekmiyor: uçların hiçbiri kiracıya (tenant) göre bölünmüş değil. Gerekirse rol kümesi genişletilir |

Kısaca: bu katman **çağıran istemciyi ayırt eder**. Kimlik yönetimi, sır
yönetimi ve ağ güvenliği kurumun zaten sahip olduğu katmanlarda kalır.

---

## 3. Nasıl çalışır

### Anahtar kaynakları (üçü birlikte kullanılabilir)

| Değişken | Rol | Biçim |
|---|---|---|
| `API_KEYS` | `tam` | virgülle ayrık |
| `API_KEYS_READONLY` | `salt-okuma` | virgülle ayrık |
| `API_KEYS_FILE` | satır başına giriş, öntanım `tam` | dosya yolu |

Her girdi `<anahtar>` ya da `<rol>:<anahtar>` biçimindedir. Önek **yalnızca**
tam olarak bilinen bir rol adıysa ayrıştırılır (`tam:`, `salt-okuma:`); böylece
içinde iki nokta geçen bir anahtar sessizce kırpılmaz. Dosyada `#` ile başlayan
satırlar yorumdur.

Aynı anahtar iki listede geçerse **daha kısıtlı** rol kazanır: bir
yapılandırma hatasının maliyeti fazladan yetki olmamalı.

`API_KEYS_FILE` verilip **okunamazsa API açılışta düşer**. Bilinçli: dosyayı
yazan operatör doğrulamayı *açmak* istemiştir; hatayı yutup doğrulamasız
açılmak tam olarak istenmeyen şeyin sessizce olması olurdu.

### İstemci tarafı

```bash
curl -H "X-API-Key: $ANATOLIA_API_KEY"        http://localhost:8000/banks
curl -H "Authorization: Bearer $ANATOLIA_API_KEY" http://localhost:8000/banks
```

İkisi de kabul edilir. Sebep pratik: kurum geçitleri ikisinden birini
dayatabiliyor ve arada seçim yapmak zorunda bırakmak, kancayı tam da
bağlanacağı yerde zorlaştırırdı.

### Cevaplar

| Durum | Ne zaman |
|---|---|
| `401` + `WWW-Authenticate: Bearer` | anahtar yok, ya da tanınmıyor |
| `403` | anahtar geçerli ama rolü yetersiz (salt-okuma → eylem ucu) |

### Ara katman sırası — bağlayıcı

Starlette'te **en son eklenen ara katman en dışta** durur. Kimlik ara katmanı
`build_app()` içinde CORS'tan ve işlem günlüğünden **önce** kurulur, yani en
içte kalır. İki sonucu var ve ikisi de istenen:

1. 401/403 yanıtları `CORSMiddleware`'den geçer, yani **CORS başlıklarını
   alır**. Aksi hâlde tarayıcı gerçek durum kodunu göremez ve panelde "ağ
   hatası" görünürdü.
2. İşlem günlüğü ara katmanı reddi de **kaydeder**. Reddedilen bir isteğin
   denetim kaydında hiç görünmemesi, kaydın en çok işe yarayacağı anda
   susması olurdu. (`tests/test_api_kimlik_dogrulama.py`
   `test_islem_gunlugunde_anahtar_YOK_ama_REDDEDILEN_ISTEK_VAR` bunu kilitler.)

---

## 4. Varsayılan KAPALI — ve neden bu doğru

Hiç anahtar tanımlı değilse doğrulama devre dışıdır ve API bugünkü gibi
çalışır. Üç somut sebep:

1. **Jüri demosu.** `docker compose up` bir anahtar dağıtımı beklemeden
   açılmalı (`CLAUDE.md` §11: 4 dakikalık sunumda beklenecek tek bir servis
   bile fazladır).
2. **Çevrimdışı kanıt koşumu.** `--network none` ile ölçülmüş kanıt zinciri
   (`docs/OFFLINE-KANIT.md`) uçları anahtarsız çağırıyor.
3. **Mevcut test paketi.** Yüzlerce API testi anahtar taşımıyor; varsayılanı
   açık yapmak hepsini aynı anda 401'e düşürürdü.

Ama **sessiz değil**: açılışta uyarı düşer.

```
Kimlik doğrulama KAPALI — üretimde `API_KEYS` verin.
Şu anda uçlar (`/health` hariç) anahtarsız çağrılabilir.
```

Güvenliğin sessizce kapalı olması, hiç olmamasından kötüdür: kimse kapalı
olduğunu bilmiyorsa kimse açmaz. Anahtar tanımlıyken açılışta karşılığı
düşer (`tam: N, salt-okuma: M` — **anahtarların kendisi asla**), ve
16 karakterden kısa anahtar varsa ayrıca uyarılır: tahmin edilebilir bir
anahtar doğrulamayı süs hâline getirir.

---

## 5. Muaf uçlar ve gerekçesi

Muafiyet listesi **kısadır ve kapalı uçludur**.

| Muaf | Gerekçe |
|---|---|
| `GET /health` | Konteyner sağlık probu ve çevrimdışı kanıt koşumu bu ucu **ağsız** (`--network none`) ortamda, anahtar dağıtımı olmadan çağırıyor (`docs/OFFLINE-KANIT.md` adım 7–8, ayrıca `docker-compose.yml` içindeki `curl -s localhost:8000/health` doğrulama komutları). Kapatmak ölçülmüş bir kanıtı kırardı. Uç yalnız üç alan döndürür (`status`, `llm`, `backend`) ve hiçbiri korpus verisi değildir. |
| `OPTIONS` (tüm yollar) | Tarayıcı ön-uçuşu (CORS preflight) özel başlık **taşımaz**; 401 verilirse tarayıcı gerçek isteği hiç göndermez ve panel "ağ hatası" görür. Kimlik katmanı CORS'un içinde kurulduğu için ön-uçuş normalde buraya hiç ulaşmaz; muafiyet, CORS bir gün kaldırılırsa sessiz bir kırılma bırakmamak için var. |

**Bilerek muaf DEĞİL:** `/docs`, `/openapi.json`, `/redoc`. Uç envanteri bir
saldırganın ilk istediği şeydir ve şema kapalıyken sistem çalışmaya devam
eder — yani muafiyetin bedeli var, karşılığı yok.

---

## 6. Rol ayrımı — okuma ile eylem

İki rol: `tam` (okuma + eylem) ve `salt-okuma`.

Ölçüt **metoda** bakar ve ölçütün kaynağı `src/api/gunluk.py::yazan_mi()`'dir
— işlem günlüğünün "yazan uç" tanımıyla **aynı yer**. İkinci bir yol listesi
tutmak iki doğruluk kaynağı demekti; ayrıştıklarında biri sessizce yanlış
karar verirdi. (Aynı gerekçe `gunluk.py` başlığında da yazılı ve orada bir kez
ödenmiş bir derstir.)

Tek istisna `SALT_OKUMA_SORGU_YOLLARI`: `POST /chat` ve `POST /extract` diske
ya da ağa hiçbir eylem yapmaz, kullanıcı sorusunu cevaplar. Panelin salt-okuma
anahtarıyla çalışabilmesi için bu ikisi salt-okuma rolüne açıktır.

Bu liste bir **izin listesidir**, yasak listesi değil. Yarın eklenen yeni bir
yazan uç listede olmadığı için kendiliğinden **kapalı** başlar. Ters yönde bir
istisna listesi (yasaklananlar) ilk yeni uçta sessizce açık kalırdı —
`tests/test_api_kimlik_dogrulama.py::test_izin_listesi_YASAK_listesi_DEGIL`
bu yönü kilitler.

Salt-okuma anahtarının **403 aldığı** uçlar (bugün): `POST /refresh`,
`POST /refresh/cancel/{id}`, `POST /summaries/build`,
`POST /summaries/cancel/{id}`, `POST /admin/*`.

---

## 7. Neden dış servis YOK — ve neden JWT değil

İki kısıt, ikisi de bu projeye özgü.

### Dış servis çevrimdışı iddiayı çökertir

OAuth sağlayıcısı, harici kimlik sunucusu ya da uzaktan çekilen bir **JWKS**
anahtar kümesi, sistemin `--network none` ile **ölçülmüş** çevrimdışı iddiasını
(`docs/OFFLINE-KANIT.md`) doğrudan geçersiz kılar. Ağı olmayan bir konteynerde
imza anahtarını indiremeyen bir doğrulayıcının iki hâli var: ya çalışmaz ya da
doğrulamayı atlar. İkincisi sessiz güvensizliktir ve *hiç doğrulama
olmamasından kötüdür*, çünkü çalıştığı sanılır.

Doğrulama bu yüzden **tamamen yereldir**: karşılaştırılan şey süreç belleğindeki
bir sırdır, hiçbir soket açılmaz.

### Yeni ağır bağımlılık gerekmedi

`PyJWT` (MIT) ve `python-jose` (MIT) lisans olarak uygun — kapı bu değil.
Kapı ihtiyaç: yerel olarak doğrulanan bir sır için `hmac.compare_digest`
**stdlib'de** ve tam olarak bu iş için var. Kütüphane eklemek üç maliyet
getirecekti:

1. Bir bağımlılık daha — `requirements.txt` pinlenmiş ve SBOM'a bağlı; her
   yeni satır tekrar-üretilebilirlik yüzeyini büyütür.
2. Bir lisans denetimi daha (`scripts/lisans_kapisi`).
3. **Yeni bir hata sınıfı:** `alg: none` kabulü, HS256/RS256 karışması, süre
   sonu doğrulamasının kapalı kalması. Hepsi, kurumun geçidinin zaten yaptığı
   bir iş için.

Sonuç: bu değişiklik `requirements.txt`'e **tek satır eklemedi**.

Kurum JWT istiyorsa doğru yer bu süreç değil, **önündeki geçittir**: geçit
jetonu doğrular ve arka uca bu kancanın anlayacağı anahtarı koyar (§8).

---

## 8. Kurum kendi kimlik sistemine nasıl bağlar

Üç yol var; hepsi ürün kodunu değiştirmeden ya da tek bir yerden değiştirerek
çalışır.

### 8.1 Geçit deseni (önerilen)

Kurumun ters vekil sunucusu / API geçidi kendi kimlik doğrulamasını yapar
(Kerberos/SAML/OIDC/mTLS — kurumun neyi varsa) ve arka uca giden istekte
paylaşılan anahtarı **sunucu tarafında** ekler:

```nginx
location /api/ {
    # Kurumun kendi doğrulaması burada koşar (auth_request, mTLS, SSO ...).
    proxy_set_header X-API-Key $anatolia_api_key;   # sır geçitte durur
    proxy_pass http://anatolia-api:8000/;
}
```

Neden önerilen: kimlik kurumun denetlediği yerde kalır, anahtar hiçbir zaman
son kullanıcıya ulaşmaz, ürün tarafında değiştirilecek **hiçbir satır yoktur**.
Rol ayrımı da geçitte yapılabilir: personel grubuna göre `tam` ya da
`salt-okuma` anahtarı enjekte edilir.

### 8.2 Sır kasasından dosya

Anahtarlar Vault / Kubernetes secret / Docker secret olarak bir dosyaya
mount edilir:

```yaml
environment:
  API_KEYS_FILE: /run/secrets/anatolia-api-anahtarlari
```

Dosya değiştiğinde süreç yeniden başlatılır (anahtar kümesi açılışta okunur).
Sıcak yenileme gerekiyorsa `app.state.kimlik` yeni bir `AnahtarDeposu` ile
değiştirilebilir: ara katman depoyu **kapanıştan değil `app.state`ten okur**,
tam olarak bu yüzden.

### 8.3 Doğrulamayı tamamen değiştirmek

Kurum kendi doğrulamasını sürecin içinde koşturmak istiyorsa değiştirilecek
tek şey `AnahtarDeposu.rol()`'dür: girdi sunulan kimlik dizgesi, çıktı
`tam` / `salt-okuma` / `None`. Yerel bir LDAP bağlaması, yerel olarak
doğrulanan bir imza ya da mTLS parmak izi eşlemesi buraya girer. Uçların,
router'ların ve arayüzün hiçbiri değişmez.

```python
class KurumDeposu(kimlik.AnahtarDeposu):
    @property
    def acik(self) -> bool:
        return True

    def rol(self, sunulan):
        return ...  # kurumun YEREL doğrulaması

app.state.kimlik = KurumDeposu()
```

Tek kural: **doğrulama ağa çıkmasın**. Çıkarsa çevrimdışı iddia ölçülemez hâle
gelir.

---

## 9. Panel ve geçit — açık uç

Anahtar açıldığında panel (`web/`) de anahtar taşımak zorundadır ve **kolay
yol yanlıştır**: anahtarı `NEXT_PUBLIC_*` ile geçirmek onu tarayıcıya
sızdırır, yani paylaşılan sır artık paylaşılan değildir.

Doğru seçenekler:

1. **Geçit enjekte eder** (§8.1) — panel anahtarı hiç görmez. Önerilen.
2. Panelin sunucu tarafı (Next.js route handler) API'yi vekil ederek anahtarı
   sunucuda tutar; tarayıcı yalnız panelin kendi yoluna konuşur.

Bugünkü depo durumunda panel anahtar **göndermiyor** — çünkü varsayılan
kapalı ve demo yolu anahtarsız. Anahtar açan kurum yukarıdaki iki yoldan
birini kurmak zorundadır; bu, bu kancanın bilinçli olarak çözmediği ve
belgelediği tek entegrasyon adımıdır.

---

## 10. Ölçüm ve testler

`tests/test_api_kimlik_dogrulama.py` — 41 test. Kilitlenen değişmezler:

| Değişmez | Test |
|---|---|
| Anahtar yokken API bugünkü gibi çalışır | `TestGeriyeUyum` |
| Kapalı olması açılışta log'lanır | `test_kapali_olmasi_ACILISTA_loglanir` |
| Yanlış / eksik anahtar → 401 | `test_yanlis_anahtar_401`, `test_anahtarsiz_istek_401` |
| Doğru anahtar → 200 | `test_dogru_anahtar_200`, `test_bearer_semasi_da_kabul` |
| `/health` muaf (anahtar açıkken bile) | `test_health_ANAHTARSIZ_calisir` |
| Salt-okuma anahtarı eylem ucunda 403 | `test_salt_okuma_yazma_ucunda_403` |
| Salt-okuma anahtarı okuma/sorgu uçlarında geçer | `test_salt_okuma_okuma_ucunda_200`, `test_salt_okuma_sorgu_uclarinda_gecer` |
| Anahtar uygulama log'una düşmez | `test_uygulama_logunda_anahtar_YOK` |
| Anahtar işlem günlüğüne düşmez, ama **reddedilen istek düşer** | `test_islem_gunlugunde_anahtar_YOK_ama_REDDEDILEN_ISTEK_VAR` |
| Hata mesajı hangi anahtarın yanlış olduğunu söylemez | `test_mesaj_HANGI_anahtarin_yanlis_oldugunu_soylemez` |
| Okunamayan anahtar dosyası sessiz geçmez | `test_okunamayan_dosya_SESSIZ_gecmez` |
| İzin listesi yasak listesi değil (yeni uç kapalı başlar) | `test_izin_listesi_YASAK_listesi_DEGIL` |

Saf birim testleri (`AnahtarDeposu`, `karar_ver`, `anahtar_oku`) **fastapi
olmadan** koşar — çekirdek katmanın sıfır bağımlılık iddiası bu dosyada da
korunuyor.

---

## 11. Bilinen sınırlar

- **Uzunluk sızar.** `hmac.compare_digest` içerik karşılaştırmasını sabit
  zamanlı yapar, ama anahtar **uzunluğu** yanıt süresinden çıkarılabilir.
  Sabit uzunlukta anahtar (`secrets.token_urlsafe(32)`) kullanmak bu kanalı
  kapatır ve önerilen budur.
- **Anahtar süresi yok.** İptal, anahtarı yapılandırmadan çıkarıp süreci
  yeniden başlatmakla olur. Süre sonu ve döndürme kurumun sır kasasının işi.
- **Kişi düzeyi denetim yok.** İşlem günlüğü hangi *anahtarın* değil hangi
  istemcinin (IP) çağırdığını kaydeder; anahtar kasıtlı olarak kayda
  girmiyor. Kişi düzeyi iz gerekiyorsa geçit kendi kaydını tutmalıdır.
- **`docs/SARTNAME-UYUM.md` 17. satırı güncellenmeli.** O satır bu dosyayı
  *"`.env.example` (88 satır, hiçbir API anahtarı alanı yok)"* diye ücretli
  servis kullanılmadığının kanıtı olarak gösteriyor. `.env.example` artık
  `API_KEYS` alanları içeriyor — ama bunlar **gelen** istekleri doğrulayan,
  kurumun kendi ürettiği yerel sırlardır; hiçbir dış servise bağlanmaz ve
  ücretli hiçbir bileşen eklemez. Kanıt cümlesi bu ayrımı yazacak şekilde
  düzeltilmeli, yoksa iki belge çelişir görünür.
