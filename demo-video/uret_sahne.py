"""Panel sahnelerini gerçek tarayıcıda koşturup video olarak kaydeder.

## Neden ekran görüntüsü değil, video

Şartname "metin girdisi verilmesi, modelin ürettiği yapılandırılmış çıktı ve
karşılaştırma sonuçları" diyor. Sıralı ekran görüntüsü bunu ANLATIR; koşan bir
tarayıcı ise GÖSTERİR — kutuya yazılan metin, basılan düğme, dönen iskelet ve
gelen sonuç aynı karede. Çıkarım gerçekten 17 saniye sürüyor (yerel model
çağrılıyor) ve bu bekleme videoda duruyor; kesilmiş bir ekran görüntüsü aynı
iddiayı taşımaz.

## İmleç neden elle çiziliyor

Playwright'ın sürücüsü gerçek fare olaylarını üretir ama işaretçiyi ÇİZMEZ:
kayıtta düğmeler kendiliğinden basılmış görünür. `IMLEC_BETIK` sayfaya bir
işaretçi enjekte eder ve olayları dinler; tık halkası da oradan gelir.

## Süre uydurma sonradan yapılır

Her sahne kendi doğal hızında koşar. Ses süresine oturtma işi `montaj.py`nin
işidir: burada süre kovalamak, çıkarımın bitmesini beklemeden ekranı
kaydırmak demek olurdu.

Tarayıcı yardımcıları (imleç, tıklama, kaydırma, çıkarım bekleme) bir
dakikalık sürümle paylaşıldığı için `sahne_ortak.py`de duruyor.
"""

import asyncio
import json
import pathlib
import shutil
import sys
import time

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
SENARYO = json.loads((KOK / "senaryo.json").read_text(encoding="utf-8"))
SAHNE_DIZIN = KOK / "sahne"
HAM_DIZIN = KOK / "sahne" / "ham"
EN, BOY = SENARYO["video"]["kayit_en"], SENARYO["video"]["kayit_boy"]


#: Sahne başladığı an. `kalani_doldur` buna göre ölçer.
_BASLANGIC = 0.0

#: Anlatım süreleri — sahnenin ne kadar sürmesi gerektiğini ses belirler.
SESLER = {
    s["id"]: s["sure"]
    for s in json.loads((KOK / "sesler.json").read_text(encoding="utf-8"))["sahneler"]
}


async def kalani_doldur(sayfa: Page, sahne_id: str, pay: float = 1.2) -> None:
    """Sahneyi anlatım süresine kadar açık tutar.

    Video anlatımdan KISA kalırsa montajda yavaşlatmak gerekir ve kaydırmalar
    ağırlaşır; UZUN kalırsa fazlası sondan kırpılır ve kimse fark etmez. Bu
    yüzden her sahne bilerek biraz uzun bırakılıyor — son görünüm birkaç
    saniye ekranda durur, izleyici okumaya zaman bulur.
    """
    hedef = SESLER.get(sahne_id, 0) + pay
    kalan = hedef - (time.monotonic() - _BASLANGIC)
    if kalan > 0:
        await bekle(sayfa, int(kalan * 1000))


# ————————————————————————————————————————————————————————————— sahneler


async def s01_panel(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "compare", 2600)
    await imleci_tasi(sayfa, 300, 165)          # künye şeridi
    await bekle(sayfa, 1600)
    await imleci_tasi(sayfa, 700, 292)          # sağlık şeridi
    await bekle(sayfa, 1800)
    await kaydir(sayfa, 180)
    for x in (287, 504, 747, 1004, 1237):       # sekme adları üzerinde gez
        await imleci_tasi(sayfa, x, 216)
        await bekle(sayfa, 520)
    await bekle(sayfa, 900)
    await kaydir(sayfa, 620, 1100)
    await bekle(sayfa, 2200)
    await kaydir(sayfa, 980, 1100)
    await bekle(sayfa, 2000)
    await kaydir(sayfa, 0, 1100)
    await kalani_doldur(sayfa, "01-panel")


