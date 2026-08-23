"""Bir dakikalık sürüm için panelin her ekranını AYRI ve KISA kaydeder.

## Neden beş dakikalık sürümün kayıtları kullanılmıyor

Orada üç ekran tek sahnede geçiyor (En Avantajlı → Banka → Delta ve
Tazeleme → Günlük → Ayarlar). Bir dakikalık sürümde her ekranın kendi etiketi
ve kendi anlatım cümlesi var; tek kayıttan üç sahne kesmek, kesme noktasını
saniyenin onda birine bağlamak olurdu. Ekran başına bir kayıt bu bağı koparır.

## Kadraj: uzun viewport, montajda ikiye bölünür

`duzen: cift` sahneleri 1280×2304 gibi UZUN bir pencerede kaydedilir. Montaj
bu kareyi ortadan bölüp yan yana koyuyor, yani tek karede iki ekran dolusu
içerik oluyor. Kayıt tarafında bunun iki sonucu var: kaydırma paylarının
çoğu gereksizleşiyor (sayfanın 2300 pikseli zaten görünüyor) ve ekranın
"altı" diye bir şey kalmıyor — bölümü kadraja almak için biraz kaydırmak
yetiyor.

Geniş matrisler (ısı haritası) bölünmeye uygun olmadığı için `duzen: tek`
ile klasik 16:9 penceresinde kaydedilir.

## Veriler korpusun DOLU olduğu yerden seçilir

Boş bir tablo sistemin çalışmadığını değil, o kesişimde belge olmadığını
gösterir — ama üç saniyelik bir sahnede kimse bu ayrımı yapmıyor. Bu yüzden
her ekran ölçülmüş en dolu kesişime ayarlanır: karşılaştırma `vade × Finansman`
(9 banka, 9'u da kıyaslanabilir), banka sayfası Kuveyt Türk (885 belge, 12
alan), ürün tablosu ve En Avantajlı `Kart` türünde (9 banka). Değerler
`/compare` ve `/stats` uçları taranarak seçildi, göz kararı değil.

## Kayıtlar hedeften uzun

Montaj her sahneyi anlatım süresine oturtuyor; kaynak kısa kalırsa son kare
donuyor. Bu yüzden her sahne 6-9 saniye kaydedilir, montaj gerekeni alır.

## Çıkarım tek kayıt, iki sahne

`02-cikarim` içinde metin yazılıyor, düğmeye basılıyor, yerel model gerçekten
çağrılıyor. Bir dakikalık sürümde o bekleme kesiliyor: kaydın BAŞI «metin
girdisi» sahnesi, SONU «yapılandırılmış çıktı» sahnesi oluyor (senaryo-60.json
içindeki `yer` alanı). Aradaki yirmi saniye videoya hiç girmiyor.
"""

import asyncio
import json
import pathlib
import shutil
import sys

from playwright.async_api import Page, async_playwright

from sahne_ortak import (
    IMLEC_BETIK,
    ORNEK_METIN,
    bekle,
    cikarimi_bekle,
    imleci_tasi,
    kadraja_al,
    kaydir,
    sekmeye_git,
    sonuca_kaydir,
    tikla,
)

KOK = pathlib.Path(__file__).parent
SENARYO = json.loads((KOK / "senaryo-60.json").read_text(encoding="utf-8"))
SAHNE_DIZIN = KOK / "sahne-60"
HAM_DIZIN = SAHNE_DIZIN / "ham"
V = SENARYO["video"]

#: Kayıt penceresi düzene göre değişir. Çift sütun düzeninde pencere iki sütun
#: yüksekliğinde açılır; montaj o kareyi ortadan bölecek.
PENCERE = {
    "tek": (V["kayit_en"], V["kayit_boy"]),
    "cift": (V["sutun_en"], V["sutun_boy"] * 2),
    # «yan» sahnelerde iki AYRI kaydın üst yarıları yan yana konuyor; kayıt
    # yine sütun genişliğinde açılır, montaj alt yarıyı kullanmaz.
    "yan": (V["sutun_en"], V["sutun_boy"] * 2),
}

#: Hangi kaydın hangi düzende çekileceğini senaryo söyler — iki dosyada iki
#: ayrı liste tutmak, birini güncelleyip ötekini unutmak demekti.
DUZENLER = {
    kaynak: sahne.get("duzen", "tek")
    for sahne in SENARYO["sahneler"] if sahne["tur"] == "panel"
    for kaynak in sahne.get("kaynaklar", [sahne.get("kaynak")])
}


