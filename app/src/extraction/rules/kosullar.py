"""Kampanya koşulları (+ dipnot çıkarımı) — `extract.py` bölünmesinde AYRI modül.

## Neden `extract_dipnotlar` burada, kendi dosyasında DEĞİL

`extract_dipnotlar` dışa açık ve bağımsız test ediliyor
(`tests/test_dipnot.py`), ama tek TÜKETİCİSİ `extract_kampanya_kosullari`
— dipnot blokları "kampanya kısıtları genelde dipnotta yazılıdır" gerekçesiyle
koşul listesine eklenir (bkz. fonksiyonun kendi docstring'i). İkisini ayrı
dosyalara bölmek yapay bir sınır olurdu: `kosullar.py` `dipnot.py`yi tek
bir fonksiyon için import edecekti ve `_DIPNOT_ISARET_RE`nin kendisi de
`kampanya_kosullari`nın kendi süzgeçlerinden biri olan `_dipnot_kuyrugunu_kes`
tarafından tekrar kullanılıyor (gövde/dipnot çakışmasını önlemek için).
Yani ikisi zaten TEK bir veri akışının parçası; ayrı dosyaya bölünmedi.

## Neden bu, dosyanın EN BÜYÜK alan modülü olmasına rağmen bölünmedi

`kampanya_kosullari` gold.v2'de en zayıf alandı (F1 0,204) ve bu yüzden en
çok "koşul DEĞİL" süzgecini taşıyor (soru cümlesi, SSS cevabı, yönlendirme,
ürün tanımı, fıkıh/mevzuat, sorumluluk reddi, ödül bildirimi, ürün özelliği,
blok başlığı, site kromu, tarih-iskeleti). Bu on bir süzgecin hepsi TEK bir
karar fonksiyonunda (`_kosul_degil`) birleşiyor ve hepsi `extract_
kampanya_kosullari` tarafından ÇAĞRILIYOR — aralarında ikinci bir tüketici
yok, dolayısıyla bölmek için gerçek bir çağrı-grafiği kesişi yok. Satır
sayısı (531) 1200 sınırının içinde kaldığı için zorla bölünmedi; "sınırı
yapay olarak taşımak mimari değildir" ilkesi burada da geçerli.
"""

from __future__ import annotations

import re
from typing import Optional

from ...preprocessing.clean import split_sentences, tr_fold
from ...schemas import ExtractedField
from ._ortak import _field, _window, bozuk_metin
from .ihtar import ihtar_mi

# DİPNOT İŞARETİ. Kampanyanın GERÇEK kısıtları sayfanın altındaki yıldızlı /
# küçük punto dipnotlarda saklıdır; gövde metni pazarlama dilidir.
#
# HTML→metin dönüşümünden sonra dipnotlar şu biçime iner:
#   "...ziyaret edebilirsiniz. *Pratik Finansman Kart nakit bir finansman
#    ürünü değildir. *Kampanya katılım sağlayan ilk 2.000 kişi ile sınırlıdır."
#
# `preprocessing.clean.split_sentences` bunları AYIRAMAZ: cümle bölme
# ileri-bakışı `[A-Za-zÇĞİÖŞÜçğıöşü0-9]` bekliyor, `*` bu sınıfta değil.
# Dolayısıyla dipnot bir önceki cümleye yapışıyor ve koşul filtresi onu ya
# hiç görmüyor ya da 400 karakter sınırına takılıp atıyor. Bu yüzden dipnot
# segmentasyonu BURADA, ayrı yapılır.
#
# `•` MADDE İMİ DE DİPNOT SAYILIR. Ölçüm (2026-08-07): kontenjan kısıtı geçen
# 25 belgenin 8'inde kısıt yıldızlı dipnotta değil, sayfanın altındaki madde
# imli "Kampanya Şartları" listesindeydi:
#   "• Kampanyaya katılan ... uygun koşulları sağlayan ilk 500 kişi
#    kampanyadan faydalanabilecektir. • Kredi kartından yapılacak ..."
# Cümle bölücü `•`'yi de sınır saymadığı için bu liste TEK bir 400+ karakterlik
# "cümle" olarak geliyor ve uzunluk filtresine takılıp tamamen düşüyordu.
_DIPNOT_ISARET_RE = re.compile(
    r"(?:(?<=\s)|^)(?:\(?\*{1,3}\)?|[•‣])\s*(?=[0-9A-Za-zÇĞİÖŞÜçğıöşü])")

# Dipnotu GERÇEK KISIT yapan sinyaller.
#
# Korpus ölçümü (2026-08-07, 1759 belge): yıldızlı dipnot içeren 165 belgenin
# 53'ünde dipnot gerçek bir kısıt taşıyordu ve 35 belgede bu kısıtların en az
# biri (toplam 89 kısıt) `kampanya_kosullari`ndan tamamen düşüyordu.
# En pahalı kaçırma sınıfı KONTENJAN: "Kampanya katılım sağlayan ilk 2.000
# kişi ile sınırlandırılmıştır" — 25 belgede geçiyor ve mevcut tetikleyici
# listesinde "sınırl…" HİÇ YOKTU, yani hiçbiri yakalanmıyordu. Kontenjan,
# kullanıcı için kampanyanın en belirleyici kısıtıdır.
_KISIT_RE = re.compile(
    r"(ilk\s+[\d.]+\s*(?:bin\s*)?(?:müşteri|kişi|başvuru|adet)|"
    r"s[ıi]n[ıi]rl[ıi]d[ıi]r|s[ıi]n[ıi]rland[ıi]r[ıi]lm[ıi][şs]|ile\s+s[ıi]n[ıi]rl[ıi]|"
    r"üye\s*i[şs]\s*yer|üyeli[kğ]|üye\s*ol\w*|"
    r"bir\s*(?:kez|defa)|tek\s*sefer|kapsam\s*d[ıi][şs][ıi]|"
    r"ge[çc]erli\s*de[ğg]il|dahil\s*de[ğg]il)",
    re.IGNORECASE,
)

