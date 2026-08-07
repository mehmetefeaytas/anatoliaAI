"""Çok-ajanlı çıkarım — rol tanımları.

İlgili: ./orchestrator.py (akış), ./extractor.py (LLMExtractor),
        ../silver/prompts.py (rol ayrımı deseni buradan alındı),
        ../../domain/terminology.py (terim kartları),
        CLAUDE.md §3 (önce kural sonra LLM), §19 (halüsinasyon yasağı)

## Yetki asimetrisi — tasarımın can damarı

Ablasyon ölçtü: **hibrit kol kuraldan daha kötü** (mikro-F1 0,612 -> 0,575,
halüsinasyon 0,102 -> 0,163). Yani "LLM ekleyelim" refleksi bu projede ölçümle
yanlışlanmış durumda. Orkestrasyon LLM sayısını artıran değil, **LLM'in
yetkisini daraltan** bir tasarım olmak zorunda:

    çıkarım ajanları  -> yalnız ÖNERİR
    hakem             -> yalnız REDDEDER (asla değer yazmaz)
    reddedilen alan   -> kural değerine düşer

Böylece orkestrasyonun en kötü hâli kural-only'dir, yani bugünkü en iyi
ölçülmüş kol. Hibrit kolun regresyonu yapısal olarak tekrarlanamaz.

## Rol ayrımı neden alan ailesine göre

Mentör önerisi: "basit alanlar için küçük/ucuz model, bağlam gerektiren alanlar
için daha yetenekli model." Donanım (RTX 5060, 8 GB) iki 8B modeli aynı anda
kaldırmıyor; ayrım bu yüzden **model düzeyinde değil, prompt ve şema
düzeyinde**. Bu sınır rapora yazılır, gizlenmez.

Ayrımın kendisi yine de değerli: sayısal alanlar biçim disiplini ister
(TR sayı formatı, birim, aralık), bağlamsal alanlar okuma ister (dipnottaki
koşul, hedef kitle negasyonu). Tek prompt ikisini birden kovalarken ikisinde de
vasat kalıyor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from ...domain.terminology import cards_for
from .extractor import LLMClient, LLMExtractor
from .schema import SYSTEM_PROMPT

#: Ajan prompt'una girecek terim kartı bütçesi. Taban sistem prompt'u ~2,6 K,
#: few-shot ~2,4 K; `OLLAMA_NUM_CTX` 8192 token (~25 K karakter) ve belge metni
#: de aynı pencereye giriyor. 1500 karakter ~4 kart demek.
KART_BUTCESI = 1500
KART_LIMITI = 6


def kart_metni(text: str, butce: int = KART_BUTCESI,
               limit: int = KART_LIMITI) -> str:
    """Bir belgenin ajan prompt'una girecek terim kartları.

    `sistem_kurucu` bunu çağırır; ölçüm betikleri de aynı kapıdan geçer. Neden
    ayrı bir ad: kart bütçesinin aşılıp aşılmadığını koşumda loglamak için
    çağıranın `cards_for`u kendi varsayılanlarıyla yeniden çağırması gerekirdi
    ve o varsayılanlar buradakilerden sessizce ayrışabilirdi. O zaman raporda
    yazan kart boyutu, modele giden kart boyutu OLMAZDI.
    """
    return cards_for(text or "", limit=limit, budget_chars=butce)


@dataclass(frozen=True)
class AgentRole:
    """Tek bir çıkarım ajanının kimliği."""

    ad: str
    alanlar: tuple[str, ...]
    yonerge: str


ROL_SAYISAL = AgentRole(
    ad="sayisal",
    alanlar=("kar_payi_orani", "finansman_tutari", "vade_ay", "taksit_sayisi",
             "tahsis_ucreti", "masraf_durumu", "odul_miktari",
             "indirim_orani", "alisveris_puani"),
    yonerge="""\
## Rolün: SAYISAL ALAN UZMANI