async def alan_sec(sayfa: Page, ad: str) -> None:
    """Karşılaştırmanın konusu olan alanı seçer.

    Alan çipleri ARIA sekmesi (`FieldChips.tsx`), düğme değil.
    """
    await tikla(sayfa, sayfa.get_by_role("tab", name=ad, exact=True).first,
                once=250, sonra=900)


async def tur_suzgeci(sayfa: Page, tur: str, sira: int = 1) -> None:
    """Ekranı tek bir ürün ailesine alır.

    Süzgeç «Tümü» kaldığında ilk bölüm «türü belirlenemedi» oluyor: sıralama
    doğru ama başlık jüriye sistemin türü bulamadığını söylüyor. Tür ayrıca
    korpusun DOLU olduğu yerden seçilir — boş bir tablo üç saniyede
    "çalışmıyor" diye okunuyor.
    """
    try:
        await sayfa.locator("select").nth(sira).select_option(label=tur)
        await bekle(sayfa, 1000)
    except Exception as hata:  # noqa: BLE001
        print("   ! süzgeç atlandı:", str(hata).split("\n")[0][:80])


async def s01_panel(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "compare", 2600)
    # Açılışta varsayılan «kâr payı · türü belirlenemedi» bölümü geliyor ve
    # sağ sütun «ölçülemedi · 8 banka» listesiyle doluyordu. Panelin ilk
    # görüntüsü de dolu bir kesişimden seçiliyor.
    await alan_sec(sayfa, "Vade (ay)")
    await tur_suzgeci(sayfa, "Finansman")
    await imleci_tasi(sayfa, 640, 300)          # sağlık şeridi
    await bekle(sayfa, 1400)
    await kaydir(sayfa, 240, 900)
    await bekle(sayfa, 1500)
    await kaydir(sayfa, 0, 800)
    await bekle(sayfa, 1400)


async def s02_cikarim(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "extract", 1800)
    await tikla(sayfa, sayfa.get_by_text("Kendi metninizi deneyin", exact=False).first,
                once=300, sonra=600)
    kutu = sayfa.locator("#zv-serbest-metin")
    # Kutu SOL sütunun üstüne konumlanıyor: yazma orada görünürken çıkarım
    # sonucu aşağıda, yani sağ sütunda açılıyor.
    await kadraja_al(sayfa, kutu, pay=320, bekleme=700)
    await kutu.click()
    await kutu.type(ORNEK_METIN, delay=14)      # yazılışı görünsün
    await bekle(sayfa, 700)
    await tikla(sayfa, sayfa.get_by_role("button", name="Serbest metinde çalıştır"),
                once=300, sonra=300)
    await cikarimi_bekle(sayfa, "Serbest metinde çalıştır")
    await bekle(sayfa, 600)
    # Sonuç künyesi solda, alan tablosunun tamamı sağda kalacak biçimde.
    await kadraja_al(sayfa, sayfa.get_by_role("heading", name="Sonuç").first,
                     pay=200, bekleme=2600)
    # Sonucu sol sütunun BAŞINA taşır: kesit kaydın sonundan alındığı için
    # sahnenin gösterdiği kadraj bu son kaydırmadır.
    await sayfa.evaluate("window.scrollBy({top: 760, behavior: 'smooth'})")
    await bekle(sayfa, 3000)


async def s04_zor_vaka(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "extract", 1800)
    await kaydir(sayfa, 240, 700)
    await tikla(sayfa, sayfa.get_by_role("button", name="Koşullu / aralıklı (12)"),
                once=300, sonra=500)
    # Altın kümesinde değeri OLAN kart seçiliyor; boş kartta sonuç tablosunun
    # her satırı «altında yok» oluyor ve yan yana karşılaştırma kalmıyor.
    dolu = sayfa.locator(".zv-vaka", has_text="altında 5 değer")
    kart = dolu.first if await dolu.count() else sayfa.locator(".zv-vaka").first
    await tikla(sayfa, kart, once=300, sonra=700)
    await tikla(sayfa, sayfa.get_by_role("button", name="Çıkarımı çalıştır"),
                once=300, sonra=300)
    await cikarimi_bekle(sayfa, "Çıkarımı çalıştır")
    await bekle(sayfa, 600)
    # Sahnenin işi karşılaştırmanın SAYIMI: kaç alan eşleşti, kaç uydurma,
    # kaç doğru boşluk. Blok solda, altındaki sonuç tablosu sağda kalıyor.
    if not await kadraja_al(
        sayfa, sayfa.get_by_role("heading", name="Model çıktısı").first,
        pay=220, bekleme=3400,
    ):
        await sonuca_kaydir(sayfa)
        await bekle(sayfa, 3000)


