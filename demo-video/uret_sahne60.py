"""Bir dakikalık sürüm için panelin her ekranını AYRI ve KISA kaydeder.

## Neden beş dakikalık sürümün kayıtları kullanılmıyor

Orada üç ekran tek sahnede geçiyor (En Avantajlı → Banka → Delta ve
Tazeleme → Günlük → Ayarlar). Bir dakikalık sürümde her ekranın kendi etiketi
ve kendi anlatım cümlesi var; tek kayıttan üç sahne kesmek, kesme noktasını
saniyenin onda birine bağlamak olurdu. Ekran başına bir kayıt bu bağı koparır.

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
    kaydir,
    sekmeye_git,
    sonuca_kaydir,
    tikla,
)

KOK = pathlib.Path(__file__).parent
SENARYO = json.loads((KOK / "senaryo-60.json").read_text(encoding="utf-8"))
SAHNE_DIZIN = KOK / "sahne-60"
HAM_DIZIN = SAHNE_DIZIN / "ham"
EN, BOY = SENARYO["video"]["kayit_en"], SENARYO["video"]["kayit_boy"]


async def s01_panel(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "compare", 2000)
    await imleci_tasi(sayfa, 700, 292)          # sağlık şeridi
    await bekle(sayfa, 1300)
    await kaydir(sayfa, 210, 800)
    await bekle(sayfa, 1200)
    await kaydir(sayfa, 0, 800)
    await bekle(sayfa, 1400)


async def s02_cikarim(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "extract", 1800)
    await tikla(sayfa, sayfa.get_by_text("Kendi metninizi deneyin", exact=False).first,
                once=300, sonra=600)
    kutu = sayfa.locator("#zv-serbest-metin")
    await kutu.scroll_into_view_if_needed()
    # `scroll_into_view` kutuyu ekranın en altına yapıştırıyor: yazılan metin
    # kadranın kenarında kalıyordu. Biraz daha kaydırmak kutuyu ortaya alır.
    await sayfa.evaluate("window.scrollBy({top: 240, behavior: 'smooth'})")
    await bekle(sayfa, 700)
    await kutu.click()
    await kutu.type(ORNEK_METIN, delay=14)      # yazılışı görünsün
    await bekle(sayfa, 700)
    await tikla(sayfa, sayfa.get_by_role("button", name="Serbest metinde çalıştır"),
                once=300, sonra=300)
    await cikarimi_bekle(sayfa, "Serbest metinde çalıştır")
    await bekle(sayfa, 600)
    await sonuca_kaydir(sayfa)
    await bekle(sayfa, 2400)
    # Künye kartlarından alan tablosuna geç: bir dakikalık sürümde bu sahnenin
    # işi «hangi alan, hangi değer, hangi güven» satırlarını göstermek.
    await sayfa.evaluate("window.scrollBy({top: 620, behavior: 'smooth'})")
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
    # Sonuç tablosunun ilk satırları «altında yok» ile başlıyor; üç saniyede
    # gösterilecek şey o değil, karşılaştırmanın SAYIMI: kaç alan eşleşti, kaç
    # uydurma, kaç doğru boşluk. Kadraj o bloğa alınıyor.
    try:
        ozet = sayfa.get_by_role("heading", name="Model çıktısı").first
        await ozet.scroll_into_view_if_needed(timeout=5000)
        # `scroll_into_view` başlığı ekranın en ALTINA getiriyor; sayım kartları
        # onun altında kalıyor ve kadraja hiç girmiyordu.
        await sayfa.evaluate("window.scrollBy({top: 320, behavior: 'smooth'})")
    except Exception:  # noqa: BLE001
        await sonuca_kaydir(sayfa)
    await bekle(sayfa, 3200)


async def s05_kanit(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "audit", 1900)
    await kaydir(sayfa, 200, 600)
    await tikla(sayfa, sayfa.get_by_role("button", name="Kuveyt Türk").first,
                once=300, sonra=600)
    await kaydir(sayfa, 1250, 900)
    await bekle(sayfa, 3000)


async def tur_suzgeci(sayfa: Page, tur: str = "Konut Finansmanı") -> None:
    """Karşılaştırmayı somut bir ürün ailesine alır.

    Süzgeç «Tümü» kaldığında ekranın ilk bölümü «türü belirlenemedi» oluyor:
    sıralama doğru ama başlık jüriye sistemin türü bulamadığını söylüyor.
    """
    try:
        await sayfa.locator("select").nth(1).select_option(label=tur)
        await bekle(sayfa, 1000)
    except Exception as hata:  # noqa: BLE001
        print("   ! süzgeç atlandı:", str(hata).split("\n")[0][:80])


async def s06_karsilastirma(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "compare", 2000)
    await kaydir(sayfa, 330, 700)
    await tur_suzgeci(sayfa)
    await kaydir(sayfa, 700, 900)
    await bekle(sayfa, 3200)


async def s07_urun_tablosu(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "compare", 2000)
    await kaydir(sayfa, 330, 700)
    await tur_suzgeci(sayfa)
    await tikla(sayfa, sayfa.locator("label", has_text="Ürün tablosu").first,
                once=300, sonra=1300)
    await kaydir(sayfa, 780, 900)
    await bekle(sayfa, 2800)


async def s08_isi(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "isi", 1900)
    await kaydir(sayfa, 480, 800)
    await bekle(sayfa, 1200)
    await kaydir(sayfa, 920, 900)
    await bekle(sayfa, 3000)


async def s09_avantajli(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "advantageous", 1900)
    await kaydir(sayfa, 400, 800)
    await bekle(sayfa, 1400)
    # 880'de liste «skor yok» satırlarına giriyordu: bileşik skorun asıl
    # gövdesi daha yukarıda.
    await kaydir(sayfa, 540, 900)
    await bekle(sayfa, 2800)


async def s10_banka(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "banka", 1900)
    # 950'ye kaydırmak sayfanın sonundaki «Banka İçi Delta» bölümüne düşüyordu
    # ve banka ekranı yerine delta ekranı görünüyordu — oysa deltanın kendi
    # sahnesi var. Kadraj bankanın künyesinde kalıyor.
    await kaydir(sayfa, 260, 800)
    await bekle(sayfa, 1600)
    await kaydir(sayfa, 600, 900)
    await bekle(sayfa, 3000)


async def s11_delta(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "delta", 1900)
    await kaydir(sayfa, 520, 900)
    await bekle(sayfa, 1400)
    await kaydir(sayfa, 940, 900)
    await bekle(sayfa, 2800)


async def s12_celiski(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "contradictions", 1900)
    await kaydir(sayfa, 430, 800)
    # DOM'daki yazı küçük harfli; ekrandaki büyük harf CSS'ten geliyor.
    await tikla(sayfa, sayfa.get_by_text("bankanın kendi ifadesi", exact=False).first,
                once=300, sonra=1400)
    await kaydir(sayfa, 900, 900)
    await bekle(sayfa, 2800)


async def s13_chatbot(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "chat", 1900)
    await kaydir(sayfa, 380, 700)
    await tikla(sayfa, sayfa.get_by_role("button",
                name="Hangi bankada en düşük kâr payı oranı var?"),
                once=300, sonra=2400)
    await kaydir(sayfa, 640, 900)
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
    await sekmeye_git(sayfa, "tazele", 2400)
    await kaydir(sayfa, 400, 800)
    await bekle(sayfa, 1200)
    for sekme_adi, yedek in (("İşlem Günlüğü", "gunluk"), ("Ayarlar", "ayarlar")):
        dugme = sayfa.get_by_role("tab", name=sekme_adi, exact=True).first
        if not await tikla(sayfa, dugme, once=250, sonra=1500):
            await sekmeye_git(sayfa, yedek, 2000)
        await kaydir(sayfa, 380, 700)
        await bekle(sayfa, 1100)
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
            baglam = await tarayici.new_context(
                viewport={"width": EN, "height": BOY},
                record_video_dir=str(HAM_DIZIN),
                record_video_size={"width": EN, "height": BOY},
                locale="tr-TR",
                timezone_id="Europe/Istanbul",
                reduced_motion="no-preference",
            )
            await baglam.add_init_script(IMLEC_BETIK)
            sayfa = await baglam.new_page()
            print(f"» {ad}")
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
