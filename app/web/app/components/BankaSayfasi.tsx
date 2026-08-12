"use client";

/**
 * Banka sayfası — künye, veri kapsamı, TÜR İÇİNDE yıldız cetveli, 12 alanın durumu.
 *
 * İlgili: ./YildizPuan.tsx, ./FieldChips.tsx, ./BankDeltaPanel.tsx,
 *         ../styles/banka.css, ../lib/api.ts (`banks`, `fields`, `campaigns`,
 *         `advantageous`), src/comparison/compare.py `rank_advantageous_by_type`,
 *         src/db/repository.py `bank_field_coverage()`
 *
 * ## Tek bir «banka puanı» ÜRETİLMEZ
 *
 * İstek şuydu: «her bankanın bir sayfası olsun; kampanya türleri vb. kısımlarda
 * puanı — bu puan yıldızların içi dolacak şekilde olsun.» Sayfa yapıldı, yıldız
 * yapıldı; ama **banka başına tek bir puan YOKTUR ve hesaplanamaz.** Sayfada
 * bileşik bir banka skoru hiç basılmaz; yerine gerekçesi basılır (aşağıdaki
 * provenans şeridi).
 *
 * Gerekçe ölçülmüş bir gerçektir, üslup tercihi değil: `/advantageous` bileşik
 * skoru KAMPANYA başına ve KAMPANYA TÜRÜ İÇİNDE üretir; normalizasyon grup içi
 * sıralama tabanlıdır (`compare.py::rank_advantageous`). Farklı türlerden gelen
 * skorların ortalaması, farklı popülasyonlarda ölçülmüş sıraların
 * ortalamasıdır — matematiksel olarak tanımsızdır. Üstelik sekiz kampanya türü
 * birbirinin ALTERNATİFİ değildir; hepsini tek sayıya toplamak, sistemin
 * reddettiği türler arası sıralamayı arka kapıdan geri getirirdi (CLAUDE.md §17).
 *
 * İkinci ve daha sinsi sonuç: bir bankanın tüm kampanyalarını ortalamak,
 * TOPLAMA KAPSAMASINI kaliteye çevirirdi. Az belge toplanabilmiş bir banka,
 * ürünü kötü olduğu için değil verisi az olduğu için düşük puan alırdı.
 *
 * ## «veri kapsamı» kutusu ve eşiği — ÖLÇÜLDÜ
 *
 * Kutu bankanın TAMAMI içindir ve öyle olması `repository.py`
 * `bank_field_coverage()` sözleşmesinin kendisidir: `belge` bankanın kampanya
 * sayısı, `alan` ise o bankada kaç ÇEŞİT bilginin çıkarılabildiğidir (üst sınır
 * `/fields` uzunluğu, yani 12).
 *
 * Kutu iki hâlde basılır ve eşik ARAYÜZÜN KENDİ KAFASINDAN gelmiyor:
 * `/advantageous` ucunun döndürdüğü `min_coverage` (bugün 0,5 —
 * `compare.py::MIN_COVERAGE`) kullanılır. Sunucu bir kampanyayı «güvenilir
 * kapsama» saymak için ölçütlerinin ağırlıkça en az yarısını istiyor; aynı
 * yarım eşiği bankanın alan çeşidine uygulamak, iki yüzeyin aynı sözü
 * söylemesini sağlar. İki nicelik AYNI ŞEY DEĞİLDİR (biri kampanya başına
 * ağırlıkça kapsama, diğeri banka başına alan çeşidi) ve bu yüzden eşik
 * uydurulmuyor, ÖDÜNÇ alınıyor: sunucu eşiğini değiştirdiğinde arayüz de
 * değişir, iki yerde yaşayan bir sabit kalmaz. Eşik henüz gelmemişse kutu
 * NÖTR basılır — bilinmeyen bir eşikle uyarı rengi basmak, ölçülmemiş bir
 * yargıdır.
 *
 * `belge === 0` hâli eşik beklemez: hiç belgesi olmayan bankada kapsama
 * tartışmasız dardır.
 *
 * ## 12 alanın durumu — üçüncü hâl neden var
 *
 * Çip şeridi, bu bankada hangi alanın dolduğunu göstermek ister. Ama alan
 * başına BANKA kapsaması veren bir uç YOK: `/stats.alan_kapsami` korpus
 * genelindedir, `/stats.banka_kapsami` yalnız KAÇ çeşit alan dolduğunu söyler,
 * `/bank-delta` sıralanabilir alanlarla sınırlıdır (`main.py:1398`). Elde iki
 * sağlam bilgi var:
 *
 *   D = `/advantageous` bileşenlerinde bu bankanın kayıtlarında değeri `null`
 *       OLMAYAN alanlar. Bir satır gerçekten var demektir → **kanıtlı dolu.**
 *   alan = `banka_kapsami.alan`, yani gerçek dolu küme A'nın BÜYÜKLÜĞÜ.
 *
 * D ⊆ A ve |A| = alan olduğundan iki çıkarım tümdengelimli olarak geçerlidir:
 *   - `alan === 12` → A tüm alanlar → hepsi dolu.
 *   - `|D| === alan` → D = A → D dışındakiler kanıtlı BOŞ.
 * Bunların dışında kalan alan için doğru cevap «bilinmiyor»dur ve çip onu
 * `· ?` olarak basar. `null` basmak, ölçülmemiş bir yokluk iddia etmek olurdu —
 * `YildizPuan`ın boş yıldız basmama kuralının çip karşılığı.
 *
 * ## Marka varlığı uydurulmuyor
 *
 * `/banks` yalnız `slug`, `name`, `website_url`, `bddk_active` döndürür; logo
 * ve marka rengi yoktur, `public/` boştur. Amblem bankanın adından türetilen
 * baş harf monogramıdır ve rengini tema vurgusundan alır. Marka rengi seçmek
 * hem görsel bir yalan hem de marka hakkı sorunu olurdu.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import BankDeltaPanel from "./BankDeltaPanel";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import FairnessNotice from "./FairnessNotice";
import FieldChips from "./FieldChips";
import type { AlanDurumu } from "./FieldChips";
import YildizPuan from "./YildizPuan";
import { api } from "../lib/api";
import type {
  Advantageous,
  BankaKapsami,
  CampaignSummary,
  CompositeScore,
  FieldMeta,
} from "../lib/api";
import { useAsync } from "../lib/useAsync";

type Props = {
  campaignTypes: string[];
  /** `/stats` → banka başına «kaç belge / kaç çeşit alan». Sayfa kendi
   *  isteğini atmaz: üst sayfa `/stats`i zaten indiriyor. */
  kapsam: Record<string, BankaKapsami> | null;
  /** Belgeyi Jüri Audit Paneli'nde açar (page.tsx `inspect` deseni). */
  onInspect: (campaignId: number) => void;
  /** Başka bir ekrandan hedeflenen banka (page.tsx `bankaAc` deseni). */
  secili?: string | null;
};

