"""FastAPI uygulaması — dashboard + chatbot backend.

İlgili: ../../entities/dashboard.md, ../../entities/chatbot.md, CLAUDE.md §7
        ../../decisions/dashboard-ve-chatbot-arayuzu.md
        CLAUDE.md §18 (yenilikçilik: güven skoru + kaynak vurgulama, çelişki tespiti)

Uçlar:
  GET  /health
  GET  /banks
  GET  /campaigns?govde=&q=&bank=&type=&belge_turu=&status=&limit=&offset=
                                         (belge listesi — ham gövde OPSİYONEL)
  GET  /search?q=&limit=                 (gruplu arama — banka / belge / tür)
  GET  /stats                            (korpusun sayısal özeti — tek istek)
  GET  /campaigns/{campaign_id}/text     (kaynak metin + alan offset'leri — vurgulama)
  GET  /compare?field=kar_payi_orani&intent=lowest&type=Konut+Finansmanı
  GET  /scoring?field=kar_payi_orani     (şeffaf skorlama: formül + adımlar)
  POST /chat            {"question": "..."}
  POST /extract         {"text": "...", "bank": "..."}   (tek metin canlı çıkarım)
  GET  /contradictions
  GET  /refresh/preview?bank=<slug>      (tazeleme ön izlemesi — ağa çıkmaz)
  POST /refresh         {"bank": "..."}  (operatör eylemi: tek bankayı ağdan tazele)
  GET  /refresh/status[/{job_id}]        (ilerleme + sonuç sayaçları)
  POST /refresh/cancel/{job_id}
  GET  /summaries/coverage               (özet kapsam sayaçları — model çağırmaz)
  POST /summaries/build                  (eksik özetleri yerel modelle üret)
  GET  /summaries/status[/{job_id}]
  POST /summaries/cancel/{job_id}
  GET  /log?yalniz_yazanlar=&metot=&yol=&baslangic=&bitis=&limit=&offset=
                                         (işlem günlüğü — denetim kaydı)
  GET  /admin/plan                       (gelecek faz: tanımlı ama KAPALI uçlar)
  POST /admin/banks | /admin/banks/{slug}/campaigns | …/products   -> 501

## İşlem günlüğü — HER istek kaydedilir, yazanlar İŞARETLENİR

Bir HTTP ara katmanı her isteği kalıcı, ekleme-only bir JSONL dosyasına yazar
(zaman, metot, yol, durum, süre, yazan-mı, istemci, iş kimliği). Yazan uçlar
(`POST`/`DELETE`) ayrıca kendi SONUÇLARINDAN türettikleri bir eylem özeti
bildirir — hangi banka, hangi iş, kaç alan. İstek gövdeleri ve sorgu dizgeleri
KAYDEDİLMEZ.

Neden var: bir canlı tazeleme `data/raw/albaraka/live/` altına 40 dosya yazdı
ve "kim tetikledi" sorusu sistemden cevaplanamadı. Şema, ne kaydedilmediği,
döndürme politikası ve "günlük yazımı isteği düşürmez" değişmezi
`src/api/gunluk.py` modül başlığındadır.

## `/summaries/*` — eksik özetleri üretir, AĞA ÇIKMAZ

Özetler yerel modelle üretilir ve `campaigns.ozet`'e yazılır. `/refresh` ham
arşive yeni belge indirdiğinde o belgeler özetsiz kalır; bu uçlar aradaki
boşluğu kapatır ve operatörü sunucuda betik koşturmaktan kurtarır. Model
yereldir, internet gerekmez. Gerekçenin tamamı `src/summarize/ozet_isi.py`
modül başlığındadır.

## `/admin/*` — gelecek faz, BİLEREK 501

Banka/kampanya/ürün ekleme uçları TANIMLIDIR ama açık değildir ve sahte bir
başarı DÖNDÜRMEZ: 501 ile birlikte neden kapalı olduklarını yazarlar. Sözleşme
`src/api/gelecek.py` içinde tek yerde durur; arayüz onu `/admin/plan`'dan okur,
kendi içinde tekrarlamaz. Gerekçe o dosyanın başlığındadır.

## `/refresh*` — sistemin ağa çıkabilen TEK yüzeyi

Kullanıcı sorusu yolu (sohbet, kıyas, çelişki, canlı çıkarım) internete
ÇIKMAZ ve bu değişmez (CLAUDE.md §1, §11): 4 dakikalık sunumda canlı toplama
donma riskidir. Tazeleme bu yüzden bir operatör eylemidir; arayüzde yalnız
jüri modunda görünür, basılmadan önce ne yapacağını (kaç istek, kaba süre,
internet gerektiği) söyler ve arka planda koşar.

Toplanan belgeler yalnız `data/raw/<slug>/live/` altına yazılır; kıyas ve
sohbet önceden doldurulmuş veri tabanından okumaya devam eder. Ham arşivden
veri tabanına geçiş ayrı ve çevrimdışı bir adımdır. Gerekçenin tamamı
`src/scraping/tazeleme.py` modül başlığındadır.

`repo`'ya tek dokunuş alt akıştır: metni DEĞİŞEN belgenin bayat AI özeti
düşürülür (`ozet=NULL`, `ozet_sebep='kaynak_degisti'`), çünkü artık var olmayan
bir metni tarif eden özet panelde sessizce duramaz. Kampanya kayıtları,
çıkarılmış alanlar ve değişmeyen belgeler ellenmez; kapsamın neden bu kadar dar
olduğu `src/tazeleme_sonrasi.py` başlığındadır.

## Veri kaynağı: HAM SQL DEĞİL, depo sözleşmesi (`src/db/base.py`)

Bu modül `src/db/factory.create_repository()` ile depo açar:

    DATABASE_URL dolu -> PostgresRepository   (üretim / pgvector yolu)
    DATABASE_URL boş  -> Repository(DATABASE_PATH)  (offline demo / test yolu)

**31 Tem 2026'ya kadar API bunu yapmıyordu.** `Repository(DATABASE_PATH)`
doğrudan kuruluyordu, yani `DATABASE_URL` verilse bile okunmuyordu: mimari
diyagramda Postgres vardı, çalışan sistemde yoktu. Bağlamanın önündeki gerçek
engel "tek satır" değildi — bu dosya `repo.rows(<ham SQL>)` kaçış kapısını
**beş yerde** kullanıyordu ve o SQL'ler `?` yer tutucusu taşıyordu (SQLite
lehçesi). `psycopg` `%s` bekler; Postgres'te her uç `ProgrammingError` ile
düşerdi. Beş çağrının hepsi sözleşme metotlarına çevrildi (`campaign_text`,
`query_fields`, `all_banks`, `all_campaigns`) ve `rows()` kaçış kapısı
KALDIRILDI. Kural: bu dosyada SQL yazılmaz; eksik bir sorgu varsa
`RepositoryProtocol`'e metot eklenir ve İKİ backend'de de uygulanır.

## `GET /campaigns` ham gövdeyi ARTIK VARSAYILAN OLARAK GÖNDERMEZ

Ölçüldü (2026-08-11): uç 1774 satırı `raw_text` ile döndürüyordu ve yanıt
**10.339.015 bayttı**. Arayüz o alanı hiçbir yerde okumuyordu — `web/app`
içinde tek geçtiği yer bir tip tanımıydı. Gövde `?govde=true` ile geri gelir;
gerçekten metin isteyen yol ise `GET /campaigns/{id}/text`tir (tek belge).

Yanıt **çıplak liste** olarak KALDI, zarfa sarılmadı: süzgeç sonrası toplam
kayıt sayısı `X-Toplam-Kayit` yanıt başlığına yazılır. Gövde biçimini
değiştirmek her çağıranı aynı anda kırardı.

## Kaynak-span (offset) — birincil yol DB, yedek yol yeniden hesaplama

`ExtractedField` hem `source_span` (±40 karakterlik pencere metni) hem
`span_start`/`span_end` (kesin karakter offset'i) taşır (`src/schemas.py`) ve
31 Tem 2026 itibarıyla ikisi de veri tabanında SAKLANIYOR
(`extracted_fields.span_start` / `span_end` / `confidence_source`).

Bu modül eskiden saklanan offset'i HİÇ OKUMUYORDU: `span_info()`'nun yedek
yolunu (`locate_span`) her alan için tek yol olarak koşturuyordu. Ölçüm
(`data/demo.db`, 849 belge / 2204 alan): saklanan offsetlerin **2204'ü de
doğrulanıyor**, yeniden hesaplama bunların **73'ünde farklı bir yer**
gösteriyordu — çünkü `str.find` aynı ham değerin ilk geçtiği yeri bulur,
çıkarımın geldiği yeri değil. Yani arayüz alanların ~%3'ünde YANLIŞ yeri
boyuyordu. Artık saklanan offset birincil, yeniden hesaplama yedektir
(`span_info()`); yedek yol eski kayıtlar ve offset üretmeyen katmanlar için
durur:

  `source_span` metnin bitişik bir alt dizesidir, `str.find` ile bulunur;
  `raw_value` pencere içinde aranır. Sonuç her zaman `text[start:end] == hedef`
  eşitliğiyle **doğrulanır** (`span_verified`), pencere metni iki kez geçiyorsa
  `span_ambiguous` ile işaretlenir. Bulunamazsa offset `null` döner —
  uydurma yok (CLAUDE.md §21).

## Çerçeve KATLANIR, SİLİNMEZ (`bloklar` alanı)

`GET /campaigns/{id}/text` metnin yanında bir de `bloklar` listesi döndürür:
her blok bir karakter aralığı + `gizle` bayrağı + gizleme `gerekce`si.

Metin DEĞİŞMEZ. Çerçeveyi (çerez/KVKK/menü) metinden ayıklamak `span_start` /
`span_end` offset'lerinin tamamını kaydırırdı ve projenin en özgün iddiası —
her değerin ham metinde bir karakter aralığına bağlı olması — çökerdi. Bu
yüzden ayıklama ÇIKARIM yolundan alınıp sunum katmanına taşındı: arayüz
`gizle=true` aralıkları katlar, kullanıcı isterse açar, offset'ler yerinde
kalır.

`bloklar` ham metni **eksiksiz ve bitişik** kaplar (boşluk yok, örtüşme yok),
yani arayüz metni aralıklardan yeniden birleştirebilir. Garanti
`src/preprocessing/blocks.gorunum_araliklari()` içinde kurulur ve
`tests/test_bloklar_gorunum.py` ile kilitlidir. `gerekce` değerleri
`blocks.py`'nin kendi karar adlarıdır (`alan_disi`, `alan_disi_bolge`,
`tekrar`); burada yeni ad üretilmez.

## `ozet` / `ozet_kaynak` — LLM özeti, yalnız gösterim

`ozet` DB'den okunur (`campaigns.ozet`), istek anında ÜRETİLMEZ — 4 dakikalık
sunumda canlı model çağrısı donma riskidir (CLAUDE.md §11). Toplu üretim
`scripts/build_summaries.py` ile önceden yapılır.

Özet yoksa `ozet` ve `ozet_kaynak` **null**'dır. Kural tabanlı sahte bir özet
(ilk N cümle) asla basılmaz: kullanıcı onu modelin ürettiğini sanır
(`src/summarize/ozet.py`). `ozet_kaynak`'ın tek geçerli değeri `'llm'`dir ve
bu bir SÜTUN DEĞİL, türetilmiş bir alandır — özet üretmenin başka yolu
olmadığı için özet varsa kaynağı tanım gereği modeldir.

Özet hiçbir ölçüm yoluna girmez: kıyas, çıkarım ve çelişki tespiti onu
görmez.

`confidence_source` da artık DB'den okunur. Eskiden "DB'de sütunu yok"
gerekçesiyle kampanya başına kural katmanı YENİDEN KOŞTURULUYOR ve alan adı +
ham değer eşleşmesiyle geri kazanılıyordu; sütun 31 Tem'de eklendi ve
`data/demo.db`'de 2204/2204 alan dolu. Yeniden çıkarım hem gereksiz maliyetti
hem de eşleşmeyen alanlarda sessizce `null` veriyordu. `POST /extract` canlı
çıkarım yaptığı için bu alanı zaten doğrudan gerçek değeriyle verir.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

from ..chatbot.bot import Chatbot
from ..chatbot.router import baglam_birlestir
from ..chatbot.safety import (
    ALL_GATES,
    GATE_INJECTION,
    sanitize_output,
)
from ..comparison.contradiction import detect as detect_contradictions
from ..db.base import (
    BELGE_TURU_SOZLESME,
)
from ..db.factory import create_repository
from ..extraction.llm.extractor import default_extractor
from ..extraction.llm.schema import EXTRACTION_FIELDS
from ..extraction.ner.classifier import default_classifier
from ..extraction.reconcile import build_campaign
from ..pipeline import run_pipeline
from ..preprocessing.blocks import cerceve_cumleler, gorunum_araliklari
from ..preprocessing.clean import normalize_text
from ..scraping.tazeleme import TazelemeYoneticisi
from ..summarize.ozet import OZET_KAYNAK_LLM
from ..summarize.ozet_isi import OzetYoneticisi
from ..tazeleme_sonrasi import alt_akis_kur
from . import gelecek, gunluk, zor_vaka
from .routers import isler, katalog, kiyas
from .sabitler import FIELD_LABELS
from .yardimcilar import (
    scoring_direction,
    span_info,
)

logger = logging.getLogger(__name__)

CONFIG = os.environ.get("BANKS_CONFIG", "config/banks.yaml")
RAW_DIR = os.environ.get("RAW_DIR", "data/raw")


def _otorite_kaynak_sluglari() -> frozenset[str]:
    """`banks.yaml`'da `otorite_kaynak: true` işaretli slug'lar (bkz. `/banks`).

    Config OKUNAMAZSA boş küme döner, yani süzme yapılmaz. Bilinçli seçim:
    banka kataloğunun eksik dönmesi, fazla dönmesinden daha kötüdür — eksik
    liste sessizce yanlış kıyas üretir, fazla liste ise gözle görülür.
    """
    try:
        from ..scraping.config import load_banks
        return frozenset(b.slug for b in load_banks(CONFIG) if b.otorite_kaynak)
    except Exception:  # config yoksa/bozuksa uç çalışmaya devam etmeli
        logger.warning("banks.yaml okunamadı; /banks otorite süzmesi atlandı",
                       exc_info=True)
        return frozenset()
# SQLite yolu için dosya (yalnızca DATABASE_URL boşken kullanılır — seçimi
# `src/db/factory.create_repository()` yapar).
DB_PATH = os.environ.get("DATABASE_PATH", ":memory:")

# Karşılaştırılabilir alanların Türkçe etiketleri `api/sabitler.py`'ye taşındı
# (19 Ağu 2026, API katmanının kademeli bölünmesinin ilk adımı — gerekçe ve
# uç nokta bağımlılık matrisi: docs/rapor/api-bolme-plani.md). Ad burada
# yeniden ihraç ediliyor, çünkü `zor_vaka.liste()` ve arayüz uçları onu
# `main.FIELD_LABELS` olarak okuyor; taşımanın davranışı değiştirmemesi
# gerekiyordu.

# --------------------------------------------------------------------------- #
# Güvenlik kapılarının rapor yüzeyi (`POST /chat` -> `safety`)
# --------------------------------------------------------------------------- #
# Kapı kimlikleri `chatbot/safety.py`'den İTHAL EDİLİR (`ALL_GATES`,
# `GATE_INJECTION`), burada tekrar YAZILMAZ. Gerekçe: iki liste ayrışırsa
# arayüz ya olmayan bir kapıyı "çalışıyor" diye gösterir ya da gerçekten
# ateşlenmiş bir kapıyı hiç basmaz — ikisi de güvenlik iddiasını çürütür.
#
# Sıra da oradan gelir: kullanıcı arka arkaya iki soru sorduğunda kapı
# listesinin yer değiştirmemesi gerekir, yoksa tablo okunmaz olur.
GUVENLIK_KAPILARI: tuple[str, ...] = ALL_GATES + (GATE_INJECTION,)

#: Kapı kimliği → (Türkçe ad, tek cümlelik açıklama). Açıklama kullanıcıya
#: gösterilir: "terminoloji" ham kimliği tek başına hiçbir şey anlatmaz.
GATE_LABELS: dict[str, tuple[str, str]] = {
    "terminoloji": (
        "Terminoloji",
        "Konvansiyonel bankacılık terimi soruda kabul edilir; cevapta "
        "katılım bankacılığındaki kâr payı karşılığıyla yazılır."),
    "fikhi_hukum": (
        "Fıkhî hüküm",
        "Bir ürünün dinen uygunluğuna hüküm verilmez; yetkili danışma "
        "kuruluna yönlendirilir."),
    "yatirim_tavsiyesi": (
        "Yatırım tavsiyesi",
        "Bankalar karşılaştırılır, hangisinin seçileceği söylenmez."),
    "garanti_imasi": (
        "Garanti iması",
        "Kâr payı oranı beklenen orandır; taahhüt edilmiş getiri gibi "
        "sunulmaz — katılma hesabı zarara da ortaktır."),
    "cekimserlik": (
        "Çekimserlik",
        "Kaynak yoksa ya da soru veri kapsamının dışındaysa değer "
        "uydurulmaz."),
    "icerik_karantinasi": (
        "İçerik karantinası",
        "Getirilen belgede talimat devralma işareti varsa belge tümüyle "
        "düşürülür; içeriği cevaba girmez."),
}

#: Karantina kaydında gösterilecek işaret payı (karakter). İşaret KANITTIR ve
#: gösterilmesi gerekir, ama gösterilen şey üçüncü taraf bir sayfadan gelen
#: saldırgan metnidir: sınırsız basmak, düşürdüğümüz belgeyi ekrana geri
#: koymak olurdu.
KARANTINA_ISARET_SINIRI = 120


def _karantina_kaydi(p: dict) -> dict:
    """Düşürülen bir pasajın kullanıcıya gösterilecek özeti.

    Belgenin METNİ TAŞINMAZ — yalnız kimliği (banka, kampanya, kaynak
    bağlantısı) ve yakalanan işaret geçer. Karantinanın gerekçesi "bu belgenin
    geri kalanına da güvenilmez"di; metnini arayüze taşımak o gerekçeyi
    kendi elimizle çürütürdü.

    İşaret `sanitize_output`tan geçirilir: eşleşen parça saldırganın yazdığı
    dizedir ve içinde konvansiyonel faiz terimi geçebilir. KAPI 1'in
    değişmezi ("o terim ekranda görünmez") güvenlik uyarısı için delinmez.
    """
    isaret = (p.get("isaret") or "").strip()
    if len(isaret) > KARANTINA_ISARET_SINIRI:
        isaret = isaret[:KARANTINA_ISARET_SINIRI].rstrip() + "…"
    temiz, _ = sanitize_output(isaret)
    cid = p.get("campaign_id")
    return {
        "bank": p.get("bank"),
        "campaign_id": int(cid) if cid is not None else None,
        "source_url": p.get("source_url"),
        "isaret": temiz or None,
    }


def _guvenlik_ozeti(rapor, gates: list, quarantined: list) -> dict:
    """`POST /chat` yanıtındaki `safety` bloğu — kapıların denetim kaydı.

    ## Neden yanıtta yer alıyor

    Sistem beş güvenlik kapısı çalıştırdığını iddia ediyor ama kapıların
    ETKİSİ metne karışmış durumda: düzeltme notu ve feragatname cevabın
    içinde, karantina ise tamamen görünmez. "Kapılar gerçekten koşuyor mu"
    sorusunun cevabı arayüzde kurulamıyordu.

    ## Neden ateşlenmeyen kapılar da dönüyor

    `fired=False` kayıtları olmadan liste "hangi kapılar var" sorusuna cevap
    veremez; jüri yalnız ateşlenenleri görüp geri kalanının varlığından
    haberdar olamazdı. Gürültü sorunu arayüzde çözülür (ayrıntı jüri
    modunda açılır), sözleşmede değil.

    ## Yasak terim neden GERİ GÖNDERİLMİYOR

    `SafetyReport.violations` yakalanan terimi ve çevresindeki ham bağlamı
    taşır. Onu yanıta koymak, KAPI 1'in az önce ekrandan sildiği dizeyi
    denetim kutusunda geri basmak olurdu. Bu yüzden yalnız SAYI geçer:
    olayın gerçekleştiği bilgisi kanıttır, terimin kendisi değil.
    """
    ates = set(gates or [])
    kirli = [_karantina_kaydi(p) for p in (quarantined or [])]
    if kirli:
        # Karantina `SafetyReport`e yazılmaz (RAG katmanında koşar), ama
        # ateşlenmiş bir kapıdır ve öyle raporlanır.
        ates.add(GATE_INJECTION)
    return {
        "gates": [
            {"id": g,
             "label": GATE_LABELS.get(g, (g, ""))[0],
             "aciklama": GATE_LABELS.get(g, (g, ""))[1],
             "fired": g in ates}
            for g in GUVENLIK_KAPILARI
        ],
        "fired": [g for g in GUVENLIK_KAPILARI if g in ates],
        "blocked_gate": getattr(rapor, "blocked_gate", None),
        "abstained": bool(getattr(rapor, "abstained", False)),
        # Çıktı süzgecinin sessizce yeniden yazdığı terim sayısı.
        "rewritten_terms": len(getattr(rapor, "violations", []) or []),
        "quarantined": kirli,
    }




# --------------------------------------------------------------------------- #
# İstek gövdesi şemaları — MODÜL SEVİYESİNDE olmak ZORUNDA (hata düzeltmesi)
# --------------------------------------------------------------------------- #
# Bu modül `from __future__ import annotations` kullanır; yani tüm annotation'lar
# string'e dönüşür ve FastAPI bunları `typing.get_type_hints()` ile **modül
# global'lerinden** çözer. Şemalar `build_app()` içinde (yerel kapsamda) tanımlı
# olduğunda `ChatReq` adı global'lerde bulunamıyordu; FastAPI de tipi çözemediği
# `req` parametresini **query parametresi** sanıyordu. Sonuç: `POST /chat` ve
# `POST /extract` gövdeyi hiç okumadan
#     422 {"loc": ["query", "req"], "msg": "Field required"}
# döndürüyordu — iki uç da fiilen çağrılamazdı. Şemalar modül seviyesine
# taşındı; pydantic yoksa `build_app()` yine anlaşılır RuntimeError verir.
try:  # pragma: no cover - pydantic yokluğu build_app()'te raporlanır
    from pydantic import BaseModel

    class ChatReq(BaseModel):
        """`POST /chat` gövdesi.

        `context` = istemcinin sakladığı son turların DURUM kayıtları,
        YENİDEN ESKİYE sıralı. Sunucu oturum tutmaz (bkz. `chatbot/bot.py`
        modül başlığı); hafıza istemcidedir ve her istekte geri gelir.

        Kayıtların içeriği serbest metin DEĞİLDİR: `chatbot/router.py`
        `ChatContext.dogrula()` her değeri sonlu bir izin listesinden geçirir,
        uymayanı sessizce atar. Bu yüzden bağlam kanalı bir enjeksiyon yüzeyi
        oluşturmaz — taşınabilecek tek şey, sunucunun kendi ürettiği alan /
        niyet / kampanya türü / banka slug'ı etiketleridir.
        """

        question: str
        context: list[dict] = []

    class ExtractReq(BaseModel):
        """`POST /extract` gövdesi (canlı çıkarım — CLAUDE.md §11).

        `gold_id` verilirse yanıt bir `gold` bloğu kazanır: aynı belgenin
        altın değerleri ve alan alan karşılaştırma sonucu. Çıkarım YİNE
        gövdedeki `text` üzerinde koşar — sunucu altın kümeden metin
        okumaz, yalnızca REFERANS okur. Aksi hâlde ekran, model çıktısı
        yerine gold'un kendisini gösteriyor olabilirdi ve bunu kimse
        ayırt edemezdi.
        """

        text: str
        bank: str = "bilinmeyen"
        gold_id: Optional[str] = None

    # `RefreshReq` `routers/isler.py`'ye taşındı (tek kullanıcısı orada).

except ModuleNotFoundError:  # pragma: no cover
    BaseModel = None  # type: ignore[assignment]

# `Request`/`Response` de AYNI SEBEPLE modül seviyesinde: `GET /campaigns`
# yanıt başlığına (`X-Toplam-Kayit`) yazabilmek için imzasında
# `response: Response`, yazan uçlar da işlem günlüğüne eylem özeti bildirmek
# için `request: Request` taşır. `build_app()` içinde import edilselerdi adlar
# modül global'lerinde bulunmaz, FastAPI onları çözemediği için birer QUERY
# parametresi sanardı ve uçlar her istekte 422 verirdi — yukarıdaki `ChatReq`
# hatasının birebir aynısı.
try:  # pragma: no cover - fastapi yokluğu build_app()'te raporlanır
    from fastapi import Request, Response
except ModuleNotFoundError:  # pragma: no cover
    Request = None  # type: ignore[assignment]
    Response = None  # type: ignore[assignment]


def build_app():
    """FastAPI uygulamasını kur. fastapi yoksa anlaşılır hata verir."""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
    except ModuleNotFoundError as e:  # pragma: no cover
        raise RuntimeError(
            "fastapi/pydantic kurulu değil. `pip install -r requirements.txt`") from e
    if BaseModel is None:  # pragma: no cover
        raise RuntimeError(
            "pydantic kurulu değil. `pip install -r requirements.txt`")

    app = FastAPI(title="Anatolia AI — Katılım Bankacılığı Kampanya API")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                       allow_headers=["*"])

    # ----------------------------------------------------------------- #
    # İşlem günlüğü (audit log) — sistemde ne olduysa kaydedilir
    # ----------------------------------------------------------------- #
    # Neden ara katman, neden uç uç değil: 2026-08-13'te bir canlı tazeleme
    # `data/raw/albaraka/live/` altına 40 dosya yazdı ve "bunu kim tetikledi"
    # sorusu sistemden CEVAPLANAMADI. Uç uç eklenen bir kayıt satırı, tam da
    # unutulduğu uçta o boşluğu geri açardı; ara katman ise yeni bir uç
    # eklendiğinde de kaydı kendiliğinden alır.
    #
    # Kaydın ŞEMASI, neyin kaydedilmediği (gövde, sorgu dizgesi, başlıklar) ve
    # döndürme politikası `src/api/gunluk.py` modül başlığındadır; burada
    # yalnız HTTP bağlaması var.
    gunluk_yazici = gunluk.GunlukYazici.ortamdan()
    # Uygulama durumuna asılır: testler geçici bir dosyaya yönlendirebilsin
    # diye — `app.state.tazeleme` / `app.state.ozet_isi` ile aynı gerekçe.
    app.state.gunluk = gunluk_yazici

    def _gunluge_dus(request, durum: int, gecen_sn: float) -> None:
        """Tek isteği günlüğe düşürür. HİÇBİR koşulda istisna sızdırmaz.

        İkinci bir `try` katmanı (yazıcının kendisi zaten yutuyor) savunma
        değil, sözleşme: bu fonksiyon isteğin yanıt yolunda çağrılıyor ve
        buradan çıkan bir istisna, kullanıcıya çalışan bir cevabı 500 olarak
        gösterirdi. Değişmez şu: günlük yazımı isteği DÜŞÜRMEZ.
        """
        try:
            eylem = getattr(request.state, gunluk.DURUM_ANAHTARI, None)
            is_id = None
            if isinstance(eylem, dict):
                # `is_id` üst düzey bir alandır (süzülebilir olmalı); eylem
                # özetinde ikinci bir kopyası tutulmaz.
                eylem = dict(eylem)
                is_id = eylem.pop("is_id", None)
            if is_id is None:
                # Yol parametresi olan iptal/durum uçları kimliği ZATEN yolda
                # taşıyor; uçtan ayrıca bildirilmesini beklemek gereksiz.
                is_id = (request.scope.get("path_params") or {}).get("job_id")
            app.state.gunluk.istek_kaydet(
                metot=request.method,
                # SADECE yol: sorgu dizgesi (`?q=`) serbest kullanıcı metni
                # taşır ve kalıcı bir denetim kaydına girmemeli (gerekçe:
                # gunluk.py "NE KAYDEDİLMEZ").
                yol=request.url.path,
                durum=durum,
                sure_ms=gecen_sn * 1000.0,
                istemci=request.client.host if request.client else None,
                is_id=is_id,
                eylem=eylem,
            )
        except Exception:  # pragma: no cover - son savunma hattı
            logger.warning("İşlem günlüğü ara katmanı düştü", exc_info=True)

    @app.middleware("http")
    async def islem_gunlugu_ara_katmani(request, call_next):
        """Her isteği süresiyle birlikte işlem günlüğüne yazar.

        Yazma, isteğin CEVAP YOLUNDA ve senkron yapılır (tek `open`+`write`,
        birkaç yüz mikrosaniye). Threadpool'a atmak, yazmanın kendisinden
        pahalı bir iş parçacığı sıçraması eklerdi.

        Handler istisna atarsa kayıt `durum=500` ile YİNE düşer ve istisna
        olduğu gibi yükselmeye devam eder: çöken bir isteğin günlükte hiç
        görünmemesi, denetim kaydının en çok işe yarayacağı anda susması
        demek olurdu.
        """
        baslangic = time.perf_counter()
        try:
            yanit = await call_next(request)
        except Exception:
            _gunluge_dus(request, 500, time.perf_counter() - baslangic)
            raise
        _gunluge_dus(request, yanit.status_code,
                     time.perf_counter() - baslangic)
        return yanit

    # Depo seçimi TEK YERDE: DATABASE_URL varsa Postgres, yoksa SQLite.
    # `thread_safe=True` iki backend için de zorunlu — FastAPI `def` uçlarını
    # threadpool'da koşturur ve ne `sqlite3` ne `psycopg` bağlantısı bu kullanım
    # için güvenlidir (gerekçe: `src/db/base.ThreadSafeRepository`).
    repo = create_repository(database_path=DB_PATH, thread_safe=True)
    # Demo verisini doldur (CLAUDE.md §11 — önceden doldurulmuş DB).
    #
    # KOŞULLU olmak ZORUNDA. Eskiden koşulsuz koşuyordu; in-memory DB'de bu
    # zararsızdı (her açılış sıfırdan başlar) ama `DATABASE_PATH` bir DOSYAYI
    # gösterdiğinde her yeniden başlatma 3 kampanya daha ekliyordu:
    # 849 -> 852 -> 855 -> ... sonsuza dek. Şemada UNIQUE kısıtı yok, yani
    # çift kayıtlar sessizce birikir ve karşılaştırma tablosunda aynı banka
    # birden çok kez görünürdü.
    #
    # `counts()` sözleşme metodudur, bu yüzden koruma Postgres yolunda da
    # AYNEN çalışır — ve orada daha da kritiktir: kalıcı bir hacim (`pgdata`)
    # her `docker compose up`'ta aynı veriyi taşır.
    #
    # `scripts/build_demo_db.py` ile üretilmiş dolu bir DB verildiğinde
    # tohumlama tamamen atlanır ve 849 belgelik gerçek korpus korunur.
    if repo.counts().get("campaigns", 0) == 0:
        run_pipeline(repo, CONFIG, raw_dir=RAW_DIR, mode="fixture")
    llm = default_extractor()
    bot = Chatbot(repo, llm=llm)
    clf = default_classifier()

    # Tembel önbellekler — kampanya başına BİR kez; istek başına değil.
    # kampanya_id → `repo.campaign_text()` sonucu (metin + alanlar + offsetler)
    _view_cache: dict[int, Optional[dict]] = {}
    # "önbellekte yok" ile "önbellekte None var" (bilinmeyen kampanya) ayrı
    # şeyler; `.get()` ikisini karıştırırdı.
    _YOK = object()

    def _ozeti_var(view: Optional[dict]) -> bool:
        """Önbellek kaydı tazelenmeden servis edilebilir mi.

        `None` (bilinmeyen kampanya) tazelenmez: o cevap değişmez.
        """
        if view is None:
            return True
        return bool((view.get("ozet") or "").strip())
    # kampanya_id → çelişki listesi (kural katmanı kampanya başına bir kez koşar)
    _contra_cache: dict[int, list[dict]] = {}
    # kampanya_id → görünürlük aralıkları (blok kararları bir kez hesaplanır)
    _blok_cache: dict[int, list[dict]] = {}
    # banka slug'ı → o bankanın belgelerinde tekrar eden cümlelerin anahtarları.
    # TEMBEL ve BANKA BAZINDA: `cerceve_cumleler()` bir grup içindeki belge
    # frekansına bakar (blocks.py'nin tasarımı), ve tüm korpusu açılışta
    # taramak demonun ilk tıklamasına saniyeler eklerdi (CLAUDE.md §11).
    _cerceve_cache: dict[str, set[str]] = {}

    # ----------------------------------------------------------------- #
    # Dahili yardımcılar
    # ----------------------------------------------------------------- #
    def _campaign_view(campaign_id: int) -> Optional[dict]:
        """Kampanyanın metni + alanları (offset'leriyle) — önbellekli.

        Tek kaynak `repo.campaign_text()`: `/campaigns/{id}/text` ve `/compare`
        AYNI metni ("span_reference": clean_text varsa o, yoksa raw_text)
        kullanmak zorunda. Ayrışsalardı `/compare`'in verdiği offset'ler
        arayüzün `/campaigns/{id}/text`'ten aldığı metinde başka bir yeri
        gösterirdi.
        """
        onbellek = _view_cache.get(campaign_id, _YOK)
        # Özeti OLMAYAN belge önbellekten SERVİS EDİLMEZ. Özetler toplu koşumda
        # (`scripts/build_summaries`) parça parça yazılıyor; koşu sürerken
        # açılan bir belge "özet yok" diye önbelleğe giriyor ve özet DB'ye
        # düşse bile API yeniden başlayana kadar öyle kalıyordu. Demo sırasında
        # jüri aynı belgeyi ikinci kez açtığında hâlâ "özet üretilmedi"
        # görürdü — üstelik özet artık VARDI.
        #
        # Maliyet yalnız eksik özetli belgelerde ödenir: özet bir kez geldiğinde
        # kayıt normal biçimde önbellekte kalır. Metin/alan/offset hesabı zaten
        # aynı sorgudan geliyor, ek yük tek satırlık bir SELECT.
        if onbellek is not _YOK and _ozeti_var(onbellek):
            return onbellek
        view = repo.campaign_text(campaign_id)
        _view_cache[campaign_id] = view
        return view

    def _field_rows(field: str, *, sozlesme_dahil: bool = False) -> list[dict]:
        """Bir alanın tüm banka satırları — kaynak, güven ve katman bilgisiyle.

        `repo.query_fields()` `raw_value`, `extractor`, `confidence_source` ve
        saklanan span offset'lerini zaten döndürür; `canonical_value` da çözülmüş
        gelir. Eskiden burada ham SQL vardı — `?` yer tutucusuyla, yani Postgres
        yolunda çalışması imkânsızdı.

        `sozlesme_dahil=False` (öntanım) **kıyas yolu** içindir: sözleşme /
        tarife / form belgeleri karşılaştırma tablosuna girmez. Korpustaki
        1761 belgenin 113'ü akit metnidir ve 41'i kıyaslanabilir bir alan
        taşır; bir genel finansman sözleşmesindeki oran ile bir kampanya
        sayfasındaki oran aynı kolonda sıralanamaz (CLAUDE.md §17 adil kıyas).

        RAG / chatbot yolu bu süzmeyi UYGULAMAZ: "şu sözleşmede ne yazıyor"
        sorusunun cevabı akit metnindedir; onu aramadan çıkarmak veri varken
        "bulunamadı" demek olurdu.

        ## İmza yoklaması KALDIRILDI (2026-08-10)

        Burada `inspect.signature(repo.query_fields)` ile `sozlesme_dahil`
        parametresi yoklanıyor, yoksa çağrı süzgeçsiz yapılıyordu. O savunma
        yazıldığında parametre yalnız sözleşmede (`src/db/base.py`) vardı ve
        backend'ler henüz uygulamamıştı.

        Artık dal ÖLÜ: parametre `RepositoryProtocol`te, `ThreadSafeRepository`
        sarmalayıcısında ve iki backend'in ikisinde de (`db/repository.py`,
        `db/postgres.py`) uygulanmış durumda. Depo bu modüle dışarıdan
        geçirilmiyor — `build_app()` onu `create_repository()` ile kendisi
        kuruyor, yani üçüncü bir uygulama sızamıyor.

        Kaldırıldı çünkü zararsız değildi: yoklama kodu okuyana "bu yetenek
        eksik olabilir" diyordu ve olmayan bir eksiklik, arananın yanlış yerde
        aranmasına yol açıyordu. Yeni bir backend eklenirse sözleşme onu zaten
        bağlar; eksik uygularsa `TypeError` ile GÜRÜLTÜLÜ düşer — sessizce
        süzgeçsiz kıyas üretmekten iyidir.
        """
        return repo.query_fields(field, sozlesme_dahil=sozlesme_dahil)

    def _kiyas_kapsami(campaign_type: Optional[str] = None) -> list[dict]:
        """Kıyasa GİRMESİ GEREKEN (banka, kampanya türü) çiftleri.

        `compare.rank(..., kapsam=...)` bunu alır ve bu kümede olup alan
        satırı bulunmayan her çifti "Belirtilmemiş" satırı olarak ekler.
        Gerekçe `compare.py`'nin "Kapsam kapısı" bloğunda; özeti: alanı
        olmayan banka tablodan DÜŞMEMELİ, şartnamenin s.11–12 tablosu eksik
        hücreli satırları açıkça gösteriyor.

        Süzme `_field_rows` ile AYNI olmak zorundadır, yoksa kapsam ile veri
        farklı evrenlerden gelir: sözleşme belgesinde oranı olan bir banka
        kıyas tablosuna "verisi yok" diye girer ya da tersi. `query_fields`
        `base.kiyas_where()` kullanıyor — *sözleşme hariç, türü BİLİNMEYEN
        dahil*; buradaki süzgeç birebir odur (`== 'kampanya'` değil).

        `govde=False`: yalnız banka + tür sayılıyor, ham metin okunmuyor
        (`/bank-delta` ile aynı gerekçe, orada ölçülmüş).
        """
        gorulen: dict[tuple[Any, Any], dict] = {}
        for c in repo.all_campaigns(govde=False):
            if c.get("belge_turu") == BELGE_TURU_SOZLESME:
                continue
            tur = c.get("campaign_type")
            if campaign_type and tur != campaign_type:
                continue
            gorulen.setdefault((c.get("bank"), tur), {
                "bank": c.get("bank"),
                "bank_name": c.get("bank_name"),
                "campaign_type": tur,
            })
        return list(gorulen.values())

    def _cerceve(bank_slug: str) -> set[str]:
        """Bir bankanın belgelerinde tekrar eden cümlelerin anahtar kümesi.

        `blocks.kararlar()`'ın "tekrar" sinyali bu kümeye bakar. Küme
        verilmezse sinyal hiç ateşlenmez ve menü/altbilgi blokları
        katlanmadan kalır — yani boş küme geçmek sessiz bir yetenek kaybıdır.

        Grup neden BANKA: `cerceve_cumleler()` belge frekansı sayar ve bir
        cümlenin çerçeve olduğunun kanıtı AYNI SİTEDE tekrar etmesidir.
        Bankalar arası tekrar farklı bir olgudur (sektör şablonu) ve burada
        aranmaz.
        """
        if bank_slug in _cerceve_cache:
            return _cerceve_cache[bank_slug]
        metinler = [c.get("raw_text") or "" for c in repo.all_campaigns()
                    if c.get("bank") == bank_slug]
        _cerceve_cache[bank_slug] = cerceve_cumleler(metinler)
        return _cerceve_cache[bank_slug]

    def _bloklar(campaign_id: int, text: str, bank_slug: str) -> list[dict]:
        """Ham metni eksiksiz kaplayan görünürlük aralıkları — önbellekli."""
        cached = _blok_cache.get(campaign_id)
        if cached is not None:
            return cached
        try:
            araliklar = gorunum_araliklari(text, _cerceve(bank_slug))
            out = [a.as_dict() for a in araliklar]
        except Exception:  # pragma: no cover - blok hatası metni düşürmesin
            # Tek güvenli geri düşüş: metnin TAMAMI görünür. Kapsama garantisi
            # (bitişik + eksiksiz) bu yolda da korunur.
            out = ([{"start": 0, "end": len(text), "gizle": False,
                     "gerekce": None}] if text else [])
        _blok_cache[campaign_id] = out
        return out

    def _ozet(camp: dict) -> tuple[Optional[str], Optional[str]]:
        """(ozet, ozet_kaynak) — üretilmemişse (None, None).

        Özet DB'den okunur; burada ÜRETİLMEZ (CLAUDE.md §11). `ozet_kaynak`
        bir sütun değildir: özet üretmenin tek yolu yerel model olduğu için
        (`src/summarize/ozet.py` kural tabanlı yedeği yasaklar) özet varsa
        kaynağı tanım gereği `'llm'`dir.

        ÇÖZÜLDÜ (2026-08-09): buradaki `TODO(G)` *"campaign_text() henüz
        c.ozet sütununu SELECT etmiyor"* diyordu. Artık ediyor — iki backend'de
        de (`db/repository.py`, `db/postgres.py`). Yorum bayattı ve teşhisi
        yanlış yere saptırıyordu: "özet görünmüyor" arandığında insanı
        olmayan bir SQL eksiğine yönlendiriyordu, oysa gerçek sebepler
        arayüzdeydi (tanımsız `.summary-box` CSS'i) ve veri kapsamındaydı
        (belgelerin ~%81'inde özet üretilmemiş).

        Özet yoksa cevap yine `null`'dır ve bu değişmedi. Değişen, arayüzün o
        `null`'ı artık SESSİZCE yutmaması: boşluk adlandırılıyor
        (`web/app/components/SummaryNotice.tsx`).
        """
        ozet = (camp.get("ozet") or "").strip()
        return (ozet, OZET_KAYNAK_LLM) if ozet else (None, None)

    def _kaynaklari_zenginlestir(handler: str, field: Optional[str],
                                 sources: list) -> list[dict]:
        """`/chat` kaynaklarına `campaign_id` + `source_url` + `ozet` ekler.

        Jüri "bu bilgiyi nereden aldın" diye sorduğunda arayüz tek tıkla
        `GET /campaigns/{campaign_id}/text`e gidebilmeli. RAG yolu bu iki
        alanı zaten taşır (`chatbot/rag.py`); yapısal sorgu yolu `RankRow`
        döndürür ve `RankRow`'da kampanya kimliği YOKTUR.

        Yapısal yol artık `campaign_id`'yi kaynakla birlikte TAŞIYOR
        (`chatbot/bot.py`), çünkü `RankRow` onu zaten biliyor. Kampanya
        kimliği elde olduğunda `source_url` doğrudan o kampanyadan okunur —
        tahmin yok.

        Kimlik yoksa (eski çağıranlar, RAG dışı yollar) `query_fields()`
        satırlarıyla (banka slug'ı + `source_span`) eşleştirmeye düşülür.
        O eşleşme **tekil olmak zorunda**: aynı banka+pencere birden çok
        kampanyaya işaret ediyorsa hangisi olduğunu bilmiyoruz demektir ve
        alan `null` kalır. Yaklaşık eşleştirmeyle bir kampanya seçmek,
        denetlenebilir bağlantı vaadinin tam tersi olurdu (CLAUDE.md §21:
        değer uydurma).

        Geri düşüş yolunun NEDEN tek başına yetmediği ölçüldü
        (`data/demo.db`): (banka, pencere) çifti `finansman_tutari`'nda
        satırların %48'inde, `vade_ay`'da %44'ünde, `masraf_durumu`'nda
        %63'ünde mükerrer. Yani kaynakların yarısına yakını "bağlantı yok"
        olarak basılıyordu — bilgi vardı, anahtar yanlıştı.

        ## `ozet` neden HER kayıtta var

        RAG pasajı kaynak olarak belgenin TAMAMINI taşır ve arayüz onu tabloya
        basıyordu — tek satır ekranı dolduruyordu. Arayüz artık varsa özeti
        basıyor; bunu yapabilmesi için alanın VARLIĞI sözleşme olmalı, yoksa
        `undefined` ile `null` ayrımı istemci tarafında tahmine dönüşür.

        Yapısal sorgu yolunda `ozet` **her zaman `null`**'dır ve bu bir eksik
        değil, doğru cevaptır: o yolun kaynak parçası `source_span`, yani
        değerin çıkarıldığı dar penceredir — zaten kısadır ve özetlenecek bir
        şey değildir. `query_fields()` özeti seçmez; kampanya başına özet
        çekmek için ayrı bir sorgu koşturmak, gösterilmeyecek bir alan için
        istek başına maliyet olurdu.
        """
        dizin: dict[tuple[Any, Any], Optional[dict]] = {}
        kimlikle: dict[Any, dict] = {}
        if handler == "structured" and field:
            # Kıyas süzmesi UYGULANMAZ: chat yolu sözleşmeleri de görebilir.
            for r in _field_rows(field, sozlesme_dahil=True):
                anahtar = (r.get("bank"), r.get("source_span"))
                # İkinci kez görülen anahtar belirsizdir -> None ile zehirle.
                dizin[anahtar] = None if anahtar in dizin else r
                # Kampanya kimliği alan başına TEKİLDİR (ölçüldü: 5455
                # satırda mükerrer (alan, kampanya) çifti yok), bu yüzden
                # zehirlenmeye gerek duymaz.
                if r.get("campaign_id") is not None:
                    kimlikle.setdefault(r["campaign_id"], r)

        out: list[dict] = []
        for s in sources:
            kayit = dict(s) if isinstance(s, dict) else {"value": s}
            # ÖNCE kimlik: kaynak kampanya numarasını taşıyorsa eşleştirme
            # tahmini değil, kesindir.
            eslesme = kimlikle.get(kayit.get("campaign_id"))
            if eslesme is None:
                eslesme = dizin.get((kayit.get("bank"),
                                     kayit.get("source_span")))
            if kayit.get("campaign_id") is None:
                cid = eslesme.get("campaign_id") if eslesme else None
                kayit["campaign_id"] = int(cid) if cid is not None else None
            if kayit.get("source_url") is None:
                kayit["source_url"] = eslesme.get("source_url") if eslesme else None
            # Özet ÜRETİLMEZ, yalnız taşınır: RAG pasajı getirmişse geçer,
            # getirmemişse alan açıkça `null` olur.
            ozet = kayit.get("ozet")
            kayit["ozet"] = ozet.strip() if isinstance(ozet, str) and ozet.strip() else None
            out.append(kayit)
        return out

    def _campaign_contradictions(campaign_id: int, text: str, bank_slug: str,
                                 scraped_at: Optional[str] = None,
                                 source_url: Optional[str] = None) -> list[dict]:
        """Bir kampanyanın iç çelişkileri.

        `scraped_at` verilirse zaman bağımlı kural da koşar: *"kampanya
        süresi dolmuş ama sayfa hâlâ yayında ve bunu söylemiyor"*. Korpusta
        doğrulanmış 6 çelişkinin **5'i** bu kuraldan geliyor; `as_of`
        geçilmediği için bu uç noktada tamamen kapalıydı.

        Duvar saati değil `scraped_at` kullanılır: iddia "biz topladığımızda
        süresi çoktan dolmuştu" biçiminde olmalı. Böylece sonuç zamanla
        sessizce değişmez ve demo yeniden-üretilebilir kalır (CLAUDE.md §11).
        """
        cached = _contra_cache.get(campaign_id)
        if cached is not None:
            return cached
        try:
            c = build_campaign(text, bank_slug=bank_slug,
                               source_url=source_url)
            out = [{"kind": k.kind, "detail": k.detail, "fields": k.fields}
                   for k in detect_contradictions(c, as_of=scraped_at)]
        except Exception:  # pragma: no cover - çıkarım hatası UI'yı düşürmesin
            out = []
        _contra_cache[campaign_id] = out
        return out

    # ----------------------------------------------------------------- #
    # Uçlar
    # ----------------------------------------------------------------- #
    # Katalog uçları (`/health`, `/banks`, `/campaigns`, `/search`, `/stats`,
    # `/fields`) `routers/katalog.py`'ye taşındı — kademeli API bölmesinin
    # 2. adımı (plan: docs/rapor/api-bolme-plani.md). Gövdeler birebir taşındı;
    # `repo`/`llm` closure yerine factory parametresi oldu, iki yardımcı da
    # parametre geçiliyor ki `routers` -> `main` yönünde dairesel import doğmasın.
    app.include_router(katalog.router_kur(
        repo, llm,
        otorite_sluglari=_otorite_kaynak_sluglari,
        scoring_direction=scoring_direction,
    ))


    @app.get("/campaigns/{campaign_id}/text")
    def campaign_text(campaign_id: int):
        """Kampanyanın kaynak metni + her alanın karakter offset'i.

        Kaynak-span vurgulaması (CLAUDE.md §18 hedef #1) ve Jüri Audit Paneli
        bu uca dayanır: metin + offsetler + güven + katman + çelişki tek yerde.

        `span_reference` alanı offsetlerin HANGİ metinde ölçüldüğünü söyler
        (`clean_text` varsa o, yoksa `raw_text`); `text` de o metindir. İkisini
        karıştırmak offsetleri kaydırır, bu yüzden sözleşmede açıkça durur.

        `bloklar` AYNI metnin görünürlük haritasıdır ve onu eksiksiz kaplar:
        `"".join(text[b.start:b.end] for b in bloklar) == text`. `gizle=true`
        aralıklar arayüzde katlanır; metin kırpılmaz, offsetler kaymaz.

        `ozet` / `ozet_kaynak` önceden üretilmiş LLM özetidir; yoksa ikisi de
        `null` (modül docstring'i).
        """
        camp = _campaign_view(campaign_id)
        if camp is None:
            raise HTTPException(status_code=404,
                                detail=f"Kampanya bulunamadı: {campaign_id}")
        text = camp.get("text") or ""

        fields_out = []
        for d in camp.get("fields", []):
            fields_out.append({
                "field": d["field_name"],
                "label": FIELD_LABELS.get(d["field_name"], d["field_name"]),
                "raw_value": d["raw_value"],
                "canonical_value": d["canonical_value"],
                "confidence": d["confidence"],
                "confidence_source": d.get("confidence_source"),
                "extractor": d["extractor"],
                "source_span": d["source_span"],
                **span_info(text, d["source_span"], d["raw_value"],
                            d.get("span_start"), d.get("span_end")),
            })

        ozet, ozet_kaynak = _ozet(camp)
        return {
            "campaign_id": campaign_id,
            "bank": camp["bank"],
            "bank_name": camp["bank_name"],
            "campaign_type": camp["campaign_type"],
            "belge_turu": camp.get("belge_turu"),
            "source_url": camp["source_url"],
            "scraped_at": camp.get("scraped_at"),
            "campaign_status": camp.get("campaign_status"),
            "text": text,
            "text_length": len(text),
            "span_reference": camp.get("span_reference"),
            "bloklar": _bloklar(campaign_id, text, camp["bank"]),
            "ozet": ozet,
            "ozet_kaynak": ozet_kaynak,
            "fields": fields_out,
            "contradictions": _campaign_contradictions(
                campaign_id, text, camp["bank"], camp.get("scraped_at"),
                camp.get("source_url")),
        }

    # Kıyas uçları (`/compare`, `/urun-tablosu`, `/bank-delta`, `/scoring`,
    # `/advantageous`) `routers/kiyas.py`'ye taşındı — bölmenin 4. adımı
    # (plan: docs/rapor/api-bolme-plani.md). 701 satır, bölmenin en büyük
    # grubu. Dört closure yardımcısı BURADA kalıyor ve parametre geçiliyor:
    # `/chat`, `/extract`, `/contradictions*` ve `/campaigns/{id}/text` de
    # onları kullanıyor, yani router'a taşınamazlardı. Durumsuz yardımcılar
    # (`span_info`, `scoring_direction`, `_en_iyi_taraf`, kıyas sabitleri)
    # `api/yardimcilar.py`'ye çıktı; `main`den import etmek dairesel
    # bağımlılık kurardı.
    app.include_router(kiyas.router_kur(
        repo,
        field_rows=_field_rows,
        kiyas_kapsami=_kiyas_kapsami,
        campaign_view=_campaign_view,
        campaign_contradictions=_campaign_contradictions,
    ))

    @app.post("/chat")
    def chat(req: ChatReq):
        """Hibrit chatbot — her kaynak kaydı DENETLENEBİLİR bağlantı taşır.

        `sources` içindeki her kayıt `campaign_id`, `source_url` ve `ozet`
        alanlarını **her zaman içerir**; bilinmiyorsa değeri `null`'dır.
        Eskiden yalnız metin parçası dönüyordu ve "bu bilgiyi nereden aldın"
        sorusunun cevabı arayüzde kurulamıyordu.

        `ozet` önceden üretilmiş belge özetidir (`campaigns.ozet`) ve istek
        anında ÜRETİLMEZ. Arayüz uzun ham metin yerine onu basar; özeti
        olmayan belgede sahte bir özet uydurulmaz, ham metnin kırpıldığı
        kullanıcıya söylenir.

        ## İşlem günlüğüne eylem özeti BİLEREK bildirilmez

        Bu uç `POST` olduğu için günlükte "yazan" olarak görünür (metot ölçütü
        — `src/api/gunluk.py`), ama `gunluk.eylem_bildir()` ÇAĞRILMAZ. Sebep
        tek: buradaki tek anlamlı özet kullanıcının SORUSU olurdu ve o soru
        kişisel veri taşıyabilir ("50 bin TL kredim var…"). Kalıcı ve
        ekleme-only bir denetim kaydına kişisel veri yazmak, günlüğün
        çözdüğünden büyük bir sorun açar (CLAUDE.md §19).

        ## Sohbet hafızası (durumsuz)

        `req.context` istemcinin taşıdığı son turların durumudur; sunucu
        hiçbir oturum saklamaz. Yanıttaki `context` bir sonraki tur için
        üretilen yeni durumdur, `inherited` ise bu turda önceki turlardan
        DEVRALINAN boyutların Türkçe etiketleridir — arayüz bunu rozet olarak
        basar, böylece kullanıcı hangi bağlamla cevaplandığını görür.

        `verbalize` yapısal cevabın LLM ile sözelleştirilip
        sözelleştirilmediğini bildirir. `applied` yanlışsa ekranda ŞABLON
        cevap vardır; `reason` neden düşüldüğünü söyler.

        ## `safety` — güvenlik kapılarının denetim kaydı

        Beş kapı + içerik karantinası her soruda koşar ama etkileri metne
        karışır: düzeltme notu ve feragatname cevabın gövdesinde durur,
        karantina ise hiçbir iz bırakmazdı. Bu blok o boşluğu kapatır ve
        hangi kapının ateşlendiğini, hangisinin cevabı DURDURDUĞUNU ve
        korpustan hangi belgenin düşürüldüğünü açıkça söyler. Alanların
        anlamı `_guvenlik_ozeti()` docstring'inde.

        `quarantined` boş değilse korpusta talimat gömülü bir belge VAR
        demektir; arayüz bunu her hâlde gösterir, jüri modu beklemez.
        """
        a = bot.ask(req.question, baglam_birlestir(req.context))
        # `quarantined` chatbot katmanına yeni taşınan bir alan; yoksa
        # `getattr` boş liste verir ve blok sessizce "karantina yok" der —
        # eksik alan yüzünden uç noktanın çökmesi kabul edilemez.
        return {"answer": a.text, "handler": a.handler, "field": a.field,
                "sources": _kaynaklari_zenginlestir(a.handler, a.field,
                                                    a.sources),
                "context": a.context, "inherited": a.inherited,
                "verbalize": a.verbalize,
                "safety": _guvenlik_ozeti(a.safety_report, a.gates,
                                          getattr(a, "quarantined", []))}

    # ----------------------------------------------------------------- #
    # Zor vaka tezgâhı — canlı yolun ÜZERİNE referans koyar
    # ----------------------------------------------------------------- #
    # Gerekçe `src/api/zor_vaka.py` modül başlığında; burada yalnız HTTP
    # yüzeyi ve banka adı çözümü var.
    _banka_adlari: dict[str, str] = {}

    def _banka_adi_haritasi() -> dict[str, str]:
        """slug → görünen ad. Bir kez kurulur; katalog koşu boyunca değişmez."""
        if not _banka_adlari:
            for b in repo.all_banks():
                slug = b.get("slug")
                if slug:
                    _banka_adlari[slug] = b.get("name") or slug
        return _banka_adlari

    @app.get("/zor-vakalar")
    def zor_vakalar():
        """Altın kümedeki ZOR belgeler + altın değerleri (CLAUDE.md §6, §16)."""
        return zor_vaka.liste(FIELD_LABELS, _banka_adi_haritasi())

    @app.post("/extract")
    def extract(request: Request, req: ExtractReq):
        """Canlı çıkarım (CLAUDE.md §11 "canlı çıkarım butonu").

        Offset'ler burada GERÇEK `ExtractedField` nesnesinden gelir ve
        `verify_span()` ile doğrulanır — DB yolundaki geri kazanıma gerek yok.

        İşlem günlüğüne yalnız çıkarımın SONUCUNUN özeti düşer (banka slug'ı,
        bulunan/eksik alan sayısı). Gövdedeki `text` KAYDEDİLMEZ: kullanıcı
        oraya kendi sözleşmesini yapıştırabilir ve kalıcı bir denetim kaydı
        kişisel veri deposuna dönüşemez (`src/api/gunluk.py`).
        """
        text = normalize_text(req.text)
        ctype, ctype_conf = clf.classify(text)
        c = build_campaign(text, bank_slug=req.bank, llm=llm, campaign_type=ctype)
        by_name = {f.field_name: f for f in c.fields}
        gunluk.eylem_bildir(
            request, banka=c.bank_slug, kampanya_turu=c.campaign_type,
            bulunan_alan=len(c.fields),
            eksik_alan=len([a for a in EXTRACTION_FIELDS if a not in by_name]),
            metin_uzunlugu=len(text))
        # Altın karşılaştırma İSTEĞE BAĞLI: `gold_id` yoksa yanıt eskisiyle
        # birebir aynıdır (serbest metin yolu bozulmaz). Bilinmeyen bir kimlik
        # 404 DEĞİL `null` döner — çıkarım gerçekleşti, yalnız referans
        # bulunamadı; isteği tümüyle reddetmek çalışan bir sonucu çöpe atardı.
        gold = None
        if req.gold_id:
            kayit = zor_vaka.kayit(req.gold_id)
            if kayit is not None:
                gold = zor_vaka.karsilastir(
                    kayit,
                    {f.field_name: f.canonical_value for f in c.fields},
                    FIELD_LABELS, list(EXTRACTION_FIELDS),
                    metin_ayni=normalize_text(kayit.get("text") or "") == text,
                )
        return {
            "gold": gold,
            "bank": c.bank_slug,
            "campaign_type": c.campaign_type,
            "campaign_type_confidence": ctype_conf,
            "text": text,
            "text_length": len(text),
            "llm_available": llm.available,
            "fields": [
                {"field": f.field_name,
                 "label": FIELD_LABELS.get(f.field_name, f.field_name),
                 "value": f.canonical_value,
                 "raw_value": f.raw_value,
                 "confidence": f.confidence,
                 "confidence_source": f.confidence_source,
                 "extractor": f.extractor.value,
                 "source_span": f.source_span,
                 "span_start": f.span_start,
                 "span_end": f.span_end,
                 "span_scope": "value" if f.span_start is not None else None,
                 "span_verified": f.verify_span(text),
                 "span_ambiguous": False}
                for f in c.fields
            ],
            # Hangi alanlar HİÇ bulunamadı — halüsinasyon yasağının görünür hali
            "missing_fields": [
                {"field": name, "label": FIELD_LABELS.get(name, name)}
                for name in EXTRACTION_FIELDS if name not in by_name
            ],
            "contradictions": [
                {"kind": k.kind, "detail": k.detail, "fields": k.fields}
                for k in detect_contradictions(c)
            ],
        }

    # ----------------------------------------------------------------- #
    # Veri tazeleme — TEK internete çıkan yol, operatör eylemi
    # ----------------------------------------------------------------- #
    # Bu dört uç, sistemin ağa çıkabilen tek yüzeyidir ve kullanıcı sorusu
    # yolundan (sohbet, kıyas, çelişki, canlı çıkarım) tamamen ayrıktır.
    # Tazeleme kampanya kayıtlarını, çıkarılmış alanları ve gömme vektörlerini
    # ELLEMEZ; kıyas ve sohbet önceden doldurulmuş veri tabanından okumaya
    # devam eder (CLAUDE.md §11 — canlı toplamaya bağlı demo yasak).
    #
    # TEK istisna alt akıştır: metni değişen belgenin bayat AI özeti düşürülür.
    # Kapsamının neden bu kadar dar tutulduğu ve özet üretiminin neden otomatik
    # zincirlenmediği `src/tazeleme_sonrasi.py` başlığında yazılı.
    #
    # Gerekçe `src/scraping/tazeleme.py` modül başlığında; burada yalnız
    # HTTP yüzeyi ve bağlama var.
    def _ozet_onbellegini_dus(kampanya_idleri: list[int]) -> None:
        """Özeti düşürülen kayıtları görünüm önbelleğinden atar.

        Şart: `_campaign_view` yalnız özeti OLMAYAN kaydı tazeliyor
        (`_ozeti_var`). Özet veri tabanından silindiğinde önbellekteki kopya
        hâlâ ESKİ özeti taşıdığı için taze sayılır ve panel, veri tabanında
        artık bulunmayan bayat özeti göstermeye devam ederdi.
        """
        for cid in kampanya_idleri:
            _view_cache.pop(cid, None)

    tazeleme = TazelemeYoneticisi(
        RAW_DIR, alt_akis=alt_akis_kur(lambda: repo, unut=_ozet_onbellegini_dus))
    # Yönetici uygulama durumuna asılır: testler gerçek toplama katmanını
    # sahte bir işle değiştirebilsin diye. Kapanış (closure) içinden
    # erişilemeyen bir nesne, ancak ağa çıkılarak sınanabilirdi.
    app.state.tazeleme = tazeleme

    def _banka_bul(slug: str):
        """`banks.yaml`'dan banka kaydını çeker; yoksa 404."""
        try:
            from ..scraping.config import load_banks
            kayitlar = {b.slug: b for b in load_banks(CONFIG)}
        except Exception as exc:  # config okunamıyorsa tazeleme yapılamaz
            logger.warning("banks.yaml okunamadı; tazeleme reddedildi",
                           exc_info=True)
            raise HTTPException(
                status_code=503,
                detail="Banka tanım dosyası okunamadı; tazeleme başlatılamıyor."
            ) from exc
        bank = kayitlar.get(slug)
        if bank is None:
            raise HTTPException(status_code=404,
                                detail=f"Tanımlı olmayan banka: {slug}")
        return bank

    # Tazelemeden farkı bilinçli: o ağa çıkar ve DB'ye dokunmaz, bu ağa
    # çıkmaz ve tam da DB'ye yazar. İkisi aynı anda koşabilir; kaynakları
    # ayrık. Gerekçe `src/summarize/ozet_isi.py` modül başlığında.
    ozet_isi = OzetYoneticisi(lambda: repo)
    # Testler sahte bir iş geçirebilsin diye uygulama durumuna asılır —
    # tazelemedeki aynı gerekçe.
    app.state.ozet_isi = ozet_isi

    # Arka plan işleri (`/refresh*`, `/summaries*`) `routers/isler.py`'ye
    # taşındı — kademeli API bölmesinin 3. adımı (plan:
    # docs/rapor/api-bolme-plani.md). İki iş yöneticisi (`tazeleme`,
    # `ozet_isi`) BURADA kalıyor ve parametre geçiliyor: koşan işin durumunu
    # bellekte tuttukları için modül seviyesine çıkmaları test izolasyonunu
    # bozardı.
    app.include_router(isler.router_kur(
        app, repo,
        tazeleme=tazeleme,
        ozet_isi=ozet_isi,
        banka_bul=_banka_bul,
        raw_dir=RAW_DIR,
    ))


    @app.get("/log")
    def islem_gunlugu(response: Response,
                      yalniz_yazanlar: bool = True,
                      metot: Optional[str] = None,
                      yol: Optional[str] = None,
                      baslangic: Optional[str] = None,
                      bitis: Optional[str] = None,
                      limit: int = gunluk.VARSAYILAN_LIMIT,
                      offset: int = 0):
        """Denetim kaydı — süzülmüş, sayfalanmış, yeniden eskiye.

        ## Ham dosya DÖKÜLMEZ

        `data/gunluk/*.jsonl` olduğu gibi gönderilmez: dosya megabaytlarca
        olabilir ve içindeki asıl bilgi (kim ne yaptı) okuma trafiğinin
        içinde kaybolur. Bu uç süzer, sayfalar ve sıralar.

        ## `yalniz_yazanlar` VARSAYILAN OLARAK AÇIK

        Panel her sekmede `/compare`, `/stats`, `/advantageous` çağırıyor ve
        iş koşarken `/refresh/status` saniyede bir yoklanıyor. Varsayılan
        "hepsi" olsaydı, uğruna bu günlüğün yazıldığı tek satır (`POST
        /refresh`) yüzlerce okuma satırının arasında kalırdı. Tam akış tek
        parametre uzakta: `?yalniz_yazanlar=false`.

        Günlük DÖNDÜRME kayıtları bu süzgeçte de görünür — "kayıt kayboldu mu"
        sorusu tam olarak bu görünümde soruluyor (`src/api/gunluk.py`).

        ## Yanıt ÇIPLAK LİSTEDİR

        Toplam `X-Toplam-Kayit` başlığına yazılır — `GET /campaigns` ile aynı
        sözleşme; arayüz iki uçta iki farklı biçim öğrenmek zorunda kalmasın.

        `baslangic` / `bitis` ISO-8601 alır (`2026-08-13` ya da
        `2026-08-13T09:00:00Z`). Yalnız tarih verildiğinde `bitis` o günün
        SONUNU kapsar; aksi hâlde "13 Ağustos'a kadar" süzgeci 13 Ağustos'u
        tümüyle dışarıda bırakır ve kullanıcı kaydın silindiğini sanırdı.
        """
        if limit < 1 or limit > gunluk.AZAMI_LIMIT:
            raise HTTPException(
                status_code=400,
                detail=f"limit 1 ile {gunluk.AZAMI_LIMIT} arasında olmalı "
                       f"(gelen: {limit}).")
        if offset < 0:
            raise HTTPException(status_code=400,
                                detail=f"offset negatif olamaz (gelen: {offset}).")
        try:
            kayitlar, toplam = app.state.gunluk.oku(
                yalniz_yazanlar=yalniz_yazanlar, metot=metot, yol=yol,
                baslangic=baslangic, bitis=bitis, limit=limit, offset=offset)
        except ValueError as exc:
            # Bozuk zaman süzgeci İSTEMCİNİN hatasıdır; 400 ile ve okunur bir
            # örnekle geri döner (`gunluk._zaman_coz`).
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response.headers["X-Toplam-Kayit"] = str(toplam)
        return kayitlar

    # ----------------------------------------------------------------- #
    # Gelecek faz — tanımlı ama KAPALI uçlar
    # ----------------------------------------------------------------- #
    # Sözleşme `src/api/gelecek.py` içinde; burada yalnız HTTP yüzeyi var.
    # Uçlar sahte başarı DÖNDÜRMEZ: 501 + gerekçe + bugünkü alternatif.
    def _kapali() -> None:
        raise HTTPException(status_code=501, detail={
            "sebep": gelecek.KAPALI_SEBEBI,
            "bugunku_yol": gelecek.BUGUNKU_YOL,
        })

    @app.get("/admin/plan")
    def admin_plan():
        """Gelecek faz uçlarının sözleşmesi — arayüz bunu çizer."""
        return gelecek.plan()

    @app.post("/admin/banks")
    def admin_bank_ekle():
        """Gelecek faz: banka ekleme. Bu sürümde KAPALI (501)."""
        _kapali()

    @app.post("/admin/banks/{slug}/campaigns")
    def admin_kampanya_ekle(slug: str):
        """Gelecek faz: kampanya ekleme. Bu sürümde KAPALI (501)."""
        _kapali()

    @app.post("/admin/banks/{slug}/products")
    def admin_urun_ekle(slug: str):
        """Gelecek faz: finansal ürün ekleme. Bu sürümde KAPALI (501)."""
        _kapali()

    @app.get("/contradictions")
    def contradictions():
        """Tüm külliyatta otomatik yakalanan iç çelişkiler (CLAUDE.md §18 #2)."""
        out = []
        for camp in repo.all_campaigns():
            text = camp.get("raw_text", "") or ""
            for k in _campaign_contradictions(camp["id"], text, camp["bank"],
                                              camp.get("scraped_at"),
                                              camp.get("source_url")):
                out.append({
                    "bank": camp["bank"],
                    "bank_name": camp.get("bank_name"),
                    "campaign_id": camp["id"],
                    "campaign_type": camp.get("campaign_type"),
                    "source_url": camp.get("source_url"),
                    **k,
                })
        return out

    @app.get("/contradictions/summary")
    def contradictions_summary():
        """Çelişki taramasının kapsamı — "kaç belgede kaç bulgu" anlatısı."""
        # Yalnız sayım yapılıyor; ham gövdeye gerek yok (`govde=False`).
        camps = repo.all_campaigns(govde=False)
        found = contradictions()
        by_kind: dict[str, int] = {}
        for c in found:
            by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1
        return {
            "scanned_campaigns": len(camps),
            "scanned_banks": len({c["bank"] for c in camps}),
            "contradiction_count": len(found),
            "affected_campaigns": len({c["campaign_id"] for c in found}),
            "by_kind": by_kind,
        }

    return app


# uvicorn src.api.main:app
try:  # pragma: no cover
    app = build_app()
except RuntimeError:
    app = None
