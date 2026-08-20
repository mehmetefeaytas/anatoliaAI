# ADR — Mimari Karar Kayıtları (`app/docs/adr/`)

Bu dizin, **kodun içinden okunamayan** kararları tutar: bir eşiğin niçin
düşürüldüğü, bir katmanın niçin üretime alınmadığı, bir ölçütün niçin
değiştirildiği. Kodun kendisinden anlaşılan şey buraya yazılmaz.

> **Vault'taki `../../../decisions/` ile ilişkisi.** Bilgi arşivindeki
> `decisions/` sayfaları **ürün ve mimari** kararlarını tutar (ör. "Apache-2.0
> lisansı", "hibrit chatbot"). Buradaki ADR'ler **ölçüm ve kapı disiplinine**
> dair kararlardır — yani "neyi yayımlarız, hangi kanıtla, kim onaylar".
> İkisi çakışırsa vault kaynaktır; ADR ona link verir.

## Neden ayrı bir dizin

Bu projede en pahalı hata sınıfı **ölçüm dürüstlüğünün zedelenmesi**. Bir eşiği
düşürmek meşru bir mühendislik hamlesidir; **gerekçesi gömülü kaldığı sürece**
sonuca göre eşik oynatmaktan ayırt edilemez. Gerekçe bir JSON dosyasının
`_aciklama` alanında yaşarsa, onu yalnız o dosyayı açan görür — jüri görmez,
altı hafta sonraki biz görmeyiz.

ADR'nin işi sayıyı savunmak değil, **kararın nasıl alındığını denetlenebilir
kılmaktır.**

## Kalıp

Her ADR tek bir karar içerir ve şu başlıkları taşır:

```markdown
# ADR-NNNN · <karar, tek cümlede>

| | |
|---|---|
| durum | önerildi · **kabul** · reddedildi · yerini aldı: ADR-NNNN |
| tarih | YYYY-MM-DD |
| karar veren | <rol> |
| kapsam | <hangi dosyalar/kapılar> |

## Bağlam
Kararı zorunlu kılan olgu. Ölçülmüş sayı varsa künyesiyle.

## Karar
Ne yapılacağı. Tek cümlede özetlenebilmeli.

## Gerekçe
Neden bu, neden alternatif değil.

## Sonuçlar
Kabul edilen bedel dahil. Gizlenen bedel yok.

## Doğrulama
Bu kararın uygulandığını **koşarak** gösteren komut.
```

## Dizin

| ADR | konu | durum |
|---|---|---|
| [0001](0001-esik-dusurme-disiplini.md) | Bir regresyon eşiği ne zaman düşürülebilir | **kabul** (2026-08-20) |
