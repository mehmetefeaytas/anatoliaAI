"""Colab duman testi — LLM ilk kez gerçek Türkçe kampanya metninde çalışıyor mu?

Kullanım (tek Colab hücresi, kopyala-yapıştır hatası olmaz):

    !wget -qO smoke.py https://raw.githubusercontent.com/mehmetefeaytas/anatoliaAI/main/colab/00_smoke_test.py
    %run smoke.py

Önkoşul: Ollama ayakta ve model çekilmiş (bkz. colab/01_setup.py).

Neyi ölçüyor:
  1) "%1,89 ile 120 aya kadar" -> 1.89 (ARALIK DEĞİL; "120 ay" bir vadedir)
  2) gerçek aralık + fiil negasyonu ("alınmaz") + hedef kitle
  3) çelişki sinyali: masrafsız iddiası + pozitif tahsis ücreti
  4) nötr metin -> HEPSİ null   <-- en kritik: halüsinasyon testi

İlgili: app/CLAUDE.md §6 (zor anlama vakaları), §21 (halüsinasyon yasağı)
        şartname §5.5 (terminoloji), §5.6 (normalizasyon denklikleri)
"""

import json
import os
import urllib.request
from typing import Optional

MODEL = os.environ.get("SMOKE_MODEL", "qwen3:32b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

# --------------------------------------------------------------------------- #
# Şema — alan tipli, her anahtar zorunlu
# --------------------------------------------------------------------------- #
SEGMENTS = [
    "yeni_musteri",
    "mevcut_musteri",
    "maas_musterisi",
    "belirli_segment",
]

NUM_OR_RANGE = {
    "anyOf": [
        {"type": "number"},
        {
            "type": "object",
            "properties": {
                "min": {"type": "number"},
                "max": {"type": "number"},
            },
            "required": ["min", "max"],
        },
        {"type": "null"},
    ]
}

FEE_STATUS = {
    "anyOf": [
        {
            "type": "object",
            "properties": {
                "has_fee": {"type": "boolean"},
                "amount": {"anyOf": [{"type": "number"}, {"type": "null"}]},
            },
            "required": ["has_fee"],
        },
        {"type": "null"},
    ]
}

AUDIENCE = {
    "anyOf": [
        {"type": "array", "items": {"type": "string", "enum": SEGMENTS}},
        {"type": "null"},
    ]
}

FIELDS = [
    "kar_payi_orani",
    "vade_ay",
    "tahsis_ucreti",
    "masraf_durumu",
    "hedef_kitle",
]

SCHEMA = {
    "type": "object",
    "properties": {
        "kar_payi_orani": NUM_OR_RANGE,
        "vade_ay": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "tahsis_ucreti": {"anyOf": [{"type": "number"}, {"type": "null"}]},
        "masraf_durumu": FEE_STATUS,
        "hedef_kitle": AUDIENCE,
    },
    # Modeli HER anahtarı üretmeye zorla: olmayan alan açıkça null olsun.
    # "Atlandı" ile "yok" karışırsa halüsinasyon oranı ölçülemez.
    "required": FIELDS,
}

# --------------------------------------------------------------------------- #
# Sistem promptu — §5.5 terminolojisi açık tanımlarla
# --------------------------------------------------------------------------- #
SYSTEM = """Sen katılım bankacılığı (faizsiz finans) metinlerinden bilgi çıkaran bir asistansın.

TERMİNOLOJİ (doğru yorumlaman zorunlu):
- kâr payı oranı: FAİZ DEĞİLDİR. Murabahada önceden ilan edilen kâr marjıdır.
- finansman: kredi yerine kullanılır (konut/taşıt/ihtiyaç finansmanı).
- katılım fonu: mevduat yerine kullanılır.
- masrafsız finansman: masraf SIFIR demektir, "bilgi yok" DEĞİL.
- tahsis ücreti: finansman tahsisinde alınan tek seferlik ücret.

KURALLAR:
- Metinde AÇIKÇA yazmayan hiçbir değeri UYDURMA. Yoksa null yaz.
- "alınmaz / talep edilmez / yoktur" negasyondur -> ücret 0, null değil.
- Aylık ve yıllık oranları karıştırma.
- TR sayı biçimi: 1.500,00 = bin beş yüz. Nokta binlik, virgül ondalıktır.
- "X aya kadar vade" bir VADEDİR; oran aralığının üst sınırı DEĞİLDİR."""

TESTS = [
    (
        "aralik-tuzagi",
        "Konut finansmanında kâr payı oranı %1,89 ile 120 aya kadar vade. "
        "Tahsis ücreti 1.500,00 TL. "
        "Kampanya 31.12.2026 tarihine kadar geçerlidir.",
    ),
    (
        "gercek-aralik+negasyon",
        "YENİ MÜŞTERİLERE ÖZEL. Taşıt finansmanı kâr payı oranı "
        "%1,99 - %2,49 arasında, 48 ay vade. Yıllık kart ücreti alınmaz.",
    ),
    (
        "celiski",
        "Bu kampanya masrafsızdır. "
        "Ancak tahsis ücreti 500 TL olarak tahsil edilir.",
    ),
    (
        "halusinasyon-testi",
        "Şubelerimiz hafta içi 09:00-17:00 arası hizmet vermektedir.",
    ),
]


def sor(metin: str) -> dict:
    """Tek bir metni modele sorar, şema-geçerli JSON döndürür."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": metin},
        ],
        "format": SCHEMA,
        "stream": False,
        "options": {
            "temperature": 0,   # deterministik -> eval tekrar-üretilebilir
            "seed": 42,
            # KRİTİK: Ollama varsayılanı 2048 token. Prompt + şema + metin
            # bunu aşar ve Ollama SESSİZCE kırpar -> bozuk JSON üretir,
            # biz de modeli suçlarız.
            "num_ctx": 8192,
            "num_predict": 512,
        },
    }
    # qwen3'te DÜŞÜNME MODU varsayılan AÇIK: model yanıttan önce
    # <think>...</think> bloğu üretir ve ham içerik geçerli JSON olmaz.
    # Ollama 0.9+ bunu kapatmayı destekler; desteklemeyen sürümlerde
    # aşağıdaki sağlam ayrıştırıcı bloğu zaten soyar.
    payload["think"] = False

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return _sagam_json(body["message"]["content"])


def _sagam_json(raw: str) -> dict:
    """Ham LLM çıktısından JSON nesnesini söker.

    Düz `json.loads` yetmez: model <think> bloğu, markdown çiti ya da
    açıklama metni ekleyebilir. Bu, app/src/extraction/llm/parse.py'deki
    ayrıştırıcının küçültülmüş halidir (colab/ bağımsız çalışsın diye
    kopyalandı; asıl sürüm 18 patolojiye karşı test edilmiştir).
    """
    if raw is None:
        raise ValueError("bos yanit")
    s = raw.strip()

    # <think>...</think> bloğunu at
    if "</think>" in s:
        s = s.split("</think>", 1)[1].strip()

    # ```json ... ``` çitini soy
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s[3:]
        if "```" in s:
            s = s.rsplit("```", 1)[0]
        s = s.strip()

    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # Süslü parantez SAYARAK ilk dengeli nesneyi bul (string içi yok sayılır)
    start = s.find("{")
    if start < 0:
        raise ValueError(f"yanitta JSON nesnesi yok. Ham cikti:\n{raw[:400]}")
    depth, in_str, esc = 0, False, False
    for i in range(start, len(s)):
        ch = s[i]
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(s[start:i + 1])
    raise ValueError(f"dengeli JSON kapanmamis (kesik?). Ham cikti:\n{raw[:400]}")


def _saglik_kontrolu() -> Optional[str]:
    """Ollama ayakta mı? Değilse anlaşılır bir hata mesajı döndürür.

    Bu kontrol olmadan tüm testler 'Connection refused' alır ve — daha
    kötüsü — halüsinasyon testi YANLIŞLIKLA GEÇER: yanıt gelmediği için
    "hiçbir alan uydurulmamış" görünür. Yani bağlantı hatası BAŞARI diye
    raporlanırdı. Sessizce yanlış "başarı" bu projedeki en tehlikeli hata
    sınıfıdır; test aracının kendisi de ondan muaf değil.
    """
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as r:
            json.loads(r.read())
        return None
    except Exception as exc:
        return (
            f"Ollama'ya ulasilamiyor ({OLLAMA_URL}): {type(exc).__name__}\n\n"
            "  Muhtemel sebep: setup betigi `python setup.py` ile alt surec\n"
            "  olarak kosuldu; script bitince `ollama serve` de oldu.\n\n"
            "  Cozum — kurulum hucresini soyle calistirin:\n"
            "      !wget -qO setup.py https://raw.githubusercontent.com/"
            "mehmetefeaytas/anatoliaAI/main/colab/01_setup.py\n"
            "      %run setup.py\n"
            "  (satir baslarinda BOSLUK olmamali)\n\n"
            "  Ya da bu betik kendisi baslatsin:\n"
            "      %env SMOKE_AUTOSTART=1"
        )


def _ollama_baslat() -> bool:
    """SMOKE_AUTOSTART=1 ise Ollama'yı bu süreçten bağımsız başlatır."""
    import shutil
    import subprocess
    import time

    exe = shutil.which("ollama") or "/usr/local/bin/ollama"
    if not os.path.exists(exe):
        print("ollama bulunamadi — once 01_setup.py calistirin.")
        return False
    env = dict(os.environ, OLLAMA_HOST="127.0.0.1:11434",
               OLLAMA_KEEP_ALIVE="-1")
    # start_new_session: sunucu bu surecin olumunden SAG KURTULSUN
    subprocess.Popen([exe, "serve"], env=env, start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(1)
        if _saglik_kontrolu() is None:
            print("Ollama baslatildi.\n")
            return True
    return False


def main() -> int:
    print(f"model = {MODEL}")
    print(f"url   = {OLLAMA_URL}\n")

    hata = _saglik_kontrolu()
    if hata and os.environ.get("SMOKE_AUTOSTART") == "1":
        _ollama_baslat()
        hata = _saglik_kontrolu()
    if hata:
        print("=" * 62)
        print("KOSULAMADI — LLM servisi ayakta degil")
        print("=" * 62)
        print(hata)
        return 2

    sonuclar: dict[str, dict] = {}
    hatalar: dict[str, str] = {}
    for etiket, metin in TESTS:
        print(f"--- [{etiket}] {metin[:64]}...")
        try:
            out = sor(metin)
            sonuclar[etiket] = out
            print(json.dumps(out, ensure_ascii=False, indent=2))
        except Exception as exc:
            hatalar[etiket] = f"{type(exc).__name__}: {exc}"
            print(f"HATA: {hatalar[etiket]}")
        print()

    print("=" * 62)
    print("OTOMATIK KONTROL")
    print("=" * 62)

    def yaz(etiket: str, no: str, kosul: bool, detay: str) -> bool:
        """Yanıt HİÇ gelmediyse GECTI yazma — HATA yaz.

        Yanıtsız bir testi 'geçti' saymak, bağlantı hatasını başarı diye
        raporlamak demektir.
        """
        if etiket in hatalar:
            print(f"[HATA ] {no} -> yanit alinamadi: {hatalar[etiket]}")
            return False
        print(f"[{'GECTI' if kosul else 'KALDI'}] {no} -> {detay}")
        return kosul

    a = sonuclar.get("aralik-tuzagi") or {}
    yaz("aralik-tuzagi", "1) oran 1.89, aralik degil",
        a.get("kar_payi_orani") == 1.89, repr(a.get("kar_payi_orani")))

    b = sonuclar.get("gercek-aralik+negasyon") or {}
    kp = b.get("kar_payi_orani")
    yaz("gercek-aralik+negasyon", "2a) gercek aralik",
        isinstance(kp, dict) and kp.get("min") == 1.99, repr(kp))
    yaz("gercek-aralik+negasyon", "2b) fiil negasyonu",
        (b.get("masraf_durumu") or {}).get("has_fee") is False,
        repr(b.get("masraf_durumu")))

    c = sonuclar.get("celiski") or {}
    yaz("celiski", "3) celiski sinyali",
        (c.get("masraf_durumu") or {}).get("has_fee") is False
        and (c.get("tahsis_ucreti") or 0) > 0,
        f"masraf={c.get('masraf_durumu')!r} tahsis={c.get('tahsis_ucreti')!r}")

    print()
    if "halusinasyon-testi" in hatalar:
        print("!!! HALUSINASYON TESTI KOSULAMADI — yanit gelmedi.")
        print("    Bu bir GECIS DEGILDIR. Sonuc bilinmiyor.")
        return 1

    d = sonuclar.get("halusinasyon-testi") or {}
    uydurma = [k for k in FIELDS if d.get(k) is not None]
    if not uydurma:
        print("[GECTI] 4) HALUSINASYON: notr metinde uydurulan alan YOK")
        print("        Model bilmedigini biliyor.")
        return 0
    print(f"[KALDI] 4) HALUSINASYON: uydurulan alan -> {uydurma}")
    print("        250 belgeye gecmeden once prompt sikilmalidir.")
    return 1


if __name__ == "__main__":
    main()
