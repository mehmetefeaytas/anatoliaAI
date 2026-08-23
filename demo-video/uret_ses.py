"""Anlatım metinlerinden Bing/Edge seslendirme motoruyla ses üretir.

Her sahnenin sesi ÖNCE üretilir, süresi ÖLÇÜLÜR; görüntü tarafı sonra bu süreye
uydurulur. Ters sıra denenirse (önce video, sonra ses) her sahnede ses ya
kesilir ya da sessizlik biriktirir — süre yalnızca sentezden sonra bilinir.

## Birden çok senaryo

Senaryo dosyası argümanla verilebilir (`uret_ses.py senaryo-60.json`). Çıktı
adları senaryo adından türetilir — `senaryo-60.json` → `ses-60/`,
`anlatim-60/`, `sesler-60.json` — böylece beş dakikalık sürümün sesleri bir
dakikalık sürümü üretirken ezilmiyor.
"""

import asyncio
import json
import pathlib
import subprocess
import sys

import edge_tts

KOK = pathlib.Path(__file__).parent
SENARYO_YOLU = KOK / (sys.argv[1] if len(sys.argv) > 1 else "senaryo.json")
SENARYO = json.loads(SENARYO_YOLU.read_text(encoding="utf-8"))
SONEK = SENARYO_YOLU.stem.replace("senaryo", "", 1)   # "" ya da "-60"
SES_DIZIN = KOK / f"ses{SONEK}"
ANLATIM_DIZIN = KOK / f"anlatim{SONEK}"


def sure_olc(dosya: pathlib.Path) -> float:
    """ffprobe ile saniye cinsinden süre. Kendi tahminimize güvenmiyoruz."""
    ciktı = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(dosya)],
        capture_output=True, text=True, check=True,
    )
    return float(ciktı.stdout.strip())


async def main() -> None:
    SES_DIZIN.mkdir(exist_ok=True)
    ANLATIM_DIZIN.mkdir(exist_ok=True)
    ayar = SENARYO["ses"]
    kunye = []

    for sahne in SENARYO["sahneler"]:
        metin = sahne["anlatim"]
        (ANLATIM_DIZIN / f"{sahne['id']}.txt").write_text(metin, encoding="utf-8")
        hedef = SES_DIZIN / f"{sahne['id']}.mp3"
        iletisim = edge_tts.Communicate(metin, ayar["ses_adi"], rate=ayar["hiz"])
        await iletisim.save(str(hedef))
        sure = sure_olc(hedef)
        kunye.append({"id": sahne["id"], "ses": hedef.name, "sure": round(sure, 3)})
        print(f"{sahne['id']:<24} {sure:6.2f} sn")

    toplam = sum(k["sure"] for k in kunye)
    (KOK / f"sesler{SONEK}.json").write_text(
        json.dumps({"sahneler": kunye, "toplam": round(toplam, 2)},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\ntoplam anlatım: {toplam:.1f} sn ({toplam/60:.2f} dk)")


asyncio.run(main())
