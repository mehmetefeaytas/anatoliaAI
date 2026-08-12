"use client";

/**
 * Banka sayfası — tek bankanın künyesi, kampanya türü içindeki puanı ve deltası.
 *
 * İlgili: ./YildizPuan.tsx, ./BankDeltaPanel.tsx, ../styles/banka.css,
 *         ../lib/api.ts (`banks`, `stats`, `advantageous`),
 *         src/comparison/compare.py `rank_advantageous_by_type`
 *
 * ## İstenen ekran ve verilebilen puan
 *
 * İstek şuydu: «her bankanın bir sayfası olsun; içine girdiğimizde banka ile
 * ilgili bilgiler, kampanya türleri vb. kısımlarda puanı — bu puan yıldızların
 * içi dolacak şekilde olsun.» Sayfa yapıldı, yıldız da yapıldı; ama **banka
 * başına tek bir puan YOKTUR ve hesaplanamaz.**
 *
 * Gerekçe ölçülmüş bir gerçektir, üslup tercihi değil: `/advantageous`
 * bileşik skoru KAMPANYA başına ve KAMPANYA TÜRÜ İÇİNDE üretir; normalizasyon
 * grup içi sıralama tabanlıdır (`compare.py::rank_advantageous`). Farklı
 * türlerden gelen skorların ortalaması, farklı popülasyonlarda ölçülmüş
 * sıraların ortalamasıdır — matematiksel olarak tanımsızdır. Üstelik türler
 * arası kıyas adil kıyas garantisinin açıkça yasakladığı şeydir.
 *
 * İkinci ve daha sinsi sonuç: bir bankanın tüm kampanyalarını ortalamak,
 * TOPLAMA KAPSAMASINI kaliteye çevirirdi. Az belge toplanabilmiş bir banka,
 * ürünü kötü olduğu için değil verisi az olduğu için düşük puan alırdı. Kıyas
 * paneli bu hatayı zaten adıyla anıyor: «kalibre edilmemiş bir skoru kalite
 * iddiası gibi göstermek yanıltıcıdır.»
 *
 * Bu yüzden ekranda:
 *   - Yıldız HER ZAMAN bir kampanya türünün satırındadır ve türün adı yanında
 *     yazar; başlıkta, künyede, hiçbir yerde «banka puanı» yoktur.
 *   - Sunucu kapıyı kapattığında (grup < 3 ya da kapsama eşiği) yıldız
 *     ÇİZİLMEZ, gerekçe yazılır. Beş boş yıldız «çok kötü» diye okunurdu; oysa
 *     söylenen «ölçemedik».
 *
 * ## «veri kapsamı: 3 belge / 12 alan» — eksiği raporlayan etiket
 *
 * Etiket bankanın TAMAMI içindir ve öyle olması `repository.py`
 * `bank_field_coverage()` sözleşmesinin kendisidir: `belge` bankanın kampanya
 * sayısı, `alan` ise o bankada kaç ÇEŞİT bilginin çıkarılabildiğidir (üst
 * sınır 12). Tür başına alan kapsaması hiçbir uçtan gelmiyor — `/bank-delta`
 * yalnız sıralanabilir 8 alanı taşır, yani paydası 12 değildir — ve iki ayrı
 * kapsamı tek etikette karıştırmak, kimsenin denetleyemeyeceği bir sayı
 * üretirdi. Etiket her yıldız satırının yanında TEKRARLANIR; bu gürültü değil,
 * bileşenin sözü: az yıldız ile az veri aynı ekranda okunmalı.
 *
 * ## Marka varlığı uydurulmuyor
 *
 * `/banks` yalnız `slug`, `name`, `website_url`, `bddk_active` döndürür; logo
 * ve marka rengi yoktur, `public/` boştur. Amblem bankanın adından türetilen
 * baş harf monogramıdır ve rengini tema vurgusundan alır. Marka rengi seçmek
 * hem görsel bir yalan hem de marka hakkı sorunu olurdu.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import BankDeltaPanel from "./BankDeltaPanel";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import FairnessNotice from "./FairnessNotice";
import YildizPuan from "./YildizPuan";
import { api } from "../lib/api";
import type { Advantageous, BankaKapsami, CompositeScore } from "../lib/api";
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
 * Ölçülemeyen bir tür için gösterim kaydı.
 *
 * Skor `null` KALIR — burada üretilen bir puan yoktur, üretilen yalnız
 * «ölçemedik» cümlesidir. `YildizPuan` bu kaydı gördüğünde yıldız çizmez,
 * gerekçeyi basar; böylece ölçülemeyen tür ile kötü puan alan tür ekranda
 * birbirine benzemez.
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
): TurSatiri[] {
  const adlar = Array.from(
    new Set([...Object.keys(veri.types), ...turler]),
  ).sort((a, b) => a.localeCompare(b, "tr"));

  return adlar.map((ad) => {
    const grup = veri.types[ad];
    if (!grup) {
      return {
        tur: ad,
        skor: olculemedi(bank, "korpusta bu türde skorlanabilir kampanya yok"),
        sira: null,
        grupBuyuklugu: 0,
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
      };
    }

    return {
      tur: ad,
      skor: olculemedi(bank, "bu bankanın bu türde skorlanabilir belgesi yok"),
      sira: null,
      grupBuyuklugu: kiyaslanabilir.length,
    };
  });
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

  const secilenBanka = liste.find((b) => b.slug === bank);
  const bankaAdi = secilenBanka?.name ?? bank;
  const bankaKapsami = kapsam?.[bank];

  const satirlar = useMemo(
    () =>
      avantaj.data && bank
        ? turSatirlari(avantaj.data, campaignTypes, bank)
        : [],
    [avantaj.data, campaignTypes, bank],
  );

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

              {/* Eksiği raporlayan etiket — künyede bir kez, kapsamı açıkça
                  bankanın tamamı olarak. */}
              {bankaKapsami ? (
                <span className="banka-kapsam">
                  veri kapsamı: {bankaKapsami.belge} belge /{" "}
                  {bankaKapsami.alan} alan
                </span>
              ) : (
                // «Bilinmiyor», «ölçülemedi» DEĞİL: sayaç henüz gelmemiş de
                // olabilir, banka katalogda olup korpusta hiç görünmemiş de.
                // İkisini tek cümlede ayırmadan «ölçülemedi» demek, sayfanın
                // bilmediği bir şeyi iddia etmesi olurdu.
                <span className="banka-kapsam">veri kapsamı bilinmiyor</span>
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
            </div>
          </div>

          <div className="banka-secim row-tight">
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
          </div>
        </div>

        {banks.loading && <Loading label="Banka kataloğu yükleniyor…" />}
        {!!banks.error && <ErrorNotice error={banks.error} />}

        <p className="lede">
          Bu sayfada <b>banka puanı yoktur</b>: puan her zaman tek bir{" "}
          <b>kampanya türü içinde</b> verilir ve türün adı yıldızların yanında
          yazar. Farklı türlerin puanları ayrı popülasyonlarda ölçüldüğü için
          ortalamaları anlam taşımaz.
        </p>

        <FairnessNotice varyant="serit" />
      </section>

      <section className="card">
        <h2>Kampanya türü içinde puan</h2>
        <p className="lede">
          Sıra, o türdeki <b>kıyaslanabilir kampanyalar</b> arasındadır — banka
          sayısı değil. Bir bankanın aynı türde birden çok belgesi varsa en iyi
          kaydı gösterilir. Yanındaki veri kapsamı etiketi{" "}
          <b>bu bankanın tamamı</b> içindir: kaç belge toplandı ve kaç çeşit
          alan çıkarılabildi. Satırdaki <b>«düşük kapsama»</b> ise başka bir
          şeyi söyler — o kampanyanın skoru, ölçütlerin dörtte üçünden azıyla
          hesaplanmıştır.
        </p>

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
          <div className="banka-turler">
            {satirlar.map((s) => (
              <YildizPuan
                key={s.tur}
                skor={s.skor}
                tur={s.tur}
                belge={bankaKapsami?.belge}
                alan={bankaKapsami?.alan}
                sira={s.sira}
                grupBuyuklugu={s.grupBuyuklugu}
              />
            ))}
          </div>
        )}
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