async def s02_metin_girdisi(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "extract")
    ozet = sayfa.get_by_text("Kendi metninizi deneyin", exact=False).first
    await tikla(sayfa, ozet, sonra=900)
    kutu = sayfa.locator("#zv-serbest-metin")
    await kutu.scroll_into_view_if_needed()
    await bekle(sayfa, 500)
    await kutu.click()
    await kutu.type(ORNEK_METIN, delay=18)      # yazılışı görünsün
    await bekle(sayfa, 900)
    await tikla(sayfa, sayfa.get_by_role("button", name="Serbest metinde çalıştır"),
                sonra=400)
    # Çıkarım koşarken ekran iskelet basıyor; yerel model gerçekten çağrılıyor.
    await cikarimi_bekle(sayfa, "Serbest metinde çalıştır")
    await bekle(sayfa, 700)
    await sonuca_kaydir(sayfa)
    await bekle(sayfa, 3200)
    await sayfa.evaluate("window.scrollBy({top: 420, behavior: 'smooth'})")
    await bekle(sayfa, 3200)
    await kalani_doldur(sayfa, "02-metin-girdisi")


async def s03_zor_vaka(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "extract")
    await kaydir(sayfa, 240)
    await tikla(sayfa, sayfa.get_by_role("button", name="Koşullu / aralıklı (12)"))
    await bekle(sayfa, 700)
    # Listenin ilk kartı değil, ALTIN DEĞERİ OLAN kart seçiliyor. İlk turda
    # seçilen belgenin altın kümesinde hiç değer yoktu: sonuç tablosunun her
    # satırı «değer üretilmedi · altında yok» oldu ve yan yana karşılaştırma
    # gösterecek bir şey kalmadı. Kart künyesindeki «altında N değer» sayısı
    # bunu önceden söylüyor.
    dolu = sayfa.locator(".zv-vaka", has_text="altında 5 değer")
    kart = dolu.first if await dolu.count() else sayfa.locator(".zv-vaka").first
    await tikla(sayfa, kart, sonra=1000)
    await tikla(sayfa, sayfa.get_by_role("button", name="Çıkarımı çalıştır"), sonra=400)
    await cikarimi_bekle(sayfa, "Çıkarımı çalıştır")
    await bekle(sayfa, 700)
    await sonuca_kaydir(sayfa)
    await bekle(sayfa, 2600)
    await sayfa.evaluate("window.scrollBy({top: 400, behavior: 'smooth'})")
    await kalani_doldur(sayfa, "03-zor-vaka")


async def s04_kanit(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "audit")
    await kaydir(sayfa, 200)
    await tikla(sayfa, sayfa.get_by_role("button", name="Kuveyt Türk").first)
    await bekle(sayfa, 900)
    await kaydir(sayfa, 700, 1000)
    await bekle(sayfa, 1400)
    await kaydir(sayfa, 1250, 1100)
    await bekle(sayfa, 2600)
    await kaydir(sayfa, 1900, 1100)
    await bekle(sayfa, 2600)
    await kaydir(sayfa, 2500, 1100)
    await kalani_doldur(sayfa, "04-kanit")


async def s05_karsilastirma(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "compare")
    await kaydir(sayfa, 430)
    await bekle(sayfa, 1500)
    await kaydir(sayfa, 820, 1000)
    await bekle(sayfa, 2400)                    # kâr payı sıralaması
    await tikla(sayfa, sayfa.get_by_role("button", name="Vade (ay)", exact=True).first,
                sonra=1800)
    await bekle(sayfa, 2200)
    await kaydir(sayfa, 330, 900)
    # Ürün tablosu türe göre bölümleniyor ve ilk bölüm «türü belirlenemedi»:
    # ilk turda tabloya geçince ekranı baştan sona «Belirtilmemiş» dolduruyordu.
    # Süzgeci somut bir ürün ailesine almak tabloyu okunur hâle getiriyor.
    try:
        await sayfa.locator("select").nth(1).select_option(label="Konut Finansmanı")
        await bekle(sayfa, 1400)
    except Exception as hata:  # noqa: BLE001
        print("   ! süzgeç atlandı:", str(hata).split("\n")[0][:80])
    # Radyo düğmesinin kendisi görsel olarak küçük ve etiketiyle sarılı;
    # ilk turda metne tıklamak «görünür değil» diye atlandı. Etiket hedefi
    # tıklanabilir alanın tamamını kapsıyor.
    await tikla(sayfa, sayfa.locator("label", has_text="Ürün tablosu").first, sonra=1800)
    await kaydir(sayfa, 760, 1000)
    await bekle(sayfa, 2600)
    await kaydir(sayfa, 1180, 1000)
    await kalani_doldur(sayfa, "05-karsilastirma")


