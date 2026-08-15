"""Demo videosu kurgusu — ffmpeg ile, ölçülen ses sürelerine göre.

Zaman çizgisi TAHMİNE değil ÖLÇÜME dayanır: `ses.json` her cümlenin gerçek
süresini taşıyor ve segment uzunlukları ona göre seçildi. Bu yüzden kendi
sesinle yeniden kaydettiğinde yalnız ilgili cümlenin dosyasını değiştirmen
yeterli — kurgu bozulmaz.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

T = Path(os.environ["CLAUDE_JOB_DIR"]) / "tmp"
KART = T / "kart"
KLIP = T / "klip"
ARA = T / "segment"
ARA.mkdir(parents=True, exist_ok=True)

EN, BOY, FPS = 1920, 1080, 30
GECIS = 0.6          # xfade süresi

# (ad, kaynak_tipi, kaynak, baslangic, sure, [(cumle_no, ofset), ...])
PLAN = [
    ("acilis",   "kart",  "acilis.png",  0,   8.5,  [(1, 0.8), (2, 2.2)]),
    ("problem",  "kart",  "problem.png", 0,  17.5,  [(3, 0.6), (4, 4.8), (5, 12.2)]),
    ("pano",     "klip",  "pano",        2.0, 10.5, [(6, 1.0)]),
    ("cetvel",   "klip",  "cetvel",      2.5, 19.0, [(7, 0.8), (8, 4.2), (9, 8.0), (10, 11.4)]),
    ("kanit",    "klip",  "kanit",       3.0, 17.0, [(11, 0.8), (12, 3.2), (13, 9.8)]),
    ("sohbet",   "klip",  "sohbet",     15.5,  9.5, [(14, 0.8), (15, 5.2)]),
    ("celiski",  "klip",  "celiski",     8.0,  7.7, [(16, 0.4)]),
    ("mimari",   "kart",  "mimari.png",  0,   12.0, [(17, 0.6), (18, 8.4)]),
    ("terminal", "mp4",   "terminal.mp4", 0.5, 11.5, [(19, 2.0)]),
    ("kapanis",  "kart",  "kapanis.png", 0,   8.0,  [(20, 1.0)]),
]


def kos(*a: str) -> None:
    subprocess.run(list(a), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def klip_yolu(ad: str) -> Path:
    return next((KLIP / ad).glob("*.webm"))


def segment_uret() -> list[Path]:
    yollar = []
    for ad, tip, kaynak, bas, sure, _ in PLAN:
        cikti = ARA / f"{ad}.mp4"
        if tip == "kart":
            # Çok yavaş bir yakınlaşma: kart canlı dursun ama dikkat dağıtmasın.
            sf = (f"scale={EN*2}:-2,zoompan=z='min(zoom+0.00018,1.06)':"
                  f"d={int(sure*FPS)}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                  f"s={EN}x{BOY}:fps={FPS},setsar=1")
            kos("ffmpeg", "-y", "-loglevel", "error", "-loop", "1",
                "-i", str(KART / kaynak), "-t", f"{sure}",
                "-vf", sf, "-c:v", "libx264", "-preset", "medium",
                "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), str(cikti))
        else:
            girdi = klip_yolu(kaynak) if tip == "klip" else T / kaynak
            sf = (f"scale={EN}:{BOY}:force_original_aspect_ratio=increase,"
                  f"crop={EN}:{BOY},fps={FPS},setsar=1")
            kos("ffmpeg", "-y", "-loglevel", "error", "-ss", f"{bas}",
                "-i", str(girdi), "-t", f"{sure}",
                "-vf", sf, "-c:v", "libx264", "-preset", "medium",
                "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), str(cikti))
        yollar.append(cikti)
        print(f"  segment {ad:9s} {sure:5.1f}s")
    return yollar


def gorsel_birlestir(segmentler: list[Path], cikti: Path) -> None:
    """xfade zinciri — segmentler birbirine yumuşak geçsin."""
    girdiler: list[str] = []
    for s in segmentler:
        girdiler += ["-i", str(s)]

    sureler = [p[4] for p in PLAN]
    suzgec, onceki, gecen = [], "[0:v]", sureler[0]
    for i in range(1, len(segmentler)):
        etiket = f"[v{i}]"
        ofset = gecen - GECIS
        suzgec.append(f"{onceki}[{i}:v]xfade=transition=fade:"
                      f"duration={GECIS}:offset={ofset:.3f}{etiket}")
        onceki, gecen = etiket, ofset + sureler[i]
    zincir = ";".join(suzgec)
    kos("ffmpeg", "-y", "-loglevel", "error", *girdiler,
        "-filter_complex", zincir, "-map", onceki,
        "-c:v", "libx264", "-preset", "slow", "-crf", "19",
        "-pix_fmt", "yuv420p", "-r", str(FPS), str(cikti))
    print(f"  görüntü birleşti → {gecen:.1f}s")


def ses_birlestir(cikti: Path) -> float:
    """Her cümleyi MUTLAK zamanına yerleştir (adelay + amix)."""
    ses = {k["no"]: k for k in json.loads((T / "ses.json").read_text(encoding="utf-8"))}
    sureler = [p[4] for p in PLAN]

    baslangic, gecen = [], 0.0
    for i, s in enumerate(sureler):
        baslangic.append(gecen)
        gecen += s - (GECIS if i < len(sureler) - 1 else 0)
    toplam = gecen

    girdiler, suzgec, etiketler = [], [], []
    n = 0
    for (ad, *_, cumleler), seg_bas in zip(PLAN, baslangic, strict=True):
        for no, ofset in cumleler:
            girdiler += ["-i", str(T / "ses" / ses[no]["dosya"])]
            gecikme = int((seg_bas + ofset) * 1000)
            suzgec.append(f"[{n}:a]adelay={gecikme}|{gecikme},volume=1.0[a{n}]")
            etiketler.append(f"[a{n}]")
            n += 1
    karisim = (f"{''.join(etiketler)}amix=inputs={n}:normalize=0:"
               f"dropout_transition=0[mix]")
    kos("ffmpeg", "-y", "-loglevel", "error", *girdiler,
        "-filter_complex", ";".join(suzgec) + ";" + karisim,
        "-map", "[mix]", "-t", f"{toplam:.3f}",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(cikti))
    print(f"  ses birleşti  → {toplam:.1f}s ({n} cümle)")
    return toplam


# Şartname s.19 ayrıca 1 dakikalık bir kesit istiyor. AYRI ÇEKİM YOK:
# uzun videonun dört sahnesi kesilir — ne olduğunu söyleyen, gerçekten
# çalıştığını gösteren, farkı gösteren ve kapatan sahneler.
KISA = ["acilis", "pano", "cetvel", "kanit", "kapanis"]


def main() -> None:
    import sys as _sys
    global PLAN
    kisa = "--kisa" in _sys.argv
    if kisa:
        PLAN = [p for p in PLAN if p[0] in KISA]
    print("segmentler:")
    segmentler = segment_uret()
    ek = "_kisa" if kisa else ""
    gorsel = ARA / f"_gorsel{ek}.mp4"
    print("birleştirme:")
    gorsel_birlestir(segmentler, gorsel)
    sesyolu = ARA / f"_ses{ek}.m4a"
    ses_birlestir(sesyolu)

    son = T / ("anatolia-ai-demo-1dk.mp4" if kisa else "anatolia-ai-demo.mp4")
    kos("ffmpeg", "-y", "-loglevel", "error", "-i", str(gorsel), "-i", str(sesyolu),
        "-c:v", "copy", "-c:a", "copy", "-shortest",
        "-movflags", "+faststart", str(son))
    sure = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(son)],
        capture_output=True, text=True, check=True).stdout.strip()
    mb = son.stat().st_size / 1024 / 1024
    print(f"\n✅ {son}  {float(sure):.1f}s  {mb:.1f} MB")


if __name__ == "__main__":
    main()
