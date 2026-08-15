# Anotatörler Arası Uyum (IAA) Raporu

> `scripts/report_iaa.py` üretti. Eşik politikası anotasyon BAŞLAMADAN ilan edilmiştir (ANNOTATION_GUIDE.md §7); sayılara bakıp eşik değiştirmek yasaktır.

- Anotatörler: A, B
- Ortak anote edilmiş satır: **650**
- Karar bulunmayan hücre (boş/eksik): **1004**

## Protokol künyesi

| Dosya | Protokol | Boş hücrenin anlamı |
|---|---|---|
| `data/gold/review/round1_A.csv` | **v2** | karar verilmedi — metrik dışı |
| `data/gold/review/round1_B.csv` | **v2** | karar verilmedi — metrik dışı |

## Sonuçlar

| Ölçüt | Neyi ölçer | Değer |
|---|---|---:|
| Cohen's kappa (karar) | Aynı satırda aynı kararı mı verdiler (ok/fix/absent/unclear) | **0.844** |
| Krippendorff α (nominal) | Ortaya çıkan gold DEĞERİ birebir aynı mı | 0.913 |
| Krippendorff α (ratio) | Sayısal alanlarda değer yakınlığı (34 birim) | 0.889 |

## Alan bazında kırılım

Toplu κ bir ORTALAMADIR. Uyuşmazlıklar birkaç alanda yığılıyorsa ortalama, hem sorunun yerini hem de iyi çalışan alanları gizler.

> ⚠️ Alan başına **n küçüktür**; tek bir alanın κ'sına dayanarak eşik kararı VERİLMEZ. §7 eşiği toplu κ içindir. Bu tablo nereye müdahale edileceğini söyler, kabul/ret kararını değil.

| Alan | n | Uyum | κ | Uyuşmazlık | En sık ayrışma |
|---|---:|---:|---:|---:|---|
| `campaign_type` | 47 | %91 | 0.841 | 4 | `fix/ok` ×2 |
| `finansman_tutari` | 9 | %67 | 0.289 | 3 | `fix/ok` ×2 |
| `kampanya_kosullari` | 9 | %78 | 0.550 | 2 | `absent/ok` ×2 |
| `vade_ay` | 32 | %94 | 0.898 | 2 | `fix/ok` ×1 |
| `tahsis_ucreti` | 1 | %0 | 0.000 | 1 | `absent/unclear` ×1 |
| `alisveris_puani` | 1 | %100 | 1.000 | 0 | — |
| `hedef_kitle` | 3 | %100 | 1.000 | 0 | — |
| `kampanya_suresi` | 18 | %100 | 1.000 | 0 | — |
| `kar_payi_orani` | 9 | %100 | 1.000 | 0 | — |
| `masraf_durumu` | 5 | %100 | 1.000 | 0 | — |
| `odul_miktari` | 1 | %100 | 1.000 | 0 | — |
| `taksit_sayisi` | 6 | %100 | 1.000 | 0 | — |

## Karar (önceden ilan edilmiş eşik)

- **Durum: `kabul`**
- Yapılacak: Gold güvenilir. Ana geçişe devam.

| Eşik | Karar |
|---|---|
| κ ≥ 0,80 | kabul |
| 0,67 ≤ κ < 0,80 | notla kabul |
| κ < 0,67 | zorunlu hakemlik + kılavuz revizyonu |

## Uyuşmazlıklar (14)

Kalibrasyon toplantısında sırayla konuşulacak liste.

| Belge | Alan | Kararlar | Değerler |
|---|---|---|---|
| `albaraka--detay-dijital-musterilere-ozel-pratik-finansman-kart` | `finansman_tutari` | A=fix, B=fix | A='150000', B='{"currency":"TRY","value":150000}' |
| `albaraka--formlar-altin-hesaplarindan-donusumun-desteklenmesi-tl-katilma-hesabi-bilgilendi` | `kampanya_kosullari` | A=absent, B=ok | A='__YOK__', B='["Vergi kesintileri, Katılma Hesabı\'nın açılış/vade yenileme tarihinde ilgili vade için geçerli olan cari vergi oranları üzerinden hesaplanacağı, 8.", "Müşteri, katılma hesaplarının; Banka\'nın herhangi bir oran veya tutarda getiri taahhüdü bulunmadığı, bu bakımdan Banka\'nın asgari de olsa getiri taahhüdü/garantisi olmayan, karşılığında hesap sahibine önceden belirlenmiş herhangi bir getiri ödenmeyen ve anaparanın aynen geri ödenmesi garanti edilmeyen hesaplar olduğunu bildiğini, 10."]' |
| `albaraka--formlar-genel-kredi-sozlesmesi-ucret-bilgilendirme-formu-pdf` | `tahsis_ucreti` | A=absent, B=unclear | A='__YOK__' |
| `albaraka--formlar-genel-kredi-sozlesmesi-ucret-bilgilendirme-formu-pdf` | `vade_ay` | A=ok, B=fix | A='36', B='36' |
| `albaraka--gecmis-tarihli-aracfinansmanitalep-onayveucretbilgilendirmeformu-pdf` | `campaign_type` | A=absent, B=ok | A='__YOK__', B='Finansman' |
| `albaraka--tarim-bankaciligi-diger-finansmanlar` | `campaign_type` | A=fix, B=ok | A='Finansman', B='İhtiyaç Finansmanı' |
| `albaraka--tatiliniz-icin-devre-mulk` | `kampanya_kosullari` | A=ok, B=absent | A='["Albaraka Mobil Mobil Bankacılık Aç Devre Mülk Anasayfa Bireysel Finansmanlar İhtiyaç Finansmanı Tatiliniz İçin Devre Mülk Seyahat Devre Mülk Devre Tatil Hemen Başvur Devre mülkler tapu kaydı gerektiren ve her yıl belirli dönemlerde asgari 15 gün süreli konaklama imkânı veren mülklerdir."]', B='__YOK__' |
| `albaraka--tr-urun-ve-hizmet-ucretleri` | `campaign_type` | A=fix, B=fix | A='Yatırım Ürünü', B='Finansman' |
| `kuveyt-turk--kampanya-arsivi-bisiklet-finansmaninda-enerji-tasarrufu-haftasina-ozel-419-kar-o` | `finansman_tutari` | A=fix, B=ok | A='{"currency": "TRY", "value": 13.882,47}', B='{"currency": "TRY", "value": 13.88247}' |
| `kuveyt-turk--kampanya-arsivi-hepsiburada-alisveris-finansmaninda-enerji-tasarrufu-haftasina-o` | `finansman_tutari` | A=fix, B=ok | A='{"currency": "TRY", "value": 13.682,22}', B='{"currency": "TRY", "value": 13.68222}' |
| `kuveyt-turk--katilma-hesaplari-ara-donem-kar-payi-odemeli-hesaplar` | `vade_ay` | A=ok, B=absent | A='6', B='__YOK__' |
| `vakif-katilim--detay-vakif-katilim-aile-yili-paketi` | `campaign_type` | A=unclear, B=absent | B='__YOK__' |
| `vakif-katilim--nakdi-finansmanlar-is-yeri-finansmani` | `campaign_type` | A=ok, B=fix | A='İhtiyaç Finansmanı', B='Konut Finansmanı' |
| `ziraat-katilim--kart-kampanyalari-troy-kartla-drda-1000-tlye-varan-indirim` | `finansman_tutari` | A=absent, B=ok | A='__YOK__', B='{"currency": "TRY", "value": 1000.0}' |
