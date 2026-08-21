"""Uçtan uca pipeline — scrape → extract → classify → reconcile → store.

İlgili: ../syntheses/teknik-cozum-mimarisi.md, CLAUDE.md §3, §11
Tüm katmanları birleştiren tek giriş. Offline (fixture + kural + null-LLM) koşar;
modeller/servisler varsa otomatik devreye girer.

## Modlar — ve hangisi kaç belge yükler

| mode      | kaynak                                   | belge sayısı (2026-07-31) |
|-----------|------------------------------------------|---------------------------|
| `fixture` | `data/raw/<slug>/` **kök seviyesi**       | 3                         |
| `corpus`  | `data/raw/<slug>/**/*.txt` (özyinelemeli) | 849                       |
| `live`    | ağdan canlı toplama                       | değişken (offline: 0)     |
| `auto`    | önce `live`, boşsa `fixture`              | değişken                  |

`fixture` neden 3 belge: `collect_from_fixtures` özyinelemesiz çalışır ve
`data/raw/<slug>/` kökünde repoya işlenmiş yalnız üç sentetik örnek vardır
(`albaraka/konut.html`, `kuveyt-turk/konut.txt`, `turkiye-finans/tasit.txt`).
Scrape edilen 846 belge `live/`, `products/`, `manual/` alt klasörlerindedir ve
fixture yolundan görünmez. Bu davranış BİLEREK korunuyor: fixture kümesi
testlerin deterministik, ağdan ve scrape çıktısından bağımsız zeminidir.

`run_pipeline` artık **hangi modda kaç belge yüklediğini raporlar**
(`PipelineResult.mode` / `.documents_loaded` / `.docs_per_bank`). Sebebi
doğrudan bu projede avlanan hata sınıfıdır: eski demo yolu sessizce 3 belge
yükleyip "hazır" diyordu, `GET /contradictions` boş dönüyordu ve hiçbir yerde
"yalnız 3 belge okundu" yazmıyordu. Sayıyı görünür kılmak, o hatanın bir daha
sessiz kalmasını engeller.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .chatbot.bot import Chatbot
from .comparison.contradiction import detect as detect_contradictions
from .db.repository import Repository
from .extraction.llm.extractor import LLMExtractor, default_extractor
from .extraction.ner.classifier import default_classifier
from .extraction.reconcile import build_campaign
from .preprocessing.clean import normalize_text
from .scraping.collector import METHOD_FIXTURE, RawDoc, collect, content_hash
from .scraping.config import BankConfig, load_banks

# Mod adları — çağıranlar string yerine bunları kullanmalı.
MODE_FIXTURE = "fixture"
MODE_CORPUS = "corpus"
MODE_LIVE = "live"
MODE_AUTO = "auto"

# `corpus` modunda okunan uzantı: YALNIZ `.txt`.
#
# `.html` bilerek DIŞARIDA: `data/raw` her canlı belgeyi hem ham `.html` hem
# temizlenmiş `.txt` olarak tutar (provenance, CLAUDE.md §14). İkisini birden
# okumak (a) 849 belgeyi 1696 gibi gösterir, (b) `.txt` üretimde çıkarıcının
# gördüğü girdidir — HTML üzerinde ölçülen her şey sevk etmediğimiz bir kod
# yolunu ölçer. Ölçüm ve gerekçe: `eval/properties.py:load_corpus` docstring'i.
CORPUS_SUFFIX = ".txt"

# İlerleme geri çağrısı: (işlenen, toplam, banka_slug)
ProgressFn = Callable[[int, int, str], None]


@dataclass
class PipelineResult:
    """Bir pipeline koşusunun sonucu + **kapsam bilgisi**.

    `campaigns_stored` tek başına yanıltıcıdır: "3 kampanya kaydedildi" cümlesi
    3 belgelik bir fixture koşusunda da, 849 belgelik bir korpus koşusunun
    hatalı süzülmüş halinde de aynı görünür. Bu yüzden mod ve belge sayıları
    sonucun parçasıdır.
    """

    campaigns_stored: int
    contradictions: list[dict]
    mode: str = MODE_AUTO
    documents_loaded: int = 0
    docs_per_bank: dict[str, int] = field(default_factory=dict)
    # LLM katmanının künyesi: istendi mi, kuruldu mu, kaç çağrı yapıldı.
    #
    # Neden sonucun parçası: 2026-08-21'e kadar üretim korpusu 7.032 alanın
    # TAMAMINI `rule` olarak üretiyordu ve bunu hiçbir çıktı arıza gibi
    # göstermiyordu. `run_pipeline` LLM'i `default_extractor()` üzerinden
    # kuruyor; `LLM_BACKEND` boşsa sessizce `NullLLMExtractor`a düşüyor ve
    # `reconcile()` LLM'e hiç sormuyor. Rapor "kaç kampanya" diyordu,
    # "ikinci katman ateşledi mi" demiyordu — o soru sorulmadığı için de iki
    # jüri turu boyunca cevapsız kaldı. Künye sonucun parçası olunca cevap
    # ölçülür hâle gelir. Ayrıntı: docs/rapor/llm-uretim-devreye-alma.md
    llm: dict = field(default_factory=dict)

    def summary(self) -> str:
        """Tek satırlık insan-okur özet (betikler ve loglar için)."""
        banks_with_docs = sum(1 for n in self.docs_per_bank.values() if n)
        llm = self.llm or {}
        katman = ("kural-only" if not llm.get("available")
                  else f"kural+llm({llm.get('calls', 0)} cagri)")
        return (f"mod={self.mode} belge={self.documents_loaded} "
                f"kampanya={self.campaigns_stored} "
                f"banka={banks_with_docs}/{len(self.docs_per_bank)} "
                f"celiski={len(self.contradictions)} "
                f"katman={katman}")


def collect_corpus(bank: BankConfig, raw_dir: str | Path = "data/raw",
                   scraped_at: Optional[str] = None) -> list[RawDoc]:
    """`data/raw/<slug>/` altındaki TÜM `.txt` belgeleri özyinelemeli okur.

    `collector.collect_from_fixtures(recursive=True)` yerine ayrı bir fonksiyon
    olmasının sebebi uzantı süzgeci: fixture yolu `.html`'i de okur, korpus yolu
    okumamalıdır (bkz. `CORPUS_SUFFIX`).

    Provenance korunur: `<dosya>.txt.meta.json` yanındaysa `source_url`,
    `scraped_at`, `content_hash`, `collection_method`, `title`,
    `campaign_status` oradan alınır. Sidecar yoksa `source_url` `file://`
    yoluna düşer — uydurulmaz.

    `campaign_status` sidecar'da yoksa `None` kalır ve bu "süresi dolmamış"
    ANLAMINA GELMEZ, "bilinmiyor" demektir (bkz. `db.base.suresi_dolmus_mu`).
    Korpustaki 1774 belgenin 1316'sı damgasızdır; bunları varsayılan olarak
    geçerli ya da geçersiz saymak, ölçülmemiş bir bilgi iddia etmek olurdu.
    """
    base = Path(raw_dir) / bank.slug
    docs: list[RawDoc] = []
    if not base.is_dir():
        return docs
    for path in sorted(base.rglob(f"*{CORPUS_SUFFIX}")):
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        text = normalize_text(content)
        if not text:
            continue
        meta = _read_sidecar(path)
        docs.append(RawDoc(
            bank_slug=bank.slug,
            source_url=meta.get("source_url") or f"file://{path}",
            clean_text=text,
            scraped_at=meta.get("scraped_at") or scraped_at,
            content_hash=meta.get("content_hash") or content_hash(content),
            collection_method=meta.get("collection_method") or METHOD_FIXTURE,
            title=meta.get("title"),
            campaign_status=meta.get("campaign_status"),
        ))
    return docs


def _read_sidecar(path: Path) -> dict:
    """`<dosya>.meta.json` provenance sidecar'ını okur (yoksa boş sözlük)."""
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    if not meta_path.is_file():
        return {}
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _collect_for_mode(bank: BankConfig, raw_dir: str, mode: str,
                      scraped_at: Optional[str]) -> list[RawDoc]:
    """Moda göre belge toplama. `corpus` dışındaki modlar collector'a gider."""
    if mode == MODE_CORPUS:
        return collect_corpus(bank, raw_dir=raw_dir, scraped_at=scraped_at)
    return list(collect(bank, raw_dir=raw_dir, mode=mode, scraped_at=scraped_at))


