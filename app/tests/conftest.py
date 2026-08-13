"""Test koşumunun ortak kurulumu.

## İşlem günlüğü test koşumunda GERÇEK dosyaya yazmaz

`build_app()` her kurulduğunda bir `GunlukYazici` açıyor ve yolu ortamdan
okuyor (`AUDIT_LOG_PATH`, varsayılan `data/gunluk/islem-gunlugu.jsonl`).
Onlarca API testi uygulamayı kurup istek atıyor; kendi yazıcısını
değiştirmeyen her test, kayıtlarını GERÇEK denetim günlüğüne düşürürdü.

Ölçüldü (2026-08-13, bu koruma eklenmeden önceki tek koşu): tam suite gerçek
dosyaya **397 kayıt** yazdı ve hepsinin istemcisi `testclient`'tı. İki ayrı
zarar var:

1. **Denetim kaydı kirlenir.** "Bunu kim yaptı" sorusunun cevabı, dosyanın
   yarısı test gürültüsü olduğunda okunmaz hâle gelir — günlüğün var olma
   sebebi tam olarak o soruydu.
2. **Testler yan etki bırakır.** `pytest` koşmak, geliştiricinin makinesindeki
   bir çalışma artefaktını sessizce büyütmemeli.

Çare oturum başında ortam değişkenini geçici bir dizine çevirmek: `ortamdan()`
onu `build_app()` anında okuduğu için kendi yazıcısını değiştiren testler de
(bkz. `test_api_gunluk.py`) etkilenmeden çalışır.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_GECICI = tempfile.TemporaryDirectory(prefix="anatolia-gunluk-test-")
os.environ["AUDIT_LOG_PATH"] = str(Path(_GECICI.name) / "islem-gunlugu.jsonl")
