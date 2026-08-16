/**
 * `formatValue` — bilgi YOKLUĞUNUN ekrandaki jetonu.
 *
 * Koşum: `npm run test` (web/) — Node'un YERLEŞİK test koşucusu ve tip
 * sıyırması. Yeni bağımlılık YOKTUR (offline kısıtı + lisans denetimi).
 *
 * ## Bu testin varlık sebebi
 *
 * Şartnamenin beklenen çıktı tablosu (s.11–12) boş hücreyi bir TİRE ile değil
 * bir sözcükle dolduruyor: B Bankası satırının «Kampanya Süresi» hücresi
 * «Belirtilmemiş», C Bankası satırının «Masraf Durumu» hücresi «Masraf
 * belirtilmemiş». Sistem ise `«—»` basıyordu.
 *
 * Tire iki ayrı şeyi tek işarete indiriyordu — «bu bilgi kampanyada
 * belirtilmemiş» ile «burada gösterilecek bir şey yok» — ve ekran okuyucuda
 * hiçbir şey okunmuyordu. Jeton artık tektir ve `BELIRTILMEMIS` sabitinden
 * gelir; testler dizeyi elle yazmaz, yoksa sabit değiştiğinde sessizce
 * eskirler.
 *
 * Kıyas tablosunun kapsam satırları (`/compare`, alanı hiç olmayan banka)
 * `value: null` taşır ve tam olarak bu yoldan basılır — yani bu jeton, alanı
 * olmayan bankanın tabloda kalmasının görünen yüzüdür.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  avantajMetni,
  ayaktaDurur,
  BELIRTILMEMIS,
  formatValue,
  SUTUN_AVANTAJ_CAKISAN,
  trTarih,
} from "../app/lib/format.ts";

describe("formatValue — bilgi yokluğu", () => {
  it("null ve undefined şartnamenin jetonunu basar", () => {
    assert.equal(formatValue(null), BELIRTILMEMIS);
    assert.equal(formatValue(undefined), BELIRTILMEMIS);
  });

  it("jeton bir TİRE DEĞİLDİR", () => {
    assert.notEqual(BELIRTILMEMIS, "—");
    assert.notEqual(BELIRTILMEMIS, "-");
    assert.match(BELIRTILMEMIS, /[Bb]elirtilmemiş/);
  });

  it("alan adı verilse de jeton değişmez", () => {
    for (const alan of ["kar_payi_orani", "vade_ay", "masraf_durumu"]) {
      assert.equal(formatValue(null, alan), BELIRTILMEMIS);
    }
  });

  it("BOŞ LİSTE de bilgi taşımaz: aynı jeton", () => {
    assert.equal(formatValue([]), BELIRTILMEMIS);
    assert.equal(formatValue({ segments: [] }), BELIRTILMEMIS);
  });
});

describe("formatValue — dolu değerler etkilenmedi", () => {
  it("oran, vade ve taksit ekleri korunur", () => {
    assert.equal(formatValue(1.89, "kar_payi_orani"), "%1,89");
    assert.equal(formatValue(120, "vade_ay"), "120 ay");
    assert.equal(formatValue(12, "taksit_sayisi"), "12 taksit");
  });

  it("SIFIR bir değerdir, yokluk değildir", () => {
    // Sıfırın jetona düşmesi «masrafsız» kampanyayı «belirtilmemiş» yapardı —
    // CLAUDE.md §6'nın negasyon vakası tam burada kırılırdı.
    assert.equal(formatValue(0, "kar_payi_orani"), "%0");
    assert.equal(formatValue({ has_fee: false }), "masrafsız");
    assert.equal(formatValue({ value: 0, currency: "TRY" }), "0 TL");
  });

  it("aralık, para ve masraf biçimleri aynen kalır", () => {
    assert.equal(formatValue({ min: 1.99, max: 2.49 }, "kar_payi_orani"),
      "%1,99 – %2,49");
    assert.equal(formatValue({ value: 1500, currency: "TRY" }), "1.500 TL");
    assert.equal(formatValue({ has_fee: true, amount: 750 }), "750 TL");
  });

  it("tutarı bilinmeyen masraf «masraf var» der, jetona düşmez", () => {
    // «Ücret var, tutarı belirtilmemiş» ile «hiç bilgi yok» ayrı şeylerdir;
    // ikisini tek jetona toplamak ölçülmüş bir bulguyu silerdi.
    assert.equal(formatValue({ has_fee: true, amount: null }), "masraf var");
  });
});

describe("trTarih — kanonik ISO, Türkçe okunuş", () => {
  it("şartname A Bankası hücresi: 31 Aralık 2026", () => {
    assert.equal(trTarih("2026-12-31"), "31 Aralık 2026");
    assert.equal(formatValue("2026-12-31", "kampanya_suresi"), "31 Aralık 2026");
  });

  it("başındaki sıfır DÜŞER, ay adı Türkçe", () => {
    assert.equal(trTarih("2026-01-05"), "5 Ocak 2026");
    assert.equal(trTarih("2025-08-09"), "9 Ağustos 2025");
  });

  it("on iki ayın on ikisi", () => {
    const adlar = Array.from({ length: 12 }, (_, i) =>
      trTarih(`2026-${String(i + 1).padStart(2, "0")}-01`),
    );
    assert.deepEqual(adlar, [
      "1 Ocak 2026", "1 Şubat 2026", "1 Mart 2026", "1 Nisan 2026",
      "1 Mayıs 2026", "1 Haziran 2026", "1 Temmuz 2026", "1 Ağustos 2026",
      "1 Eylül 2026", "1 Ekim 2026", "1 Kasım 2026", "1 Aralık 2026",
    ]);
  });

  it("ISO OLMAYAN dize tarih SANILMAZ, aynen basılır", () => {
    // Tanımadığı bir biçimi yeniden yazmak olmayan bir bilgi iddia etmekti.
    for (const ham of ["31.12.2026", "yıl sonuna kadar", "2026", "2026-13-01",
                       "2026-00-10", "2026-12-32", ""]) {
      assert.equal(trTarih(ham), null, ham);
      assert.equal(formatValue(ham, "kampanya_suresi"), ham || BELIRTILMEMIS);
    }
  });

  it("tarih ARALIĞI da Türkçe okunur", () => {
    assert.equal(
      formatValue({ start: "2026-03-26", end: "2026-05-31" }),
      "26 Mart 2026 → 31 Mayıs 2026",
    );
  });
});

/**
 * «Kampanya Avantajı» — şartname s.12'nin beşinci kolonu.
 *
 * Sunucu bu kolonu SERBEST METİN olarak üretmez (CLAUDE.md §21); gerçek
 * çıkarım satırlarından derlenmiş parçalar gönderir ve metin burada kurulur.
 * Testler bunun bir birleştirme olduğunu, bir üretim olmadığını kilitler.
 */