def run_pipeline(repo: Repository, banks_yaml: str, raw_dir: str = "data/raw",
                 mode: str = MODE_AUTO, llm: Optional[LLMExtractor] = None,
                 scraped_at: Optional[str] = None,
                 on_progress: Optional[ProgressFn] = None,
                 limit: Optional[int] = None) -> PipelineResult:
    """Tüm bankalar için topla → çıkar → sınıflandır → kaydet.

    İki fazlıdır: önce tüm bankaların belgeleri toplanır (böylece toplam belge
    sayısı bilinir ve `on_progress` gerçek bir ilerleme yüzdesi verebilir),
    sonra çıkarım koşar.

    Args:
        mode: `fixture` | `corpus` | `live` | `auto` (bkz. modül başlığı).
        on_progress: her belgeden SONRA `(işlenen, toplam, banka_slug)` ile
            çağrılır. 849 belgelik korpus koşusunda betiğin ilerleme basması
            için.
        limit: toplanan belge sayısını bu sayıya indirger — **yalnız SÜRE
            ölçümü için**. LLM açıkken tam korpus koşumu saatler sürüyor
            (ölçüm: docs/rapor/llm-uretim-devreye-alma.md §6); süreyi tahmin
            etmek için tam koşumu beklemek gerekmemeli.

            Örnekleme ADIMLIdır (her k'ncı belge), ilk N değil. İlk N alınsa
            örneklem tek bankanın belgeleriyle dolardı (belgeler banka banka
            toplanıyor) ve ölçülen süre o bankanın belge uzunluğuna göre
            sapardı. Adımlı örnekleme deterministiktir — aynı `limit` aynı
            belgeleri verir — ama **kalite iddiası için kullanılamaz**:
            rastgele değildir, dolayısıyla temsilî değildir. Yalnız süre.
    """
    banks = load_banks(banks_yaml)
    llm = llm if llm is not None else default_extractor()
    clf = default_classifier()

    # 1. faz — toplama (banka kayıtları belge çıkmasa da açılır)
    per_bank: list[tuple[BankConfig, list[RawDoc]]] = []
    docs_per_bank: dict[str, int] = {}
    for bank in banks:
        repo.upsert_bank(bank.name, bank.slug, bank.website_url, bank.bddk_active)
        docs = _collect_for_mode(bank, raw_dir, mode, scraped_at)
        per_bank.append((bank, docs))
        docs_per_bank[bank.slug] = len(docs)
    total = sum(docs_per_bank.values())

    if limit is not None and 0 < limit < total:
        per_bank = _adimli_ornek(per_bank, limit, total)
        docs_per_bank = {b.slug: len(d) for b, d in per_bank}
        total = sum(docs_per_bank.values())

    # 2. faz — çıkarım + kayıt
    stored = 0
    contradictions: list[dict] = []
    done = 0
    for bank, docs in per_bank:
        for doc in docs:
            text = normalize_text(doc.clean_text)
            # `source_url` sınıflandırıcıya VERİLİR: URL yolu bu alanın en
            # güçlü sinyalidir (bkz. ner/classifier.py modül başlığı, kusur 2)
            # ve sayfa çerçevesi metni kirlettiğinde tek güvenilir kanıttır.
            ctype, _conf = clf.classify(text, doc.source_url)
            campaign = build_campaign(text, bank_slug=bank.slug,
                                      source_url=doc.source_url, llm=llm,
                                      campaign_type=ctype)
            for con in detect_contradictions(campaign):
                contradictions.append({"bank": bank.slug, "kind": con.kind,
                                       "detail": con.detail})
            # `campaign_status` toplama anında BİLİNİYOR (sidecar'da yazılı) ve
            # burada DB'ye taşınır. Alternatifi, `build_demo_db` içinde
            # `source_url` üzerinden ikinci bir korpus taraması yapmaktı —
            # `belge_turu` orada öyle atanıyor. Bu alanda o yol YANLIŞ olurdu:
            # `source_url` tekil değil (ölçüldü: 88 URL birden fazla bölümde),
            # ve aynı sayfanın `live/` ile `archive/` kopyaları tam da durumu
            # FARKLI olan çifttir. Belge başına taşımak bu çakışmayı hiç
            # doğurmaz.
            repo.insert_campaign(campaign, clean_text=text,
                                 scraped_at=doc.scraped_at,
                                 campaign_status=doc.campaign_status)
            stored += 1
            done += 1
            if on_progress is not None:
                on_progress(done, total, bank.slug)
    return PipelineResult(stored, contradictions, mode=mode,
                          documents_loaded=total, docs_per_bank=docs_per_bank,
                          llm=llm.summary())


