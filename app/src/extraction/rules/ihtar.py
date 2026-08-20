"""Genel yasal ihtar (sorumluluk saklı tutma) — TEK DOĞRULUK KAYNAĞI.

İlgili: src/extraction/rules/extract.py (`extract_kampanya_kosullari` — üreten taraf)
        scripts/kalibrasyon_hakemlik.py (`kosul-ihtar` kuralı — anotasyon tarafı)
        scripts/boilerplate_audit.py (çerçeve metninin ölçüm tarafı)
        data/gold/ANNOTATION_GUIDE.md §kampanya_kosullari

## Neden ayrı bir modül

«Bankamız … kampanya koşullarını değiştirme … kampanyayı durdurma hakkını
saklı tutar.» cümlesi **koşul değildir**. Her kampanya metninde birebir aynı
geçtiği için kıyasta sıfır ayırt edici bilgi taşır: bu cümle "koşul" diye
sayılırsa iki bankanın koşul listesi birbirine benzer görünür ve
`kampanya_kosullari` üzerinden yapılan her karşılaştırma yapay olarak
yumuşar.

Kural önce yalnız ANOTASYON tarafında uygulandı (`kalibrasyon_hakemlik.py`,
`kosul-ihtar`, 18 hücre temizlendi) ama ÇIKARICI cümleyi üretmeye devam etti.
Sonuç ölçüldü (2026-08-09): 20 kalibrasyon belgesinin **5'inde** model değeri
ihtar cümlesi taşıyor, gold taşımıyor — yani model o satırlarda **haksız
yere** yanlış sayılıyordu. `data/demo.db` genelinde aynı sızıntı 1774
belgenin **248'inde** vardı.

Desen İKİ KOPYA olarak yaşarsa bu hata sessizce geri gelir: bir taraf
güncellenir, öteki güncellenmez ve fark yine "model yanlış" diye okunur.
Bu yüzden desen burada TEK kez tanımlıdır; iki taraf da buradan okur.
`tests/test_ihtar_tek_kaynak.py` kopyaların ayrışmasını kapıda tutar.
"""

from __future__ import annotations

import re
from typing import Iterable

#: Genel yasal ihtar kalıbı. Üç yüz görülüyor (gerçek korpustan):
#:   1. "… değiştirme / iptal etme hakkını saklı tutar"
#:   2. "… değişiklik yapma ve/veya kampanyayı durdurma …"
#:   3. "Bu metin bilgilendirme amaçlıdır."
#: Üçü de kampanyaya ÖZGÜ hiçbir kısıt taşımaz.
#:
#: ## DESEN GENİŞLETİLDİ (2026-08-20) — ölçüldü
#:
#: Üç yüzlü dar desen gerçek korpusta ihtarın YALNIZCA bir çekimini görüyordu:
#: "hakkını saklı tutar" ve tam sırayla "değişiklik yapma … durdurma". Bankalar
#: aynı cümleyi üç ayrı kalıpla yazıyor ve ikisi süzgeçten geçiyordu
#: (gold.v2, 48 belge, `kampanya_kosullari` yanlış pozitiflerinden sayıldı):
#:
#:   "… kampanyayı dilediği zaman durdurma ve/veya kampanya koşullarını
#:    değiştirme hakkına sahiptir."            (Emlak ×3, Hayat Finans, BKM)
#:   "… kampanya koşullarını dilediği zaman durdurma ve değiştirme hakkına
#:    sahiptir."                               (Türkiye Finans)
#:   "… kar payı oranlarını … değişiklik yapma hakkına sahiptir."  (Kuveyt Türk)
#:   "… önceden haber vermeden kampanya koşullarında değişiklik yapabilir ya da
#:    kampanyayı sonlandırabilir."             (Kuveyt Türk ×2)
#:
#: Yani K2 kuralı ("genel yasal ihtar koşul DEĞİLDİR") kodda üç bankada hiç
#: uygulanmıyordu: 9 yanlış pozitif kalem. Dar desen "sahiptir/yetkisine
#: sahiptir" ailesini ve fiil çekimini (yapabilir/sonlandırabilir) kaçırıyordu.
#:
#: GÜVENLİK KAPISI: yeni desen gold.v2'nin **137 gerçek koşul kaleminin
#: hiçbirine** ateşlenmiyor (`tests/test_kampanya_kosullari_kalite.py`
#: KAPI 2 bunu kilitler). Yani genişleme geri çağırmadan bir şey yemiyor.
#:
#: `[^.]{0,140}` sınırı KASITLI: "hakkına sahiptir" ile fiil arasına cümle
#: sınırı girmesin. Desen cümle bazında (`ihtar_mi`) çağrıldığı için nokta
#: dışlaması pratikte "aynı cümle" demektir.
IHTAR_RE = re.compile(
    r"hakk[ıi]n[ıi]\s+sakl[ıi]\s+tutar|"
    r"de[ğg]i[şs]iklik\s+yapma\s+(?:ve/?veya\s+)?(?:kampanyay[ıi]\s+)?durdurma|"
    r"bilgilendirme\s+ama[çc]l[ıi]d[ıi]r|"
    # "… durdurma / değiştirme / iptal etme HAKKINA | YETKİSİNE sahiptir"
    r"(?:de[ğg]i[şs]iklik\s+yapma|de[ğg]i[şs]tirme|durdurma|sonland[ıi]rma|"
    r"iptal\s+etme|sona\s+erdirme)"
    r"[^.]{0,140}?(?:hakk[ıi]na|yetkisine|hakk[ıi]|yetkisi)\s*"
    r"(?:sahip\w*|bulunmaktad[ıi]r|vard[ıi]r)|"
    # "önceden haber vermeden … değiştirebilir / sonlandırabilir"
    r"[öo]nceden\s+(?:haber\s+ver\w*|bildirim\w*|bilgi\s*ver\w*)"
    r"[^.]{0,160}?(?:de[ğg]i[şs]\w*|sonland[ıi]r\w*|durdur\w*|iptal\s+ed\w*)",
    re.IGNORECASE)


def ihtar_mi(cumle: str) -> bool:
    """Cümle genel yasal ihtar mı? (koşul DEĞİL demektir)"""
    return bool(IHTAR_RE.search(cumle or ""))


def ihtar_ayikla(cumleler: Iterable[str]) -> list[str]:
    """Koşul listesinden ihtar cümlelerini düşürür; sıra korunur.

    Geriye hiç koşul kalmazsa boş liste döner — çağıran tarafın alanı
    ÜRETMEMESİ beklenir (uydurma yok: elde koşul yoksa `kampanya_kosullari`
    da yoktur).
    """
    return [c for c in cumleler if c and not ihtar_mi(c)]
