"""Panel kayıtlarının iki sürümü arasında paylaşılan tarayıcı yardımcıları.

`uret_sahne.py` (beş dakikalık sürüm) ve `uret_sahne60.py` (bir dakikalık
sürüm) aynı paneli aynı biçimde sürüyor: aynı imleç, aynı tıklama ritmi, aynı
"hedef yoksa sahneyi düşürmeden devam et" davranışı. İkisi ayrı ayrı kopya
tutarsa bir seçici değiştiğinde biri düzeltilip öteki sessizce bozulur.

Sürümlere özgü olan şeyler burada DEĞİL: süre doldurma (yalnız beş dakikalık
sürümde var, çünkü orada sahne uzunluğunu anlatım belirliyor) ve sahne
listeleri kendi dosyalarında kalır.
"""

import pathlib

from playwright.async_api import Page

KOK = pathlib.Path(__file__).parent
TABAN = "http://localhost:3000"

# Serbest metin yolunda kullanılan örnek. Korpustan değil KASITLI olarak
# sentetik: jüri "bunu daha önce görmüştünüz" diyemesin diye. İçinde beş
# alan var (oran, tutar, vade, süre, masraf) ve biri —taksit— yok; boş
# bırakılan alanın ekranda nasıl göründüğü de gösterilmiş oluyor.
ORNEK_METIN = (
    "Konut finansmanında 36 ay vadeye kadar %2,49 kâr payı oranı ile "
    "1.500.000 TL tutarına kadar finansman imkânı. Kampanya 31.12.2026 "
    "tarihine kadar geçerlidir; tahsis ücreti alınmaz."
)

# Playwright'ın sürücüsü gerçek fare olaylarını üretir ama işaretçiyi ÇİZMEZ:
# kayıtta düğmeler kendiliğinden basılmış görünür. Bu betik sayfaya bir
# işaretçi enjekte eder ve olayları dinler; tık halkası da oradan gelir.
IMLEC_BETIK = """
document.addEventListener('DOMContentLoaded', () => {
  const im = document.createElement('div');
  im.id = '__imlec';
  im.style.cssText = [
    'position:fixed','z-index:2147483647','pointer-events:none',
    'width:22px','height:22px','margin:-11px 0 0 -11px','border-radius:50%',
    'background:rgba(43,47,143,.28)','border:2px solid rgba(43,47,143,.9)',
    'box-shadow:0 2px 10px rgba(0,0,0,.25)','transition:transform .06s linear',
    'left:-100px','top:-100px'
  ].join(';');
  document.body.appendChild(im);
  addEventListener('mousemove', e => {
    im.style.left = e.clientX + 'px';
    im.style.top = e.clientY + 'px';
  }, true);
  addEventListener('mousedown', () => {
    const h = document.createElement('div');
    h.style.cssText = [
      'position:fixed','z-index:2147483646','pointer-events:none',
      'left:' + im.style.left,'top:' + im.style.top,
      'width:14px','height:14px','margin:-7px 0 0 -7px','border-radius:50%',
      'border:2px solid rgba(43,47,143,.85)','animation:__hlk .5s ease-out forwards'
    ].join(';');
    document.body.appendChild(h);
    setTimeout(() => h.remove(), 520);
  }, true);
  const s = document.createElement('style');
  s.textContent = '@keyframes __hlk{to{transform:scale(4.2);opacity:0}}';
  document.head.appendChild(s);
});
"""


async def bekle(sayfa: Page, ms: int) -> None:
    await sayfa.wait_for_timeout(ms)


async def imleci_tasi(sayfa: Page, x: float, y: float, adim: int = 14) -> None:
    """Fareyi yumuşak taşır — sıçrayan bir işaretçi kayıtta göze batıyor."""
    await sayfa.mouse.move(x, y, steps=adim)


async def tikla(sayfa, hedef, once: int = 420, sonra: int = 700) -> bool:
    """Görünür kıl → imleci üstüne taşı → tıkla. Hedef yoksa False döner.

    Sahne bir düğme bulamadığında ÇÖKMEZ: o adım atlanır ve kayıt sürer.
    Tek bir seçici değiştiğinde bütün videoyu kaybetmek istemiyoruz.
    """
    try:
        await hedef.scroll_into_view_if_needed(timeout=4000)
        kutu = await hedef.bounding_box()
        if not kutu:
            return False
        await imleci_tasi(sayfa, kutu["x"] + kutu["width"] / 2,
                          kutu["y"] + kutu["height"] / 2)
        await bekle(sayfa, once)
        await hedef.click(timeout=4000)
        await bekle(sayfa, sonra)
        return True
    except Exception as hata:  # noqa: BLE001 — kayıt sürsün diye yutuluyor
        print("   ! atlandı:", str(hata).split("\n")[0][:90])
        return False


async def kaydir(sayfa: Page, hedef_y: int, sure_ms: int = 900) -> None:
    """Yumuşak kaydırma; sonra hareketin bitmesini bekler."""
    await sayfa.evaluate(
        "y => window.scrollTo({top: y, behavior: 'smooth'})", hedef_y
    )
    await bekle(sayfa, sure_ms)


async def sekmeye_git(sayfa: Page, sekme: str, bekleme: int = 2200) -> None:
    await sayfa.goto(f"{TABAN}/?juri=1&sekme={sekme}", wait_until="domcontentloaded")
    await bekle(sayfa, bekleme)


async def sonuca_kaydir(sayfa: Page) -> None:
    """Çıkarım sonucunu kadraja alır.

    Sabit piksel kullanılmıyor: sonuç bölümünün yüksekliği seçili belgenin
    metin uzunluğuna göre değişiyor ve ilk turda 900 piksel bir vakada sonuca
    yetişti, diğerinde kart listesinde kaldı — sonuç ekrana hiç girmedi.
    """
    try:
        baslik = sayfa.get_by_role("heading", name="Sonuç").first
        await baslik.scroll_into_view_if_needed(timeout=5000)
        await sayfa.evaluate("window.scrollBy({top: -90, behavior: 'smooth'})")
    except Exception:  # noqa: BLE001
        await kaydir(sayfa, 950, 1100)


async def cikarimi_bekle(sayfa: Page, dugme_adi: str) -> None:
    """Düğme yazısı eski hâline dönene kadar bekler — yani çıkarım bitene dek.

    Düğme koşarken «Çıkarım koşuyor…» yazıyor; adıyla aranan düğme o sırada
    DOM'da yok. Geri gelmesi, işin bittiğinin ekrandaki karşılığıdır.
    """
    try:
        await sayfa.get_by_role("button", name=dugme_adi).wait_for(timeout=90_000)
    except Exception:  # noqa: BLE001
        await bekle(sayfa, 20_000)