def _adimli_ornek(per_bank: list[tuple[BankConfig, list[RawDoc]]], limit: int,
                  total: int) -> list[tuple[BankConfig, list[RawDoc]]]:
    """Belgeleri banka sırasına göre düzleştirip her k'ncısını seçer.

    Gerekçe `run_pipeline(limit=...)` docstring'inde. Banka kayıtları
    korunur: belgesi kalmayan banka da listede kalır, yoksa
    `docs_per_bank` bankaları sessizce kaybeder ve rapor "kaç banka" sorusuna
    yanlış cevap verir.
    """
    duz = [(i, b, d) for i, (b, docs) in enumerate(per_bank) for d in docs]
    adim = max(1, total // limit)
    secilen = duz[::adim][:limit]
    kova: dict[int, list[RawDoc]] = {i: [] for i in range(len(per_bank))}
    for i, _b, d in secilen:
        kova[i].append(d)
    return [(b, kova[i]) for i, (b, _docs) in enumerate(per_bank)]


def build_demo_repo(banks_yaml: str = "config/banks.yaml",
                    raw_dir: str = "data/raw",
                    mode: str = MODE_FIXTURE) -> Repository:
    """Önceden doldurulmuş in-memory DB (demo stratejisi).

    İlgili: ../decisions/demo-onceden-doldurulmus-db.md

    Varsayılan `fixture` KORUNUYOR: mevcut testler ve chatbot beklentileri
    (`tests/test_scraping_pipeline.py`) 3 belgelik deterministik kümeye bağlıdır.
    Gerçek 849 belgelik demo DB'si için `scripts/build_demo_db.py` kullanılır —
    o kalıcı bir dosya üretir, her açılışta yeniden kurulmaz (CLAUDE.md §11).
    """
    repo = Repository(":memory:")
    run_pipeline(repo, banks_yaml, raw_dir=raw_dir, mode=mode)
    return repo


def make_chatbot(repo: Repository, llm: Optional[LLMExtractor] = None) -> Chatbot:
    return Chatbot(repo, llm=llm)


__all__ = [
    "MODE_AUTO", "MODE_CORPUS", "MODE_FIXTURE", "MODE_LIVE", "PipelineResult",
    "build_demo_repo", "collect_corpus", "make_chatbot", "run_pipeline",
]
