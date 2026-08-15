# Bağımlılık Lisans Envanteri

## Künye

- **Üretim tarihi:** 2026-08-15 21:14 +03
- **Üreten komut:** `make lisanslar`
  (`scripts/lisans_envanteri.py` → `.venv/bin/python -m piplicenses --format=json --with-urls --with-authors`)
- **Yorumlayıcı:** Python 3.14.6 (`/Users/mehmetefeaytas/anatoliaaI/app/.venv/bin/python`)
- **Kapsam:** bu koşumun `.venv` envanteri — **91 paket**. Kurulu ortamda ne varsa o listelenmiştir; `requirements.txt`'te ilan edilen ama kurulu olmayan paketler burada YOKTUR, kurulu olup ilan edilmeyenler ise VARDIR.
- **Makine-okur eşi:** [`sbom.json`](sbom.json) — CycloneDX 1.6, `make sbom` ile üretilir.
- **Kapı:** [`../scripts/lisans_kapisi.py`](../scripts/lisans_kapisi.py), `make lisans-kapisi` ile koşar.

### ⚠️ Sınır uyarısı

> **Python kilit dosyası yok** (`requirements.txt` `>=` pinleri taşıyor, hash yok); bu envanter **bu koşumun kesitidir**, sürüm aralığı değişirse yeniden üretilmelidir.

Somut sonucu: `>=` pini bir sürüm aralığı açar ve **lisans sürümle değişebilir**. Bir paketin bugün izin verici olması, aralığın tamamının izin verici olduğunu kanıtlamaz. Aşağıdaki tablo tek bir noktayı belgeler — aralığın tamamını değil.

## Özet

| Hüküm | Paket sayısı |
|---|---:|
| ✅ izinli | 85 |
| ⚠️ listede yok | 3 |
| ❓ bilinmiyor | 0 |
| ⛔ yasak | 3 |
| **toplam** | **91** |

Bunlardan **7** paket [`config/lisans_istisnalari.yaml`](../config/lisans_istisnalari.yaml) içinde **gerekçeli istisna** olarak kayıtlıdır; kapı onları bilerek geçirir. Gerekçesiz istisna kabul edilmez.

## ⚠️ Risk kalemleri — çözülen ve çözülmeyen

### ✅ ÇÖZÜLDÜ — `trafilatura` gerçekte Apache-2.0

**İddia:** `requirements.txt` bu paketi yorumunda **GPLv3+** olarak işaretliyor ve bu yüzden opsiyonel bırakılmış, teslim imajına alınmamıştı. `docs/model-license-audit.md` §2 kalemi 31 Tem 2026'dan beri `⏳ AÇIK RİSK` olarak duruyordu.

**Bulgu: iddia yanlış. Paketin gerçek lisansı Apache-2.0.**

Doğrulama, paketin kendi dosyaları okunarak yapıldı (`pip download --no-deps --no-binary :all:` ile kaynak dağıtımı indirildi, `PKG-INFO` ve `LICENSE` açıldı):

| Sürüm | `PKG-INFO` lisans alanı | `LICENSE` dosyasının gövdesi |
|---|---|---|
| `trafilatura 2.2.0` | `License-Expression: Apache-2.0` | Apache License 2.0 tam metni; içinde **sıfır** `GNU`/`GPL` geçişi |
| `trafilatura 1.8.0` | `License: Apache-2.0` + `Classifier: License :: OSI Approved :: Apache Software License` | aynı |

İki uç da sınandı çünkü `requirements.txt` pini `>=1.8` bir **aralık** açıyor ve lisans sürümle değişebilir. Aralığın alt sınırı (1.8.0) ve bugünkü üst ucu (2.2.0) Apache-2.0 çıktı; yani pinin GPL bir sürüme denk gelme riski bu iki ölçüm arasında gözlenmedi.

