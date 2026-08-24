"""Yeni tasarımın kareleri. Yalnız GÖRÜNTÜ alır; açıklamalar manifest.json'da.

Kırpma sabit yükseklikte (`yuk`); `capa` verilirse o öğenin üstünden başlar.
Sabit konumlu yüzeyler (sohbet çekmecesi, komut paleti, kaynak yan paneli)
`gorunum=True` ile viewport olarak çekilir — `full_page` kırpması bunları
kaydırılmış sayfanın dışında bırakıyor.
"""
from __future__ import annotations

import json
import pathlib
import sys

from playwright.sync_api import Page, sync_playwright

URL = "http://localhost:3010"
CIKTI = pathlib.Path("/Users/mehmetefeaytas/anatoliaaI/docs-ekran/ss")
GENISLIK = 1600
KAYIT: list[str] = []
SIRA = 0


def _loc(pg: Page, secici: str):
    """`"sel::2"` → o seçicinin 2. eşleşmesi; yoksa ilki."""
    if "::" in secici:
        sel, _, idx = secici.rpartition("::")
        return pg.locator(sel).nth(int(idx))
    return pg.locator(secici).first


def mutlak_y(pg: Page, capa) -> float:
    """Adaylardan İLK VAR OLANIN belge koordinatındaki üst kenarı.

    Tek bir seçiciye güvenmek kırılgandı: başlıklar CSS ile büyütülüyor,
    düğme etiketleri tıklanınca değişiyor ve bir aday yoksa kare tamamen
    kayboluyordu. Aday listesi bu kaybı önlüyor.
    """
    adaylar = [capa] if isinstance(capa, str) else list(capa)
    son: Exception | None = None
    for a in adaylar:
        try:
            loc = _loc(pg, a)
            loc.wait_for(state="attached", timeout=4000)
            return loc.evaluate(
                "el => el.getBoundingClientRect().top + window.scrollY")
        except Exception as e:  # sıradaki adaya geç
            son = e
    raise son or RuntimeError("çapa bulunamadı")


def cek(pg: Page, ad: str, *, secici: str | None = None, capa=None,
        yuk: int = 1400, gorunum: bool = False) -> None:
    global SIRA
    SIRA += 1
    dosya = CIKTI / f"{SIRA:02d}-{ad}.png"
    pg.wait_for_timeout(500)
    try:
        _cek(pg, dosya, secici, capa, yuk, gorunum)
    except Exception as e:
        SIRA -= 1
        print(f"  ! {ad} atlandı: {str(e).splitlines()[0][:90]}", flush=True)
        return
    KAYIT.append(dosya.name)
    print(f"  ✓ {dosya.name}", flush=True)


def _cek(pg: Page, dosya: pathlib.Path, secici, capa, yuk, gorunum) -> None:
    if secici:
        loc = pg.locator(secici).first
        loc.scroll_into_view_if_needed()
        pg.wait_for_timeout(400)
        loc.screenshot(path=str(dosya))
    elif gorunum:
        pg.screenshot(path=str(dosya))
    else:
        sayfa_yuk = pg.evaluate("document.documentElement.scrollHeight")
        y = max(0, int(mutlak_y(pg, capa)) - 28) if capa else 0
        h = int(min(yuk, max(320, sayfa_yuk - y)))
        pg.screenshot(path=str(dosya), full_page=True,
                      clip={"x": 0, "y": y, "width": GENISLIK, "height": h})


def sekme(pg: Page, ad: str, bekle: int = 3000) -> None:
    """Sekmeye geç. Tıklama başarısızsa akış durmaz, kare atlanır."""
    try:
        pg.get_by_role("tab", name=ad, exact=True).click()
    except Exception as e:
        print(f"  ! «{ad}» sekmesi açılamadı: {str(e).splitlines()[0][:80]}", flush=True)
    pg.wait_for_timeout(bekle)


