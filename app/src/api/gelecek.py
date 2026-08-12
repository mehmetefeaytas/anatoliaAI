"""Gelecek faz uçlarının SÖZLEŞMESİ — tanımlı, çalışmıyor, sahte cevap vermiyor.

İlgili: ./main.py (`/admin/*` uçları), ../../web/app/components/AyarlarPanel.tsx
        ../scraping/config.py (`banks.yaml` — bugünkü banka ekleme yolu)
        CLAUDE.md §13 (config-driven banka onboarding), §18 #3, §21

## Ne için var

Sistemin bir sonraki fazında — **yakın dönem, bir iş birliği durumunda** —
bankaların kampanyaları ve finansal ürünleri arayüzden eklenebilecek. Bu dosya
o uçların adreslerini, gövde alanlarını, ZAMAN ÇERÇEVESİNİ ve kapalı olma
gerekçelerini TEK YERDE tanımlar; `main.py` uçları buradan kurar ve
`AyarlarPanel` listeyi `/admin/plan`'dan okur.

Sözleşmeyi arayüzde ikinci kez yazmak, bu projede altı kez tekrarlayan «aynı
bilgi iki yerde» kusuruna yeni bir örnek eklerdi: uçlar değiştiğinde ekran
eskisini göstermeye devam ederdi ve kimse fark etmezdi.

## Neden ÇALIŞMIYOR — ve neden bu bilinçli bir karar

Üç ayrı gerekçe, üçü de mimarinin merkezinde:

1. **Kanıt zinciri.** Korpustaki her belge ham HTML + toplama zamanı + kaynak
   adresiyle (provenance) birlikte duruyor; çıkarılan her alan o metindeki bir
   karakter aralığına bağlı (`span_start`/`span_end`). Arayüzden elle girilen
   bir kampanya metninin kaynağı yoktur. Onu doğrudan `campaigns`'e yazmak,
   doğrulanmış zincire doğrulanmamış bir halka eklemek olurdu — özetlerin
   ölçüm yollarına sokulmama gerekçesiyle aynı (`src/summarize/ozet.py`).

2. **Ölçümün bütünlüğü.** Gold küme ve P/R/F1 ölçümleri korpusun içeriğine
   dayanıyor. Ölçüm koşusuyla arayüzden veri girişi arasında bir kilit yokken,
   kimin neyi ne zaman eklediği bilinmeden yapılan bir ölçüm tekrar
   üretilemez (CLAUDE.md §16).

3. **Yetkilendirme.** Yazma uçlarının kimlik doğrulaması yok. Sistem
   internetsiz ve tek operatörlü çalışacak biçimde tasarlandı; açık bir yazma
   ucu o varsayımı sessizce bozar.

Bugünkü doğru yol banka eklemek için hâlâ `config/banks.yaml`'dır: tek satır
ekleyip tazelemek (CLAUDE.md §13, §18 #3). Bu uçlar o yolu DEĞİŞTİRMEZ,
üstüne bir ekran koyar.

## Neden 501, neden 404 değil ve neden sahte 200 değil

* **Sahte 200** en kötüsü: operatör kampanyayı eklediğini sanır, veri hiçbir
  yere yazılmaz ve kayıp ancak demoda fark edilir.
* **404** yolun hiç var olmadığını söyler — doğru değil, sözleşme tanımlı.
* **501 Not Implemented** tam olarak durumu anlatır: uç tanımlı, davranış
  henüz uygulanmadı. Yanıt gövdesi gerekçeyi ve bugünkü alternatifi taşır.
"""

from __future__ import annotations

from typing import Any

#: NE ZAMAN açılacağı — ekranın en üstünde, kaçırılamayacak bir ağırlıkla
#: duran cümle. Eskiden hiçbir yerde yazmıyordu: ekran yalnızca "gelecek faz"
#: diyordu ve "gelecek faz" bir takvim değil, bir erteleme gibi okunuyordu.
#: Bu uçlar bir ürün yol haritası maddesi değil, bir İŞ BİRLİĞİ koşuludur —
#: bankanın kendi verisini girmesi ancak o ilişki kurulduğunda anlamlıdır.
ZAMAN_CERCEVESI = "Yakın dönem / iş birliği durumunda"

#: Ekranın en büyük punto cümlesi — takvimi söyler. Arayüzde SABİT YAZILMAZ,
#: buradan okunur: başlık ile gerekçe iki ayrı yerde yaşasaydı, biri
#: değiştiğinde diğeri eski ifadeyi göstermeye devam ederdi (bu depoda altı
#: kez tekrarlayan kusur).
KAPALI_BASLIK = f"{ZAMAN_CERCEVESI} açılacak"

#: Başlığın üstündeki küçük durum etiketi. Takvim ile DURUM ayrı iki bilgidir:
#: "ne zaman" büyük puntoda, "şu an ne" küçük puntoda.
KAPALI_DURUM_ETIKETI = "Bu sürümde kapalı"