Yalnız ölçülebilir alanlarla ilgileniyorsun: oran, tutar, vade, taksit, ücret,
ödül, indirim, puan. Koşul cümlelerini, hedef kitleyi ve kampanya tarihlerini
BAŞKA bir ajan çıkarıyor — onları senin çıktına yazma.

Bu rolde en sık yapılan üç hata:
1. Nitel iddiadan sayı üretmek. "avantajlı kâr payı", "özel oranlı finansman",
   "düşük maliyetli" ifadelerinde SAYI YOKTUR; alan null kalır.
2. Yanlış sütunu okumak. Oran tablolarında etiketin hemen ardındaki ilk sayı
   çoğu zaman TUTAR ya da VADE'dir, oran değil. Değeri birimiyle birlikte
   doğrula.
3. Ödül/indirim ile kâr payını karıştırmak. "1.000 TL bonus" bir ödüldür
   (`odul_miktari`), finansman maliyeti değil.

Aralık gördüğünde aralık yaz: {"min": 1.99, "max": 2.49}. Tek bir uca
yuvarlama — bu, karşılaştırmayı sessizce bozar.""")


ROL_BAGLAMSAL = AgentRole(
    ad="baglamsal",
    alanlar=("kampanya_suresi", "kampanya_kosullari", "hedef_kitle"),
    yonerge="""\
## Rolün: KOŞUL VE BAĞLAM UZMANI

Yalnız kampanya süresi, koşullar ve hedef kitle ile ilgileniyorsun. Oran,
tutar, vade gibi sayısal alanları BAŞKA bir ajan çıkarıyor — onları senin
çıktına yazma.

Bu rolde en sık yapılan üç hata:
1. Dipnotu atlamak. Gerçek kısıtlar ("ilk 10.000 müşteri", üyelik şartı,
   kanal şartı) çoğu zaman sayfanın altındaki yıldızlı/küçük punto notlarda
   saklıdır. Onları da `kampanya_kosullari`na al.
2. Tarihi koşul sanmak. Yalnız geçerlilik tarihi bildiren cümle koşul
   DEĞİLDİR; o `kampanya_suresi`ne gider. Başlangıç ve bitişi BİRLİKTE ara —
   ikisinden yalnız biri varsa diğerini uydurma.
3. Negasyondan etiket üretmek. `hedef_kitle` yalnız şu etiketleri alır:
   yeni_musteri, mevcut_musteri, maas_musterisi, belirli_segment.
   "yeni müşteri olmayanlar" bir etiket DEĞİLDİR; sinyal yoksa null.

Bir sayfa birden çok ürün anlatıyorsa koşulları hangi ürüne ait olduğunu
belirterek yaz; hepsini tek torbaya atma.""")


ROLLER: tuple[AgentRole, ...] = (ROL_SAYISAL, ROL_BAGLAMSAL)


# --------------------------------------------------------------------------- #
# Sistem prompt kurucusu
# --------------------------------------------------------------------------- #

def sistem_kurucu(rol: Optional[AgentRole] = None,
                  terim_karti: bool = True,
                  butce: int = KART_BUTCESI,
                  limit: int = KART_LIMITI) -> Callable[[str], str]:
    """Belge metnini alıp o belgeye özel sistem prompt'u üreten fonksiyon.

    Neden fonksiyon, sabit dize değil: terim kartları BELGEYE bağlıdır. Sözlük
    76.200 karakter, bağlam penceresi ~25.000 — tümünü koymak imkânsız ve
    Ollama taşan bağlamı BAŞTAN kırpıp sistem prompt'unu yok ediyor. Yalnız
    belgede fiilen geçen terimler enjekte edilir.

    `terim_karti=False` ablasyon kolu içindir (Ö1: temel / sadeleştirme /
    sözlük kartı). Kart enjeksiyonunun katkısı ancak kapatılabildiği zaman
    ölçülebilir.
    """
    def kur(text: str) -> str:
        parcalar = [SYSTEM_PROMPT]
        if rol is not None:
            parcalar.append(rol.yonerge)
        if terim_karti:
            kartlar = kart_metni(text, butce=butce, limit=limit)
            if kartlar:
                parcalar.append(
                    "## Bu metinde geçen katılım finansı terimleri\n\n"
                    "Aşağıdaki ayrımlar uyum açısından bağlayıcıdır. Bir terimi\n"
                    "'DEĞİLDİR' listesindeki bir kavramla eşitleme.\n\n"
                    + kartlar)
        return "\n\n".join(parcalar)
    return kur


def ajan_kur(client: Optional[LLMClient], rol: AgentRole,
             *, strict: Optional[bool] = None,
             terim_karti: bool = True) -> LLMExtractor:
    """Bir rol için çıkarım ajanı."""
    return LLMExtractor(
        client, strict=strict, role=rol.ad, fields=rol.alanlar,
        system_builder=sistem_kurucu(rol, terim_karti=terim_karti))


# --------------------------------------------------------------------------- #
# Hakem (judge) — ÇIKARIM YAPMAZ
# --------------------------------------------------------------------------- #

HAKEM_SYSTEM = """\
Sen bir DENETLEYİCİSİN. Çıkarım YAPMIYORSUN.