> **Kapsam notu:** `trafilatura` bu `.venv`de **kurulu değildir**, bu yüzden yukarıdaki envanter tablosunda görünmez. Lisansı kurulu ortamdan değil, PyPI'dan indirilen kaynak dağıtımından okunmuştur. Paket kurulursa kapı onu kendiliğinden `Apache-2.0 → ✅ izinli` olarak sınıflandırır; istisna gerekmez.

**Sonuç:** GPLv3+ gerekçesiyle konmuş kısıt dayanaksız kalmıştır. Paketi teslim imajına almak lisans açısından serbesttir — bu, lisans kararı değil artık bir mimari karardır (kod `strip_html` yedeğiyle onsuz da çalışıyor). `requirements.txt` içindeki `# GPLv3+` yorumu **yanlıştır ve düzeltilmelidir.**

### ✅ ÇÖZÜLDÜ — `transformers` SBOM'da lisanssız görünüyor

`docs/sbom.json` içinde `transformers` bileşeninin lisans alanı **boştur**. Bu, paketin lisansı olmadığı anlamına gelmez; `cyclonedx-py`nin okuyamadığı anlamına gelir. Paket lisansını PEP 639 `License-Expression` alanıyla ya da `Classifier:` satırıyla değil, eski serbest metin `License:` alanıyla bildiriyor.

Elle doğrulandı — `transformers-*.dist-info/METADATA` içinde `License: Apache 2.0 License` yazıyor ve dizinde `licenses/LICENSE` (Apache-2.0 metni) duruyor. `pip-licenses` aynı paketi doğru okuyor; iki aracın çelişmesi kaydın sebebidir.

Bu kalem, kapının **"UNKNOWN sessiz geçmez"** kuralının neden gerektiğinin kanıtıdır: lisansı boş bırakılan bir paket, sessizce geçirilseydi denetim onu hiç görmeyecekti.

## İki aracın paket sayısı neden farklı

`docs/sbom.json` (CycloneDX) bu belgeden **daha fazla** paket listeler. Fark bir tutarsızlık değil, kapsam farkıdır: `pip-licenses` varsayılan olarak **kendini ve kendi bağımlılıklarını** (`pip-licenses`, `prettytable`, `wcwidth`) ve ortam altyapısını (`pip`, `setuptools`) envanterden düşürür; `cyclonedx-py environment` ise ortamda ne varsa onu yazar.

Yani SBOM, bu belgenin **üst kümesidir**. Lisans kapısı bilerek SBOM'u okur: denetimin kör noktası olmaması, aracın kendi bağımlılıklarının da sayılmasını gerektirir.

## İzin listesi dışındaki kalemler

| Paket | Sürüm | Lisans | Hüküm | İstisna |
|---|---|---|---|---|
| `chardet` | 5.2.0 | GNU Lesser General Public License v2 or later (LGPLv2+) | ⛔ yasak | gerekçeli |
| `numpy` | 2.5.1 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | ⚠️ listede yok | gerekçeli |
| `psycopg` | 3.3.4 | LGPL-3.0-only | ⛔ yasak | gerekçeli |
| `psycopg-binary` | 3.3.4 | LGPL-3.0-only | ⛔ yasak | gerekçeli |
| `regex` | 2026.7.19 | Apache-2.0 AND CNRI-Python | ⚠️ listede yok | gerekçeli |
| `torch` | 2.13.0 | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT | ⚠️ listede yok | gerekçeli |

## Tam envanter

