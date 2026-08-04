"""Klasik banka korpusunu "eğitimde kullanılabilir / kullanılamaz" diye ayırır.

İlgili: ../src/scraping/collector.py · ../scripts/build_silver.py · CLAUDE.md §4

## Bu araç ne YAPMAZ

Yarışma veri setine dokunmaz. `data/raw-classic/` KAPSAM DIŞI (katılım
bankacılığı yapmayan) bankalardan toplanmış bir korpustur ve tek amacı 8-sınıf
kampanya türü sınıflandırıcısı için **gümüş** eğitim verisi kaynağı olmaktır.
Altın küme (`data/gold/`) ve yarışma değerlendirmesi bu betikten etkilenmez.

## Neden gerekli

Toplanan 427 belgenin hepsi eğitilebilir değil. Ölçülmüş kirlilik türleri
(2026-08-04, bu betik gerçek korpusla koşularak doğrulandı):

- **Boş kabuk / 404**: TEB'in `FileNotFound.aspx` sayfası 3628 karakter — ama
  içeriği tamamen gezinme menüsü + "Görüntülemek istediğiniz sayfa
  bulunamadı." Uzunluk eşiği bunu YAKALAMAZ (bkz. `R_BOS_KABUK` gerekçesi).
- **Çerçeve ağırlıklı**: DenizBank'ın 9 kampanya LİSTESİ sayfası 57 KB metin
  taşıyor ama sayfaya özel içeriği 0-3 sözcük; gerisi her sayfada aynen
  tekrar eden çerçeve. Yapı Kredi'de "Test Figma", "Test BES" başlıklı test
  sayfaları 27 KB metinle korpusa girmiş.
- **Ürün olmayan sayfa**: Halkbank'ın bağış/kurban tahsilat listesi ve iki
  basın haberi (2016 reklam filmi, 2020 Milli Dayanışma bağış çağrısı).
- **Blog / sözlük / rehber**: eğitici içerik; ürün ya da kampanya değil.
- **Mükerrer metin**: aynı temiz metin farklı dosya adlarıyla.

## Yaklaşım: kararı ÇEKİRDEK metin üzerinden ver

Anahtar fikir, her belgeyi iki parçaya ayırmaktır:

    tam metin = ÇERÇEVE (aynı bankanın belgelerinde tekrar eden bloklar)
              + ÇEKİRDEK (yalnız bu belgeye ait metin)

Çerçeve, bankanın gezinme menüsü / altbilgisi / kampanya adı dizini /
çerez bandıdır. Çekirdek, belgenin gerçek bilgi taşıyan kısmıdır. Bütün
kararlar çekirdek üzerinden verilir; bu, anahtar-kelime eşleşmesini yanlış
pozitif makinesi olmaktan çıkarır:

    ÖLÇÜM (2026-08-04): "kişisel verilerin korunması" + "çerez politikası"
    ifadeleri TAM metinde 9 DenizBank + 30 Yapı Kredi belgesinde geçiyor —
    hepsi altbilgi çerçevesinden. Tam metinde arayan bir kural 39 GERÇEK
    kampanya sayfasını "KVKK sayfası" sanıp elerdi. Çekirdekte hiçbirinde
    geçmiyor. Aynı şey "nelere dikkat" için de geçerli: `data/raw/` altındaki
    3 GERÇEK ürün sayfasının SSS bölümünde geçiyor (Dünya Katılım ihtiyaç
    finansmanı, Vakıf Katılım hesaplama aracı, Türkiye Finans görüntülü
    hesap açma) — bu yüzden blog işaretçileri yalnız BAŞLIK BÖLGESİNDE
    aranır, gövdede değil.

`trainable.jsonl` hem `text` (tam metin) hem `core_text` (çerçeve ayıklanmış)
alanını yazar; aşağı akış hangisini kullanacağına kendisi karar verir.

## Kullanım

    .venv/bin/python -m scripts.split_trainable \\
        --docs data/raw-classic --out-dir data/silver

Çıktılar: `trainable.jsonl`, `excluded.jsonl`, `split_report.md`.

## Sessiz kayıp yok

Her belge tam olarak bir dosyaya düşer ve rapor `trainable + excluded ==
toplam` eşitliğini açıkça doğrular; eşitlik bozulursa betik hata koduyla
çıkar. Belgeler `<banka>/` altındaki TÜM alt klasörlerden taranır (`live/`
ve `manual/`), çünkü şartname §5.1 elle toplamaya izin veriyor ve yalnız
`live/` taramak elle eklenen belgeleri sessizce düşürürdü.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.preprocessing.clean import tr_fold, tr_fold_ascii

# --------------------------------------------------------------------------
# GEREKÇE KODLARI — sabit küme. Serbest metin gerekçe YASAK: rapor sayılabilir
# olmalı ve eşik değiştiğinde hangi kuralın kaç belgeyi elediği izlenebilmeli.
# --------------------------------------------------------------------------
R_UYGUN = "R_UYGUN"                        # eğitimde kullanılabilir
R_KISA = "R_KISA"                          # belge kendisi çok kısa
R_BOS_KABUK = "R_BOS_KABUK"                # "bulunamadı" diyen kabuk / 404
R_BLOG = "R_BLOG"                          # blog / sözlük / rehber
R_URUN_DEGIL = "R_URUN_DEGIL"              # bağış, haber, KVKK, kariyer...
R_CERCEVE_AGIRLIKLI = "R_CERCEVE_AGIRLIKLI"  # metni neredeyse tamamen çerçeve
R_MUKERRER = "R_MUKERRER"                  # aynı metin başka dosya adıyla

# Raporda sabit sıra — sayımların karşılaştırılabilir olması için.
EXCLUDE_CODES: tuple[str, ...] = (
    R_MUKERRER, R_KISA, R_BOS_KABUK, R_BLOG, R_URUN_DEGIL, R_CERCEVE_AGIRLIKLI,
)
ALL_CODES: tuple[str, ...] = (R_UYGUN, *EXCLUDE_CODES)

# --------------------------------------------------------------------------
# EŞİKLER — her biri gerçek korpusla ölçüldü. Ölçüm yorumu değiştirilmeden
# sayı değiştirilmemeli; sayı ölçümün özeti, tersi değil.
# --------------------------------------------------------------------------

# Çerçeve tespiti için sözcük n-gram uzunluğu.
#
# NEDEN SATIR DEĞİL n-GRAM: `collector.py` temiz metni beyaz boşluk
# normalleştirerek yazıyor — 427 belgenin 427'sinde satır sonu YOK, hepsi tek
# satır. Satır bazlı çerçeve tespiti bu korpusta tanım gereği çalışmaz.
# Cümle bölme de çalışmaz: menü metinlerinde noktalama yoktur ("Krediler SKY
# Limit Hayalleri yüksek olanların..." tek "cümle" olurdu).
#
# 8 seçildi: 4 gram gerçek kampanya cümlelerindeki kalıp ifadeleri
# ("kampanya koşullarında değişiklik yapma") çerçeve sayacak kadar kısa,
# 16 gram menü öğelerinin farklı sırayla dizildiği sayfalarda hiç
# eşleşmeyecek kadar uzun.
SHINGLE_SIZE = 8

# Bir n-gram kaç belgede geçerse "çerçeve" sayılır (aynı banka içinde).
#
# ÖLÇÜM (2026-08-04, 427 belge): eşik 2 iken korpus çöküyor — Yapı Kredi ve
# Akbank belgeleri `<slug>.txt` / `<slug>-2.txt` çiftleri hâlinde geliyor
# (aynı kampanyanın bireysel + KOBİ görünümü). Çift üyeleri birbirinin
# neredeyse tamamını paylaştığı için eşik 2'de GERÇEK kampanya metni de
# çerçeve sayılıyor ve çekirdeği 20 sözcüğün altına düşen belge sayısı
# 21'den 99'a çıkıyor.
#
# Eşik 3 bu çift etkisini kırıyor ve ölçülen iki uçta da doğru davranıyor:
#   - Yapı Kredi'nin `yapikrediplay.com.tr` alt sitesinden gelen 2 sayfa
#     eşik 0,5·n (=52) ile menüsü çerçeve sayılmadığı için 1397 sözcük
#     "özgün" görünüyordu; eşik 3'te menü doğru şekilde çerçeve sayılıyor ve
#     çekirdek 326-336 sözcüğe (gerçek kampanya metni) iniyor.
#   - Ziraat'in 5 üyeli Bankkart ailesi (Jest / Gold / Platinum / Emekli /
#     Prestij) eşik 3'te çerçeveye gömülmüyor, ürün sayfası olarak kalıyor.
BOILERPLATE_MIN_DOCS = 3

# Çekirdek bu sözcük sayısının ALTINDAYSA belge çerçeveden ibarettir.
#
# ÖLÇÜM (2026-08-04, 427 belge, eşik taraması): çekirdek sözcük sayısı
# 12'nin altında olan 14 belge var ve ELLE OKUNAN 14'ün 14'ü gerçekten
# atılmalıydı: 8 DenizBank kampanya LİSTESİ sayfası (çekirdek 0-3 sözcük,
# yalnız kategori adı), 1 DenizBank "deneeme kampanya" test sayfası, 4 Yapı
# Kredi test sayfası ("x", "Test Figma", "Test BES"), 1 Ziraat sayfası
# (çekirdek "İçeriğe atla" — geri kalan 1503 karakter çerez bandı + promo).
#
# 12'NİN ÜSTÜNE ÇIKILMADI, çünkü 13-20 bandında GERÇEK içerik var ve eşik 20
# olsa 7 doğru belge elenirdi: Ziraat Bankkart Jest (13) / Gold (18) /
# Platinum (16) / Emekli (20) gerçek ürün sayfaları — kardeş sayfalarla
# ortak metni çerçeveye gittiği için çekirdekleri kısa görünüyor; Halkbank
# Kampanyalı İhtiyaç Kredisi (13) ve Maaşını Halkbank'tan Alanlar (17) faiz
# tablosu taşıyor; ING 500 TL Bonus (19) kendi başına geçerli bir kampanya.
MIN_CORE_TOKENS = 12

# Belgenin KABUL eşiği — `collector.MIN_DOC_CHARS` ile aynı sayı, kasten
# yeniden tanımlandı: toplayıcının kabul eşiği değişirse bu betiğin kararı
# sessizce kaymamalı. Bu korpusta en kısa belge 214 karakter (VakıfBank
# kredili mevduat listesi), yani bugün hiçbir belgeyi elemiyor — kalıcı bir
# alt sınır olarak duruyor.
MIN_DOC_CHARS = 200

# "İçerik yok" işaretçisi + kısalık BİRLİKTE arandığı üst sınır.
#
# NEDEN UZUNLUK TEK BAŞINA YETMİYOR: geçerli ama kısa bir VakıfBank ürün
# listesi 294 karakter (`krediler-proje-ve-yatirim-kredileri.txt`) ve
# korunmalı; buna karşılık İş Bankası'nın yanlış giriş noktasından gelen boş
# kabukları 202-262 karakterdi. İkisini uzunlukla ayırmak imkânsız, o yüzden
# işaretçi şart. `collector._is_empty_result_page` ile aynı mantık.
EMPTY_RESULT_MAX_CHARS = 600
EMPTY_RESULT_MARKERS: tuple[str, ...] = (
    "bulunamadi", "sonuc yok", "kayit yok",
)

# 404 / hata sayfası işaretçileri — ÇEKİRDEKTE aranır, uzunluğa bakılmaz.
#
# NEDEN AYRI KURAL: TEB'in `FileNotFound.aspx` sayfası 3628 karakter, yani
# `EMPTY_RESULT_MAX_CHARS`ın 6 katı; kısalık kuralı onu hiç görmez. Metnin
# tamamı gezinme menüsü artı şu cümle: "Görüntülemek istediğiniz sayfa
# bulunamadı. Lütfen adresi kontrol ederek tekrar deneyin." Bu cümle korpusta
# 2 TEB belgesinde geçtiği için (eşik 3) çerçeveye gitmiyor ve çekirdekte
# kalıyor — kural tam da orada yakalıyor.
NOT_FOUND_MARKERS: tuple[str, ...] = (
    "sayfa bulunamadi", "sayfayi bulamadik", "adresi kontrol ederek",
    "aradiginiz sayfaya ulasilamiyor",
)

# BAŞLIK BÖLGESİ uzunluğu — içerik türü kararları yalnız burada aranır.
#
# NEDEN: "nelere dikkat" ifadesi gerçek ürün sayfalarının SSS bölümünde
# geçiyor (yukarıdaki modül açıklamasındaki ölçüm). Blog/sözlük sayfalarında
# ise BAŞLIKTA geçer ("Kredi Kartı Terimleri Sözlüğü", "Kredi Kullanırken
# Nelere Dikkat Edilmeli"). 200 karakter, korpustaki en uzun çekirdek
# başlığını (Yapı Kredi'nin 137 karakterlik kampanya başlığı) rahat kapsıyor.
TITLE_ZONE_CHARS = 200

# Blog / sözlük / rehber işaretçileri — BAŞLIK BÖLGESİNDE aranır.
#
# ÖLÇÜLMÜŞ ÖRNEKLER (2026-08-04, korpusta gerçekten var):
#   - QNB `qnbcard.com.tr/kart-sozlugu` — "Kart Sözlüğü": terim başlıkları
#     listesi, ürün/kampanya bilgisi yok.
#   - QNB `qnb.com.tr/dijitalkopru/akademi/...` — "Akademi Blog" etiketli,
#     "Okuma Süresi 3 dk" başlıklı eğitici yazılar.
# "okuma suresi" işaretçisi kasten listede: blog altyapılarının okuma süresi
# rozetini bankacılık ürün sayfalarında kullanan bir örnek ÖLÇÜLMEDİ, ama
# blog yazılarının hepsinde var.
BLOG_TITLE_MARKERS: tuple[str, ...] = (
    "terimleri sozlugu", "sozlugu", "sozluk", "nelere dikkat",
    "dikkat edilmeli", "dikkat edilir", "bilmeniz gerekenler", "ipuclari",
    "nedir ve nasil", "hakkinda bilmeniz", "akademi blog", "okuma suresi",
)
# URL yol parçası (segment) eşleşmesi — parça bu ön eklerden biriyle
# BAŞLIYORSA blog sayılır. Parça bazlı eşleşme şart: alt dize eşleşmesi
# `.../play-karta-ozel-...-egitim-ve-kariyer-platformlarinda-...` gibi gerçek
# bir kampanya URL'sini "kariyer sayfası" sanıyordu (ölçülmüş yanlış pozitif).
BLOG_URL_SEGMENTS: tuple[str, ...] = (
    "blog", "sozluk", "rehber", "makale", "bilgi-merkezi", "akademi",
)

# Ürün/kampanya olmayan sayfa işaretçileri — BAŞLIK BÖLGESİNDE aranır.
NON_PRODUCT_TITLE_MARKERS: tuple[str, ...] = (
    "bagis ve kurban", "kurban tahsilat", "bagis tahsilat",
    "yardim kampanyalari", "reklam kampanyasi", "cerez politikasi",
    "gizlilik politikasi", "kisisel verilerin korunmasi", "kvkk aydinlatma",
    "site haritasi", "basin bulteni", "milli dayanisma kampanyasi",
)
NON_PRODUCT_URL_SEGMENTS: tuple[str, ...] = (
    "iletisim", "kariyer", "insan-kaynaklari", "haberler", "duyurular",
    "basin", "kvkk", "cerez", "gizlilik", "site-haritasi",
    "yatirimci-iliskileri", "hakkimizda", "bagis", "surdurulebilirlik",
    "sosyal-sorumluluk", "etik", "bize-ulasin", "sikayet",
)

# LİSTELEME (dizin) SAYFASI — URL yolu kampanya kökünü gösteriyorsa sayfa tek
# bir kampanyanın detayı değil, kampanya ADLARININ listesidir.
#
# NEDEN ÇEKİRDEK UZUNLUĞU YETMİYOR (2026-08-04 ölçümü): bu sayfaların çekirdeği
# KISA DEĞİL — Akbank `/kampanyalar` 107, İş Bankası `/kampanyalar` 972,
# Bonus `/kampanyalar` 3803 sözcük. Çekirdek eşiği 12 olduğu için hiçbiri
# yakalanmıyordu ve 19 dizin sayfası "kullanılabilir" sayılıyordu. Ama içerik
# kampanya adı + kategori adı listesinden ibaret ("Tüm Kampanyalar Bireysel
# Kurumsal Mobilden Akbanklı Olanlara Genç Akbanklı ... Seçiniz 2025 2026").
# Tek etiketli bir sınıflandırıcı için bu sayfa gürültüdür: onlarca farklı
# kampanya türünün adını taşır, hiçbirinin detayını taşımaz.
#
# ÖLÇÜM: kural 19 belge eledi; 19'unun 19'u elle açılıp okundu ve hepsi dizin
# çıktı (Akbank + Axess, Garanti + Bonus, Halkbank + Paraf x3, ING, İş
# Bankası x3, TEB, Yapı Kredi x4 kart alt sitesi + `kategori/kobi`,
# Bankkart ana sayfası, DenizBank `/kampanya`). Yanlış pozitif yok.
#
# ARŞİV KAMPANYA DETAYLARI KORUNUR, ARŞİV DİZİNİ ELENİR: eşleşme yol
# parçasının TAMAMIYLA yapılır, ön ekle değil. Böylece QNB'nin
# `/kampanyalar/arsivdeki-kampanyalar` DİZİNİ eleniyor ama DenizBank'ın
# `/kampanya/arsivdeki-kampanyalar/<slug>-18027` KAMPANYA DETAYI elenmiyor
# (son parça kampanya slug'ı). Bu ayrım kritik: "Kampanya bulunamadı" deyip
# altında "Geçmiş Kampanyalarımız" başlığıyla GERÇEK arşiv içeriği taşıyan
# 31 İş Bankası belgesi kullanılabilir sayılmak zorunda.
LISTING_LAST_SEGMENTS: tuple[str, ...] = (
    "kampanyalar", "kampanya", "kampanyalarimiz", "tum-kampanyalar",
    "firsatlar", "arsivdeki-kampanyalar", "gecmis-kampanyalar",
    "arsiv-kampanyalar",
)
# Yol içinde bu parça varsa sayfa kategori listelemesidir
# (`/kampanyalar/kategori/kobi/`).
LISTING_PATH_SEGMENTS: tuple[str, ...] = ("kategori",)
_URL_EXT_RE = re.compile(r"\.(html?|aspx|php|jsp)$")

# Rapordaki BİLGİ AMAÇLI uyarı: bu kadar çok "Kampanya" geçen belge tek bir
# kampanyanın detayı değil, çok-kampanyalı bir toplama sayfasıdır. Ölçüm
# (2026-08-04): Garanti BBVA'nın 209 KB'lık "Gençlik Bankacılığı" sayfası
# 735 kez "Kampanya" geçiriyor ve onlarca kampanyanın koşullarını art arda
# taşıyor. ELEME YAPILMIYOR — tek etiketli eğitim için sorunlu olduğu ölçüldü
# ama hangi eşikte kaç belgenin gerçekten çok-kampanyalı olduğu ELLE
# DOĞRULANMADI; o yüzden yalnız raporlanıyor.
MULTI_CAMPAIGN_WARN_HITS = 200

_WORD_RE = re.compile(r"\w+", re.UNICODE)


@dataclass
class Doc:
    """Korpustan okunmuş tek belge + provenance."""

    doc_id: str
    bank: str
    rel_path: str
    text: str
    title: Optional[str] = None
    source_url: Optional[str] = None
    scraped_at: Optional[str] = None
    # Çerçeve ayıklandıktan sonra kalan metin (`_split_core` doldurur).
    core_text: str = ""
    core_tokens: int = 0
    total_tokens: int = 0
    decision: str = ""
    detail: str = ""
    duplicate_of: Optional[str] = None
    warnings: list[str] = field(default_factory=list)

    @property
    def novelty_ratio(self) -> float:
        """Çekirdek sözcüklerin toplam sözcüklere oranı (0..1)."""
        if not self.total_tokens:
            return 0.0
        return self.core_tokens / self.total_tokens


def _tokens(text: str) -> list[str]:
    """Sözcük listesi — özgün büyük/küçük harfi KORUR (çekirdek okunabilir kalsın)."""
    return _WORD_RE.findall(text)


def text_key(text: str) -> str:
    """Tekilleştirme anahtarı: beyaz boşluk normalize edilmiş metnin sha256'sı.

    `collector._text_key` ile AYNI mantık; kasten kopyalandı çünkü bu betik
    toplayıcıdan bağımsız koşabilmeli (elle eklenen `manual/` belgeleri
    toplayıcıdan hiç geçmez).
    """
    return hashlib.sha256(
        re.sub(r"\s+", " ", text).strip().encode("utf-8")).hexdigest()


def iter_docs(docs_dir: str) -> list[Doc]:
    """`<docs_dir>/<banka>/**/*.txt` belgelerini oku (yanındaki meta ile).

    doc_id kuralı `scripts/build_silver._iter_docs` ile aynı tutuldu:
    `<banka>--<dosya adı>` (uzantısız). İki hat aynı belgeden bahsederken
    aynı kimliği kullanmalı, aksi hâlde raporlar birleştirilemez.
    """
    out: list[Doc] = []
    for bank in sorted(os.listdir(docs_dir)):
        bdir = os.path.join(docs_dir, bank)
        if not os.path.isdir(bdir):
            continue
        for root, dirs, files in os.walk(bdir):
            dirs.sort()
            for fn in sorted(files):
                if not fn.endswith(".txt"):
                    continue
                path = os.path.join(root, fn)
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                meta: dict[str, object] = {}
                mpath = path + ".meta.json"
                if os.path.exists(mpath):
                    try:
                        with open(mpath, encoding="utf-8") as fh:
                            meta = json.load(fh)
                    except (OSError, ValueError):
                        # Bozuk meta belgeyi DÜŞÜRMEZ: provenance eksikliği
                        # eğitilebilirlik kararını etkilemez, sessiz kayıp ise
                        # bu betiğin tek yasağı.
                        meta = {}
                title = meta.get("title")
                url = meta.get("source_url")
                out.append(Doc(
                    doc_id=f"{bank}--{fn[:-4]}",
                    bank=bank,
                    rel_path=os.path.relpath(path, docs_dir),
                    text=text,
                    title=title if isinstance(title, str) else None,
                    source_url=url if isinstance(url, str) else None,
                    scraped_at=(meta.get("scraped_at")
                                if isinstance(meta.get("scraped_at"), str)
                                else None),
                ))
    return out


def boilerplate_shingles(texts: list[str], min_docs: int = BOILERPLATE_MIN_DOCS,
                         size: int = SHINGLE_SIZE) -> set[str]:
    """Aynı bankanın belgelerinde `min_docs` veya daha fazlasında geçen n-gramlar.

    Belge sayısı `min_docs`ın altındaysa BOŞ küme döner: 2 belgeden çerçeve
    çıkarmaya kalkmak, iki belgenin ortak olan gerçek içeriğini de siler.
    """
    if len(texts) < min_docs:
        return set()
    df: collections.Counter[str] = collections.Counter()
    for text in texts:
        words = [tr_fold(w) for w in _tokens(text)]
        seen = {" ".join(words[i:i + size])
                for i in range(max(0, len(words) - size + 1))}
        df.update(seen)
    return {gram for gram, n in df.items() if n >= min_docs}


def core_text(text: str, boiler: set[str], size: int = SHINGLE_SIZE) -> str:
    """Çerçeve n-gramlarının kapsadığı sözcükleri atıp kalan metni döndürür.

    Bir sözcük, çerçeve sayılan HERHANGİ bir n-gramın içinde geçiyorsa atılır.
    Kapsama (pencere içindeki tüm sözcükleri işaretlemek) şart: yalnız
    n-gramın ilk sözcüğünü atmak menüyü paramparça bırakır ve geriye
    okunamayan sözcük çöplüğü kalır.
    """
    words = _tokens(text)
    if not boiler or len(words) < size:
        return " ".join(words)
    folded = [tr_fold(w) for w in words]
    is_boiler = [False] * len(words)
    for i in range(len(words) - size + 1):
        if " ".join(folded[i:i + size]) in boiler:
            for j in range(i, i + size):
                is_boiler[j] = True
    return " ".join(w for w, b in zip(words, is_boiler, strict=True) if not b)


def _url_segments(url: Optional[str]) -> list[str]:
    """URL yolunu parçalara ayır (diakritiksiz, küçük harf)."""
    if not url:
        return []
    path = re.sub(r"^[a-zA-Z]+://[^/]*", "", url)
    path = path.split("?", 1)[0].split("#", 1)[0]
    return [tr_fold_ascii(seg) for seg in path.split("/") if seg]


def _title_zone(doc: Doc) -> str:
    """Başlık bölgesi: meta başlık + URL son parçası + çekirdeğin başı.

    Üçü birlikte kullanılıyor çünkü hiçbiri tek başına güvenilir değil:
    meta başlık bazen jenerik ("Türk Ekonomi Bankasi"), URL bazen anlamsız
    (`/kampanyalar/detay/250218`), çekirdeğin başı bazen boş.
    """
    segments = _url_segments(doc.source_url)
    last = segments[-1].replace("-", " ") if segments else ""
    parts = [doc.title or "", last, doc.core_text[:TITLE_ZONE_CHARS]]
    return tr_fold_ascii(" ".join(parts))


def _first_hit(haystack: str, needles: tuple[str, ...]) -> Optional[str]:
    for needle in needles:
        if needle in haystack:
            return needle
    return None


def _segment_hit(segments: list[str],
                 prefixes: tuple[str, ...]) -> Optional[str]:
    for seg in segments:
        for pref in prefixes:
            if seg.startswith(pref):
                return pref
    return None


def is_listing_url(url: Optional[str]) -> Optional[str]:
    """URL bir kampanya DİZİN sayfasını mı gösteriyor? (gerekçe metni veya None)

    `source_url` yoksa None döner — meta eksikliği belgeyi elemek için gerekçe
    değildir. Bu ayrım şart: URL'siz belgede "yol boş" koşulu doğru görünür ve
    kural yanlışlıkla TÜM belgeleri elerdi.
    """
    if not url or not url.strip():
        return None
    segments = _url_segments(url)
    if not segments:
        return "url site kokunu gosteriyor (kampanya detayi degil)"
    hit = _segment_hit(segments, LISTING_PATH_SEGMENTS)
    if hit:
        return f"url yol parcasi '{hit}' (kategori listelemesi)"
    last = _URL_EXT_RE.sub("", segments[-1])
    if last in LISTING_LAST_SEGMENTS:
        return f"url '{last}' ile bitiyor (kampanya dizini)"
    return None


def classify(doc: Doc) -> tuple[str, str]:
    """(gerekçe kodu, ayrıntı) — kural sırası KASITLI.

    Sıra: MUKERRER → KISA → BOS_KABUK → BLOG → URUN_DEGIL → CERCEVE
    (CERCEVE içinde: önce listeleme URL'si, sonra çekirdek uzunluğu).

    Neden bu sıra: en dar ve en kesin kural önce gelir. Mükerrer bir belge
    zaten korpusta var, başka hiçbir gerekçeye bakmaya gerek yok. Kısalık ve
    boş kabuk mekanik ölçümlerdir. İçerik türü (blog / ürün değil) çerçeve
    ölçümünden ÖNCE gelir, çünkü elenen belgenin NEDEN elendiğini bilmek
    raporu kullanılır kılar: "bağış sayfası" bilgisi "çerçeve ağırlıklı"dan
    daha çok şey söyler.
    """
    if doc.duplicate_of:
        return R_MUKERRER, f"ayni metin: {doc.duplicate_of}"

    if len(doc.text) < MIN_DOC_CHARS:
        return R_KISA, f"{len(doc.text)} karakter < {MIN_DOC_CHARS}"

    folded_all = tr_fold_ascii(doc.text)
    if len(doc.text) <= EMPTY_RESULT_MAX_CHARS:
        hit = _first_hit(folded_all, EMPTY_RESULT_MARKERS)
        if hit:
            return R_BOS_KABUK, f"isaretci '{hit}' + {len(doc.text)} karakter"
    folded_core = tr_fold_ascii(doc.core_text)
    hit = _first_hit(folded_core, NOT_FOUND_MARKERS)
    if hit:
        return R_BOS_KABUK, f"cekirdekte 404 isaretcisi: '{hit}'"

    zone = _title_zone(doc)
    segments = _url_segments(doc.source_url)
    hit = _first_hit(zone, BLOG_TITLE_MARKERS)
    if hit:
        return R_BLOG, f"baslik bolgesinde '{hit}'"
    hit = _segment_hit(segments, BLOG_URL_SEGMENTS)
    if hit:
        return R_BLOG, f"url parcasi '{hit}'"

    hit = _first_hit(zone, NON_PRODUCT_TITLE_MARKERS)
    if hit:
        return R_URUN_DEGIL, f"baslik bolgesinde '{hit}'"
    hit = _segment_hit(segments, NON_PRODUCT_URL_SEGMENTS)
    if hit:
        return R_URUN_DEGIL, f"url parcasi '{hit}'"

    listing = is_listing_url(doc.source_url)
    if listing:
        return R_CERCEVE_AGIRLIKLI, f"listeleme sayfasi: {listing}"

    if doc.core_tokens < MIN_CORE_TOKENS:
        return R_CERCEVE_AGIRLIKLI, (
            f"cekirdek {doc.core_tokens} sozcuk < {MIN_CORE_TOKENS} "
            f"(toplam {doc.total_tokens})")

    return R_UYGUN, f"cekirdek {doc.core_tokens}/{doc.total_tokens} sozcuk"


def split_corpus(docs: list[Doc]) -> list[Doc]:
    """Tüm belgeleri sırayla işaretle: çerçeve çıkar, tekilleştir, sınıflandır.

    Belgeler yerinde güncellenir ve aynı liste döner (çağıran taraf sırayı
    korusun). Sıra deterministiktir: `iter_docs` banka ve dosya adına göre
    sıralı okur, tekilleştirmede İLK gören kazanır.
    """
    by_bank: dict[str, list[Doc]] = collections.defaultdict(list)
    for doc in docs:
        by_bank[doc.bank].append(doc)

    for bank_docs in by_bank.values():
        boiler = boilerplate_shingles([d.text for d in bank_docs])
        for doc in bank_docs:
            doc.total_tokens = len(_tokens(doc.text))
            doc.core_text = core_text(doc.text, boiler)
            doc.core_tokens = len(_tokens(doc.core_text))

    seen: dict[str, str] = {}
    for doc in docs:
        key = text_key(doc.text)
        if key in seen:
            doc.duplicate_of = seen[key]
        else:
            seen[key] = doc.doc_id

    for doc in docs:
        doc.decision, doc.detail = classify(doc)
        hits = len(re.findall("Kampanya", doc.text))
        if doc.decision == R_UYGUN and hits >= MULTI_CAMPAIGN_WARN_HITS:
            doc.warnings.append(f"cok-kampanyali olabilir ('Kampanya' x{hits})")
    return docs


def _record(doc: Doc) -> dict[str, object]:
    """JSONL satırı — provenance ve ölçümler kayıtta kalır."""
    return {
        "doc_id": doc.doc_id,
        "bank_slug": doc.bank,
        "rel_path": doc.rel_path,
        "source_url": doc.source_url,
        "scraped_at": doc.scraped_at,
        "title": doc.title,
        "reason": doc.decision,
        "reason_detail": doc.detail,
        "chars": len(doc.text),
        "total_tokens": doc.total_tokens,
        "core_tokens": doc.core_tokens,
        "novelty_ratio": round(doc.novelty_ratio, 4),
        "warnings": doc.warnings,
        "text": doc.text,
        "core_text": doc.core_text,
    }


def write_jsonl(path: str, docs: list[Doc]) -> int:
    with open(path, "w", encoding="utf-8") as fh:
        for doc in docs:
            fh.write(json.dumps(_record(doc), ensure_ascii=False) + "\n")
    return len(docs)


def _table(header: list[str], rows: list[list[str]]) -> str:
    align = "|" + "|".join(["---"] + ["--:"] * (len(header) - 1)) + "|"
    lines = ["| " + " | ".join(header) + " |", align]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def build_report(docs: list[Doc], docs_dir: str) -> str:
    """`split_report.md` içeriği — banka başına ve gerekçe başına sayım."""
    trainable = [d for d in docs if d.decision == R_UYGUN]
    excluded = [d for d in docs if d.decision != R_UYGUN]
    banks = sorted({d.bank for d in docs})
    per: dict[tuple[str, str], int] = collections.Counter(
        (d.bank, d.decision) for d in docs)

    out: list[str] = [
        "# Eğitilebilirlik Ayrımı Raporu",
        "",
        "> Otomatik üretildi: `python -m scripts.split_trainable`. "
        "Elle düzenlemeyin — yeniden koşuda üzerine yazılır.",
        "",
        f"- **Kaynak:** `{docs_dir}`",
        f"- **Toplam belge:** {len(docs)}",
        f"- **Kullanılabilir (`{R_UYGUN}`):** {len(trainable)}",
        f"- **Kullanılamaz:** {len(excluded)}",
        f"- **Toplam doğrulaması:** {len(trainable)} + {len(excluded)} = "
        f"{len(trainable) + len(excluded)} "
        f"({'TAMAM' if len(trainable) + len(excluded) == len(docs) else 'BOZUK'})",
        "",
        "## Gerekçe Başına Sayım",
        "",
    ]
    counts = collections.Counter(d.decision for d in docs)
    out.append(_table(
        ["Gerekçe", "Belge", "Oran"],
        [[f"`{code}`", str(counts.get(code, 0)),
          f"%{100 * counts.get(code, 0) / max(1, len(docs)):.1f}"]
         for code in ALL_CODES],
    ))

    out += ["", "## Banka Başına Dağılım", ""]
    out.append(_table(
        ["Banka", "Toplam", "Kullanılabilir", *[c.replace("R_", "")
                                                for c in EXCLUDE_CODES]],
        [[f"`{bank}`",
          str(sum(per[(bank, c)] for c in ALL_CODES)),
          str(per[(bank, R_UYGUN)]),
          *[str(per[(bank, c)]) for c in EXCLUDE_CODES]]
         for bank in banks],
    ))

    out += ["", "## Eşikler", "",
            f"- `SHINGLE_SIZE` = {SHINGLE_SIZE} sözcük",
            f"- `BOILERPLATE_MIN_DOCS` = {BOILERPLATE_MIN_DOCS} belge",
            f"- `MIN_CORE_TOKENS` = {MIN_CORE_TOKENS} sözcük",
            f"- `MIN_DOC_CHARS` = {MIN_DOC_CHARS} karakter",
            f"- `EMPTY_RESULT_MAX_CHARS` = {EMPTY_RESULT_MAX_CHARS} karakter",
            "",
            "Gerekçeler için `scripts/split_trainable.py` sabit yorumlarına bakın.",
            "", "## Elenen Belgeler", ""]
    out.append(_table(
        ["Gerekçe", "doc_id", "Krkt", "Çekirdek", "Ayrıntı"],
        [[f"`{d.decision}`", f"`{d.doc_id}`", str(len(d.text)),
          str(d.core_tokens), d.detail]
         for d in sorted(excluded, key=lambda d: (d.decision, d.doc_id))],
    ))

    warned = [d for d in trainable if d.warnings]
    out += ["", "## Uyarılar (elenmedi, bilgi amaçlı)", ""]
    if warned:
        out.append(_table(
            ["doc_id", "Krkt", "Uyarı"],
            [[f"`{d.doc_id}`", str(len(d.text)), "; ".join(d.warnings)]
             for d in sorted(warned, key=lambda d: -len(d.text))],
        ))
    else:
        out.append("Yok.")

    out += ["", "## Çekirdek Uzunluğu Dağılımı (kullanılabilir belgeler)", ""]
    if trainable:
        cores = sorted(d.core_tokens for d in trainable)
        out.append(_table(
            ["Ölçü", "Değer"],
            [["en az", str(cores[0])],
             ["%10", str(cores[len(cores) // 10])],
             ["ortanca", str(cores[len(cores) // 2])],
             ["%90", str(cores[9 * len(cores) // 10])],
             ["en çok", str(cores[-1])]],
        ))
    else:
        out.append("Kullanılabilir belge yok.")
    return "\n".join(out) + "\n"


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="split_trainable",
        description="Klasik banka korpusunu eğitilebilir / eğitilemez diye ayırır.")
    ap.add_argument("--docs", default="data/raw-classic",
                    help="korpus kökü (varsayılan: data/raw-classic)")
    ap.add_argument("--out-dir", default="data/silver",
                    help="çıktı klasörü (varsayılan: data/silver)")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.docs):
        print(f"HATA: korpus klasörü yok: {args.docs}")
        return 2
    docs = iter_docs(args.docs)
    if not docs:
        print(f"HATA: {args.docs} altında .txt belge bulunamadı.")
        return 2

    split_corpus(docs)
    trainable = [d for d in docs if d.decision == R_UYGUN]
    excluded = [d for d in docs if d.decision != R_UYGUN]
    if len(trainable) + len(excluded) != len(docs):
        print("HATA: sessiz kayıp — trainable + excluded != toplam")
        return 3

    os.makedirs(args.out_dir, exist_ok=True)
    tpath = os.path.join(args.out_dir, "trainable.jsonl")
    epath = os.path.join(args.out_dir, "excluded.jsonl")
    rpath = os.path.join(args.out_dir, "split_report.md")
    write_jsonl(tpath, trainable)
    write_jsonl(epath, excluded)
    with open(rpath, "w", encoding="utf-8") as fh:
        fh.write(build_report(docs, args.docs))

    counts = collections.Counter(d.decision for d in docs)
    print(f"toplam {len(docs)} belge | kullanilabilir {len(trainable)} | "
          f"elenen {len(excluded)}")
    for code in EXCLUDE_CODES:
        if counts.get(code):
            print(f"  {code:22} {counts[code]}")
    print(f"{tpath}\n{epath}\n{rpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