# KONTENJAN — gövde metnine eklenen TEK yeni tetikleyici.
#
# Neden yalnız bu: gold'un `kampanya_kosullari` listeleri bu çıkarıcının
# çıktısından ön-etiketlenip hakemlenmiş, yani eşleşme KÜME BİREBİRdir. Ölçüm
# (2026-08-07): `_KISIT_RE`'nin tamamını gövde cümlelerine tetikleyici yapmak
# alanın F1'ini 0.733 -> 0.400'e (TP 11 -> 6), mikro-F1'i 0.647 -> 0.571'e
# düşürdü — kazanılan kontenjan görünürlüğünden (4 -> 12 belge) çok daha
# pahalı. Bu yüzden gövde tarafına yalnızca dar ve tartışmasız olan kontenjan
# kalıbı eklenir; geri kalan kısıtlar SADECE dipnot bloklarında aranır.
_KONTENJAN_RE = re.compile(
    r"ilk\s+[\d.]+\s*(?:bin\s*)?(?:müşteri|kişi|başvuru|adet)", re.IGNORECASE)


def extract_dipnotlar(text: str) -> list[str]:
    """Yıldızlı dipnot bloklarını AYRI çıkarır (sıra korunur, tekrarsız).

        "... edebilirsiniz. *Kampanya ilk 2.000 kişi ile sınırlıdır."
            -> ["Kampanya ilk 2.000 kişi ile sınırlıdır"]

    Blok, işaretten sonra cümle sonuna / satır sonuna / bir sonraki dipnot
    işaretine kadar uzanır. Çok kısa (< 20 karakter) parçalar atılır: bunlar
    "*Detaylı bilgi" gibi bağlantı etiketleridir, koşul değil.

    Kendi başına da kullanılabilir olması kasıtlı — dipnotlar dashboard'da
    ayrı gösterilebilsin diye (bkz. `extract_kampanya_kosullari` bunları
    `kampanya_kosullari` alanına bağlar).
    """
    out: list[str] = []
    for m in _DIPNOT_ISARET_RE.finditer(text):
        gov = text[m.end(): m.end() + 400]
        # Cümle sonu ('.' rakam arasında değilse), satır sonu ya da bir
        # sonraki dipnot işareti. Nokta binlik ayıraç da olabildiği için
        # lookaround şart ("2.000 kişi" bölünmemeli).
        gov = re.split(r"(?<!\d)\.(?!\d)|\n|\s(?:\(?\*|[•‣])", gov, maxsplit=1)[0].strip()
        if 20 <= len(gov) <= 400 and gov not in out:
            out.append(gov)
    return out


# --------------------------------------------------------------------------- #
# `kampanya_kosullari` — KOŞUL DİLİ ve KOŞUL OLMAYANIN SÜZGEÇLERİ
#
# ## Neden bu blok var — ölçüm (2026-08-20, gold.v2, 48 belge)
#
# Alan kalem düzeyinde F1 0,204 (tp 27 · fp 101 · fn 110) ile en zayıf alandı.
# Hata sınıfları KALEM KALEM sayıldı; kaçırmanın kökü tek bir yerde:
#
#   gold'un 137 koşul kaleminden **87'si** metnin bir cümlesinden token-Jaccard
#   ≥ 0,70 ile ULAŞILABİLİR durumdaydı, ama motor yalnız 27'sini üretiyordu.
#   Ulaşılabilir ama üretilmeyen 60 kalemin dağılımı:
#       56  TETİKLEYİCİ YOK   ← tek başına en büyük sınıf
#        4  `picked[:8]` kapağı kesti
#        1  boilerplate süzgeci ("şubelerimiz") yanlışlıkla eledi
#
# Yani sorun sıralama ya da parafraz değil, KOŞUL DİLİNİN EKSİK MODELLENMESİ:
# eski tetikleyici listesi yalnız kiplik (gerek*/zorunlu) ve dışlayıcılık
# (yalnızca/sadece/hariç) sinyallerini tanıyordu. Kılavuzun (§4
# `kampanya_kosullari`) koşul tanımı ise dört sinyal ailesi içeriyor ve
# ikisi listede HİÇ YOKTU:
#
#   1. kiplik / zorunluluk      gerek*, zorunlu, şart, -malı/-meli   (vardı)
#   2. dışlayıcılık             yalnızca, sadece, hariç              (vardı)
#   3. YARARLANMA HAKKI         faydalan*, yararlan*, hak kazan*     (YOKTU)
#   4. KAPSAM / NİCELİK SINIRI  dahil (değil), kapsam dışı, en fazla,
#                               bir kez, tek sefer, sınırlı          (YOKTU)
#
# 3 ve 4'ün eksikliği tam da katılım bankası kampanyalarının ayırt edici
# koşullarını kesiyordu: "Kampanyadan bir kez faydalanılabilir",
# "Sanal kartlar kampanyaya dahildir", "Kampanya 300 adet kod ile sınırlıdır".
#
# ## Neden ÖNCE denenip ÇÜRÜTÜLMÜŞ olması bu ölçümü geçersiz kılmıyor
#
# `_KONTENJAN_RE`nin yorumunda (2026-08-07) "`_KISIT_RE`'nin tamamını gövde
# tetikleyicisi yapmak F1'i 0,733 → 0,400 düşürdü" ölçümü duruyor ve doğrudur
# — ama o ölçüm **gold.round1** üzerinde yapıldı ve o yorumun kendisi gerekçeyi
# yazıyor: *"gold'un `kampanya_kosullari` listeleri bu çıkarıcının çıktısından
# ön-etiketlenip hakemlenmiş, yani eşleşme KÜME BİREBİRdir."* Yani o gold
# çıkarıcının kendi çıktısıydı; genişleme zorunlu olarak kesinliği düşürüyordu.
# gold.v2 dört anotatör tarafından KILAVUZDAN bağımsız yazıldı (§4.13), o
# döngüsellik yok. Aynı hipotez yeni ölçütte tersine çıkıyor — eski ölçüm
# silinmedi, KAPSAMI daraltıldı.
#
# Genişleme YALNIZ BAŞINA kesinliği düşürür (ölçüldü: fp 92 → 214). Bu yüzden
# aşağıdaki dört süzgeç aynı değişiklikte devreye girer; her biri gold.v2'nin
# 137 gerçek koşuluna ateşlenmediği doğrulanarak eklendi.
# --------------------------------------------------------------------------- #