async def s05_kanit(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "audit", 2200)
    await kaydir(sayfa, 200, 600)
    # Kuveyt Türk korpusun en dolu bankası (885 belge, 12 alan): kanıt zinciri
    # satırları dolu geliyor.
    await tikla(sayfa, sayfa.get_by_role("button", name="Kuveyt Türk").first,
                once=300, sonra=800)
    await kaydir(sayfa, 900, 900)
    await bekle(sayfa, 3200)


async def s06_karsilastirma(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "compare", 2400)
    await kaydir(sayfa, 300, 700)
    # `vade × Finansman` ölçülmüş en dolu kesişim: dokuz banka dolu ve
    # dokuzu da kıyaslanabilir. Kâr payı × Konut Finansmanı yalnız ikisiydi.
    await alan_sec(sayfa, "Vade (ay)")
    await tur_suzgeci(sayfa, "Finansman")
    await kaydir(sayfa, 620, 900)
    await bekle(sayfa, 3400)


async def s07_urun_tablosu(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "compare", 2400)
    await kaydir(sayfa, 300, 700)
    await tur_suzgeci(sayfa, "Kart")     # Kart: dokuz bankada dolu
    await tikla(sayfa, sayfa.locator("label", has_text="Ürün tablosu").first,
                once=300, sonra=1400)
    await kaydir(sayfa, 560, 900)
    await bekle(sayfa, 3000)


async def s08_isi(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "isi", 2200)
    try:
        # «Kampanya Süresi» 1.179 kayıtla dolu görünüyor ama haritada 0/99
        # hücre veriyordu: harita KIYASLANABİLİR değerleri sayıyor, tarih
        # alanı sıralamaya girmiyor. Vade her ürün ailesinde ölçülüyor.
        await sayfa.locator("#isi-alan").select_option(label="Vade (ay)")
        await bekle(sayfa, 1200)
    except Exception as hata:  # noqa: BLE001
        print("   ! ısı alanı atlandı:", str(hata).split("\n")[0][:80])
    await kaydir(sayfa, 470, 900)
    await bekle(sayfa, 3400)


async def s09_avantajli(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "advantageous", 2200)
    await tur_suzgeci(sayfa, "Kart", sira=0)
    await kaydir(sayfa, 420, 900)
    await bekle(sayfa, 3400)


async def s10_banka(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "banka", 2200)
    try:
        # Varsayılan banka listenin ilki (Adil Katılım, 11 belge): ekran
        # baştan sona «bu türde belge yok» diyordu.
        await sayfa.locator("#banka-secici").select_option(label="Kuveyt Türk")
        await bekle(sayfa, 1400)
    except Exception as hata:  # noqa: BLE001
        print("   ! banka seçimi atlandı:", str(hata).split("\n")[0][:80])
    await kaydir(sayfa, 380, 900)
    await bekle(sayfa, 3400)


async def s11_delta(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "delta", 2200)
    try:
        await sayfa.locator("#delta-bank").select_option(label="Kuveyt Türk")
        await bekle(sayfa, 1400)
    except Exception as hata:  # noqa: BLE001
        print("   ! delta bankası atlandı:", str(hata).split("\n")[0][:80])
    await kaydir(sayfa, 520, 900)
    await bekle(sayfa, 3400)


async def s12_celiski(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "contradictions", 2200)
    await kaydir(sayfa, 400, 800)
    # DOM'daki yazı küçük harfli; ekrandaki büyük harf CSS'ten geliyor.
    await tikla(sayfa, sayfa.get_by_text("bankanın kendi ifadesi", exact=False).first,
                once=300, sonra=1600)
    await kaydir(sayfa, 700, 900)
    await bekle(sayfa, 3000)