def dene(etiket: str, islev) -> bool:
    """Etkileşimi dene; başarısızsa akışı durdurmadan bildir."""
    try:
        islev()
        return True
    except Exception as e:
        print(f"  ! {etiket} yapılamadı: {str(e).splitlines()[0][:90]}", flush=True)
        return False


def main() -> int:
    for eski in CIKTI.glob("*.png"):
        eski.unlink()

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": GENISLIK, "height": 1000},
                        device_scale_factor=2, locale="tr-TR")
        pg.set_default_timeout(15_000)
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(4500)

        # ───────────────────────────────────────────────── kabuk
        cek(pg, "genel-bakis", yuk=1150)
        cek(pg, "korpus-kunyesi", secici=".kunye, [class*='kunye']")
        cek(pg, "durum-seridi", secici=".durum-serit, [class*='durum-serit'], [class*='durum']")
        cek(pg, "ozet-kapsam", secici=".ozet-kapsam")

        # ───────────────────────────────────── 1. Karşılaştırma
        cek(pg, "kiyas-cetveli", capa="main svg", yuk=1300)
        dene("adil kıyas şeridini aç", lambda: pg.locator(".fairness-ozet").first.click())
        pg.wait_for_timeout(1200)
        cek(pg, "adil-kiyas-notu", secici=".fairness-serit")
        cek(pg, "kiyas-tablosu", capa="main table", yuk=1400)

        # ¶ kaynak dipnotu → yan panel
        dene("¶ kaynak dipnotu", lambda: pg.locator("button.kaynak-dipnot, button[class*='kaynak-dipnot']").first.click())
        pg.wait_for_timeout(3500)
        cek(pg, "kaynak-dipnotu", gorunum=True)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(1200)

        cek(pg, "seffaf-skorlama", capa=["h2:has-text('Şeffaf Skorlama')", "text=Şeffaf Skorlama"], yuk=1400)

        # ───────────────────────────────────── 2. Isı Haritası
        sekme(pg, "Isı Haritası", 4000)
        cek(pg, "isi-haritasi", yuk=1400)
        dene("ısı alanı: Masraf Durumu", lambda: pg.locator("main select").first.select_option(label="Masraf Durumu"))
        pg.wait_for_timeout(3000)
        cek(pg, "isi-haritasi-masraf", capa="main svg", yuk=1250)

        # ───────────────────────────────────── 3. En Avantajlı
        sekme(pg, "En Avantajlı", 4500)
        cek(pg, "en-avantajli", yuk=1400)
        dene("ağırlıkları aç", lambda: pg.get_by_role("button", name="Ağırlıklar ve gerekçeleri (5)").click())
        pg.wait_for_timeout(1500)
        cek(pg, "agirlik-gerekceleri", capa=["h3:has-text('AĞIRLIK')", "h3:has-text('Ağırlık')",
                  "button:has-text('Ağırlıklar')"], yuk=1250)

        # ───────────────────────────────────── 4. Banka Sayfası
        sekme(pg, "Banka Sayfası", 4500)
        dene("banka: Kuveyt Türk", lambda: pg.locator("main select").first.select_option(label="Kuveyt Türk"))
        pg.wait_for_timeout(4500)
        cek(pg, "banka-sayfasi", yuk=1400)
        cek(pg, "banka-yildiz", capa=[".banka-gozustu::0", "h3:has-text('KAMPANYA TÜRÜ')"], yuk=1350)
        cek(pg, "banka-alan-durumu", capa=[".banka-gozustu::1", "h3:has-text('ALANIN DURUMU')"], yuk=1250)

        # ───────────────────────────────── 5. Banka İçi Delta
        sekme(pg, "Banka İçi Delta", 4500)
        cek(pg, "banka-ici-delta", yuk=1400)
        cek(pg, "delta-ekseni", capa=["h3:has-text('ALAN ALAN DELTA')"], yuk=1250)

        # ─────────────────────────── 6. Katılma Oranları
        # Panel sırasıyla AYNI yerde duruyor (page.tsx: delta ile çelişki
        # arasında). Kare sırası panel sırasından ayrılırsa PDF'i okuyan
        # jüri ekranı ekranda bulamaz.
        sekme(pg, "Katılma Oranları", 4500)
        cek(pg, "katilma-oranlari",
            capa=["h2:has-text('Katılma Hesabı Oranları')", "#katilma-baslik"],
            yuk=1400)

        # ──────────────────────────────── 7. Çelişki Tespiti
        sekme(pg, "Çelişki Tespiti", 5000)
        cek(pg, "celiski-tespiti", yuk=1400)
        # Kartın iki alıntısı <details> içinde katlı duruyor; kapalı hâli
        # yalnız gerekçeyi gösteriyor, ekranın TEZİ ise iki cümlenin yan yana
        # durması. Bu yüzden açılıyor.
        dene("bankanın kendi ifadesini aç",
             lambda: pg.locator(".celiski-kart summary").first.click())
        pg.wait_for_timeout(1500)
        cek(pg, "celiski-iki-alinti", secici=".celiski-kart")

        # ─────────────────────────────────── sohbet çekmecesi
        dene("sohbet çekmecesini aç", lambda: pg.locator("button.sohbet-fab").click())
        pg.wait_for_timeout(2500)
        cek(pg, "sohbet-cekmecesi", gorunum=True)
        dene("sohbeti kapat", lambda: pg.keyboard.press("Escape"))
        pg.wait_for_timeout(1200)

        # ───────────────────────────────────────── komut paleti
        pg.keyboard.press("Control+k")
        pg.wait_for_timeout(1200)
        pg.keyboard.type("konut", delay=90)
        pg.wait_for_timeout(3500)
        cek(pg, "komut-paleti", gorunum=True)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(1000)

        # ─────────────────────────────────────────── jüri modu
        dene("jüri modunu aç", lambda: pg.get_by_role("button", name="Jüri modu: kapalı").click())
        pg.wait_for_timeout(2500)
        cek(pg, "juri-modu", yuk=1150)

        # ──────────────────────────── 7. Kanıt defteri (audit)
        sekme(pg, "Jüri Audit Paneli", 5000)
        cek(pg, "kanit-defteri", yuk=1400)
        cek(pg, "belge-secici", capa="[class*='arama'], main input", yuk=1000)
        cek(pg, "kanit-cikarilan-deger", capa=["h2:has-text('Çıkarılan değer')"], yuk=1350)
        cek(pg, "kanit-kaynak-cumle", capa=["h3:has-text('KAYNAK METİN')", "h3:has-text('KAYNAK')"], yuk=1300)

        # ─────────────────────── 8. Zor Vaka Tezgâhı (extract)
        sekme(pg, "Canlı Çıkarım", 4500)
        cek(pg, "zor-vaka-tezgahi", yuk=1400)
        dene("çelişkili metin kümesi", lambda: pg.get_by_role("button", name="Çelişkili metin (4)").click())
        pg.wait_for_timeout(2500)
        cek(pg, "zor-vaka-celiskili-kume", yuk=1400)
        # kümedeki ilk vakayı çalıştır
        dene("vakayı seç",
             lambda: pg.locator("main button").filter(has_text="Çelişkili metin").nth(1).click())
        pg.wait_for_timeout(2500)
        # Vakayı seçmek çıkarımı BAŞLATMIYOR: metin sağda duruyor ve ayrı bir
        # düğme bekliyor. İlk turda bu adım atlandığı için sonuç karesi boş
        # kalmıştı.
        dene("çıkarımı çalıştır",
             lambda: pg.get_by_role("button", name="Çıkarımı çalıştır").click())
        # 30 sn yetmiyordu: düğme tıklanıyor ama «Model çıktısı» başlığı
        # gelmeden kare alınıyor ve `zor-vaka-sonuc` sessizce düşüyordu
        # (ölçüldü 2026-08-24, iki ardışık koşumda da). CPU'da Ollama'nın
        # kısıtlı JSON üretimi bu vakada 30 sn'yi aşıyor.
        pg.wait_for_timeout(90000)
        # Çapa YANLIŞ ETİKETTEYDİ: bileşen başlığı `<h2>Model çıktısı ↔ altın
        # küme</h2>` (ExtractLive.tsx:407), betik ise `h3` arıyordu. Dört
        # adayın dördü de tutmuyordu ve kare iki aydır sessizce düşüyordu —
        # `cek()` hatayı yutup SIRA'yı geri aldığı için koşum yeşil görünüyor.
        cek(pg, "zor-vaka-sonuc", capa=["h2:has-text('Model çıktısı')",
                  "h2:has-text('Sonuç')", "h3:has-text('Model çıktısı')"], yuk=1400)
        cek(pg, "zor-vaka-altin-kume", capa=["h3:has-text('Altın küme')", "h3:has-text('ALTIN KÜME')",
                  "text=Altın küme"], yuk=1350)

        # ───────────────────────────────────────── 9. Chatbot
        sekme(pg, "Chatbot", 2000)
        cek(pg, "chatbot-bos", yuk=1200)
        dene("hazır soru 1", lambda: pg.get_by_role("button", name="Hangi bankada en düşük kâr payı oranı var?").click())
        pg.wait_for_timeout(2000)
        dene("soruyu gönder", lambda: pg.get_by_role("button", name="Sor", exact=True).click())
        pg.wait_for_timeout(45000)
        cek(pg, "chatbot-yapisal-sorgu", capa=["h2:has-text('Chatbot')"], yuk=1400)
        cek(pg, "chatbot-kaynaklar", capa=["h3:has-text('KAYNAKLAR')", "text=KAYNAKLAR"], yuk=1100)

        dene("yeni konu", lambda: pg.get_by_role("button", name="Yeni konu").click())
        pg.wait_for_timeout(2000)
        dene("hazır soru 2", lambda: pg.get_by_role("button", name="Konut finansmanı kampanyasının koşulları neler?").click())
        pg.wait_for_timeout(2000)
        dene("soruyu gönder", lambda: pg.get_by_role("button", name="Sor", exact=True).click())
        pg.wait_for_timeout(55000)
        cek(pg, "chatbot-rag", capa=["h2:has-text('Chatbot')"], yuk=1400)

        # ───────────────────────────────── 10. Veri Tazeleme
        sekme(pg, "Veri Tazeleme", 3500)
        cek(pg, "veri-tazeleme", yuk=1400)
        cek(pg, "toplama-taahhudu", capa=["h3:has-text('TOPLAMA TAAHH')"], yuk=1100)
        dene("şimdi tazele", lambda: pg.get_by_role("button", name="Şimdi tazele").nth(1).click())
        pg.wait_for_timeout(6000)
        cek(pg, "tazeleme-onizleme", capa=["h2:has-text('Başlatmadan önce')", "h3:has-text('Başlatmadan önce')"], yuk=1200)

        # ──────────────────────────────────────── 11. Ayarlar
        sekme(pg, "Ayarlar", 3500)
        cek(pg, "ayarlar", yuk=1400)

        # ────────────────────────────────────────── koyu tema
        dene("koyu tema", lambda: pg.get_by_role("button", name="Koyu", exact=True).click())
        pg.wait_for_timeout(1500)
        sekme(pg, "Karşılaştırma", 4000)
        cek(pg, "koyu-tema", yuk=1400)

        # ───────────────────────────────────── API dokümanı
        pg.goto("http://127.0.0.1:8010/docs", wait_until="networkidle")
        pg.wait_for_timeout(4000)
        cek(pg, "api-dokumani", yuk=1300)

        b.close()

    (CIKTI.parent / "cekilen.json").write_text(
        json.dumps(KAYIT, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(KAYIT)} kare alındı")
    return 0


if __name__ == "__main__":
    sys.exit(main())