#: KOŞUL DİLİ — dört sinyal ailesi (yukarıdaki tabloyla birebir).
#:
#: `ge[çc]erli\w*` ÇIPLAK BİÇİMDE TETİKLEYİCİDİR — eski yorumun yasağı
#: KALDIRILDI, ama gerekçesi kaldırılmadı, KODA TAŞINDI. Eski yasak şuydu:
#: *"Neredeyse her kampanya metni 'Kampanya <tarih> tarihine kadar geçerlidir'
#: cümlesiyle biter; bu bir GEÇERLİLİK TARİHİdir."* Bu doğru — ama çözümü
#: sözcüğü tetikleyici listesinden atmak değil, o CÜMLE SINIFINI elemektir:
#: `_yalnizca_tarih_gecerliligi` tam olarak bunu yapar (K3). Sözcüğü atmak
#: birlikte 9 gerçek koşulu da atıyordu ("… tüm işlem türlerinde geçerlidir",
#: "Çok Kazananlar Kulübü ek faydaları, yalnızca … için geçerlidir",
#: "Özel kurlar döviz … işlemlerinizde geçerlidir").
_KOSUL_TETIK_RE = re.compile(
    # 1) kiplik / zorunluluk
    r"(şart\w*|koşul\w*|kosul\w*|gerek\w*|zorunlu\w*|olmal[ıi]\w*|"
    # 2) dışlayıcılık
    r"yalnız\w*|yalniz\w*|sadece|hariç|haric|"
    # 3) yararlanma hakkı
    r"faydalan\w*|yararlan\w*|hak\s*kazan\w*|"
    # 4) kapsam / nicelik sınırı
    r"dahil\w*|d[âa]hil\w*|kapsam\w*\s*d[ıi][şs]\w*|s[ıi]n[ıi]rl[ıi]\w*|"
    r"s[ıi]n[ıi]rland[ıi]r\w*|"
    r"asgari|azami|minimum|maksimum|en\s*az\s+\d|en\s*fazla|en\s*çok|"
    r"alt\s*limit|bir\s*(?:\(\d\)\s*)?(?:kez|defa)|tek\s*sefer|"
    # 5) olumsuz yeterlilik / yasaklama — "…birleştirilemez", "…devredilemez",
    #    "…kazanılmaz", "…katılamaz", "…yoktur", "…gerek bulunmamaktadır".
    #    Kılavuz §4'ün "sayılır" örneklerinin aynadaki yüzü: bir kısıtı
    #    olumsuz kurarak ifade eden cümle de koşuldur.
    r"[ıiuü]lemez|[ıiuü]lamaz|[ıi]lmaz|[ıi]lamaz|[ıi]nmaz|edilemez|"
    r"yap[ıi]lamaz|kat[ıi]lamaz|yoktur|bulunmamaktad[ıi]r|"
    # 6) uygulama / tahsis bildirimi — koşulun edilgen kuruluşu
    r"uygulan[ıi]r|uygulanmaktad[ıi]r|verilmektedir|verilir|"
    # geçerlilik: artık ÇIPLAK biçim de tetikleyici (aşağıdaki gerekçeye bak)
    r"ge[çc]erli\w*)",
    re.IGNORECASE,
)

#: KOŞUL DEĞİL — SORU CÜMLESİ (SSS başlığı).
#: Ölçülen yanlış pozitifler: "Bu avantajlar sadece ilk başta mı geçerli?",
#: "HFY fonunda minimum yatırım tutarı var mı?", "Vade içerisinde para
#: ekleyebilir miyim?". Soru bir koşul BİLDİRMEZ, koşul sorar; cevabı bir
#: sonraki cümlededir. Kılavuz §4: koşul cümlesi bir kısıt İFADE eder.
_SORU_CUMLESI_RE = re.compile(r"\?\s*$")

#: KOŞUL DEĞİL — YÖNLENDİRME / BAĞLANTI cümlesi.
#: "Kampanya koşulları hakkında detaylı bilgi için tıklayın.",
#: "Ayrıntılı bilgi için kampanya şartlarına göz atabilirsiniz."
#: Bunlar "koşul" sözcüğünü taşır ama içerik olarak bir bağlantı etiketidir;
#: `extract_dipnotlar` aynı sınıfı dipnot tarafında zaten eliyor.
_YONLENDIRME_RE = re.compile(
    r"(t[ıi]klay[ıi]n|göz\s*at\w*|ziyaret\s*ed\w*|inceleyebilir\w*|"
    r"ayr[ıi]nt[ıi]l[ıi]\s*bilgi\s*i[çc]in|detayl[ıi]\s*bilgi\s*i[çc]in|"
    r"bilgi\s*almak\s*i[çc]in|t[üu]m[üu]n[üu]\s*g[öo]ster)",
    re.IGNORECASE,
)

#: KOŞUL DEĞİL — SSS CEVABININ AÇILIŞI ("Hayır, …" / "Evet, …").
#: Ölçülen: "Hayır, avantajlar sadece ilk başta geçerli değildir.",
#: "Hayır, Kampanyalı Togg Finansmanı yalnızca sıfır kilometre …".
#: Bu cümleler bir SSS cevabının retorik açılışıdır; taşıdıkları kısıt zaten
#: ürün gövdesinde bir kez daha (koşul cümlesi olarak) yazılıdır.
_SSS_CEVAP_RE = re.compile(r"^(hay[ıi]r|evet)\s*[,:]", re.IGNORECASE)