describe("avantajMetni — parçalardan metin", () => {
  const ETIKET: Record<string, string> = {
    odul_miktari: "Ödül Miktarı",
    alisveris_puani: "Alışveriş Puanı",
    indirim_orani: "İndirim Oranı",
    masraf_durumu: "Masraf Durumu",
  };
  const etiketle = (alan: string) => ETIKET[alan] ?? alan;

  it("şartname C Bankası hücresi: 5.000 TL ödül", () => {
    // s.12: «5.000 TL alışveriş çeki». Sistem kanonik değeri ve alan adını
    // basar; «alışveriş çeki» ibaresini UYDURMAZ.
    const metin = avantajMetni(
      [{ field_name: "odul_miktari", value: { value: 5000, currency: "TRY" } }],
      etiketle,
    );
    assert.equal(metin, "Ödül Miktarı: 5.000 TL");
  });

  it("şartname A Bankası hücresi: masraf muafiyeti", () => {
    const metin = avantajMetni(
      [{ field_name: "masraf_durumu", value: { has_fee: false } }],
      etiketle,
    );
    assert.equal(metin, "Masraf Durumu: masrafsız");
  });

  it("birden çok parça « · » ile birleşir, sıra KORUNUR", () => {
    const metin = avantajMetni(
      [
        { field_name: "odul_miktari", value: { value: 500, currency: "TRY" } },
        { field_name: "alisveris_puani", value: { kind: "points", value: 750 } },
        { field_name: "indirim_orani", value: 10 },
      ],
      etiketle,
    );
    assert.equal(
      metin,
      "Ödül Miktarı: 500 TL · Alışveriş Puanı: 750 · İndirim Oranı: %10",
    );
  });

  it("parça yoksa jeton — tablonun geri kalanıyla AYNI", () => {
    assert.equal(avantajMetni([], etiketle), BELIRTILMEMIS);
  });

  it("etiket çözülemezse ALAN ADI basılır, ad uydurulmaz", () => {
    const metin = avantajMetni(
      [{ field_name: "yeni_alan", value: 42 }],
      etiketle,
    );
    assert.equal(metin, "yeni_alan: 42");
  });

  it("alan adı yoksa yalnız değer basılır", () => {
    assert.equal(avantajMetni([{ field_name: null, value: 42 }], etiketle), "42");
  });
});