async def s06_isi(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "isi")
    await kaydir(sayfa, 420)
    await bekle(sayfa, 2200)
    await kaydir(sayfa, 900, 1100)
    await bekle(sayfa, 3000)
    await kaydir(sayfa, 1400, 1100)
    await bekle(sayfa, 3000)
    await kaydir(sayfa, 1850, 1100)
    await kalani_doldur(sayfa, "06-isi-haritasi")


async def s07_avantaj(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "advantageous")
    await kaydir(sayfa, 430)
    await bekle(sayfa, 2400)
    await kaydir(sayfa, 900, 1000)
    await bekle(sayfa, 1600)
    await sekmeye_git(sayfa, "banka", 1800)
    await kaydir(sayfa, 500, 1000)
    await bekle(sayfa, 2200)
    await sekmeye_git(sayfa, "delta", 1800)
    await kaydir(sayfa, 520, 1000)
    await bekle(sayfa, 2400)
    await kaydir(sayfa, 950, 1000)
    await kalani_doldur(sayfa, "07-avantaj-banka-delta")


async def s08_celiski(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "contradictions")
    await kaydir(sayfa, 430)
    await bekle(sayfa, 2600)
    # DOM'daki yazı küçük harfli; ekrandaki büyük harf CSS'ten geliyor.
    # İlk turda ekranda görüneni aramak bu adımı düşürdü.
    await tikla(sayfa, sayfa.get_by_text("bankanın kendi ifadesi", exact=False).first,
                sonra=1800)
    await bekle(sayfa, 2600)
    await kaydir(sayfa, 950, 1100)
    await bekle(sayfa, 2600)
    await kaydir(sayfa, 1450, 1100)
    await kalani_doldur(sayfa, "08-celiski")


async def s09_chatbot(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "chat")
    await kaydir(sayfa, 380)
    await tikla(sayfa, sayfa.get_by_role("button",
                name="Hangi bankada en düşük kâr payı oranı var?"), sonra=2600)
    await kaydir(sayfa, 620, 1000)
    await bekle(sayfa, 3600)
    kutu = sayfa.locator("textarea").first
    await kutu.scroll_into_view_if_needed()
    await kutu.click()
    await kutu.type("Peki 36 ay ve üzeri vade veren konut finansmanları?", delay=22)
    await bekle(sayfa, 600)
    await tikla(sayfa, sayfa.get_by_role("button", name="Sor").first, sonra=2600)
    await kaydir(sayfa, 700, 1000)
    await bekle(sayfa, 3200)
    await kaydir(sayfa, 1100, 1000)
    await kalani_doldur(sayfa, "09-chatbot")


async def s10_operasyon(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "tazele")
    await kaydir(sayfa, 430)
    await bekle(sayfa, 2600)
    await sekmeye_git(sayfa, "gunluk", 1800)
    await kaydir(sayfa, 430, 1000)
    await bekle(sayfa, 2800)
    await sekmeye_git(sayfa, "ayarlar", 1800)
    await kaydir(sayfa, 430, 1000)
    await bekle(sayfa, 2800)
    await kaydir(sayfa, 900, 1000)
    await kalani_doldur(sayfa, "10-operasyon")


SAHNELER = {
    "01-panel": s01_panel,
    "02-metin-girdisi": s02_metin_girdisi,
    "03-zor-vaka": s03_zor_vaka,
    "04-kanit": s04_kanit,
    "05-karsilastirma": s05_karsilastirma,
    "06-isi-haritasi": s06_isi,
    "07-avantaj-banka-delta": s07_avantaj,
    "08-celiski": s08_celiski,
    "09-chatbot": s09_chatbot,
    "10-operasyon": s10_operasyon,
}


async def main() -> None:
    global _BASLANGIC
    SAHNE_DIZIN.mkdir(exist_ok=True)
    HAM_DIZIN.mkdir(parents=True, exist_ok=True)
    # Argüman verilirse yalnız o sahneler çekilir: tek bir seçici düzeltmesi
    # için on sahnenin tamamını yeniden çekmek gereksiz.
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
            _BASLANGIC = time.monotonic()
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
