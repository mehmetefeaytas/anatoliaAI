# Anatolia AI — geliştirme ve denetim hedefleri
#
# ## Neden bu dosya var
#
# Şartname §5.10 lisans problemi çıkarma potansiyeli olan çözümleri yasaklıyor,
# §9 "bağımlılıkların eksiksiz listesi" istiyor. 15 Ağu 2026'ya kadar bu iki
# şart ELLE tutulan bir tabloyla (`docs/model-license-audit.md`) karşılanıyordu.
# Elle tutulan tablo eskir: trafilatura'nın lisansı yorumda "GPLv3+" yazıyordu,
# paketin kendi LICENSE dosyası Apache-2.0 diyordu. Aradaki fark bir yılı aşkın
# süredir "açık risk" olarak duruyordu — çünkü kimse dosyayı açmamıştı.
#
# Buradaki hedefler tabloyu değil ORTAMI okur. Kaynak: `.venv` içindeki
# `dist-info/METADATA`, yani paketin kendi beyanı.
#
# ## Neden `.venv/bin/python -m`
#
# Sistem python'una güvenilmez: makinede birden çok yorumlayıcı var ve
# `pip-licenses` KURULU ORTAMI tarar. Yanlış yorumlayıcıyla koşulursa envanter
# başka bir ortamın envanteri olur — sessizce yanlış bir belge üretir.
# Bu yüzden her hedef mutlak `.venv` yolunu kullanır.

PY      := .venv/bin/python
PYTEST  := $(PY) -m pytest
DOCS    := docs

# Varsayılan hedef: ne yapılabileceğini göster. Yanlışlıkla `make` yazan biri
# bir şeyi ÜRETMEK yerine seçenekleri görmeli.
.DEFAULT_GOAL := help

.PHONY: help lisanslar sbom lisans-kapisi test

## help: bu listeyi göster
help:
	@echo "Anatolia AI — kullanılabilir hedefler:"
	@echo ""
	@echo "  make lisanslar      Bağımlılık lisans envanterini docs/LISANSLAR.md'ye yazar"
	@echo "  make sbom           CycloneDX SBOM üretir → docs/sbom.json"
	@echo "  make lisans-kapisi  İzin listesi dışı lisans varsa çıkış kodu 1 verir"
	@echo "  make test           Test paketini koşar"
	@echo "  make help           Bu liste (varsayılan)"
	@echo ""
	@echo "Tümü .venv/bin/python ile koşar; sistem python'u kullanılmaz."

## lisanslar: pip-licenses çıktısını insan-okur belgeye yazar
# `--with-*` bayrakları künyeyi zenginleştirir: sürüm olmadan envanter
# tekrar üretilebilir değildir, URL olmadan iddia doğrulanabilir değildir.
lisanslar:
	@mkdir -p $(DOCS)
	@$(PY) -m scripts.lisans_envanteri --cikti $(DOCS)/LISANSLAR.md
	@echo "yazıldı: $(DOCS)/LISANSLAR.md"

## sbom: makine-okur CycloneDX SBOM üretir
# `environment` alt komutu KURULU ortamı tarar (requirements.txt'i değil).
# Fark önemli: requirements.txt `>=` pinleri taşıyor, yani hangi sürümün
# gerçekten kurulu olduğunu yalnızca ortam bilir.
sbom:
	@mkdir -p $(DOCS)
	@$(PY) -m cyclonedx_py environment $(PY) \
		--output-format JSON \
		--spec-version 1.6 \
		--output-file $(DOCS)/sbom.json
	@echo "yazıldı: $(DOCS)/sbom.json"

## lisans-kapisi: izin listesi dışında lisans varsa çıkış kodu 1
# Kapı `docs/sbom.json`'u okur; yoksa açık hata verir (sessizce geçmez).
lisans-kapisi:
	@$(PY) -m scripts.lisans_kapisi \
		--girdi $(DOCS)/sbom.json \
		--istisnalar config/lisans_istisnalari.yaml

## test: test paketini koşar
test:
	@$(PYTEST) tests/ -q