/** Harf olmayan her şey (nokta, kısaltma tiresi) atılır. */
const HARF_DISI = /[^\p{L}]/gu;

/**
 * Amblemdeki baş harfler — «Kuveyt Türk» → «KT».
 *
 * Tek harfli parçalar («T.A.Ş.» kalıntıları) elenir; hiçbir parça kalmazsa
 * adın ilk harfine düşülür. Monogram DEKORATİFTİR: adın kendisi yanında yazar.
 */
function basHarfler(ad: string): string {
  const parcalar = ad
    .split(/\s+/)
    .map((p) => p.replace(HARF_DISI, ""))
    .filter((p) => p.length > 1);
  const kaynak = parcalar.length > 0 ? parcalar : [ad.replace(HARF_DISI, "")];
  return kaynak
    .slice(0, 2)
    .map((p) => Array.from(p)[0] ?? "")
    .join("")
    .toLocaleUpperCase("tr");
}

/**
 * «12 alandan 2'si» — sayıya 3. tekil iyelik eki.
 *
 * Türkçe ek ses uyumuna bağlıdır ve sayının OKUNUŞUNA göre değişir (2 → iki'si,
 * 3 → üç'ü, 6 → altı'sı). Bir kural yazmak yerine 0–12 aralığı sayıldı: ekranda
 * payda `/fields` uzunluğu, yani 12'dir ve pay ondan büyük olamaz. Aralık
 * dışında kalırsa ek yerine «tanesi» kullanılır — yanlış ek yazmaktansa daha
 * uzun ama doğru bir cümle.
 */
