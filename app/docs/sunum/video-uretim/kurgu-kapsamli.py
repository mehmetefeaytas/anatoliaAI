"""Kapsamlı demo kurgusu — yalnız gerçek arayüz klipleri, kart yok.

Zaman çizgisi TAHMİNE değil ÖLÇÜME dayanır: `ses2.json` her cümlenin gerçek
süresini taşır; segment uzunlukları o sürelerden türetilir. Bir cümleyi kendi
sesinle yeniden kaydedersen yalnız o dosyayı değiştir — kurgu bozulmaz.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

T = Path(os.environ["CLAUDE_JOB_DIR"]) / "tmp"
KLIP = T / "klip2"
ARA = T / "segment2"
ARA.mkdir(parents=True, exist_ok=True)

EN, BOY, FPS = 1920, 1080, 30
GECIS = 0.55
ONSES = 0.7          # ilk cümleden önceki nefes payı
ARTSES = 0.9         # son cümleden sonraki kuyruk

# (klip, baslangic_sn | None, [(cumle_no, klip_ici_ofset), ...])
#
# `None` = pencereyi klibin SONUNA yasla. Sekme turlarında sayfa yüklemesi
# klibin başındaki 6-7 saniyeyi yiyor; sabit bir başlangıç vermek yükleme
# ekranını kadraja sokuyordu (kare denetiminde yakalandı). Sona yaslamak
# içeriğin yüklü olduğunu garanti eder. Sabit sayı verilen iki sahne
# (açılış, cetvel) belirli bir TIKLAMA anını yakalamak zorunda.
PLAN = [
    ("acilis",  2.0, [(1, 0.0), (2, 8.1), (3, 15.3)]),
    ("cetvel",  9.0, [(4, 0.0), (5, 6.1), (6, 12.2), (7, 18.0)]),
    ("isi",    None, [(8, 0.0), (9, 5.8)]),
    ("avantaj", None, [(10, 0.0), (11, 6.3)]),
    ("banka",  None, [(12, 0.0)]),
    ("delta",  None, [(13, 0.0)]),
    ("celiski", None, [(14, 0.0), (15, 4.1), (16, 10.8)]),
    ("kanit",  None, [(17, 0.0), (18, 4.2), (19, 8.7), (20, 15.9)]),
    ("canli",  None, [(21, 0.0), (22, 5.3)]),
    ("sohbet", None, [(23, 0.0), (24, 8.4)]),
    ("tazele", None, [(25, 0.0)]),
    ("gunluk", None, [(26, 0.0), (27, 5.5), (28, 13.8)]),
]

# Şartname içinde açık bir süre çelişkisi var (s.14 "en çok 5 dakika" ↔ s.19
# "demo videosu 1 dakika"; `docs/SARTNAME-UYUM.md` satır 68). İkisi de üretilir.
#
# AYRI ÇEKİM YOK: kısa sürüm aynı kliplerden, cümlelerin bir alt kümesiyle
# kesilir — ne olduğunu söyleyen, kanıtı gösteren, farkı gösteren, kapatan.
KISA_PLAN = [
    ("acilis",  2.0, [(1, 0.0), (2, 8.1)]),
    ("kanit",  None, [(17, 0.0), (19, 4.2), (20, 11.4)]),
    ("celiski", None, [(14, 0.0), (15, 4.1)]),
    ("gunluk", None, [(28, 0.0)]),
]


def kos(*a: str) -> None:
    ç = subprocess.run(list(a), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if ç.returncode:
        raise RuntimeError(ç.stderr.decode()[-900:])


def olc(yol: Path) -> float:
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(yol)],
        capture_output=True, text=True, check=True).stdout.strip())


def klip_yolu(ad: str) -> Path:
    d = KLIP / ad
    v = sorted(d.glob("*.webm"))
    if not v:
        raise FileNotFoundError(f"{ad}: klip yok — çekim başarısız")
    return v[0]


def sahne_sureleri(ses: dict[int, dict]) -> list[float]:
    """Sahne süresi = son cümlenin bitişi + kuyruk. Uydurma değil, ölçüm."""
    sureler = []
    for _, _, cumleler in PLAN:
        son = max(ofset + ses[no]["sure"] for no, ofset in cumleler)
        sureler.append(round(ONSES + son + ARTSES, 2))
    return sureler


def segment_uret(sureler: list[float]) -> list[Path]:
    yollar = []
    for (ad, bas, _), sure in zip(PLAN, sureler, strict=True):
        girdi = klip_yolu(ad)
        ham = olc(girdi)
        if bas is None:
            bas = ham - sure
        if bas + sure > ham or bas < 0:
            # Klip yetmiyorsa sessizce yanlış kadraj basmak yerine haykır.
            bas = max(0.0, ham - sure)
            print(f"  ⚠ {ad}: klip {ham:.1f}s, pencere {sure:.1f}s → başlangıç {bas:.1f}s")
        cikti = ARA / f"{ad}.mp4"
        sf = (f"scale={EN}:{BOY}:force_original_aspect_ratio=increase,"
              f"crop={EN}:{BOY},fps={FPS},setsar=1")
        kos("ffmpeg", "-y", "-loglevel", "error", "-ss", f"{bas}",
            "-i", str(girdi), "-t", f"{sure}", "-vf", sf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", str(FPS), str(cikti))
        yollar.append(cikti)
        print(f"  {ad:8s} {bas:5.1f} → {bas + sure:5.1f}  ({sure:4.1f}s)")
    return yollar


def gorsel_birlestir(segmentler: list[Path], sureler: list[float], cikti: Path) -> None:
    girdiler: list[str] = []
    for s in segmentler:
        girdiler += ["-i", str(s)]
    suzgec, onceki, gecen = [], "[0:v]", sureler[0]
    for i in range(1, len(segmentler)):
        etiket = f"[v{i}]"
        ofset = gecen - GECIS
        suzgec.append(f"{onceki}[{i}:v]xfade=transition=fade:"
                      f"duration={GECIS}:offset={ofset:.3f}{etiket}")
        onceki, gecen = etiket, ofset + sureler[i]
    kos("ffmpeg", "-y", "-loglevel", "error", *girdiler,
        "-filter_complex", ";".join(suzgec), "-map", onceki,
        "-c:v", "libx264", "-preset", "slow", "-crf", "19",
        "-pix_fmt", "yuv420p", "-r", str(FPS), str(cikti))
    print(f"  görüntü → {gecen:.1f}s")


def ses_birlestir(ses: dict[int, dict], sureler: list[float], cikti: Path) -> float:
    baslangic, gecen = [], 0.0
    for i, s in enumerate(sureler):
        baslangic.append(gecen)
        gecen += s - (GECIS if i < len(sureler) - 1 else 0)

    girdiler, suzgec, etiketler = [], [], []
    n = 0
    for (_, _, cumleler), seg_bas in zip(PLAN, baslangic, strict=True):
        for no, ofset in cumleler:
            girdiler += ["-i", str(T / "ses2" / ses[no]["dosya"])]
            gecikme = int((seg_bas + ONSES + ofset) * 1000)
            suzgec.append(f"[{n}:a]adelay={gecikme}|{gecikme}[a{n}]")
            etiketler.append(f"[a{n}]")
            n += 1
    karisim = (f"{''.join(etiketler)}amix=inputs={n}:normalize=0:"
               f"dropout_transition=0[mix]")
    kos("ffmpeg", "-y", "-loglevel", "error", *girdiler,
        "-filter_complex", ";".join(suzgec) + ";" + karisim,
        "-map", "[mix]", "-t", f"{gecen:.3f}",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(cikti))
    print(f"  ses     → {gecen:.1f}s ({n} cümle)")
    return gecen


def main() -> None:
    global PLAN
    kisa = "--kisa" in sys.argv
    if kisa:
        PLAN = KISA_PLAN

    ses = {k["no"]: k for k in json.loads((T / "ses2.json").read_text(encoding="utf-8"))}
    sureler = sahne_sureleri(ses)
    print("segmentler:")
    segmentler = segment_uret(sureler)

    ek = "-kisa" if kisa else ""
    gorsel, sesyolu = ARA / f"_g{ek}.mp4", ARA / f"_s{ek}.m4a"
    print("birleştirme:")
    gorsel_birlestir(segmentler, sureler, gorsel)
    ses_birlestir(ses, sureler, sesyolu)

    son = T / f"anatolia-ai-demo-tam{ek}.mp4"
    kos("ffmpeg", "-y", "-loglevel", "error", "-i", str(gorsel), "-i", str(sesyolu),
        "-c:v", "copy", "-c:a", "copy", "-shortest",
        "-movflags", "+faststart", str(son))
    s = olc(son)
    print(f"\n✅ {son.name}  {int(s // 60)}:{s % 60:04.1f}  "
          f"{son.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