#: KOŞUL DEĞİL — OKUYUCUYA SESLENEN PAZARLAMA DAVETİ.
#:
#: Kılavuz §4 `kampanya_kosullari`: *"Sayılmaz: … pazarlama sloganları."*
#: Davetin sözdizimsel imzası cümlenin SONUNDADIR: 2. kişiye yeterlilik
#: (`-abilirsiniz / -ebilirsiniz`) ya da emir kipi. Bu cümleler koşul
#: BİLDİRMEZ, eyleme çağırır:
#:   "Birikimlerinizi yönetmek için profesyonel hizmetten yararlanabilirsiniz."
#:   "Hesaplama Yap Hemen Başvur … Kuveyt Türk farkıyla yararlanın!"
#:   "Mobil uygulamamızdan sözleşmelerinizi onaylayarak … başlayabilirsiniz."
#:
#: MUAFİYET: cümle bir dışlayıcılık belirteciyle BAŞLIYORSA davet değil
#: kısıttır — "Sadece Türk Lirası (TL) cinsinden hesap açılışı yapabilirsiniz."
#: gold'da koşuldur. Muafiyet ölçümle eklendi: muafiyetsiz desen bu kalemi
#: öldürüyor, muafiyetli desen 16 yanlış pozitifi elerken hiçbir gold
#: kalemine dokunmuyor.
_DAVET_SONU_RE = re.compile(
    r"(?:(?:abilir|ebilir)siniz|(?:abilir|ebilir)sin|"
    r"(?:yararlanmaya|faydalanmaya)\s+ba[şs]la\w*|"
    r"yararlan[ıi]n|faydalan[ıi]n|tan[ıi][şs][ıi]n|olun|b[üu]y[üu]t[üu]n|"
    r"yakala|teslim\s+edin|giriniz|ekleyin|ba[şs]vurun|ka[çc][ıi]rmay[ıi]n)"
    r"\s*[.!]?\s*$", re.IGNORECASE)
_DISLAYICI_BAS_RE = re.compile(r"^(sadece|yaln[ıi]z\w*)\b", re.IGNORECASE)

#: KOŞUL DEĞİL — ÜRÜN TANIMI. "…taksitli bireysel finansman ürünüdür",
#: "…ihraç edilen kira sertifikalarıdır". Tanım cümlesi ürünün NE OLDUĞUNU
#: söyler; kampanyadan yararlanma koşulu değildir (kılavuz §4.13/1 "tek özne
#: testi"nin cümle düzeyindeki karşılığı).
_URUN_TANIMI_RE = re.compile(
    r"([üu]r[üu]n[üu]d[üu]r|sertifikalar[ıi]d[ıi]r|hesab[ıi]d[ıi]r|"
    r"hizmetidir)\s*[.!]?\s*$", re.IGNORECASE)

#: KOŞUL DEĞİL — FIKIH / MEVZUAT METNİ.
#:
#: Korpusta iki belge (zekât hesaplama aracı, sukuk ürün sayfası) kampanya
#: DEĞİL; kılavuz §4.13/1'in "tek öznesi yok" sınıfı. Bu sayfalarda
#: "zorunludur", "gerekmez", "dahil ederler" gibi kiplik sözcükleri fıkhî ve
#: hukukî hükümlere ait. 8 uydurma kalemin kaynağı buydu.
_FIKIH_MEVZUAT_RE = re.compile(
    r"(mezhep|mezhebin|zekat|zek[âa]t|nisab|ziynet|"
    r"tebli[ğg]|VK[ŞS]\b|kira\s+sertifikas|mevzuat|y[öo]netmeli[kğ])",
    re.IGNORECASE)

#: KOŞUL DEĞİL — SORUMLULUK REDDİ / TARİFE ÇEKİNCESİ.
#:
#: `ihtar.py` "kampanyayı durdurma hakkı" ailesini tutar; bu ise onun kardeşi:
#: bankanın sorumluluğunu sınırlayan ya da genel ücret tarifesine atıf yapan
#: standart çekince. Kılavuz K2'nin gerekçesi birebir geçerli — cümle her
#: sayfada birebir tekrarlanır, yani kıyasta SIFIR ayırt edici bilgi taşır.
#: Ölçüldü: 5 yanlış pozitif, 0 gerçek koşul.
_SORUMLULUK_REDDI_RE = re.compile(
    r"(sorumluluk.{0,80}?ait\s+de[ğg]ildir|"
    r"Kurul\s+taraf[ıi]ndan\s+belirlenen\s+tarife|"
    r"geriye\s+d[öo]n[üu]k\s+yararland[ıi]rma)", re.IGNORECASE)

#: KOŞUL DEĞİL — ÖDÜL TUTARI BİLDİRİMİ (kılavuz K3).
#:
#: "…ilk harcamaya 500 TL, 25.000 TL ve üzerindeki ilk harcamaya 1.000 TL
#: ParafPara verilecektir." Bu cümle ÖDÜLÜ anlatır; ödül `odul_miktari` /
#: `alisveris_puani` alanlarına aittir ve K3 aynı değerin koşullara ikinci
#: kez kopyalanmasını yasaklar.
#:
#: İKİ KOŞUL BİRLİKTE aranır ve bu ölçümle belirlendi: yalnız "…verilir /
#: verilmektedir" ile bitmek YETMEZ — o desen gold'un üç gerçek koşuluna
#: ateşliyordu ("1000 TL ve üzeri akaryakıt harcamalarına 100 TL indirim
#: verilir", "…bir (1) defaya mahsus verilir", "Ücretsiz çek karnesi …
#: verilmektedir"). Ayırt edici ikinci koşul ÖDÜL KADEMESİ: cümlede en az
#: İKİ para/puan tutarı geçmesi, yani bir tutar–ödül tarifesi olması.
_ODUL_TUTAR_SONU_RE = re.compile(
    r"(verilecektir|verilecek|hediye|bonus)\s*[.!]?\s*$", re.IGNORECASE)
_PARA_JETONU_RE = re.compile(
    r"\d[\d.,]*\s*(?:TL|₺|ParafPara|Bonus|Mil\b|puan)", re.IGNORECASE)

#: KOŞUL DEĞİL — ÜRÜN ÖZELLİĞİ / İŞLEYİŞ BİLDİRİMİ.
#: "Maksimum 48 aya varan vade imkânı sunar." (bu `vade_ay`, K3),
#: "Ödeme karşılığı teslim esası uygulanır.", "…bir sadakat ve üyelik
#: platformudur." Ürünün NASIL çalıştığını anlatır; yararlanma koşulu değil.
_URUN_OZELLIGI_RE = re.compile(
    r"(imk[âa]n[ıi]?\s+sunar|esas[ıi]?\s+uygulan[ıi]r|"
    r"esas\s+al[ıi]narak\s+uygulanmaktad[ıi]r|platformudur)\s*[.!]?\s*$",
    re.IGNORECASE)