const IYELIK: Record<number, string> = {
  0: "0'ı",
  1: "1'i",
  2: "2'si",
  3: "3'ü",
  4: "4'ü",
  5: "5'i",
  6: "6'sı",
  7: "7'si",
  8: "8'i",
  9: "9'u",
  10: "10'u",
  11: "11'i",
  12: "12'si",
};

function sayiIyelik(n: number): string {
  return IYELIK[n] ?? `${n} tanesi`;
}

/**
 * Ölçülemeyen bir tür için gösterim kaydı.
 *
 * Skor `null` KALIR — burada üretilen bir puan yoktur, üretilen yalnız
 * «ölçemedik» cümlesidir. `YildizPuan` bu kaydı gördüğünde yıldız çizmez.
 */
function olculemedi(bank: string, gerekce: string): CompositeScore {
  return {
    bank,
    bank_name: null,
    campaign_id: null,
    score: null,
    coverage: 0,
    comparable: false,
    note: gerekce,
    components: [],
  };
}

/** Bir kampanya türünün bu bankadaki karşılığı. */
type TurSatiri = {
  tur: string;
  skor: CompositeScore;
  /** Tür içindeki sıra — yalnız kıyaslanabilir kayıtlar arasında. */
  sira: number | null;
  /** Sıranın paydası: türdeki kıyaslanabilir kampanya sayısı. */
  grupBuyuklugu: number;
  /**
   * Bu bankanın BU TÜRDEKİ belge sayısı — yıldızın paydası.
   * `null` = belge listesi henüz gelmedi ("ölçtük, yok" DEĞİL).
   */
  belge: number | null;
};

/**
 * Türleri satırlara çevirir.
 *
 * Bankanın hiç kaydı olmayan türler de LİSTEDE KALIR: «bu türde belgemiz yok»
 * bilgi taşıyan bir cevaptır ve gizlenmesi, eksiği saklayan bir ekran üretirdi.
 */
function turSatirlari(
  veri: Advantageous,
  turler: string[],
  bank: string,
  turBelgeleri: Map<string, number> | null,
): TurSatiri[] {
  const adlar = Array.from(
    new Set([...Object.keys(veri.types), ...turler]),
  ).sort((a, b) => a.localeCompare(b, "tr"));

  const belgeSayisi = (ad: string) =>
    turBelgeleri === null ? null : (turBelgeleri.get(ad) ?? 0);

  return adlar.map((ad) => {
    const belge = belgeSayisi(ad);
    const grup = veri.types[ad];
    if (!grup) {
      return {
        tur: ad,
        skor: olculemedi(bank, "korpusta bu türde skorlanabilir kampanya yok"),
        sira: null,
        grupBuyuklugu: 0,
        belge,
      };
    }

    // Küçük grup: sunucu `ranked`ı boş bırakır ve gerekçeyi `note`ta verir.
    if (grup.ranked.length === 0) {
      return {
        tur: ad,
        skor: olculemedi(
          bank,
          grup.note ?? "yetersiz kapsama — bu türde sıralama yapılmadı",
        ),
        sira: null,
        grupBuyuklugu: 0,
        belge,
      };
    }

    // Sıra yalnız KIYASLANABİLİR kayıtlar arasında verilir: kıyas dışı
    // bırakılmış kayıtlar listenin sonundadır ve sıralamada yerleri yoktur.
    const kiyaslanabilir = grup.ranked.filter(
      (c) => c.comparable && c.score !== null,
    );
    const yer = kiyaslanabilir.findIndex((c) => c.bank === bank);
    if (yer >= 0) {
      // Aynı bankanın bu türde birden çok kampanyası olabilir; liste skora göre
      // azalan sıralı olduğu için ilk eşleşme bankanın EN İYİ kaydıdır.
      return {
        tur: ad,
        skor: kiyaslanabilir[yer],
        sira: yer + 1,
        grupBuyuklugu: kiyaslanabilir.length,
        belge,
      };
    }

    // Kaydı var ama kapsama eşiğini geçemedi: gerekçe sunucudan gelir, arayüz
    // yeniden yazmaz ki ikisi aynı şeyi söylesin.
    const kiyasDisi = grup.ranked.find((c) => c.bank === bank);
    if (kiyasDisi) {
      return {
        tur: ad,
        skor: kiyasDisi,
        sira: null,
        grupBuyuklugu: kiyaslanabilir.length,
        belge,
      };
    }

    return {
      tur: ad,
      skor: olculemedi(bank, "bu bankanın bu türde skorlanabilir belgesi yok"),
      sira: null,
      grupBuyuklugu: kiyaslanabilir.length,
      belge,
    };
  });
}

