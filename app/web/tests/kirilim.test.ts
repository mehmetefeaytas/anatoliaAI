/**
 * Yıldız kırılımının saf çekirdeğinin testleri (`app/lib/kirilim.ts`).
 *
 * Koşum: `npm run test` (web/) — Node'un YERLEŞİK test koşucusu ve tip
 * sıyırması. Yeni bağımlılık YOKTUR (offline kısıtı + lisans denetimi).
 * React render testi kurulmaz: hesap bilerek JSX'in dışına alındı.
 *
 * Bu testlerin ağırlığı üç yerde:
 *
 *  1. **KIRILIM TOPLAMI SKORLA TUTMALI.** Kırılım, yıldızın gerekçesini iddia
 *     eder. Ekranda yazan katkı/ağırlık bölmesi sunucunun `score`unu geri
 *     vermiyorsa, ekran düzeltmeye çalıştığı hatanın daha kötü bir biçimini
 *     üretir: yanlış gerekçeli bir kesinlik iddiası. Formülün tek doğruluk
 *     kaynağı `src/comparison/compare.py:934-1002`.
 *  2. **«TÜRDE HİÇ ÖLÇÜLEMEYEN» KÜMESİ TÜRETİLİR, TAHMİN EDİLMEZ.** Küme,
 *     `/advantageous.weights` ile `skor.components` arasındaki KÜME FARKIDIR.
 *     Bileşen listesi ağırlık tablosunun yalnız aktif alt kümesidir
 *     (compare.py:935) ve beş yıldızın tek bir %20'lik kalemden gelebilmesinin
 *     sebebi tam olarak bu fark.
 *  3. **SKORSUZ SATIRDA KIRILIM BASILMAZ.** «Boş yıldız basılmaz» kuralının
 *     kırılım karşılığı: ölçülemeyen tür için açılacak bir hesap yoktur.
 *
 * Ayrıca: ağırlık tablosu GELMEMİŞSE birinci payda satırı üretilmez. Ölçemediğimiz
 * bir yokluğu yokluk gibi göstermek bu ekranın reddettiği hatanın kendisi.
 *
 * KAYIT KAYNAĞI: `KT_317` canlı uçtan alındı — `GET /advantageous`, 13 Ağustos
 * 2026, Kuveyt Türk · Alışveriş Puanı · `campaign_id` 317. Hiçbir test ağa
 * çıkmaz; kayıt elden yazılmış sabit.
 *
 * ÖLÇÜLDÜ (13 Ağustos 2026): aynı yanıtın TAMAMI `kirilimOzeti()` ile tarandı —
 * dokuz türde 1.094 kayıt, `skor` ve `kapsama`da SIFIR sapma (tolerans 1e-9).
 * Kırılımın çizildiği kayıt sayısı 57. Tarama tek seferlikti; kalıcı bekçi
 * aşağıdaki testlerdir.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type { CompositeScore, ScoreComponent, WeightRow } from "../app/lib/api.ts";
import {
  kirilimCizilir,
  kirilimOzetSayilari,
  kirilimOzeti,
} from "../app/lib/kirilim.ts";

/** `/advantageous.weights` — beş ölçüt, toplam ağırlık 1,00. */
const AGIRLIKLAR: WeightRow[] = [
  { field_name: "kar_payi_orani", weight: 0.4, rationale: null, direction: "dusuk_iyi" },
  { field_name: "masraf_durumu", weight: 0.2, rationale: null, direction: "dusuk_iyi" },
  { field_name: "odul_miktari", weight: 0.15, rationale: null, direction: "yuksek_iyi" },
  { field_name: "vade_ay", weight: 0.15, rationale: null, direction: "yuksek_iyi" },
  { field_name: "finansman_tutari", weight: 0.1, rationale: null, direction: "yuksek_iyi" },
];

/**
 * Kuveyt Türk · Alışveriş Puanı · 317 — ÖLÇÜLMÜŞ kayıt.
 *
 * Beş yıldız, ama bileşen listesinde iki ölçüt var ve yalnız biri dolu:
 * ağırlık tablosunun %65'i bu türde hiç aktif değil.
 */
const KT_317: CompositeScore = {
  bank: "kuveyt-turk",
  bank_name: "Kuveyt Türk",
  campaign_id: 317,
  score: 1.0,
  coverage: 0.5714285714285715,
  comparable: true,
  note: null,
  components: [
    {
      field_name: "masraf_durumu",
      value: { has_fee: false, amount: 0.0 },
      normalized: 1.0,
      weight: 0.2,
      contribution: 0.2,
      note: null,
    },
    {
      field_name: "odul_miktari",
      value: null,
      normalized: null,
      weight: 0.15,
      contribution: 0.0,
      note: "veri yok",
    },
  ],
};