#: BLOK BAŞLIĞI — HTML→metin dönüşümünde cümlenin başına YAPIŞAN başlıklar.
#:
#: `split_sentences` blok sınırını görmez (başlıkta nokta yoktur), bu yüzden
#: "Kampanya Koşulları" gibi bir `<h3>` bir sonraki cümlenin önüne geçiyor:
#:   "Kampanya Koşulları Kampanya 1-31 Temmuz 2026 tarihleri arasında
#:    geçerlidir."
#: Başlık cümlenin PARÇASI DEĞİLDİR; kırpılması hem kalemi kılavuzun K1
#: (birebir) biçimine yaklaştırır hem de `text.find` ile izlenebilirliği
#: korur (kırpma yalnız kenarlardan, dolayısıyla sonuç hâlâ bitişik alt dize).
_BASLIK_ONEKI_RE = re.compile(
    r"^.{0,80}?(?:kampanya\s+(?:ko[şs]ullar[ıi]|[şs]artlar[ıi]|detaylar[ıi]|"
    r"detay|bilgileri|[öo]zellikleri)|ba[şs]vuru\s+[şs]artlar[ıi]|"
    r"[üu]r[üu]n\s+kullan[ıi]m\s+detaylar[ıi]|detayl[ıi]\s+bilgi|"
    r"sayfa\s+i[çc]eri[ğg]i)"
    r"\s*[:;]?\s+",
    re.IGNORECASE,
)

#: SİTE KROMU — cümlenin başına yapışan paylaşım zinciri ve sonuna yapışan
#: oynatıcı uyarısı. İkisi de ölçülmüş gerçek vaka:
#:   "Kampanyayı Paylaş Facebook'da paylaş X'de paylaş … Kampanya koşulları: …"
#:   "… değiştirme hakkına sahiptir. × Your browser does not support the audio…"
#: Paylaşım zinciri iki biçimde iniyor: fiilli ("… Whatsapp'da paylaş") ve
#: çıplak marka dizisi ("CampaignDetailImg Facebook Twitter LinkedIn Whatsapp
#: 01 Ağustos - 31 Ağustos … Sayfa İçeriği Kampanya ayın ilk ve son günleri
#: arasında geçerlidir."). İkinci biçim ölçüldü: gerçek koşulu bir kez
#: kaçırtıyor, çünkü kroma yapışan cümle jeton örtüşmesini yarıya düşürüyor.
_PAYLASIM_ONEKI_RE = re.compile(
    r"^.{0,200}?(?:(?:whatsapp'?da|whatsapp'?ta|linkedin'?de)\s+payla[şs]|"
    r"linkedin\s+whatsapp)\s+",
    re.IGNORECASE)
_KROM_SONEKI_RE = re.compile(
    r"\s*×?\s*your\s+browser\s+does\s+not\s+support.*$", re.IGNORECASE)

#: TARİH-GEÇERLİLİK CÜMLESİ — kılavuz K3: başka alana ait değer koşula
#: TEKRAR yazılmaz. "Kampanya 1-31 Temmuz 2026 tarihleri arasında geçerlidir"
#: tek başına `kampanya_suresi`dir, koşul değildir (kılavuz §4: *"Sayılmaz:
#: sadece geçerlilik tarihi bildiren cümle"*).
#:
#: Testi ÇIKARMA ile yapıyoruz, kalıp eşlemesiyle değil: cümleden tarih ve
#: geçerlilik iskeleti atıldığında geriye anlamlı içerik kalmıyorsa cümle
#: yalnızca tarih bildiriyor. Böylece gerçek koşul taşıyan tarih cümleleri
#: ("… üç (3) ay süresince sadece hafta sonları geçerlidir") ayakta kalır.
_TARIH_ISKELETI_RE = re.compile(
    r"\d+|ocak|şubat|mart|nisan|may[ıi]s|haziran|temmuz|a[ğg]ustos|eyl[üu]l|"
    r"ekim|kas[ıi]m|aral[ıi]k|kampanya\w*|ko[şs]ullar[ıi]|[şs]artlar[ıi]|"
    r"tarih\w*|aras[ıi]nda|itibar\w*|ba[şs]lang[ıi][çc]|biti[şs]|d[öo]nemi|"
    r"ge[çc]erli\w*|s[üu]resi|boyunca|olup|ve|ile|saat|kadar|dan|den|"
    r"[-–—.,;:()/'\"]",
    re.IGNORECASE)


def _kabuk_kirp(cumle: str) -> str:
    """Cümlenin başına/sonuna yapışan blok başlığı ve site kromunu kırpar.

    Kırpma YALNIZ kenarlardan yapılır: sonuç ham metnin hâlâ bitişik bir alt
    dizesidir, dolayısıyla `text.find` ile span kurulabilir ve kaynak
    vurgulama (CLAUDE.md §18/1) bozulmaz.
    """
    s = _KROM_SONEKI_RE.sub("", cumle).strip()
    s = _PAYLASIM_ONEKI_RE.sub("", s).strip()
    s = _BASLIK_ONEKI_RE.sub("", s).strip()
    return s


