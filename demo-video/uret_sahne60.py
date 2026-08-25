"""Bir dakikalık sürüm için panelin her ekranını AYRI ve KISA kaydeder.

## v2 (2026-08-25) — neden yeniden yazıldı

v1'in sahneleri 23 Ağustos'ta çekilmişti; o günden sonra eklenen Bilgiler
sekmesi, hesap makinesi çekmecesi, chatbotun sesli karşılaması/mikrofonu ve
karşılaştırma tablosunun CSV/PDF indirmesi hiçbirinde YOKTU. Kullanıcı ayrıca
"Sunum Modu" ile (page.tsx `TUR_ADIMLARI`) çekmeyi AÇIKÇA reddetti — o tur
yalnız yedi ekranı gezer ve aşağıdaki dört yeni noktayı (CSV/PDF, hesap
makinesi, sesli karşılama, mikrofon) hiç göstermez. Bu yüzden her ekran
burada, önceki sürümdeki gibi, kendi Playwright fonksiyonuyla elle sürülüyor.

Değişmeyen sahneler (kanıt, ısı haritası, en avantajlı, banka, delta, çelişki,
zor vaka) fonksiyon olarak AYNI kaldı — bu ekranlara dokunulmadı, yalnız id
numaraları yeni sıraya göre kaydırıldı. `01-panel` CSV/PDF indirme beat'i
aldı; `13-chatbot` artık tam sayfa sekmesi değil, ÇEKMECE (karşılama ve
mikrofon yalnız orada var, bkz. SohbetCekmecesi.tsx) kullanıyor.

## Neden hesap makinesi ve chatbot `duzen: tek`

İkisi de SABİT KONUMLU yüzen çekmece (`position: fixed`, ekranın köşesinde).
`cift` düzeni kaydı yatayda ortadan bölüp yan yana koyar — sayfa AKIŞI olan
içerik için doğru ("devamı sağ sütunda"), ama sabit bir kutu ortadan
bölünürse kesim çizgisinden yırtılmış görünür. Bu yüzden ikisi doğal 16:9
penceresinde (`tek`) kaydedilir, tıpkı ısı haritası matrisinin bölünmeye
uygun olmaması gibi.

## Mikrofon ve yazdırma — kayıt sırasında ASILI KALMAMASI için iki önlem

1. `window.print()` gerçek bir OS yazdırma penceresi açar ve bu pencere
   Playwright'ın sayfa olaylarıyla KAPATILAMAZ — kayıt sonsuza dek asılı
   kalırdı (elle doğrulandı). `main()` her bağlama `window.print = () => {}`
   enjekte ediyor: tıklama görsel olarak kayda giriyor (imleç + tık halkası)
   ama pencere hiç açılmıyor.
2. Mikrofon düğmesi gerçek `getUserMedia` ister; `--use-fake-device-for-media-
   stream` + `--use-fake-ui-for-media-stream` bayrakları hem izin penceresini
   hem de gerçek donanım beklemesini ortadan kaldırır — düğme "dinliyor"
   durumuna geçer ama gerçek ses girmediği için bir sonuç ÜRETMEZ (beklenen;
   sahnenin işi düğmenin var olduğunu göstermek, sahte bir transkript değil).

## Hesap makinesi demosu — kampanya #25

`data/demo.db` sorgulanarak seçildi: Kuveyt Türk, Finansman, kâr payı oranı
4,19 VE vade 12 ay — ikisi de dolu tek bir kampanya. "Kampanyadan doldur"un
gerçekten ikisini birden doldurduğu bu yüzden görünür; rastgele bir kampanya
seçilse "elle girin" notu çıkabilirdi (uydurma yasağı, bkz. HesapCekmecesi.tsx).

## Bilgiler sekmesi — hangi kısım kadraja alınıyor

Sekmede donut grafiği İLE "Ek Veri Alanları" vitrini AYNI 2304 piksellik
pencereye SIĞMIYOR (ölçüldü: donut y≈654, vitrin y≈3037-3329, aralarında
2383px var). İkisinden biri seçilmek zorunda; vitrin seçildi çünkü jüri
turunda puan kaybedilen nokta tam oydu (tahsis_ucreti/hedef_kitle/
taksit_sayisi görünmüyordu) — donut renk dağılımı görsel ama ikincil.
"""