function bilesen(over: Partial<ScoreComponent> = {}): ScoreComponent {
  return {
    field_name: "kar_payi_orani",
    value: 2.5,
    normalized: 0.5,
    weight: 0.4,
    contribution: 0.2,
    note: null,
    ...over,
  };
}

function skor(over: Partial<CompositeScore> = {}): CompositeScore {
  return { ...KT_317, ...over };
}

/** İki kayan sayı ekranda aynı sayıyı yazar mı — kırılımın tek kabul ölçütü. */
function yakin(a: number | null, b: number | null, tolerans = 1e-9): void {
  assert.ok(a !== null && b !== null, `beklenmeyen null: ${a} / ${b}`);
  assert.ok(
    Math.abs((a as number) - (b as number)) < tolerans,
    `${a} ≈ ${b} değil`,
  );
}

describe("kirilimOzeti — kırılım toplamı skorla tutar", () => {
  it("canlı kayıtta yeniden türetilen skor sunucunun score'una eşit", () => {
    const o = kirilimOzeti(KT_317, AGIRLIKLAR);
    yakin(o.skor, KT_317.score);
    yakin(o.katkiToplami, 0.2);
    yakin(o.kapsananAgirlik, 0.2);
  });

  it("canlı kayıtta kapsama sunucunun coverage'ına eşit", () => {
    const o = kirilimOzeti(KT_317, AGIRLIKLAR);
    // total_active = 0,20 + 0,15 = 0,35 · covered_w = 0,20 → 0,571
    yakin(o.aktifAgirlik, 0.35);
    yakin(o.kapsama, KT_317.coverage);
    assert.equal(Math.round((o.kapsama as number) * 100), 57);
  });

  it("çok bileşenli kayıtta da katkı toplamı / kapsanan ağırlık = skor", () => {
    const s = skor({
      score: 0.6,
      components: [
        bilesen({ field_name: "kar_payi_orani", weight: 0.4, normalized: 0.5, contribution: 0.2 }),
        bilesen({ field_name: "masraf_durumu", weight: 0.2, normalized: 1.0, contribution: 0.2 }),
        bilesen({ field_name: "vade_ay", weight: 0.15, normalized: null, contribution: 0.0, value: null }),
      ],
    });
    const o = kirilimOzeti(s, AGIRLIKLAR);
    yakin(o.kapsananAgirlik, 0.6);
    yakin(o.katkiToplami, 0.4);
    yakin(o.skor, 0.4 / 0.6);
    yakin(o.kapsama, 0.6 / 0.75);
  });

  it("hiçbir bileşen kapsanmadıysa skor null — 0 DEĞİL", () => {
    const s = skor({
      components: [bilesen({ normalized: null, contribution: 0.0, value: null })],
    });
    const o = kirilimOzeti(s, AGIRLIKLAR);
    assert.equal(o.skor, null);
    assert.equal(o.kapsanan, 0);
    yakin(o.kapsama, 0);
  });
});

describe("kirilimOzeti — «türde hiç ölçülemeyen» kümesi weights − components", () => {
  it("canlı kayıtta üç ölçüt hiç aktif değil, ağırlığın %65'i", () => {
    const o = kirilimOzeti(KT_317, AGIRLIKLAR);
    assert.equal(o.tabloToplam, 5);
    assert.deepEqual(
      o.olculemeyen?.map((x) => x.field_name),
      ["kar_payi_orani", "vade_ay", "finansman_tutari"],
    );
    yakin(o.olculemeyenPay, 0.65);
    assert.equal(Math.round((o.olculemeyenPay as number) * 100), 65);
  });

  it("küme farkı hesaplanır: bileşende geçen hiçbir alan listeye girmez", () => {
    const bilesenAdlari = new Set(KT_317.components.map((c) => c.field_name));
    const beklenen = AGIRLIKLAR.filter((w) => !bilesenAdlari.has(w.field_name)).map(
      (w) => w.field_name,
    );
    const o = kirilimOzeti(KT_317, AGIRLIKLAR);
    assert.deepEqual(o.olculemeyen?.map((x) => x.field_name), beklenen);
    for (const x of o.olculemeyen ?? []) {
      assert.equal(bilesenAdlari.has(x.field_name), false);
    }
  });

  it("sıra ağırlık tablosundan gelir, yeniden üretilmez", () => {
    const ters = [...AGIRLIKLAR].reverse();
    const o = kirilimOzeti(KT_317, ters);
    assert.deepEqual(
      o.olculemeyen?.map((x) => x.field_name),
      ["finansman_tutari", "vade_ay", "kar_payi_orani"],
    );
  });

  it("tablonun tamamı aktifse küme BOŞ DİZİ olur (null değil)", () => {
    const o = kirilimOzeti(KT_317, [
      { field_name: "masraf_durumu", weight: 0.2, rationale: null, direction: "dusuk_iyi" },
      { field_name: "odul_miktari", weight: 0.15, rationale: null, direction: "yuksek_iyi" },
    ]);
    assert.deepEqual(o.olculemeyen, []);
    yakin(o.olculemeyenPay, 0);
  });

  it("ağırlık tablosu gelmemişse birinci payda satırı ÜRETİLMEZ", () => {
    for (const yok of [undefined, null, [] as WeightRow[]]) {
      const o = kirilimOzeti(KT_317, yok);
      assert.equal(o.olculemeyen, null, "olculemeyen null kalmalı");
      assert.equal(o.tabloToplam, null);
      assert.equal(o.olculemeyenPay, null);
      // Tablo yine çizilir: bileşenlere dayanan paydalar hesaplanmış olmalı.
      yakin(o.skor, KT_317.score);
      yakin(o.kapsama, KT_317.coverage);
      assert.equal(o.bosKalan.length, 1);
    }
  });
});