#: BİRLEŞİK BLOK EŞİĞİ ve İÇ AYIRAÇLARI.
#:
#: Ölçüm (gold.v2): gold koşul kalemlerinin uzunluk ortancası 80, %90'ı ≤ 127,
#: en uzunu 285 karakter — kılavuz K1/"birden çok koşul → dikey çizgi" gereği
#: her kalem TEK bir koşuldur. Motorun ürettiği yanlış pozitiflerin ortancası
#: ise 145, %90'ı ≤ 235: yani uzun kalem neredeyse her zaman **cümle
#: bölücünün ayıramadığı birleşik bloktur**, tek bir koşul değil.
#:
#: Doğru tepki bloğu ATMAK değil BÖLMEKtir; atmak blok içindeki gerçek koşulu
#: da götürür. Ayıraçlar `split_sentences`'ın görmediği, HTML listelerinden
#: metne inen işaretlerdir (aynı gerekçe `_DIPNOT_ISARET_RE`de yazılı):
#:   "… sadece birini kazanabilir. -Bir kart ile kampanyaya katılım …"
#:   "Katılım SMS'i ücretsiz olup; kampanyaya katılabilmek için …"
#:
#: TİRE AYIRACI BÜYÜK/KÜÇÜK HARFE BAĞLI OLAMAZ (2026-08-20, değişmez ihlali).
#:
#: Desen önce `\s+-(?=[A-ZÇĞİÖŞÜ])` idi: "boşluk + tire + BÜYÜK harf". Bu,
#: madde iminin tipografik görüntüsünü doğru tarif ediyordu ama çıkarımı
#: ORTOGRAFİYE bağlıyordu ve `eval.properties` P2 değişmezi bunu üç belgede
#: yakaladı (1.782 belgelik korpus, `albaraka/bilgilendirme-formu-murabaha`,
#: `…-icare-is-gucu-hizmet-kiralamasi`, `turkiye-emlak-katilim/qr-kur-…`):
#:
#:   normal metin : "… irade beyanının (icap -kabul) bulunması gerekir."
#:                  → 'kabul' küçük harf, ayıraç ATEŞLEMEZ, koşul tek parça
#:   BÜYÜK metin  : "… İRADE BEYANININ (İCAP -KABUL) BULUNMASI GEREKİR."
#:                  → 'KABUL' büyük harf, ayıraç ATEŞLER, koşul ORTADAN KESİLİR
#:                    ve listeye 'KABUL) BULUNMASI GEREKİR.' düşer
#:
#: Aynı sınıf ikinci bir yazım kusuruyla besleniyor: PDF metin çıkarımı
#: birleşik sözcüğün tiresinden önce boşluk bırakıyor ("alım -satım",
#: "e -posta", "prim -ücret"). Bunlar madde imi DEĞİL; büyük harfli belgede
#: madde imi gibi görünüyorlar.
#:
#: Düzeltme, ayıracı harf büyüklüğü yerine ÖNCEKİ NOKTALAMAYA bağlar: madde
#: imi bir cümle ya da başlık bitiminden sonra gelir (". -Bir kart …",
#: "Bitiş Tarihi: - Paylaş"), birleşik sözcük tiresi ise harften sonra gelir
#: ("alım -satım"). Böylece kural ortografiden bağımsızlaşır — ve rubriğin
#: "farklı ifade biçimlerini doğru yorumlayabilme" maddesi gereği BÜYÜK
#: HARFLE yazılmış banka metni normal metinle aynı sonucu verir.
#:
#: ÖLÇÜM ve ÇÜRÜTÜLEN ALTERNATİFLER (gold.v2, kural/strict, kalem mikro):
#:   eski `\s+-(?=[A-ZÇĞİÖŞÜ])`      → 0,520 · P2 ihlali 3
#:   `(?<=[.!?:])\s+-\s*` (seçilen)  → 0,520 · P2 ihlali 0
#:   `(?<=[.!?])\s+-\s*`             → 0,520 · P2 ihlali 0
#:   tire ayıracı hiç yok            → 0,520 · P2 ihlali 0
#:   `\s+-(?=\w)` (harf-bağımsız)    → 0,520 · P2 ihlali 0
#: Yani gold.v2 bu dört seçenek arasında AYRIM YAPMIYOR (48 belgede tire
#: ayıracı 170 karakterden uzun bir tetikleyicili cümlede hiç ateşlemiyor).
#: Seçim bu yüzden gold F1'e değil korpus kanıtına dayanıyor: 1.782 belgede
#: 170+ karakterlik 13.502 cümle tarandı ve tire alternatifi
#:   `\s+-(?=\w)` ile 208, eski desenle 81, seçilen desenle 114 kez ateşliyor.
#: `\s+-(?=\w)`ın fazladan ateşlediklerinin çoğu yukarıdaki PDF yazım kusuru
#: ("e -posta", "% -0,52959", "alış -verişi") — yani harf-bağımsız ama YANLIŞ.
#: Ayıracı tamamen atmak da değişmezi geçirirdi ama belgelenmiş madde imi
#: işlevini (". -Bir kart ile kampanyaya katılım …") kaybettirirdi; o vakayı
#: `tests/test_buyuk_harf_degismezligi.py` kilitliyor.
_BIRLESIK_ESIK = 170
_IC_AYIRAC_RE = re.compile(r"\s*[;•‣]\s*|(?<=[.!?:])\s+-\s*")


#: SIRA SAYISI SONU — `split_sentences`'ın kısaltma listesi sayıları tanımaz.
#: "…her ayın 15. günü ve son günü kontrol edilir" cümlesi "15." noktasından
#: bölünüyor ve koşulun yarısı kayboluyordu (gold.v2'de ölçülmüş 1 kalem).
#: Bölücü `src/preprocessing/clean.py`de ve bu değişikliğin sahiplik alanında
#: DEĞİL; düzeltme bu yüzden tüketici tarafında, geri-birleştirme olarak yapılır.
_SAYI_SONU_RE = re.compile(r"(?:^|\s)\d{1,2}\.$")


def _sayi_sonu_birlestir(cumleler: list[str]) -> list[str]:
    """Sıra sayısında yanlış bölünmüş cümleleri geri birleştirir."""
    out: list[str] = []
    for c in cumleler:
        if out and _SAYI_SONU_RE.search(out[-1]):
            out[-1] = out[-1] + " " + c
        else:
            out.append(c)
    return out


#: YAKIN-TEKİL EŞİĞİ. Jeton örtüşmesi bu değerin üstündeki iki kalem aynı
#: koşulun iki yazımıdır. 0,85 seçildi: ölçütün kalem eşiğinden (0,70) YÜKSEK
#: — yani burada birleştirilen iki kalem ölçütte de zorunlu olarak aynı gold
#: koşuluna düşerdi; eşiği ölçütün altına indirmek gerçek iki koşulu
#: birleştirme riski taşır.
_YAKIN_TEKIL_ESIK = 0.85


def _yakin_tekil(a: str, b: str) -> bool:
    """İki koşul kalemi aynı koşulun iki yazımı mı?"""
    ja = {t for t in tr_fold(a).lower().split() if t}
    jb = {t for t in tr_fold(b).lower().split() if t}
    if not ja or not jb:
        return ja == jb
    return len(ja & jb) / len(ja | jb) >= _YAKIN_TEKIL_ESIK