import asyncio
import json
import pathlib
import shutil
import sys

from playwright.async_api import Page, async_playwright

from sahne_ortak import (
    IMLEC_BETIK,
    bekle,
    cikarimi_bekle,
    imleci_tasi,
    kadraja_al,
    kaydir,
    sekmeye_git,
    tikla,
)

KOK = pathlib.Path(__file__).parent
SENARYO = json.loads((KOK / "senaryo-60.json").read_text(encoding="utf-8"))
SAHNE_DIZIN = KOK / "sahne-60"
HAM_DIZIN = SAHNE_DIZIN / "ham"
V = SENARYO["video"]

#: Yazdırma penceresini asılı bırakmadan PDF düğmesinin tıklanabilmesi için.
YAZDIR_ENGELLE = "window.print = () => {};"

PENCERE = {
    "tek": (V["kayit_en"], V["kayit_boy"]),
    "cift": (V["sutun_en"], V["sutun_boy"] * 2),
    "yan": (V["sutun_en"], V["sutun_boy"] * 2),
}

DUZENLER = {
    kaynak: sahne.get("duzen", "tek")
    for sahne in SENARYO["sahneler"] if sahne["tur"] == "panel"
    for kaynak in sahne.get("kaynaklar", [sahne.get("kaynak")])
}


async def alan_sec(sayfa: Page, ad: str) -> None:
    await tikla(sayfa, sayfa.get_by_role("tab", name=ad, exact=True).first,
                once=250, sonra=900)


async def tur_suzgeci(sayfa: Page, tur: str, sira: int = 1) -> None:
    try:
        await sayfa.locator("select").nth(sira).select_option(label=tur)
        await bekle(sayfa, 1000)
    except Exception as hata:  # noqa: BLE001
        print("   ! süzgeç atlandı:", str(hata).split("\n")[0][:80])


async def s01_panel(sayfa: Page) -> None:
    """Karşılaştırma + CSV/PDF indirme — v1'in `01-panel` + `06-karsilastirma`
    tek sahnede birleşti (vade × Finansman aynı ekran, tekrar çekmenin
    anlamı yoktu) ve indirme düğmeleri eklendi."""
    await sekmeye_git(sayfa, "compare", 2600)
    await alan_sec(sayfa, "Vade (ay)")
    await tur_suzgeci(sayfa, "Finansman")
    await imleci_tasi(sayfa, 640, 300)
    await bekle(sayfa, 1200)
    # YENİ: CSV + PDF indirme beat'i. PDF gerçek pencere AÇMAZ
    # (`YAZDIR_ENGELLE`, main()) — tıklama görsel, kayıt asılı kalmaz.
    await tikla(sayfa, sayfa.get_by_role("button", name="CSV indir"),
                once=300, sonra=700)
    await tikla(sayfa, sayfa.get_by_role("button", name="PDF olarak yazdır"),
                once=300, sonra=700)
    await kaydir(sayfa, 240, 900)
    await bekle(sayfa, 1200)
    await kaydir(sayfa, 620, 900)
    await bekle(sayfa, 1600)


async def s02_bilgiler(sayfa: Page) -> None:
    """YENİ. "Alan Kapsamı" tablosundan "Ek Veri Alanları" vitrinine kadar
    tek kadraj — gerekçe dosya başlığında (donut ile aynı pencereye sığmıyor)."""
    await sekmeye_git(sayfa, "bilgiler", 2600)
    await kadraja_al(sayfa, sayfa.get_by_role("heading", name="Alan Kapsamı",
                     exact=True).first, pay=380, bekleme=1600)
    await bekle(sayfa, 3400)