describe("kirilimOzeti — bu kampanyada boş kalan aktif ölçüt", () => {
  it("normalized === null olan bileşenler boş sayılır", () => {
    const o = kirilimOzeti(KT_317, AGIRLIKLAR);
    assert.deepEqual(o.bosKalan.map((c) => c.field_name), ["odul_miktari"]);
    assert.equal(o.aktif, 2);
    assert.equal(o.kapsanan, 1);
  });

  it("değeri olan ama normalize edilemeyen bileşen BOŞ sayılır", () => {
    // Süre/güven kapısı ham değeri bırakır ama `normalized`ı düşürür
    // (compare.py:922-928). Kapsamanın ölçütü `normalized`dır, `value` değil.
    const s = skor({
      components: [
        bilesen({ field_name: "masraf_durumu", weight: 0.2, normalized: 1.0, contribution: 0.2 }),
        bilesen({
          field_name: "kar_payi_orani",
          value: 2.5,
          normalized: null,
          contribution: 0.0,
          note: "güven eşiğinin altında",
        }),
      ],
    });
    const o = kirilimOzeti(s, AGIRLIKLAR);
    assert.deepEqual(o.bosKalan.map((c) => c.field_name), ["kar_payi_orani"]);
    yakin(o.skor, 1.0);
  });
});

describe("kirilimCizilir — skorsuz satırda kırılım basılmaz", () => {
  it("ölçülmüş satırda çizilir", () => {
    assert.equal(kirilimCizilir(KT_317, 12), true);
  });

  it("skoru olmayan satırda çizilmez", () => {
    assert.equal(kirilimCizilir(skor({ score: null }), 12), false);
  });

  it("kıyas dışı satırda çizilmez", () => {
    assert.equal(kirilimCizilir(skor({ comparable: false }), 12), false);
  });

  it("belge sayısı bilinmiyorsa ya da sıfırsa çizilmez", () => {
    assert.equal(kirilimCizilir(KT_317, null), false);
    assert.equal(kirilimCizilir(KT_317, 0), false);
  });

  it("bileşen listesi boşsa çizilmez — açılacak hesap yok", () => {
    assert.equal(kirilimCizilir(skor({ components: [] }), 12), false);
  });

  it("ölçülemedi kaydında (BankaSayfasi `olculemedi()`) çizilmez", () => {
    const olculemedi: CompositeScore = {
      bank: "kuveyt-turk",
      bank_name: null,
      campaign_id: null,
      score: null,
      coverage: 0,
      comparable: false,
      note: "bu türde hiç belge toplanamadı",
      components: [],
    };
    assert.equal(kirilimCizilir(olculemedi, 0), false);
    assert.equal(kirilimCizilir(olculemedi, 12), false);
  });
});

describe("kirilimOzetSayilari — katlanmış <summary> de bilgi taşır", () => {
  it("canlı kayıtta iki sayı: 5 ölçütün 1'i (tasarımdaki cümle)", () => {
    const s = kirilimOzetSayilari(kirilimOzeti(KT_317, AGIRLIKLAR));
    assert.deepEqual(s, { payda: 5, pay: 1, tabloyaDayali: true });
  });

  it("payda ağırlık TABLOSUNUN sayısıdır, aktif bileşen sayısı değil", () => {
    const o = kirilimOzeti(KT_317, AGIRLIKLAR);
    const s = kirilimOzetSayilari(o);
    assert.equal(o.aktif, 2, "aktif bileşen 2");
    assert.equal(s.payda, 5, "ama payda ağırlık tablosundan gelir");
  });

  it("ağırlık tablosu yoksa payda AKTİF ölçüt sayısına düşer ve bildirir", () => {
    const s = kirilimOzetSayilari(kirilimOzeti(KT_317, null));
    assert.deepEqual(s, { payda: 2, pay: 1, tabloyaDayali: false });
  });
});