#: Ekranda ve `/admin/plan` yanıtında görünen tek gerekçe metni. `main.py`'nin
#: 501 gövdesi de bunu kullanır — iki metin ayrışırsa ekran ile sunucu farklı
#: sebep söyler.
KAPALI_SEBEBI = (
    # Vurgu büyük harfle YAPILMAZ: "YAKIN" harf katlamada (casefold) "yakin"
    # olur — Türkçe İ/ı tuzağı — ve cümleyi arayan denetim/arama yolları
    # ıskalar. Aynı ders korpus tarafında da ölçülmüştü (ALL-CAPS başlıklar).
    "Bu uç yakın dönem için tanımlı ve bir iş birliği durumunda açılacak; "
    "bu sürümde kapalı. Arayüzden elle "
    "girilen bir kayıt, korpustaki her belgenin taşıdığı kaynak zincirini "
    "(ham sayfa + toplama zamanı + kaynak adresi + karakter aralığı) "
    "taşımadığı için ölçüm yollarına giremez. Bugün banka ve kampanya ekleme "
    "yolu `config/banks.yaml` dosyasına satır eklemek ve o bankayı "
    "tazelemektir."
)

#: Bugün geçerli olan alternatif — ekranda gerekçenin yanında gösterilir.
BUGUNKU_YOL = "config/banks.yaml + Veri Tazeleme sekmesi"


def _alan(ad: str, tip: str, zorunlu: bool, aciklama: str) -> dict[str, Any]:
    return {"ad": ad, "tip": tip, "zorunlu": zorunlu, "aciklama": aciklama}


#: Gelecek faz uçlarının tam sözleşmesi. Arayüz bu listeyi olduğu gibi çizer.
UCLAR: tuple[dict[str, Any], ...] = (
    {
        "yol": "/admin/banks",
        "yontem": "POST",
        "baslik": "Banka ekle",
        "ozet": "Yeni bir katılım bankasını sisteme tanıtır; bugün "
                "`config/banks.yaml` dosyasına karşılık gelir.",
        "alanlar": (
            _alan("slug", "metin", True,
                  "Dosya ve URL'lerde kullanılan kısa ad (ör. `ornek-katilim`)."),
            _alan("name", "metin", True, "Bankanın görünen tam adı."),
            _alan("website_url", "url", True, "Kurumsal site kök adresi."),
            _alan("campaign_paths", "metin listesi", True,
                  "Kampanya liste sayfalarının yolları."),
            _alan("scrape_mode", "static | browser", False,
                  "Sayfalar JavaScript ile mi çiziliyor."),
            _alan("bddk_active", "evet/hayır", False,
                  "BDDK Liste 77'de faal görünüyor mu."),
        ),
    },
    {
        "yol": "/admin/banks/{slug}/campaigns",
        "yontem": "POST",
        "baslik": "Kampanya ekle",
        "ozet": "Tek bir kampanya belgesini elle ekler. Çıkarım katmanı "
                "metni normal akıştaki gibi işler.",
        "alanlar": (
            _alan("title", "metin", True, "Kampanyanın başlığı."),
            _alan("source_url", "url", True,
                  "Metnin alındığı sayfa — kanıt zincirinin ilk halkası."),
            _alan("raw_text", "uzun metin", True, "Kampanya metninin tamamı."),
            _alan("campaign_type", "8 türden biri", False,
                  "Boş bırakılırsa sınıflandırıcı belirler."),
            _alan("scraped_at", "ISO tarih", False,
                  "Metnin alındığı an; boşsa ekleme anı yazılır."),
        ),
    },
    {
        "yol": "/admin/banks/{slug}/products",
        "yontem": "POST",
        "baslik": "Finansal ürün ekle",
        "ozet": "Kampanya değil, sürekli bir ürün kaydı (konut finansmanı, "
                "katılma hesabı, kart). Kampanyalardan ayrı tutulur çünkü "
                "süresi ve kıyas kuralları farklıdır.",
        "alanlar": (
            _alan("name", "metin", True, "Ürünün adı."),
            _alan("product_type", "8 türden biri", True, "Ürün ailesi."),
            _alan("source_url", "url", True, "Ürün sayfası."),
            _alan("kar_payi_orani", "oran", False, "Örn. 2,05."),
            _alan("vade_ay", "tam sayı ya da aralık", False, "Ay cinsinden."),
            _alan("finansman_tutari", "tutar", False, "TRY."),
            _alan("kosullar", "uzun metin", False, "Ürünün başlıca koşulları."),
        ),
    },
)


def plan() -> dict[str, Any]:
    """`/admin/plan` yanıtı — arayüzün çizdiği sözleşmenin tamamı."""
    return {
        "acik": False,
        "baslik": KAPALI_BASLIK,
        "durum_etiketi": KAPALI_DURUM_ETIKETI,
        "sebep": KAPALI_SEBEBI,
        "bugunku_yol": BUGUNKU_YOL,
        "uclar": [
            {**uc, "alanlar": list(uc["alanlar"])} for uc in UCLAR
        ],
    }