/**
 * ÇAKIŞAN parça — yanındaki «Masraf Durumu» kolonunu tekrar etmesin.
 *
 * Sunucu, avantaj kaynağı aynı zamanda bir tablo kolonuysa parçayı
 * `SUTUN_AVANTAJ_CAKISAN` ile işaretler. O parça bankanın KENDİ ifadesiyle
 * basılır — ama yalnız ham ifade tek başına ayakta durabiliyorsa. Eşik
 * ölçüldü; gerekçesi `ayaktaDurur` docstring'inde.
 */
describe("avantajMetni — kolonu tekrar eden parça", () => {
  const etiketle = (alan: string) =>
    ({ masraf_durumu: "Masraf Durumu" })[alan] ?? alan;
  const cakisan = (raw: string | null) => ({
    field_name: "masraf_durumu",
    value: { has_fee: false, amount: 0 },
    sutun: SUTUN_AVANTAJ_CAKISAN,
    raw_value: raw,
  });

  it("şartname B Bankası: bankanın KENDİ cümlesi basılır", () => {
    // s.12 avantaj hücresi: «Ekspertiz ücreti banka tarafından karşılanıyor».
    assert.equal(
      avantajMetni([cakisan("ekspertiz ücreti banka tarafından karşılanmaktadır")], etiketle),
      "«ekspertiz ücreti banka tarafından karşılanmaktadır»",
    );
  });

  it("üç sözcüklü muafiyet de ayakta durur", () => {
    assert.equal(
      avantajMetni([cakisan("tahsis ücreti yansıtılmayacaktır")], etiketle),
      "«tahsis ücreti yansıtılmayacaktır»",
    );
  });

  it("TEK sözcük ayakta duramaz: alan-adlı biçime düşer", () => {
    // Korpustaki 414 muafiyetin 414'ü bu dalda. «Ücretsiz» tek başına
    // ücretin var mı yok mu olduğunu söylemiyor; kanonik değer söylüyor.
    for (const ham of ["Ücretsiz", "ücretsiz", "ücret", "masraf", "masrafsız"]) {
      assert.equal(
        avantajMetni([cakisan(ham)], etiketle),
        "Masraf Durumu: masrafsız",
        ham,
      );
    }
  });

  it("ham ifade yoksa da alan-adlı biçime düşer — hücre BOŞALMAZ", () => {
    for (const ham of [null, "", "   "]) {
      assert.equal(
        avantajMetni([cakisan(ham)], etiketle),
        "Masraf Durumu: masrafsız",
        String(ham),
      );
    }
  });

  it("İŞARETSİZ parça ham ifadeye SAPMAZ (ödül/puan/indirim dokunulmadı)", () => {
    const metin = avantajMetni(
      [{
        field_name: "odul_miktari",
        value: { value: 5000, currency: "TRY" },
        raw_value: "5.000 TL değerinde alışveriş çeki",
      }],
      (a) => (a === "odul_miktari" ? "Ödül Miktarı" : a),
    );
    assert.equal(metin, "Ödül Miktarı: 5.000 TL");
  });

  it("eşik: 2 sözcük ayakta durur, 1 sözcük durmaz", () => {
    // Ölçülen dağılımda 2 sözcüklü kayıt YOK; eşik o boşluğa oturuyor.
    assert.equal(ayaktaDurur("iki sözcük"), true);
    assert.equal(ayaktaDurur("tek"), false);
    assert.equal(ayaktaDurur("   Ücretsiz   "), false, "kenar boşlukları sayılmaz");
    assert.equal(ayaktaDurur("iki   sözcük"), true, "iç boşluk çokluğu sayılmaz");
    assert.equal(ayaktaDurur(null), false);
    assert.equal(ayaktaDurur(undefined), false);
  });
});
