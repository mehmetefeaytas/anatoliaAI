# Panel Ekran Görüntüleri → PDF

Sistemin **her sekmesinin ve öne çıkan her özelliğinin** canlı ekran görüntüsü ve
altında ne işe yaradığını anlatan açıklama; tek PDF hâlinde.

**Çıktı:** [`anatolia-ai-panel-ekranlari.pdf`](anatolia-ai-panel-ekranlari.pdf)
— 45 sayfa (kapak + içindekiler + 42 ekran).

Kapsam: 6 ürün sekmesi (Karşılaştırma · Isı Haritası · En Avantajlı · Banka
Sayfası · Banka İçi Delta · Çelişki Tespiti), 5 jüri/operatör sekmesi (Kanıt
defteri · Zor Vaka Tezgâhı · Chatbot · Veri Tazeleme · Ayarlar) ve sekmeye
bağlı olmayan yüzeyler (kabuk künyesi, durum şeridi, `¶` kaynak dipnotu, sohbet
çekmecesi, komut paleti, koyu tema, `/docs`).

## Dosyalar

| Dosya | Ne |
|---|---|
| `ss/*.png` | Ekran görüntüleri (1600 px genişlik, 2× ölçek) |
| `manifest.json` | Her karenin başlığı + açıklaması — **doğruluk kaynağı, elle yazılmış** |
| `ekran_cek.py` | Arayüzü gezip kareleri alan Playwright betiği |
| `ekran_cek_rag.py` | Yalnız RAG karesini sıfırdan sohbette alan yardımcı betik |
| `pdf_uret.py` | `manifest.json` + `ss/` → PDF |

`ekran_cek.py` kendi açıklama taslağını `manifest.otomatik.json`'a yazar;
`manifest.json`'u **ezmez**. Ekranda gerçekten görünen sayılar (kapsama kesirleri,
karakter aralıkları, ağırlık katsayıları, çelişki sayıları) `manifest.json`'a elle
işlendi — her kare tek tek açılıp doğrulanarak.

## Yeniden üretmek

Kareler canlı arayüzden alınır, sabit görüntülerden değil. Betikler **3010/8010**
portlarını kullanır; böylece geliştirme sırasında açık olan 3000/8000 çiftine
dokunulmaz.

```bash
cd app

# API (8010) — önceden doldurulmuş demo veri tabanı + yerel LLM
DATABASE_PATH=data/demo.db LLM_BACKEND=ollama \
OLLAMA_MODEL=qwen2.5:7b-instruct OLLAMA_NUM_CTX=8192 \
  .venv/bin/uvicorn src.api.main:app --host 127.0.0.1 --port 8010

# Arayüz (3010)
cd web && NEXT_PUBLIC_API_URL=http://127.0.0.1:8010 npx next dev -p 3010
```

Sonra:

```bash
cd app
.venv/bin/python ../docs-ekran/ekran_cek.py      # ss/*.png yenilenir
.venv/bin/python ../docs-ekran/ekran_cek_rag.py  # 35b-chatbot-rag.png
.venv/bin/python ../docs-ekran/pdf_uret.py       # PDF üretilir
```

**LLM açık olmalı.** `LLM_BACKEND` boşsa sistem kural-only çalışır; sohbet,
AI özet ve zor vaka kareleri o hâlde farklı görünür. Durum şeridi hangi hâlde
olduğunu her karede yazdığı için karışma riski yok — ama PDF'teki koşum yerel
Ollama açıkken alındı.

## Bu boru hattında öğrenilenler

- **Kırpma sabit yükseklikte.** `full_page` çekim bazı sekmelerde 146.000 piksele
  çıkıyordu; PDF'e yerleştirilince okunmaz bir şerite dönüşüyordu. Her kare en çok
  ~1.400 CSS pikseli ve istenirse bir çapa öğesinden başlıyor.
- **Çapa tek seçici değil, aday listesi.** Başlıklar CSS ile büyütülüyor, düğme
  etiketleri tıklanınca değişiyor; tek seçiciye güvenen kareler sessizce
  kayboluyordu.
- **Sabit konumlu yüzeyler viewport olarak çekilir.** Sohbet çekmecesi, komut
  paleti ve `¶` yan paneli `full_page` kırpmasının dışında kalıyor.
- **Katlanmış içerik önce açılır.** Adil kıyas şeridi ve çelişki kartındaki iki
  alıntı `<details>` içinde; kapalı hâlleri ekranın tezini göstermiyor.
- **Vakayı seçmek çıkarımı başlatmıyor.** Zor Vaka Tezgâhı'nda ayrı bir «Çıkarımı
  çalıştır» adımı var; ilk turda atlandığı için sonuç karesi boş kalmıştı.
- **Bağlam devri RAG yolunu gölgeliyor.** Aynı sohbette sorulan ikinci soru
  önceki turun alanını devralıp yapısal yola gidiyor; RAG karesi bu yüzden
  sıfırdan bir sohbette alınıyor (`ekran_cek_rag.py`).
- **PDF, Chromium'un yazdırma motoruyla** üretiliyor (yeni bağımlılık yok).
  Resimler base64 gömülü: `file://` ile yüklenenler yazdırma anında bazen hazır
  olmuyor ve boş sayfa basılıyordu.
