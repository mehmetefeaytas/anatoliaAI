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
DOCS    := docs

# Varsayılan hedef: ne yapılabileceğini göster. Yanlışlıkla `make` yazan biri
# bir şeyi ÜRETMEK yerine seçenekleri görmeli.
.DEFAULT_GOAL := help

.PHONY: help lisanslar sbom lisans-kapisi test veri-seti veri-seti-yukle baslat durdur

# Veri seti paketinin çıktı dizini. Tek yerde tanımlı ki iki hedef
# (üretim ve yükleme) aynı dizine baksın — ayrışırlarsa yükleyici bir
# ÖNCEKİ paketi yükler ve bunu kimse fark etmez.
VERI_SETI := data/yayin/anatolia-ai-gold

## help: bu listeyi göster
help:
	@echo "Anatolia AI — kullanılabilir hedefler:"
	@echo ""
	@echo "  make baslat         Tüm yığını kaldırır: API + panel + yerel model"
	@echo "                      (LLM=0 make baslat → modelsiz, kural-only)"
	@echo "  make durdur         Yığını kapatır, modeli bellekten düşürür"
	@echo ""
	@echo "  make lisanslar      Bağımlılık lisans envanterini docs/LISANSLAR.md'ye yazar"
	@echo "  make sbom           CycloneDX SBOM üretir → docs/sbom.json"
	@echo "  make lisans-kapisi  İzin listesi dışı lisans varsa çıkış kodu 1 verir"
	@echo "  make gold-butunluk   Gold sha256 tanığı + eşik künyesi sapmışsa çıkış kodu 1"
	@echo "  make sbom-sapma     Kurulu ortam ile commit'li SBOM ayrıştıysa çıkış kodu 1"
	@echo "  make veri-seti      Yayın paketini üretir → $(VERI_SETI)"
	@echo "  make veri-seti-yukle  Ne yükleneceğini LİSTELER (kuru koşu, ağa çıkmaz)"
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

## gold-butunluk: gold sha256 tanığı ve eşik künyesi gerçekle tutuyor mu
# "Gold dondurulmuştur" bir iddiadır; tanığı `data/gold/*.json.sha256` ve
# `eval/esikler*.json`'daki `gold_sha256` künyesidir. 20-21 Ağu 2026'da üç
# hakemlik commit'i gold'u değiştirirken tanık tazelenmedi ve `shasum -c`
# FAILED verecek duruma geldi — dondurma bozulmamıştı, TANIK bayatlamıştı.
# Aradaki fark jüri karşısında ölçüm anlatısının tamamına mal olur.
gold-butunluk:
	@$(PY) -m scripts.gold_butunluk

## sbom-sapma: kurulu ortam ile commit'li SBOM birebir tutuyor mu
# `make lisans-kapisi` BİLEREK commit'li `docs/sbom.json`u okur (bağımlılıksız
# CI işinde de koşsun diye) — ama o SBOM'un TAZE olduğunu kimse denetlemiyordu.
# Boşluk iki kez ısırdı: 16 Ağu ve 23 Ağu 2026'da demo videosu seslendirmesi
# `.venv`e dokuz paket soktu (96 -> 105) ve taze SBOM'la lisans kapısı DÜŞTÜ.
# İlk seferinde paketler kaldırıldı ama kararı KORUYAN kapı yoktu; bu hedef o
# kapıdır. Ortam projenin `.venv`i değilse atlar.
sbom-sapma:
	@$(PY) -m scripts.sbom_sapma

## veri-seti: yayına hazır veri seti paketini üretir (JSONL + sızıntısız bölme + kart)
# Şartname s.18 veri setini ZORUNLU teslim kalemi sayar. Paket türetilmiştir:
# `data/gold/*.json`'dan yeniden üretilir, bu yüzden `.gitignore`'dadır
# (istisna: dataset card izlenir — gerekçe `.gitignore` girdisinde).
#
# Bölmeler arası belge sızıntısı bulunursa hedef çıkış kodu 1 verir: sızıntılı
# bir bölme, üzerinde ölçülen her sayıyı geçersiz kılar.
veri-seti:
	@$(PY) -m scripts.veri_seti_paketle --cikti $(VERI_SETI)

## veri-seti-yukle: paketi Hugging Face'e yükler — VARSAYILAN KURU KOŞU
# Bu hedef AĞA ÇIKMAZ. Yalnızca ne yükleneceğini listeler (dosya + boyut +
# sha256) ve zorunlu dosyaların varlığını denetler.
#
# Gerçek yükleme bilerek `make` hedefi DEĞİLDİR: geri alınamaz bir işlemi
# `make <bir şey>` kadar kolay yapmak yanlış olurdu. Token `HF_TOKEN` ortam
# değişkeninden okunur ve betik ayrıca etkileşimli onay ister:
#
#     .venv/bin/python -m scripts.veri_seti_yukle --gercekten-yukle
veri-seti-yukle:
	@$(PY) -m scripts.veri_seti_yukle --dizin $(VERI_SETI)

## test: test paketini koşar (CI ile aynı koşucu: unittest)
test:
	@$(PY) -m unittest discover -s tests

## baslat: tüm yığını kaldırır — API + panel + yerel model
# Betik `bash` ile çağrılır, `./scripts/baslat.sh` ile değil: çalıştırma bitinin
# git'te korunması platformdan platforma değişir ve kaybolduğu gün hedef
# "permission denied" ile ölürdü.
#
# Ortam değişkenleri betiğe GEÇER (make bunları dışa aktarır):
#   LLM=0             modelsiz, kural-only koşum
#   API_PORT / WEB_PORT   varsayılan 8000 / 3000
baslat:
	@bash scripts/baslat.sh

## durdur: yığını kapatır ve model ağırlığını bellekten düşürür
# Yalnız `baslat`ın kendi başlattığı süreçleri kapatır — gerekçe betiğin
# başındaki nottadır.
durdur:
	@bash scripts/durdur.sh