async def s03_kanit(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "audit", 2200)
    await kaydir(sayfa, 200, 600)
    await tikla(sayfa, sayfa.get_by_role("button", name="Kuveyt Türk").first,
                once=300, sonra=800)
    await kaydir(sayfa, 900, 900)
    await bekle(sayfa, 3200)


async def s04_hesap(sayfa: Page) -> None:
    """YENİ. Kampanya #25 (Kuveyt Türk · Finansman · oran 4,19 · vade 12) —
    seçim gerekçesi dosya başlığında."""
    await sekmeye_git(sayfa, "compare", 2200)
    await tikla(sayfa, sayfa.get_by_role("button", name="Hesap makinesini aç"),
                once=300, sonra=900)
    try:
        await sayfa.locator("#hesap-kampanya").select_option(value="25")
    except Exception as hata:  # noqa: BLE001
        print("   ! kampanya seçimi atlandı:", str(hata).split("\n")[0][:80])
    await bekle(sayfa, 1600)  # oran/vade otomatik dolsun
    # Anapara kampanyadan DOLMAZ (belgede yok) — elle girilmesi gerekiyor,
    # aksi hâlde "Hesapla" doğrulama hatası verir, sonuç değil.
    await tikla(sayfa, sayfa.locator("#hesap-anapara"), once=200, sonra=200)
    await sayfa.locator("#hesap-anapara").fill("500000")
    await bekle(sayfa, 500)
    await tikla(sayfa, sayfa.get_by_role("button", name="Hesapla", exact=True),
                once=300, sonra=800)
    await bekle(sayfa, 3400)


async def s05_isi(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "isi", 2200)
    try:
        await sayfa.locator("#isi-alan").select_option(label="Vade (ay)")
        await bekle(sayfa, 1200)
    except Exception as hata:  # noqa: BLE001
        print("   ! ısı alanı atlandı:", str(hata).split("\n")[0][:80])
    await kaydir(sayfa, 470, 900)
    await bekle(sayfa, 3400)


async def s06_avantajli(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "advantageous", 2200)
    await tur_suzgeci(sayfa, "Kart", sira=0)
    await kaydir(sayfa, 420, 900)
    await bekle(sayfa, 3400)


async def s07_banka(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "banka", 2200)
    try:
        await sayfa.locator("#banka-secici").select_option(label="Kuveyt Türk")
        await bekle(sayfa, 1400)
    except Exception as hata:  # noqa: BLE001
        print("   ! banka seçimi atlandı:", str(hata).split("\n")[0][:80])
    await kaydir(sayfa, 380, 900)
    await bekle(sayfa, 3400)


async def s08_delta(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "delta", 2200)
    try:
        await sayfa.locator("#delta-bank").select_option(label="Kuveyt Türk")
        await bekle(sayfa, 1400)
    except Exception as hata:  # noqa: BLE001
        print("   ! delta bankası atlandı:", str(hata).split("\n")[0][:80])
    await kaydir(sayfa, 520, 900)
    await bekle(sayfa, 3400)


async def s09_celiski(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "contradictions", 2200)
    await kaydir(sayfa, 400, 800)
    await tikla(sayfa, sayfa.get_by_text("bankanın kendi ifadesi", exact=False).first,
                once=300, sonra=1600)
    await kaydir(sayfa, 700, 900)
    await bekle(sayfa, 3000)


