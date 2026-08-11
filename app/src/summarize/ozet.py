"""LLM ile kısa belge özeti — **yalnız gösterim**, ölçülen hiçbir yola girmez.

İlgili: ../preprocessing/blocks.py (katlanmış metin), ../../scripts/build_summaries.py
        ../../eval/predictors.py (ölçülmeyen şey ölçülmüş gibi raporlanmaz)
        CLAUDE.md §11 (önceden üret), §19 (halüsinasyon yasağı: bilgi yoksa null)

## Bu özet NEREYE GİRMEZ

Özet **hiçbir** karar yolunun girdisi değildir:

  * kıyas / sıralama (`src/comparison/compare.py`)          -> girmez
  * alan çıkarımı (`src/extraction/**`)                     -> girmez
  * çelişki tespiti (`src/comparison/contradiction.py`)     -> girmez
  * chatbot'un yapısal sorgu yolu (`src/chatbot/structured`) -> girmez

Sebep: özet üretken bir modelin çıktısıdır ve doğrulanmamıştır. Ham metinden
çıkarılan her alan bir karakter aralığına (`span_start`/`span_end`) bağlıyken,
özetin böyle bir dayanağı yoktur. Onu bir ölçüm yoluna sokmak, doğrulanmış
kanıt zincirine doğrulanmamış bir halka eklemek olurdu. Özet ekranda metnin
yanında durur; iddiaların kaynağı yine ham metnin kendisidir.

## LLM kapalıysa özet ÜRETİLMEZ

Kural tabanlı bir sahte özet (ilk N cümle, en uzun cümle, anahtar sözcük
yoğunluğu) **basılmaz**. Kullanıcı ekranda "özet" etiketini gördüğünde onu
modelin ürettiğini varsayar; ilk üç cümleyi özet diye sunmak ölçülmemiş bir
yeteneği ölçülmüş gibi göstermektir. Aynı ilke `eval/predictors.py` içinde
zaten uygulanıyor: LLM kapalıyken sahte bir "hibrit = kural" satırı üretmek
yerine konfig ATLANIYOR ve sebebi yazılıyor. Burada da karşılığı `ozet=None` +
`sebep` alanıdır.

## Neden katlanmış metin

Modele giden metin, `blocks.gorunur_metin()` ile çerçevesi katlanmış metindir.
İki gerekçe:

1. **Bağlam bütçesi.** Çerez/KVKK/site haritası blokları bazı belgelerde
   metnin yarısını kaplıyor; bağlam penceresini onlarla doldurmak gerçek
   kampanya cümlelerinin kırpılmasına yol açar.
2. **Tutarlılık.** Panelde katlanan bir bloğu özetin anlatması, kullanıcının
   ekranda göremediği bir şeyi iddia etmek olurdu.

Ham metnin kendisi DEĞİŞMEZ; katlama yalnızca bu modülün modele verdiği
kopyada geçerlidir (bkz. `blocks.gorunum_araliklari` docstring'i).

## Bağlam penceresi

Ollama'nın varsayılan bağlamı 2048'dir ve fazlasını **sessizce baştan kırpar**
— yani sistem yönergesi kaybolur. `OllamaClient` bunu `OLLAMA_NUM_CTX` (öntanım
8192) ile açıkça set eder; `scripts/build_summaries.py` da değişkeni açıkça
verir. `MAKS_GIRDI_KARAKTER` bu pencereye sığmayan belgeleri kırpar ve kırpma
`OzetSonucu.kirpildi` ile **görünür** kalır.

## Alfabe kapısı: Latin dışına kayan özet REDDEDİLİR

Yerel model (`qwen2.5:7b-instruct`) üretimin ORTASINDA dil değiştirebiliyor.
Ölçüldü (2026-08-11, `data/demo.db`, 1751 özet): **67 özet** Türkçenin
kullanmadığı bir alfabeye taşmıştı — 65'i Çince ideogram, biri Kiril harfi,
ikisi yalnız Çin noktalaması. Kaymalar kelimenin ortasına giriyordu:

    "…finansman tutarı, vade süresi ve kâr oranı gibi faktörlerden зависecektir."
    "…500 TL nakit iade提供的优惠活动。该活动仅限每位客户一次机会…"

Bu metinler ekranda "AI özeti" etiketiyle duruyordu. Kapı bu yüzden üretimin
ÇIKIŞINDA durur: özet Latin/Türkçe alfabesinin dışında tek karakter taşısa bile
kabul edilmez ve `sebep="yabanci_alfabe"` ile `None` döner.

Elle düzeltme, çeviri ya da kırpma YOKTUR — kirli parçayı silip kalanı özet diye
sunmak, modelin yazmadığı bir metni model çıktısı gibi göstermektir. Modülün
baştan sona ilkesi aynı: **sahte özet basmaktansa özet olmaması yeğdir.**

Kapının eşiği ölçümle kalibre edildi: aynı korpusta Latin dışına taşmayan 1684
özetin hiçbiri reddedilmiyor (yanlış pozitif = 0).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from ..preprocessing.blocks import gorunur_metin

#: `ozet_kaynak` alanının tek geçerli değeri. Kural tabanlı bir kaynak YOKTUR:
#: özet ya yerel modelden gelir ya da hiç üretilmez.
OZET_KAYNAK_LLM = "llm"

#: Modele verilecek en fazla karakter. 8192 token'lık pencerede Türkçe metin
#: kabaca 3 karakter/token gider; 6000 karakter (~2000 token) yönerge, örnek
#: ve çıktı için geniş pay bırakır. Aşan belge kırpılır ve kırpma raporlanır.
MAKS_GIRDI_KARAKTER = 6000

#: Özetin en fazla kaç karakter olmasını istediğimiz. Yönergede geçer;
#: aşan çıktı REDDEDİLMEZ (model cümleyi ortadan kesmek yerine biraz taşabilir),
#: yalnızca `OzetSonucu.uzun` ile işaretlenir.
HEDEF_OZET_KARAKTER = 400

SISTEM_PROMPT = (
    "Sen bir katılım bankacılığı belgesini özetleyen yardımcısın. "
    "SADECE sana verilen metindeki bilgiyi kullan. "
    "Metinde geçmeyen hiçbir oran, tutar, vade, tarih veya koşul EKLEME; "
    "emin olmadığın hiçbir sayıyı yazma. "
    "En fazla üç cümlelik, düz ve sade Türkçe bir özet yaz: belge neyi "
    "anlatıyor, kime yönelik, hangi başlıca koşulu taşıyor. "
    "Konvansiyonel bankacılık terimlerini kullanma; metnin kendi "
    "terminolojisine sadık kal (kâr payı, finansman, katılma hesabı). "
    # Yönergedeki bu cümle KAPININ YERİNE GEÇMEZ, onu tamamlar: model
    # yönergeye uymayabilir, kapı ise uymadığında çıktıyı geçirmez.
    "Yalnızca Türkçe yaz; Türk alfabesi dışında hiçbir harf ya da "
    "noktalama işareti kullanma. "
    "Özetlenecek anlamlı bir içerik yoksa boş dize döndür. "
    'Çıktı biçimi: {"ozet": "..."}'
)

#: `sebep` alanının kapıya ait değeri — toplu raporlar bunu sayarak
#: "kaç özet alfabe kaymasından düştü" sorusunu cevaplar.
SEBEP_YABANCI_ALFABE = "yabanci_alfabe"

#: Türkçe bir özetin kullanabileceği Unicode aralıkları (kapsayıcı sınırlar).
#: Bunların DIŞINDA tek karakter = üretim ortasında dil kayması.
#:
#:   0x0000-0x024F  Temel Latin + Latin-1 + Latin Genişletilmiş A/B
#:                  (ç ğ ı İ ö ş ü â î û burada)
#:   0x2000-0x206F  Genel noktalama (– — ' ' " " … ‰)
#:   0x20A0-0x20BF  Para birimi simgeleri (₺ € ₽)
#:   0x2100-0x214F  Harf benzeri simgeler (№ ™ ℅)
#:
#: Kasıtlı olarak DAR: matematik işleçleri, oklar, emoji ve tüm Latin dışı
#: yazı sistemleri dışarıda kalır. Dar eşiğin bedeli en kötü ihtimalle bir
#: özetin `None` olmasıdır; geniş eşiğin bedeli ise ekranda Çince cümle.
TURKCE_ARALIKLARI: tuple[tuple[int, int], ...] = (
    (0x0000, 0x024F), (0x2000, 0x206F), (0x20A0, 0x20BF), (0x2100, 0x214F),
)

SEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"ozet": {"type": "string"}},
    "required": ["ozet"],
}


@dataclass(frozen=True)
class OzetSonucu:
    """Tek belgenin özet sonucu — üretilemediğinde SEBEBİ taşır.

    `ozet is None` sessiz bir başarısızlık değildir: `sebep` her zaman doludur
    ve toplu üretim raporu sebepleri sayarak "kaç belge neden özetlenemedi"
    sorusunu cevaplayabilir.
    """

    ozet: Optional[str]
    kaynak: Optional[str]
    sebep: Optional[str] = None
    kirpildi: bool = False
    girdi_karakter: int = 0

    @property
    def uretildi(self) -> bool:
        return self.ozet is not None

    @property
    def uzun(self) -> bool:
        return bool(self.ozet) and len(self.ozet) > HEDEF_OZET_KARAKTER

    def as_dict(self) -> dict:
        return {"ozet": self.ozet, "ozet_kaynak": self.kaynak,
                "sebep": self.sebep, "kirpildi": self.kirpildi,
                "girdi_karakter": self.girdi_karakter}


def llm_hazir(llm: Any) -> bool:
    """Çıkarıcı gerçekten çağrılabilir mi (`.available` + `.client`).

    `default_extractor()` LLM kapalıyken `NullLLMExtractor` döndürür; o nesne
    `available=False` taşır ve `client`'ı yoktur. İkisi de kontrol edilir,
    çünkü `available=True` olup istemcisi düşmüş bir nesne de çağrılamaz.
    """
    return bool(getattr(llm, "available", False)
                and getattr(llm, "client", None) is not None)


def alfabe_disi_karakterler(metin: str) -> list[str]:
    """Metindeki Türkçe alfabe dışı karakterler — sırayı koruyan tekil liste.

    Boş liste = metin temiz. Dönen liste hem kapı kararı hem de tanılama
    içindir: toplu temizlik betiği "hangi alfabeye kaymış" sorusunu bu
    karakterlere bakarak cevaplar.
    """
    gorulen: set[str] = set()
    disari: list[str] = []
    for ch in metin:
        if ch in gorulen:
            continue
        gorulen.add(ch)
        kod = ord(ch)
        if not any(alt <= kod <= ust for alt, ust in TURKCE_ARALIKLARI):
            disari.append(ch)
    return disari


def turkce_alfabede_mi(metin: str) -> bool:
    """Metnin tamamı Türkçenin kullandığı alfabede mi (kapının yüklemi)."""
    return not alfabe_disi_karakterler(metin)


def katlanmis_metin(text: str, cerceve: Optional[set[str]] = None, *,
                    terimler: Optional[Iterable[str]] = None) -> str:
    """Modele verilecek metin: çerçevesi katlanmış hâli (ham metin değişmez)."""
    return gorunur_metin(text, cerceve, terimler=terimler)


def ozetle(text: str, llm: Any, *, cerceve: Optional[set[str]] = None,
           terimler: Optional[Iterable[str]] = None,
           maks_karakter: int = MAKS_GIRDI_KARAKTER) -> OzetSonucu:
    """Belgenin kısa Türkçe özeti; üretilemezse `ozet=None` + `sebep`.

    Hiçbir koşulda kural tabanlı yedek üretilmez (modül docstring'i). Model
    boş dize döndürürse bu bir hata değil, geçerli bir "özetlenecek bir şey
    yok" cevabıdır ve yine `None` olarak saklanır — arayüzde boş bir özet
    kutusu göstermek yerine hiç göstermemek doğrudur.
    """
    if not llm_hazir(llm):
        return OzetSonucu(None, None, sebep="llm_kapali")

    girdi = katlanmis_metin(text, cerceve, terimler=terimler)
    if not girdi:
        return OzetSonucu(None, None, sebep="metin_bos")

    kirpildi = len(girdi) > maks_karakter
    if kirpildi:
        girdi = girdi[:maks_karakter]

    try:
        cevap = llm.client.generate_json(
            SISTEM_PROMPT, f"Belge metni:\n{girdi}", SEMA)
    except Exception as exc:  # pragma: no cover - ağ/servis hatası
        return OzetSonucu(None, None, sebep=f"llm_hatasi: {type(exc).__name__}",
                          kirpildi=kirpildi, girdi_karakter=len(girdi))

    ham = cevap.get("ozet") if isinstance(cevap, dict) else None
    ozet = " ".join(str(ham).split()) if ham else ""
    if not ozet:
        return OzetSonucu(None, None, sebep="bos_cikti", kirpildi=kirpildi,
                          girdi_karakter=len(girdi))
    # ALFABE KAPISI — kirli özet DÜZELTİLMEZ, reddedilir (modül docstring'i).
    # Kaymış karakterleri ayıklayıp kalanı yazmak, modelin üretmediği bir
    # metni "AI özeti" etiketiyle sunmak olurdu.
    if not turkce_alfabede_mi(ozet):
        return OzetSonucu(None, None, sebep=SEBEP_YABANCI_ALFABE,
                          kirpildi=kirpildi, girdi_karakter=len(girdi))
    return OzetSonucu(ozet, OZET_KAYNAK_LLM, kirpildi=kirpildi,
                      girdi_karakter=len(girdi))
