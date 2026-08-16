"""1 dakikalık kesit — dolu veri, detaylı anlatım, hızlandırılmış görüntü.

İki hızlandırma var ve ikisi ayrı işe yarıyor:

  ses    · edge-tts `+38%`  → aynı saniyede daha çok cümle
  görüntü· setpts/1.4       → aynı saniyede daha çok ekran

Görüntü hızlandırması sahte bir hız değil: her sahnede kaynak pencere
`sure × HIZ` kadar alınıp `sure`ye sıkıştırılıyor, yani sahne %40 daha
fazla kaydırma/tıklama gösteriyor. Kare atlanmıyor, gerçek görüntü.

Süreler `ses3.json`daki ÖLÇÜLEN cümle sürelerinden türetiliyor; 60 saniye
aşılırsa çıktı bunu haykırır.
"""
from __future__ import annotations

import json
import os
import subprocess
from collections import OrderedDict
from pathlib import Path

T = Path(os.environ["CLAUDE_JOB_DIR"]) / "tmp"
KLIP = T / "klip2"
ARA = T / "segment3"
ARA.mkdir(parents=True, exist_ok=True)

EN, BOY, FPS = 1920, 1080, 30
GECIS = 0.42
ONSES, ARTSES, ARA_BOSLUK = 0.28, 0.30, 0.15
HIZ = 1.4            # görüntü hızlandırma çarpanı
TAVAN = 60.0         # şartname s.19

# Kullanıcının istediği sıra + kapanışta Ayarlar.
# `bas=None` → pencereyi klibin SONUNA yasla: seçimler (banka, tür, alan)
# klibin başında yapılıyor, en dolu tablo sonda oluşuyor.
SIRA = ["cetvel3", "avantaj3", "banka3", "celiski", "sohbet", "tazele",
        "kanit", "ayarlar"]
BASLANGIC: dict[str, float | None] = dict.fromkeys(SIRA)


def kos(*a: str) -> None:
    ç = subprocess.run(list(a), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if ç.returncode:
        raise RuntimeError(ç.stderr.decode()[-900:])


def olc(yol: Path) -> float:
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(yol)],
        capture_output=True, text=True, check=True).stdout.strip())


def main() -> None:
    ses = json.loads((T / "ses3.json").read_text(encoding="utf-8"))
    sahne_cumleleri: OrderedDict[str, list[dict]] = OrderedDict((s, []) for s in SIRA)
    for k in ses:
        sahne_cumleleri[k["sahne"]].append(k)

    # sahne süresi = ön nefes + cümleler + aralar + kuyruk   (ÖLÇÜM, tahmin değil)
    sureler, ofsetler = [], []
    for ad in SIRA:
        cs, t, yerler = sahne_cumleleri[ad], 0.0, []
        for c in cs:
            yerler.append((c, t))
            t += c["sure"] + ARA_BOSLUK
        t -= ARA_BOSLUK
        sureler.append(round(ONSES + t + ARTSES, 3))
        ofsetler.append(yerler)

    print("segmentler (kaynak penceresi ×%.1f hızlandırılıyor):" % HIZ)
    segmentler = []
    for ad, sure in zip(SIRA, sureler, strict=True):
        girdi = next((KLIP / ad).glob("*.webm"))
        ham, pencere = olc(girdi), sure * HIZ
        bas = BASLANGIC[ad]
        if bas is None:
            bas = ham - pencere
        if bas < 0 or bas + pencere > ham + 1e-6:
            bas = max(0.0, ham - pencere)
            print(f"  ⚠ {ad}: klip {ham:.1f}s < kaynak penceresi {pencere:.1f}s "
                  f"— hızlandırma bu sahnede tam uygulanamadı")
        cikti = ARA / f"{ad}.mp4"
        kos("ffmpeg", "-y", "-loglevel", "error", "-ss", f"{bas}", "-i", str(girdi),
            "-t", f"{pencere}",
            "-vf", (f"scale={EN}:{BOY}:force_original_aspect_ratio=increase,"
                    f"crop={EN}:{BOY},setpts=PTS/{HIZ},fps={FPS},setsar=1"),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", str(FPS), str(cikti))
        segmentler.append(cikti)
        print(f"  {ad:9s} kaynak {bas:5.1f}→{bas + pencere:5.1f} ({pencere:4.1f}s)"
              f"  → sahne {sure:4.1f}s")

    # görüntü
    girdiler: list[str] = []
    for s in segmentler:
        girdiler += ["-i", str(s)]
    suzgec, onceki, gecen = [], "[0:v]", sureler[0]
    for i in range(1, len(segmentler)):
        etiket, ofs = f"[v{i}]", gecen - GECIS
        suzgec.append(f"{onceki}[{i}:v]xfade=transition=fade:"
                      f"duration={GECIS}:offset={ofs:.3f}{etiket}")
        onceki, gecen = etiket, ofs + sureler[i]
    gorsel = ARA / "_g.mp4"
    kos("ffmpeg", "-y", "-loglevel", "error", *girdiler,
        "-filter_complex", ";".join(suzgec), "-map", onceki,
        "-c:v", "libx264", "-preset", "slow", "-crf", "19",
        "-pix_fmt", "yuv420p", "-r", str(FPS), str(gorsel))
    print(f"birleştirme:\n  görüntü → {gecen:.1f}s")

    # ses — her cümle MUTLAK saniyesine
    sahne_bas, t = [], 0.0
    for i, s in enumerate(sureler):
        sahne_bas.append(t)
        t += s - (GECIS if i < len(sureler) - 1 else 0)
    girdiler, suzgec, etiketler, n = [], [], [], 0
    for yerler, sb in zip(ofsetler, sahne_bas, strict=True):
        for c, ofs in yerler:
            girdiler += ["-i", str(T / "ses3" / c["dosya"])]
            g = int((sb + ONSES + ofs) * 1000)
            suzgec.append(f"[{n}:a]adelay={g}|{g}[a{n}]")
            etiketler.append(f"[a{n}]")
            n += 1
    sesyolu = ARA / "_s.m4a"
    kos("ffmpeg", "-y", "-loglevel", "error", *girdiler,
        "-filter_complex", ";".join(suzgec) +
        f";{''.join(etiketler)}amix=inputs={n}:normalize=0:dropout_transition=0[mix]",
        "-map", "[mix]", "-t", f"{t:.3f}",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(sesyolu))
    print(f"  ses     → {t:.1f}s ({n} cümle)")

    son = T / "anatolia-ai-demo-1dk-dolu.mp4"
    kos("ffmpeg", "-y", "-loglevel", "error", "-i", str(gorsel), "-i", str(sesyolu),
        "-c:v", "copy", "-c:a", "copy", "-shortest",
        "-movflags", "+faststart", str(son))
    s = olc(son)
    print(f"\n{'⚠ TAVAN AŞILDI' if s > TAVAN else '✅'} {son.name}  {s:.1f} sn  "
          f"{son.stat().st_size / 1024 / 1024:.1f} MB  (tavan {TAVAN:.0f} sn)")


if __name__ == "__main__":
    main()