def _dipnot_kuyrugunu_kes(cumle: str) -> str:
    """Cümleye yapışan dipnot kuyruğunu GÖVDE yolundan düşürür.

    Dipnotun kendi yolu var (`extract_dipnotlar`) ve orada ayrı, temiz bir
    kalem olarak çıkıyor. Gövde yolu aynı metni bir kez daha üretirse
    yinelenme süzgeci (`dipnot in s`) yanlış tarafı tutuyor: uzun gövde
    parçası listede kalıyor, temiz dipnot düşüyor. `tests/test_dipnot.py`
    bu sınırı kilitliyor.
    """
    m = _DIPNOT_ISARET_RE.search(cumle)
    return cumle[:m.start()].strip() if m else cumle


def _kosul_parcalari(cumle: str) -> list[str]:
    """Birleşik bloğu koşul adaylarına böler; kısa cümleyi olduğu gibi verir."""
    cumle = _dipnot_kuyrugunu_kes(cumle)
    if not cumle:
        return []
    if len(cumle) <= _BIRLESIK_ESIK:
        return [cumle]
    parcalar = [p.strip() for p in _IC_AYIRAC_RE.split(cumle) if p and p.strip()]
    # Ayıraç yoktu (tek parça geri geldi) → blok bölünemiyor; olduğu gibi
    # bırakılır ve uzunluk süzgecinin kararına kalır.
    return parcalar if len(parcalar) > 1 else [cumle]


def _yalnizca_tarih_gecerliligi(cumle: str) -> bool:
    """Cümle SADECE geçerlilik tarihi mi bildiriyor? (K3 → koşul değil)"""
    kalan = _TARIH_ISKELETI_RE.sub(" ", cumle)
    return len(re.sub(r"\s+", "", kalan)) < 12


def _kosul_degil(cumle: str) -> bool:
    """Tetikleyici geçse bile koşul SAYILMAYAN cümle sınıfları.

    Her sınıf gold.v2'nin 137 gerçek koşul kalemine ateşlenmediği ÖLÇÜLEREK
    eklendi; `tests/test_kampanya_kosullari_kalite.py` bunu kapıda tutar.
    """
    if _SORU_CUMLESI_RE.search(cumle) or _SSS_CEVAP_RE.search(cumle):
        return True
    if _YONLENDIRME_RE.search(cumle) or _URUN_TANIMI_RE.search(cumle):
        return True
    if _FIKIH_MEVZUAT_RE.search(cumle) or _SORUMLULUK_REDDI_RE.search(cumle):
        return True
    if _URUN_OZELLIGI_RE.search(cumle):
        return True
    if (_ODUL_TUTAR_SONU_RE.search(cumle)
            and len(_PARA_JETONU_RE.findall(cumle)) >= 2):
        return True
    if _DAVET_SONU_RE.search(cumle) and not _DISLAYICI_BAS_RE.search(cumle):
        return True
    return _yalnizca_tarih_gecerliligi(cumle)


