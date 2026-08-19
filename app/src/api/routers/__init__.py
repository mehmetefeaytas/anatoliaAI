"""API uç noktalarının tematik router'ları.

`api/main.py`'nin kademeli bölünmesi kapsamında oluşturuldu; sıra, gerekçe
ve uç nokta bağımlılık matrisi `docs/rapor/api-bolme-plani.md`'de.

Her modül bir **factory** ihraç eder (`router_kur(...) -> APIRouter`), sınıf
ya da modül-seviyesi router DEĞİL. Sebep ölçülmüş bir kısıt: uç noktalar
istek-arası önbellekler dahil paylaşılan duruma erişiyor ve o durum
`build_app()` kapsamında kalmak zorunda — modül seviyesine çıkarsa süreç ömrü
boyunca paylaşılır ve test izolasyonu bozulur.
"""