Başka ajanların bir banka kampanya metninden çıkardığı alan önerileri sana
veriliyor. Görevin her öneriyi metne karşı denetlemek ve KABUL ya da RED
kararı vermek. Yeni değer üretme, mevcut değeri düzeltme, eksik alan ekleme —
bunların hiçbiri senin yetkinde değil. Yetkin yalnız reddetmektir.

SIRA ÖNEMLİ. Her öneri için şu üç adımı bu sırayla yap:
1. `source_span` metinde BİREBİR geçiyor mu? Geçmiyorsa red.
2. Değer o alıntıdan gerçekten çıkıyor mu? Alıntı başka bir kalemi
   anlatıyorsa (ör. alıntı "rehin ücreti" derken değer tahsis ücreti diye
   önerilmişse) red.
3. Değer alanın birimine uygun mu? Oran alanına tutar, tutar alanına oran
   önerilmişse red.

Emin olamadığın öneriyi REDDET. Reddedilen alan kural katmanının değerine
düşer; yanlış bir LLM değerini geçirmek, o alanı boş bırakmaktan daha
zararlıdır.

Katılım finansı terminolojisinde bir eşitleme görürsen (ör. kâr payı = faiz,
sukuk = tahvil) o öneriyi reddet ve gerekçesine yaz.

SADECE istenen JSON'u döndür; açıklama, selamlama, markdown yazma."""

HAKEM_SEMASI: dict = {
    "type": "object",
    "properties": {
        "kararlar": {
            "type": "array",
            "maxItems": 12,
            "items": {
                "type": "object",
                "properties": {
                    "alan": {"type": "string"},
                    "kabul": {"type": "boolean"},
                    "gerekce": {"type": "string"},
                },
                "required": ["alan", "kabul", "gerekce"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["kararlar"],
    "additionalProperties": False,
}

#: Hakeme gidecek belge metni kırpma sınırı — bağlam penceresi ortak.
HAKEM_METIN_SINIRI = 6000


def hakem_user_prompt(text: str, oneriler: list[dict],
                      max_chars: int = HAKEM_METIN_SINIRI) -> str:
    """Hakeme gidecek kullanıcı mesajı.

    Önerilerin hangi ajandan geldiği KASITLI olarak yazılmaz: hakem kaynağa
    değil kanıta bakmalı. (`silver/prompts.py`'deki denetleyici de öneriyi
    görmeden önce kendi kararını verir; aynı bağımsızlık kaygısı.)
    """
    import json as _json
    govde = (text or "")[:max_chars]
    kirpma = "" if len(text or "") <= max_chars else (
        f"\n[NOT: metin {max_chars} karakterde kırpıldı]")
    return (
        f"METİN:\n{govde}{kirpma}\n\n"
        f"DENETLENECEK ÖNERİLER:\n"
        f"{_json.dumps(oneriler, ensure_ascii=False, indent=1)}\n\n"
        f"Her öneri için bir karar üret. `alan` değerini birebir yukarıdaki "
        f"gibi yaz.")