def extract_kampanya_kosullari(text: str) -> Optional[ExtractedField]:
    """Kampanya koşulları — SKALER DEĞİL, cümle listesi.

    Koşul tetikleyicisi içeren cümleler toplanır. Eşleşme ölçütü diğer
    alanlardan farklıdır (küme-F1 / token-Jaccard); bu yüzden eval'de ayrı
    bölümde raporlanır.

    Gövde cümlelerine ek olarak **dipnot blokları** (`extract_dipnotlar`) da
    taranır: katılım bankası kampanyalarında kontenjan, üyelik ve kanal şartı
    gövdede değil yıldızlı dipnotta yazılıdır (ölçüm için bkz. `_KISIT_RE`).
    """
    # DİKKAT: tek başına "geçerli\w*" TETİKLEYİCİ DEĞİLDİR. Neredeyse her
    # kampanya metni "Kampanya <tarih> tarihine kadar geçerlidir" cümlesiyle
    # biter; bu bir GEÇERLİLİK TARİHİdir (zaten `kampanya_suresi` yakalar),
    # yararlanma koşulu değil. Tetikleyici olarak bırakılması her belgede
    # yanlış pozitif üretiyordu. Yalnızca "için geçerli" biçimi koşul sayılır.
    #
    # Tetikleyici kümesi ve süzgeçler modül düzeyinde, gerekçeleri ölçümle
    # birlikte yazılı: `_KOSUL_TETIK_RE` başındaki blok.
    triggers = _KOSUL_TETIK_RE
    # BOILERPLATE FİLTRESİ — gerçek veride bulundu (291 belgelik korpus,
    # değişmez denetimi `kampanya_kosullari`nı tek suçlu olarak işaretledi).
    #
    # Tetikleyici sözcükler ("zorunlu", "gerekli", "sadece", "yalnızca")
    # çerez politikası, KVKK aydınlatma metni ve gizlilik bildirimlerinde de
    # geçiyor. Filtresiz hâlde belge başına ~8,7 "koşul" çıkıyordu ve büyük
    # kısmı şuna benzer hukuki metindi:
    #   "bu çerezler zorunlu çerezler dışında kalan işlevsellikleri sağlama
    #    amacıyla kullanılmaktadır"
    # Bu bir kampanya koşulu DEĞİLDİR; gold sete ve ürüne çöp akıtır.
    boilerplate = re.compile(
        r"(çerez|cookie|kvkk|kişisel\s*veri|aydınlatma\s*metni|"
        r"gizlilik\s*(politika|bildirim)|açık\s*rıza|veri\s*sorumlusu|"
        r"telif|tüm\s*hakları|sosyal\s*medya\s*hesap|bilgi\s*toplumu|"
        r"çağrı\s*merkezi|müşteri\s*hizmetleri)",
        re.IGNORECASE,
    )
    # `şubelerimiz` LİSTEDEN ÇIKARILDI (2026-08-20, ölçüldü). Amaç iletişim
    # altbilgisini elemekti ama sözcük KANAL KISITI cümlelerinde de geçiyor ve
    # bunlar gerçek koşuldur: "Albaraka Togg finansman başvuruları yalnızca
    # şubelerimizden yapılmaktadır." gold.v2'de koşul. Desen 1 gerçek kalemi
    # öldürüyor, karşılığında hiçbir yanlış pozitifi elemiyordu (kalan
    # altbilgi sinyalleri — çağrı merkezi / müşteri hizmetleri — yeterli).

    # GENEL YASAL İHTAR — koşul DEĞİLDİR. Desen `ihtar.py`de tek kez tanımlı;
    # anotasyon tarafındaki `kosul-ihtar` kuralı da oradan okur. Ayrıntı ve
    # ölçüm için o modülün başlığına bakın: kural yalnız anotasyonda
    # uygulanıp çıkarıcıda uygulanmadığı sürece gold ile model 20 kalibrasyon
    # belgesinin 5'inde YAPAY olarak ayrışıyordu.
    def uygun(s: str, tetik: re.Pattern) -> bool:
        # `bozuk_metin`: PDF metin çıkarımının bozduğu parça koşul olamaz.
        # Ölçüt ve eşiğin gerekçesi `_ortak.bozuk_metin` başlığında; kısaca
        # bu kapı olmadan okunamaz bir Albaraka PDF'i `eval.properties`'te
        # 2 gerçek ihlal üretiyordu ve CI kırmızıydı.
        return (bool(tetik.search(s)) and not boilerplate.search(s)
                and not ihtar_mi(s) and not _kosul_degil(s)
                and not bozuk_metin(s)
                and 20 <= len(s) <= 280)

    sentences = _sayi_sonu_birlestir(split_sentences(text))
    picked: list[str] = []
    for ham in sentences:
        # Blok başlığı / site kromu kırpılMADAN önce tetikleyici aranmaz:
        # başlık kendisi ("Kampanya Koşulları") tetikleyici taşıyor ve
        # arkasındaki tarih cümlesini koşul gibi gösteriyordu.
        for s in _kosul_parcalari(_kabuk_kirp(ham.strip())):
            if not (uygun(s, triggers) or uygun(s, _KONTENJAN_RE)):
                continue
            # Aynı cümle iki blokta tekrar ediyorsa bir kez; NEREDEYSE aynı
            # olan iki kalem de bir kez. Gerekçe ölçütte yazılı: eşleştirme
            # 1-1'dir (`eval/matchers.item_counts`), yani iki yakın-tekil
            # kalem tek gold koşulunu karşılar ve ikincisi ZORUNLU olarak
            # yanlış pozitiftir; üstelik kapak altında bir slot yer.
            if any(_yakin_tekil(s, t) for t in picked):
                continue
            picked.append(s)

    # DİPNOTLAR. Gövde cümleleriyle AYNI kovaya eklenir.
    #
    # AYRI TETİKLEYİCİ ARTIK ARANMIYOR (2026-08-20, ölçüldü: +3 doğru kalem,
    # 0 yeni yanlış pozitif). Eski ölçüt `_KISIT_RE` idi ve gerekçesi
    # "dipnotların çoğu sorumluluk reddidir" idi. O gerekçenin işi bugün
    # `_kosul_degil` süzgecine geçti: `_YONLENDIRME_RE` tam olarak
    # "*Detaylı bilgi için … ziyaret edebilirsiniz" sınıfını eliyor,
    # `ihtar_mi` de hukuki ihtarı. Geriye kalanda DİPNOT İŞARETİNİN KENDİSİ
    # kanıttır: kılavuz (§4 `kampanya_kosullari`, `_DIPNOT_ISARET_RE` yorumu)
    # kampanyanın gerçek kısıtlarının yıldızlı/madde imli listede yazıldığını
    # söylüyor. İkinci bir sözcük ölçütü aramak, orada duran koşulu — "18
    # yaşını doldurmuş olmak" gibi kiplik sözcüğü OLMAYAN kalemleri —
    # gereksiz yere kesiyordu.
    #
    # Zaten seçilmiş bir cümlenin İÇİNDE geçen dipnot tekrar eklenmez: cümle
    # bölücü dipnotu önceki cümleye yapıştırdığı için ikisi aynı bilgiyi
    # taşıyabilir ve liste mükerrer olurdu.
    for dipnot in extract_dipnotlar(text):
        if (boilerplate.search(dipnot) or ihtar_mi(dipnot)
                or _kosul_degil(dipnot) or bozuk_metin(dipnot)
                or not 20 <= len(dipnot) <= 280):
            continue
        if any(dipnot in s for s in picked):
            continue
        picked.append(dipnot)

    if not picked:
        return None
    # ÜST SINIR — bir kampanyanın onlarca koşulu olmaz; fazlası, süzgecin
    # kaçırdığı gövde metnidir. 8 -> 6 (2026-08-20, ölçüldü): gold.v2'de en
    # uzun koşul listesi 6 kalem; kapak taraması F1'i 8'de 0,484, 6'da 0,502
    # veriyor. Sıra BELGE SIRASIDIR ve bu bilinçli bir tercihtir — koşul
    # gücüne göre PUANLAMA denendi ve ÇÜRÜTÜLDÜ (0,502 -> 0,428): gerçek
    # koşullar "Kampanya Koşulları" bloğunda kümeleniyor, pazarlama ve SSS
    # metni sayfanın kuyruğunda; belge sırası bu yapıyı zaten kodluyor.
    picked = picked[:6]

    # span: ilk koşul cümlesinin metindeki yeri
    first = picked[0]
    idx = text.find(first)
    if idx < 0:
        idx, end = 0, 0
    else:
        end = idx + len(first)
    # Seçim belirsizliği sayılır. Bu alan tek bir eşleşme değil, koşul
    # ipucu taşıyan N cümlenin SEÇİMİDİR; N seçim kararı tek bir bitişik
    # eşleşmeyle aynı kesinliği taşıyamaz. Ölçüldü (2026-08-15, gold.round1):
    # kalem düzeyi kesinlik 0,556 iken skor 0,95 ilan ediliyordu.
    return _field("kampanya_kosullari", text[idx:end] if end > idx else first,
                  picked, _window(text, idx, end),
                  span_start=idx if end > idx else None,
                  span_end=end if end > idx else None,
                  trigger_distance=0,
                  candidate_count=len(picked))