| Paket | Sürüm | Lisans | Hüküm | Proje adresi |
|---|---|---|---|---|
| `annotated-doc` | 0.0.5 | MIT | ✅ izinli | <https://github.com/fastapi/annotated-doc> |
| `annotated-types` | 0.8.0 | MIT | ✅ izinli | <https://github.com/annotated-types/annotated-types> |
| `anyio` | 4.14.2 | MIT | ✅ izinli | <https://anyio.readthedocs.io/en/stable/versionhistory.html> |
| `arrow` | 1.4.0 | Apache Software License | ✅ izinli | <https://github.com/arrow-py/arrow> |
| `attrs` | 26.1.0 | MIT | ✅ izinli | <https://www.attrs.org/en/stable/changelog.html> |
| `beautifulsoup4` | 4.15.0 | MIT License | ✅ izinli | <https://www.crummy.com/software/BeautifulSoup/bs4/> |
| `boolean.py` | 5.0 | BSD-2-Clause | ✅ izinli | <https://github.com/bastikr/boolean.py> |
| `certifi` | 2026.7.22 | Mozilla Public License 2.0 (MPL 2.0) | ✅ izinli | <https://github.com/certifi/python-certifi> |
| `chardet` | 5.2.0 | GNU Lesser General Public License v2 or later (LGPLv2+) | ⛔ yasak | <https://github.com/chardet/chardet> |
| `charset-normalizer` | 3.4.9 | MIT | ✅ izinli | <https://github.com/jawah/charset_normalizer/blob/master/CHANGELOG.md> |
| `click` | 8.4.2 | BSD-3-Clause | ✅ izinli | <https://github.com/pallets/click/> |
| `cyclonedx-bom` | 7.3.1 | Apache Software License | ✅ izinli | <https://github.com/CycloneDX/cyclonedx-python/#readme> |
| `cyclonedx-python-lib` | 11.12.0 | Apache Software License | ✅ izinli | <https://github.com/CycloneDX/cyclonedx-python-lib/#readme> |
| `defusedxml` | 0.7.1 | Python Software Foundation License | ✅ izinli | <https://github.com/tiran/defusedxml> |
| `fastapi` | 0.141.1 | MIT | ✅ izinli | <https://github.com/fastapi/fastapi> |
| `filelock` | 3.32.2 | MIT | ✅ izinli | <https://github.com/tox-dev/py-filelock> |
| `fqdn` | 1.5.1 | Mozilla Public License 2.0 (MPL 2.0) | ✅ izinli | <https://github.com/ypcrts/fqdn> |
| `fsspec` | 2026.7.0 | BSD-3-Clause | ✅ izinli | <https://github.com/fsspec/filesystem_spec> |
| `greenlet` | 3.5.4 | MIT AND PSF-2.0 | ✅ izinli | <https://greenlet.readthedocs.io> |
| `h11` | 0.16.0 | MIT License | ✅ izinli | <https://github.com/python-hyper/h11> |
| `hf-xet` | 1.6.0 | Apache-2.0 | ✅ izinli | <https://github.com/huggingface/xet-core> |
| `httpcore` | 1.0.9 | BSD-3-Clause | ✅ izinli | <https://www.encode.io/httpcore/> |
| `httpx` | 0.28.1 | BSD License | ✅ izinli | <https://github.com/encode/httpx> |
| `huggingface_hub` | 1.27.0 | Apache Software License | ✅ izinli | <https://github.com/huggingface/huggingface_hub> |
| `idna` | 3.18 | BSD-3-Clause | ✅ izinli | <https://github.com/kjd/idna> |
| `iniconfig` | 2.3.0 | MIT | ✅ izinli | <https://github.com/pytest-dev/iniconfig> |
| `isoduration` | 20.11.0 | ISC License (ISCL) | ✅ izinli | <https://github.com/bolsote/isoduration> |
| `Jinja2` | 3.1.6 | BSD License | ✅ izinli | <https://github.com/pallets/jinja/> |
| `joblib` | 1.5.3 | BSD-3-Clause | ✅ izinli | <https://joblib.readthedocs.io> |
| `jsonpointer` | 3.1.1 | BSD License | ✅ izinli | <https://github.com/stefankoegl/python-json-pointer> |
| `jsonschema` | 4.26.0 | MIT | ✅ izinli | <https://github.com/python-jsonschema/jsonschema> |
| `jsonschema-specifications` | 2025.9.1 | MIT | ✅ izinli | <https://github.com/python-jsonschema/jsonschema-specifications> |
| `lark` | 1.3.1 | MIT License | ✅ izinli | <https://github.com/lark-parser/lark> |
| `license-expression` | 30.4.4 | Apache-2.0 | ✅ izinli | <https://github.com/aboutcode-org/license-expression> |
| `lxml` | 6.1.1 | BSD-3-Clause | ✅ izinli | <https://lxml.de/> |
| `markdown-it-py` | 4.2.0 | MIT License | ✅ izinli | <https://github.com/executablebooks/markdown-it-py> |
| `MarkupSafe` | 3.0.3 | BSD-3-Clause | ✅ izinli | <https://github.com/pallets/markupsafe/> |
| `mdurl` | 0.1.2 | MIT License | ✅ izinli | <https://github.com/executablebooks/mdurl> |
| `mpmath` | 1.3.0 | BSD License | ✅ izinli | <http://mpmath.org/> |
| `narwhals` | 2.24.0 | MIT | ✅ izinli | <https://github.com/narwhals-dev/narwhals> |
| `networkx` | 3.6.1 | BSD-3-Clause | ✅ izinli | <https://networkx.org/> |
| `numpy` | 2.5.1 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | ⚠️ listede yok | <https://numpy.org> |
| `packageurl-python` | 0.17.6 | MIT License | ✅ izinli | <https://github.com/package-url/packageurl-python> |
| `packaging` | 26.3 | Apache-2.0 OR BSD-2-Clause | ✅ izinli | <https://github.com/pypa/packaging> |
| `pgvector` | 0.5.0 | MIT | ✅ izinli | <https://github.com/pgvector/pgvector-python> |
| `pip-requirements-parser` | 32.0.1 | MIT | ✅ izinli | <https://github.com/nexB/pip-requirements-parser> |
| `playwright` | 1.61.0 | Apache-2.0 | ✅ izinli | <https://github.com/Microsoft/playwright-python> |
| `pluggy` | 1.6.0 | MIT License | ✅ izinli | — |
| `psycopg` | 3.3.4 | LGPL-3.0-only | ⛔ yasak | <https://psycopg.org/> |
| `psycopg-binary` | 3.3.4 | LGPL-3.0-only | ⛔ yasak | <https://psycopg.org/> |
| `py-serializable` | 2.1.0 | Apache Software License | ✅ izinli | <https://github.com/madpah/serializable#readme> |
| `pydantic` | 2.13.4 | MIT | ✅ izinli | <https://github.com/pydantic/pydantic> |
| `pydantic_core` | 2.46.4 | MIT | ✅ izinli | <https://github.com/pydantic> |
| `pyee` | 13.0.1 | MIT License | ✅ izinli | <https://github.com/jfhbrook/pyee> |
| `Pygments` | 2.20.0 | BSD-2-Clause | ✅ izinli | <https://pygments.org> |
| `pyparsing` | 3.3.2 | MIT | ✅ izinli | <https://github.com/pyparsing/pyparsing/> |
| `pypdf` | 6.14.2 | BSD-3-Clause | ✅ izinli | <https://github.com/py-pdf/pypdf> |
| `pytest` | 9.1.1 | MIT | ✅ izinli | <https://docs.pytest.org/en/latest/> |
| `python-dateutil` | 2.9.0.post0 | Apache Software License; BSD License | ✅ izinli | <https://github.com/dateutil/dateutil> |
| `PyYAML` | 6.0.3 | MIT License | ✅ izinli | <https://pyyaml.org/> |
| `referencing` | 0.37.0 | MIT | ✅ izinli | <https://github.com/python-jsonschema/referencing> |
| `regex` | 2026.7.19 | Apache-2.0 AND CNRI-Python | ⚠️ listede yok | <https://github.com/mrabarnett/mrab-regex> |
| `requests` | 2.34.2 | Apache Software License | ✅ izinli | <https://github.com/psf/requests> |
| `rfc3339-validator` | 0.1.4 | MIT License | ✅ izinli | <https://github.com/naimetti/rfc3339-validator> |
| `rfc3986-validator` | 0.1.1 | MIT License | ✅ izinli | <https://github.com/naimetti/rfc3986-validator> |
| `rfc3987-syntax` | 1.1.0 | MIT | ✅ izinli | <https://github.com/willynilly/rfc3987-syntax> |
| `rich` | 15.0.0 | MIT License | ✅ izinli | <https://github.com/Textualize/rich> |
| `rpds-py` | 2026.6.3 | MIT | ✅ izinli | <https://github.com/crate-py/rpds> |
| `ruff` | 0.16.1 | MIT | ✅ izinli | <https://docs.astral.sh/ruff> |
| `safetensors` | 0.8.0 | Apache Software License | ✅ izinli | <https://github.com/huggingface/safetensors> |
| `scikit-learn` | 1.9.0 | BSD-3-Clause | ✅ izinli | <https://scikit-learn.org> |
| `scipy` | 1.18.0 | BSD License | ✅ izinli | <https://scipy.org/> |
| `shellingham` | 1.5.4 | ISC License (ISCL) | ✅ izinli | <https://github.com/sarugaku/shellingham> |
| `six` | 1.17.0 | MIT License | ✅ izinli | <https://github.com/benjaminp/six> |
| `sortedcontainers` | 2.4.0 | Apache Software License | ✅ izinli | <http://www.grantjenks.com/docs/sortedcontainers/> |
| `soupsieve` | 2.9.1 | MIT | ✅ izinli | <https://github.com/facelessuser/soupsieve> |
| `starlette` | 1.3.1 | BSD-3-Clause | ✅ izinli | <https://github.com/Kludex/starlette> |
| `sympy` | 1.14.0 | BSD License | ✅ izinli | <https://sympy.org> |
| `threadpoolctl` | 3.6.0 | BSD License | ✅ izinli | <https://github.com/joblib/threadpoolctl> |
| `tokenizers` | 0.22.2 | Apache Software License | ✅ izinli | <https://github.com/huggingface/tokenizers> |
| `torch` | 2.13.0 | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT | ⚠️ listede yok | <https://pytorch.org> |
| `tqdm` | 4.70.0 | MPL-2.0 AND MIT | ✅ izinli | <https://tqdm.github.io> |
| `transformers` | 5.14.1 | Apache 2.0 License | ✅ izinli | <https://github.com/huggingface/transformers> |
| `typer` | 0.27.1 | MIT | ✅ izinli | <https://github.com/fastapi/typer> |
| `typing-inspection` | 0.4.2 | MIT | ✅ izinli | <https://github.com/pydantic/typing-inspection> |
| `typing_extensions` | 4.16.0 | PSF-2.0 | ✅ izinli | <https://github.com/python/typing_extensions> |
| `tzdata` | 2026.3 | Apache-2.0 | ✅ izinli | <https://github.com/python/tzdata> |
| `uri-template` | 1.3.0 | MIT License | ✅ izinli | <https://gitlab.linss.com/open-source/python/uri-template> |
| `urllib3` | 2.7.0 | MIT | ✅ izinli | <https://github.com/urllib3/urllib3/blob/main/CHANGES.rst> |
| `uvicorn` | 0.52.0 | BSD-3-Clause | ✅ izinli | <https://uvicorn.dev/> |
| `webcolors` | 25.10.0 | BSD License | ✅ izinli | <https://webcolors.readthedocs.io> |

## Yeniden üretim

```bash
make lisanslar      # bu belge
make sbom           # docs/sbom.json (CycloneDX 1.6)
make lisans-kapisi  # izin listesi dışı varsa çıkış kodu 1
```