/**
 * Skorun bileşenlerinden «hangi ölçüt doldu, hangisi geçmiyor» cümlesi.
 *
 * Cümle VERİDEN türetilir; hiçbir alan adı burada sabit yazılmaz. Bileşen
 * listesi boşsa (ölçülemeyen tür) hiç cümle üretilmez — boş bir liste
 * hakkında konuşmak, ölçülmemiş bir şeyi anlatmak olurdu.
 */
function olcutCumlesi(
  skor: CompositeScore,
  etiket: (field: string) => string,
): ReactNode {
  if (skor.components.length === 0) return null;
  const dolu = skor.components
    .filter((c) => c.value !== null && c.value !== undefined)
    .map((c) => etiket(c.field_name));
  const bos = skor.components
    .filter((c) => c.value === null || c.value === undefined)
    .map((c) => etiket(c.field_name));

  return (
    <>
      {dolu.length > 0 && <>Dolu ölçütler: {dolu.join(", ")}.</>}
      {dolu.length > 0 && bos.length > 0 && " "}
      {bos.length > 0 && <>Bu belgelerde geçmeyen: {bos.join(", ")}.</>}
    </>
  );
}

/**
 * 12 alanın bu bankadaki durumu — kanıt ve tümdengelim, tahmin değil.
 *
 * Kuralların gerekçesi dosya başlığında («12 alanın durumu»). Özet: kanıtlı
 * dolu küme D `/advantageous` bileşenlerinden gelir; gerçek dolu kümenin
 * BÜYÜKLÜĞÜ `banka_kapsami.alan`dan gelir. İkisi kapanıyorsa geri kalan
 * kanıtlı boştur, kapanmıyorsa bilinmiyordur.
 */
function alanDurumlari(
  fields: FieldMeta[],
  veri: Advantageous | null,
  bank: string,
  alan: number | null,
): Record<string, AlanDurumu> {
  const kanitli = new Set<string>();
  if (veri) {
    for (const grup of Object.values(veri.types)) {
      for (const kayit of grup.ranked) {
        if (kayit.bank !== bank) continue;
        for (const c of kayit.components) {
          if (c.value !== null && c.value !== undefined) {
            kanitli.add(c.field_name);
          }
        }
      }
    }
  }

  // `alan === fields.length` → gerçek dolu küme TÜM alanlardır.
  const hepsiDolu = alan !== null && alan >= fields.length;
  // D = A kapanışı: kanıtlı kümenin boyu, ölçülmüş dolu alan sayısına eşit.
  const kapandi = alan !== null && kanitli.size === alan;

  const cikti: Record<string, AlanDurumu> = {};
  for (const f of fields) {
    if (hepsiDolu || kanitli.has(f.field)) {
      // Sayı UYDURULMAZ: bileşenler yalnız skorlanan belgeleri gezer, yani
      // buradan çıkacak adet gerçek belge sayısının ALT sınırıdır. Alt sınırı
      // kesin sayı gibi basmak yanlış bir kesinlik iddiasıdır.
      cikti[f.field] = { tip: "dolu", adet: null };
    } else if (kapandi) {
      cikti[f.field] = { tip: "bos" };
    } else {
      cikti[f.field] = { tip: "bilinmiyor" };
    }
  }
  return cikti;
}