async def s13_chatbot(sayfa: Page) -> None:
    """Chatbotun İKİ yolu da tek sahnede: yapısal sorgu ve belge erişimi.

    Hazır sorulardan ilki sayısal — yönlendirici onu text-to-SQL'e atıyor.
    Takip sorusu koşul soruyor, o da belge erişimli üretime düşüyor; rozet
    ikisinde farklı yazıyor. Çift sütunda ilk cevap ve kaynakları solda,
    ikinci cevap sağda kalıyor.
    """
    await sekmeye_git(sayfa, "chat", 2200)
    await kaydir(sayfa, 340, 700)
    # SIRA ÖNEMLİ: koşul sorusu önce sorulur, çünkü bağlamı boş bir turda
    # belge erişimine düşüyor. Ters sırada ikinci soru önceki turun alanını
    # (`vade_ay`) devralıyor — «Yeni konu» bile bu devri kesmiyor — ve o da
    # yapısal sorguya gidiyordu: ekranda aynı rozet iki kez çıkıyor, oysa
    # sahnenin iddiası iki AYRI yol. Sayısal soru ise bağlam devralsa da
    # yapısal kalıyor, yani bu sırada iki yol da garanti görünüyor.
    await tikla(sayfa, sayfa.get_by_role("button",
                name="Konut finansmanı kampanyasının koşulları neler?"),
                once=300, sonra=1200)
    await cikarimi_bekle(sayfa, "Sor")
    await bekle(sayfa, 2200)
    await tikla(sayfa, sayfa.get_by_role("button",
                name="En yüksek vade veren banka hangisi?"),
                once=250, sonra=1200)
    await cikarimi_bekle(sayfa, "Sor")
    await bekle(sayfa, 2400)
    await kaydir(sayfa, 700, 900)
    await bekle(sayfa, 3200)


async def s14_operasyon(sayfa: Page) -> None:
    """Üç operasyon ekranı tek sahnede: montaj bunu hızlandırarak gösterir.

    Sekmeler arasında `goto` ile gezmek sayfayı her seferinde yeniden yükletti
    ve üç kat hızlandırılmış kayıtta son ekran «alan listesi yükleniyor»
    iskeletine denk geldi. Sekme düğmesine tıklamak uygulama içinde kalıyor:
    geçiş anında oluyor, ekran hazır görünüyor.

    Sekme şeridi ARIA sekme deseni kullanıyor (`role="tab"`, bkz.
    `app/web/app/components/ui/Tabs.tsx`); `button` rolüyle aranınca
    bulunamıyor ve sahne sessizce `goto` yedeğine düşüyordu.
    """
    await sekmeye_git(sayfa, "tazele", 2600)
    await kaydir(sayfa, 320, 800)
    await bekle(sayfa, 1300)
    for sekme_adi, yedek in (("İşlem Günlüğü", "gunluk"), ("Ayarlar", "ayarlar")):
        dugme = sayfa.get_by_role("tab", name=sekme_adi, exact=True).first
        if not await tikla(sayfa, dugme, once=250, sonra=1600):
            await sekmeye_git(sayfa, yedek, 2200)
        await kaydir(sayfa, 300, 700)
        await bekle(sayfa, 1300)
    await bekle(sayfa, 1200)


SAHNELER = {
    "01-panel": s01_panel,
    "02-cikarim": s02_cikarim,
    "04-zor-vaka": s04_zor_vaka,
    "05-kanit": s05_kanit,
    "06-karsilastirma": s06_karsilastirma,
    "07-urun-tablosu": s07_urun_tablosu,
    "08-isi-haritasi": s08_isi,
    "09-avantajli": s09_avantajli,
    "10-banka": s10_banka,
    "11-delta": s11_delta,
    "12-celiski": s12_celiski,
    "13-chatbot": s13_chatbot,
    "14-operasyon": s14_operasyon,
}


async def main() -> None:
    SAHNE_DIZIN.mkdir(exist_ok=True)
    HAM_DIZIN.mkdir(parents=True, exist_ok=True)
    istenen = sys.argv[1:] or list(SAHNELER)
    async with async_playwright() as p:
        tarayici = await p.chromium.launch(args=["--force-color-profile=srgb"])
        for ad, islev in ((a, SAHNELER[a]) for a in istenen):
            en, boy = PENCERE[DUZENLER.get(ad, "tek")]
            baglam = await tarayici.new_context(
                viewport={"width": en, "height": boy},
                record_video_dir=str(HAM_DIZIN),
                record_video_size={"width": en, "height": boy},
                locale="tr-TR",
                timezone_id="Europe/Istanbul",
                reduced_motion="no-preference",
            )
            await baglam.add_init_script(IMLEC_BETIK)
            sayfa = await baglam.new_page()
            print(f"» {ad}  ({en}×{boy})")
            try:
                await islev(sayfa)
            except Exception as hata:  # noqa: BLE001
                print("   !! sahne hatası:", str(hata).split("\n")[0][:120])
            yol = await sayfa.video.path()
            await baglam.close()
            hedef = SAHNE_DIZIN / f"{ad}.webm"
            shutil.move(yol, hedef)
            print(f"   kaydedildi: {hedef.name}")
        await tarayici.close()


asyncio.run(main())