async def s10_zor_vaka(sayfa: Page) -> None:
    await sekmeye_git(sayfa, "extract", 1800)
    await kaydir(sayfa, 240, 700)
    await tikla(sayfa, sayfa.get_by_role("button", name="Koşullu / aralıklı (12)"),
                once=300, sonra=500)
    dolu = sayfa.locator(".zv-vaka", has_text="altında 5 değer")
    kart = dolu.first if await dolu.count() else sayfa.locator(".zv-vaka").first
    await tikla(sayfa, kart, once=300, sonra=700)
    await tikla(sayfa, sayfa.get_by_role("button", name="Çıkarımı çalıştır"),
                once=300, sonra=300)
    await cikarimi_bekle(sayfa, "Çıkarımı çalıştır")
    await bekle(sayfa, 600)
    await kadraja_al(sayfa, sayfa.get_by_role("heading", name="Model çıktısı").first,
                     pay=220, bekleme=3400)


async def s11_chatbot(sayfa: Page) -> None:
    """Karşılama VE mikrofon yalnız ÇEKMECEDE var (SohbetCekmecesi.tsx) —
    tam sayfa `chat` sekmesinde değil. Bu yüzden v1'in tersine burada FAB
    tıklanıyor, sekmeye gidilmiyor. Karşılama, TAZE bağlamda (her sahne kendi
    `new_context`ini alıyor) FAB'a İLK tıklamada otomatik tetikleniyor."""
    await sekmeye_git(sayfa, "compare", 2000)
    await tikla(sayfa, sayfa.get_by_role("button", name="Sohbeti aç"),
                once=300, sonra=1400)
    await bekle(sayfa, 2600)  # karşılama metni okunsun
    # Mikrofonun VAR OLDUĞUNU göster — gerçek ses yok (sahte medya aygıtı),
    # bu yüzden durdurmaya çalışmadan doğrudan hazır soruya geçiliyor.
    mik = sayfa.get_by_role(
        "button", name="Sesle soru sor (tarayıcının konuşma tanıma özelliğini kullanır)")
    await tikla(sayfa, mik, once=300, sonra=1800)
    # DİKKAT: soru metni çekmecenin AÇILDIĞI bağlamın (burada "compare")
    # hazır sorularından biri OLMAK ZORUNDA — HAZIR_SORULAR bağlama göre
    # değişiyor (SohbetCekmecesi.tsx). "compare" bağlamının üç sorusundan biri.
    await tikla(sayfa, sayfa.get_by_role(
        "button", name="Hangi bankada en düşük kâr payı oranı var?"),
        once=250, sonra=1200)
    await cikarimi_bekle(sayfa, "Sor")
    await bekle(sayfa, 3000)


SAHNELER = {
    "01-panel": s01_panel,
    "02-bilgiler": s02_bilgiler,
    "03-kanit": s03_kanit,
    "04-hesap-makinesi": s04_hesap,
    "05-isi-haritasi": s05_isi,
    "06-avantajli": s06_avantajli,
    "07-banka": s07_banka,
    "08-delta": s08_delta,
    "09-celiski": s09_celiski,
    "10-zor-vaka": s10_zor_vaka,
    "11-chatbot": s11_chatbot,
}


async def main() -> None:
    SAHNE_DIZIN.mkdir(exist_ok=True)
    HAM_DIZIN.mkdir(parents=True, exist_ok=True)
    istenen = sys.argv[1:] or list(SAHNELER)
    async with async_playwright() as p:
        tarayici = await p.chromium.launch(args=[
            "--force-color-profile=srgb",
            "--use-fake-device-for-media-stream",
            "--use-fake-ui-for-media-stream",
        ])
        for ad, islev in ((a, SAHNELER[a]) for a in istenen):
            en, boy = PENCERE[DUZENLER.get(ad, "tek")]
            baglam = await tarayici.new_context(
                viewport={"width": en, "height": boy},
                record_video_dir=str(HAM_DIZIN),
                record_video_size={"width": en, "height": boy},
                locale="tr-TR",
                timezone_id="Europe/Istanbul",
                reduced_motion="no-preference",
                permissions=["microphone"],
            )
            await baglam.add_init_script(IMLEC_BETIK)
            await baglam.add_init_script(YAZDIR_ENGELLE)
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