export default function BankaSayfasi({
  campaignTypes,
  kapsam,
  onInspect,
  secili,
}: Props) {
  // Banka listesi katalogdan gelir, kampanyalardan DEĞİL: hiç belgesi
  // toplanmamış bankanın da sayfası olmalı — «bizde hiç ürün yok» bu ekranın
  // cevaplaması gereken sorulardan biri.
  const banks = useAsync(() => api.banks(), []);
  const [bank, setBank] = useState("");
  const liste = useMemo(() => banks.data ?? [], [banks.data]);

  // Dışarıdan gelen hedef BİR KEZ uygulanır. Her render'da uygulansaydı,
  // kullanıcının sayfadaki seçiciyle yaptığı değişiklik bir sonraki render'da
  // sessizce geri alınırdı — sıçrama bir başlangıç değeri verir, bir kilit değil.
  const uygulananHedef = useRef<string | null>(null);
  useEffect(() => {
    if (liste.length === 0) return;
    if (
      secili &&
      secili !== uygulananHedef.current &&
      liste.some((b) => b.slug === secili)
    ) {
      uygulananHedef.current = secili;
      setBank(secili);
      return;
    }
    if (!bank || !liste.some((b) => b.slug === bank)) setBank(liste[0].slug);
  }, [liste, bank, secili]);

  // Tür süzgeci VERİLMEZ: sayfa bankanın tüm türlerdeki durumunu gösterir ve
  // her tür kendi grubunda sıralanır.
  const avantaj = useAsync(() => api.advantageous(), []);
  // 12 alanın adı ve Türkçe etiketi — çip şeridi ve ölçüt cümlesi buradan.
  // Sayı sabit yazılmaz: payda `/fields` uzunluğudur.
  const alanlar = useAsync(() => api.fields(), []);
  /**
   * Bankanın belge ÜSTVERİSİ (gövde yok). İki şeyi tek istekte verir:
   * tür başına belge sayısı (yıldızın paydası) ve son toplama damgası.
   * `/stats` bunların ikisini de vermiyor: `banka_kapsami` tür boyutu
   * taşımıyor, tarih hiç taşımıyor.
   */
  const belgeler = useAsync<CampaignSummary[] | null>(
    () => (bank ? api.campaigns({ bank }) : Promise.resolve(null)),
    [bank],
  );

  const secilenBanka = liste.find((b) => b.slug === bank);
  const bankaAdi = secilenBanka?.name ?? bank;
  const bankaKapsami = kapsam?.[bank];
  const alanListesi = alanlar.data ?? [];

  /**
   * SINIFLANDIRILAMAYAN belgelerin kovası — adı sabit yazılmaz, TÜRETİLİR.
   *
   * ÖLÇÜLDÜ: `/advantageous` `types` sözlüğünde dokuz anahtar var, `/stats`
   * `campaign_types` sekiz; fark tek bir sözde-kovadır ve `campaign_type IS
   * NULL` belgeleri o kovada toplanır (bugün «Sınıflandırılamadı»). Etiketi
   * arayüze sabit yazmak, sunucunun dilini iki yerde yaşatmak olurdu — o yüzden
   * KÜME FARKI alınır. Fark tek bir anahtar değilse kova bulunamamış sayılır ve
   * tür süzgeci olmayan belgeler hiçbir satırda sayılmaz (yanlış satıra
   * yazmaktansa sayılmasın; künyedeki not zaten kaç belge olduğunu söylüyor).
   *
   * Bu kova olmadan ekran KENDİYLE ÇELİŞİYORDU: künye «1 belge hiçbir türe
   * sınıflandırılamadı» derken, cetvel aynı türü «hiç belge toplanamadı»
   * satırına koyuyordu.
   */
  const tursuzKova = useMemo(() => {
    if (!avantaj.data) return null;
    const fazla = Object.keys(avantaj.data.types).filter(
      (t) => !campaignTypes.includes(t),
    );
    return fazla.length === 1 ? fazla[0] : null;
  }, [avantaj.data, campaignTypes]);

  /** Tür → bu bankadaki belge sayısı. Liste gelmeden `null` (0 DEĞİL). */
  const turBelgeleri = useMemo(() => {
    if (!belgeler.data) return null;
    const m = new Map<string, number>();
    for (const c of belgeler.data) {
      const ad = c.campaign_type ?? tursuzKova;
      if (!ad) continue;
      m.set(ad, (m.get(ad) ?? 0) + 1);
    }
    return m;
  }, [belgeler.data, tursuzKova]);

  /** Sınıflandırılamamış belgeler — hiçbir türün satırında sayılmazlar. */
  const tursuzBelge = useMemo(
    () =>
      belgeler.data
        ? belgeler.data.filter((c) => !c.campaign_type).length
        : null,
    [belgeler.data],
  );

  /** Son toplama damgası (ISO'nun gün kısmı). Yoksa UYDURULMAZ. */
  const sonToplama = useMemo(() => {
    if (!belgeler.data) return null;
    let enSon: string | null = null;
    for (const c of belgeler.data) {
      const t = c.scraped_at;
      if (!t) continue;
      if (enSon === null || t > enSon) enSon = t;
    }
    return enSon ? enSon.slice(0, 10) : null;
  }, [belgeler.data]);

  const satirlar = useMemo(
    () =>
      avantaj.data && bank
        ? turSatirlari(avantaj.data, campaignTypes, bank, turBelgeleri)
        : [],
    [avantaj.data, campaignTypes, bank, turBelgeleri],
  );

  const etiket = useMemo(() => {
    const m = new Map(alanListesi.map((f) => [f.field, f.label]));
    return (field: string) => m.get(field) ?? field;
  }, [alanListesi]);

  const durumlar = useMemo(
    () =>
      alanDurumlari(
        alanListesi,
        avantaj.data ?? null,
        bank,
        bankaKapsami?.alan ?? null,
      ),
    [alanListesi, avantaj.data, bank, bankaKapsami],
  );

  // Cetvelin sırası: ölçülmüş satırlar önce (yıldızı olanlar), sonra belgesi
  // olup skoru olmayanlar, en sonda hiç belge toplanamamış türler TEK satırda.
  // Sıralama bir yargı değil, okuma kolaylığı: her satır listede kalır.
  const yildizli = satirlar.filter(
    (s) => s.skor.score !== null && s.skor.comparable && (s.belge ?? 0) > 0,
  );
  const belgesizler = satirlar.filter((s) => s.belge === 0);
  const skorsuzlar = satirlar.filter(
    (s) => !yildizli.includes(s) && !belgesizler.includes(s),
  );

  /** Çip şeridinde GERÇEKTEN basılan hâller — açıklama buna göre kısalır. */
  const basilanHaller = useMemo(
    () => new Set(Object.values(durumlar).map((d) => d.tip)),
    [durumlar],
  );

  const alanToplam = alanListesi.length;
  const esik = avantaj.data?.min_coverage ?? null;
  // Kapsama DAR mı? Gerekçe dosya başlığında; eşik sunucunun `min_coverage`ı.
  const kapsamaDar =
    bankaKapsami !== undefined &&
    (bankaKapsami.belge === 0 ||
      (esik !== null &&
        alanToplam > 0 &&
        bankaKapsami.alan / alanToplam < esik));

  if (!banks.loading && liste.length === 0) {
    return (
      <section className="card">
        <h2>Banka sayfası</h2>
        {banks.error ? (
          <ErrorNotice error={banks.error} />
        ) : (
          <EmptyNotice title="Gösterilecek banka yok">
            Banka kataloğundan hiçbir kayıt dönmedi; sayfanın öznesi
            belirlenemiyor.
          </EmptyNotice>
        )}
      </section>
    );
  }

  return (
    <div className="stack">
      <section className="card">
        <div className="banka-bas">
          {/* Monogram dekoratiftir: adı hemen yanında yazılı. */}
          <div className="banka-amblem" aria-hidden="true">
            {bankaAdi ? basHarfler(bankaAdi) : ""}
          </div>

          <div className="banka-kimlik">
            <h2 className="banka-ad">{bankaAdi || "—"}</h2>
            <span className="banka-altyazi">
              {bank || "—"}
              {" · "}
              {sonToplama
                ? `son toplama ${sonToplama}`
                : belgeler.loading
                  ? "toplama damgası okunuyor…"
                  : "toplama damgası yok"}
            </span>

            <div className="banka-etiketler">
              {/* Katalog gelmeden rozet BASILMAZ: yüklenirken «aktif değil»
                  yazmak, henüz bilinmeyen bir şeyi iddia etmek olurdu. */}
              {secilenBanka && (
                <span
                  className={
                    secilenBanka.bddk_active ? "badge badge-ok" : "badge"
                  }
                >
                  {secilenBanka.bddk_active
                    ? "BDDK listesinde aktif"
                    : "BDDK listesinde aktif değil"}
                </span>
              )}

              {secilenBanka?.website_url && (
                <a
                  className="btn-link"
                  href={secilenBanka.website_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  title={secilenBanka.website_url}
                >
                  banka sitesi ↗
                </a>
              )}

              <span className="banka-secim row-tight">
                <label className="small muted" htmlFor="banka-secici">
                  Banka
                </label>
                <select
                  id="banka-secici"
                  className="select"
                  style={{ width: "auto" }}
                  value={bank}
                  onChange={(e) => setBank(e.target.value)}
                >
                  {liste.map((b) => (
                    <option key={b.slug} value={b.slug}>
                      {b.name}
                    </option>
                  ))}
                </select>
              </span>
            </div>
          </div>

          {/* VERİ KAPSAMI — sayfadaki her işaretin paydası. */}
          <div
            className={
              kapsamaDar
                ? "banka-kapsam-kutu banka-kapsam-kutu-dar"
                : "banka-kapsam-kutu"
            }
            role="note"
            aria-label="Bu bankanın veri kapsamı"
          >
            <span className="banka-kapsam-etiket">veri kapsamı</span>
            {bankaKapsami ? (
              <>
                <div className="banka-kapsam-sayi">
                  {bankaKapsami.belge} belge
                  {alanToplam > 0 && (
                    <>
                      {" · "}
                      {alanToplam} alandan {sayiIyelik(bankaKapsami.alan)} dolu
                    </>
                  )}
                </div>
                <p className="banka-kapsam-not">
                  {kapsamaDar && <b>Kapsama dar. </b>}
                  Bu sayfadaki her yıldız yalnız bu {bankaKapsami.belge} belgeye
                  dayanıyor. Aşağıdaki hiçbir işaret bankanın kendisi hakkında
                  bir yargı değil: toplanabilen belge sayısı bankanın ürününü
                  değil, sitesinin ne kadarının okunabildiğini ölçer.
                  {tursuzBelge !== null && tursuzBelge > 0 && (
                    <>
                      {" "}
                      Bu belgelerin {tursuzBelge} tanesi hiçbir kampanya türüne
                      sınıflandırılamadı;{" "}
                      {tursuzKova
                        ? `aşağıda «${tursuzKova}» satırında sayılıyor.`
                        : "aşağıdaki tür satırlarında sayılmıyor."}
                    </>
                  )}
                </p>
              </>
            ) : (
              // «Bilinmiyor», «ölçülemedi» DEĞİL: sayaç henüz gelmemiş de
              // olabilir, banka katalogda olup korpusta hiç görünmemiş de.
              // İkisini ayırmadan «ölçülemedi» demek, sayfanın bilmediği bir
              // şeyi iddia etmesi olurdu.
              <p className="banka-kapsam-not">
                Kapsama sayacı bu banka için gelmedi; aşağıdaki işaretlerin
                paydası bilinmiyor.
              </p>
            )}
          </div>
        </div>

        {banks.loading && <Loading label="Banka kataloğu yükleniyor…" />}
        {!!banks.error && <ErrorNotice error={banks.error} />}
        {!!belgeler.error && <ErrorNotice error={belgeler.error} />}

        {/* KURAL: tek bir «banka puanı» üretilmiyor. Metin tasarımdan birebir. */}
        <div className="banka-serit" role="note">
          Tek bir «banka puanı» üretilmiyor. Sekiz kampanya türü birbirinin
          alternatifi değil; hepsini tek sayıya toplamak, sistemin reddettiği
          türler arası sıralamayı arka kapıdan geri getirirdi.
        </div>

        <h3 className="banka-gozustu">kampanya türü başına</h3>

        {avantaj.loading && (
          <Loading label="Kampanya türü içindeki puanlar hesaplanıyor…" />
        )}
        {!!avantaj.error && <ErrorNotice error={avantaj.error} />}

        {avantaj.data && satirlar.length === 0 && (
          <EmptyNotice title="Puanlanacak kampanya türü yok">
            Korpusta skorlanabilir kampanya bulunamadı; yıldız çizilmesi için
            önce ölçülebilir bir alan gerekiyor.
          </EmptyNotice>
        )}

        {satirlar.length > 0 && (
          <div className="tur-cetveli">
            {yildizli.map((s) => (
              <YildizPuan
                key={s.tur}
                skor={s.skor}
                tur={s.tur}
                belge={s.belge}
                sira={s.sira}
                grupBuyuklugu={s.grupBuyuklugu}
                gerekce={olcutCumlesi(s.skor, etiket)}
              />
            ))}

            {skorsuzlar.map((s) => (
              <YildizPuan
                key={s.tur}
                skor={s.skor}
                tur={s.tur}
                belge={s.belge}
                sira={s.sira}
                grupBuyuklugu={s.grupBuyuklugu}
              />
            ))}

            {/* Hiç belge toplanamamış türler TEK satırda: aynı gerekçeyi n kez
                basmak, ekranı ölçülemeyen türle doldurup ölçülmüş satırları
                aşağı iterdi. Türlerin adları tam yazılır — hiçbiri düşmez. */}
            {belgesizler.length > 0 && (
              <YildizPuan
                skor={olculemedi(bank, "bu türde hiç belge toplanamadı")}
                tur={belgesizler.map((s) => s.tur).join(" · ")}
                belge={0}
                gerekce={
                  <>
                    {belgesizler.length === 1 ? (
                      <>Bu türde hiç belge toplanamadı. </>
                    ) : (
                      <>
                        Bu {belgesizler.length} türün hiçbirinde belge
                        toplanamadı.{" "}
                      </>
                    )}
                    <b className="tur-kapsama-sayi">Boş yıldız basılmıyor</b> —
                    «ölçemedik» ile «çok kötü» aynı şey değil.
                  </>
                }
              />
            )}
          </div>
        )}

        <h3 className="banka-gozustu">
          {alanToplam > 0 ? `${alanToplam} alanın durumu` : "alanların durumu"}
        </h3>

        {alanlar.loading && <Loading label="Alan listesi yükleniyor…" />}
        {!!alanlar.error && <ErrorNotice error={alanlar.error} />}

        {alanToplam > 0 && (
          <>
            <FieldChips fields={alanListesi} durumlar={durumlar} />
            {/* Açıklama yalnız EKRANDA OLAN hâlleri anlatır. Üç hâli her
                seferinde açıklamak, ilk ekranın kelime bütçesini ölçülmüş bir
                sebep olmadan harcardı (bkz. FairnessNotice «iki varyant»). */}
            <p className="alan-seridi-not">
              Alanların {alanToplam} tanesi her hâlde basılır; boş olan
              gizlenmez.
              {basilanHaller.has("bos") && (
                <>
                  {" "}
                  <span className="mono">null</span> «ölçtük, bu bankada yok»
                  demektir — sıfır değil, boş.
                </>
              )}
              {basilanHaller.has("bilinmiyor") && (
                <>
                  {" "}
                  <span className="mono">?</span> ise «ölçemedik»: alan başına
                  banka kapsaması veren bir uç yok, o yüzden yalnız{" "}
                  <span className="mono">/advantageous</span> bileşenlerinde
                  kanıtı geçen alanlar dolu sayılıyor. Kanıtsız bir alana{" "}
                  <span className="mono">null</span> basmak, ölçülmemiş bir
                  yokluk iddia etmek olurdu.
                </>
              )}
            </p>
          </>
        )}

        <FairnessNotice varyant="serit" />
      </section>

      {/* Delta görünümü bu sayfanın parçası: «tür içinde kaçıncıyım» sorusunun
          hemen ardından gelen soru «hangi alanda geride kaldım» oluyor ve iki
          ekran arasında sekme değiştirmek, öznenin aynı banka olduğunu
          kullanıcıya yeniden kurdurmak demekti. Panel burada banka seçicisini
          basmaz; sayfanın öznesi yukarıdaki künyeden gelir. */}
      {bank && (
        <BankDeltaPanel
          campaignTypes={campaignTypes}
          onInspect={onInspect}
          sabitBanka={bank}
        />
      )}
    </div>
  );
}
