"use client";

/**
 * Karşılaştırma Paneli — bankalar arası tek alan kıyası.
 *
 * İlgili: src/api/main.py `/compare`, src/comparison/compare.py (adil kıyas),
 *         CLAUDE.md §17
 *
 * Eskiye göre ne değişti:
 *  - 3 sabit alan yerine 12 alanın tamamı (`GET /fields`).
 *  - Her satırda GÜVEN skoru + güven kaynağı + hangi KATMAN ürettiği görünür.
 *  - Değere tıklanınca kaynak metin açılır ve span vurgulanır (`SourceSpanView`).
 *  - `intent` (en düşük / en yüksek) artık gerçekten çalışır.
 *  - Çelişki taşıyan kampanyalar satırda işaretlenir.
 *  - Hata artık yutulmuyor; "veri yok" ile "API kapalı" ayrı gösteriliyor.
 *
 * GÜVEN SKORU burada JÜRİ MODUNA bağlıdır (bkz. ../lib/juryMode.tsx): bu tablo
 * ticari/bilgi arayan izleyicinin gördüğü tek yüzeydir ve kalibre edilmemiş bir
 * skoru orada kalite iddiası gibi göstermek yanıltıcıdır. Denetim yüzeyleri
 * (Audit / Canlı Çıkarım / Şeffaf Skorlama) skoru her hâlde gösterir.
 *
 * ## KAMPANYA TÜRÜ KAPISI (2026-08-09)
 *
 * Bu tablo «elma ile armut kıyaslıyor» diye bildirildi ve şikâyet yerindeydi.
 * Tür süzmesi VARDI ama varsayılanı «Tümü» idi ve `comparable` bayrağı yalnız
 * BİRİM uyumunu doğruluyordu, kampanya türünü değil. Sonuç: `vade_ay` alanında
 * 120 aylık bir **konut finansmanı** 1. sırada, 36 aylık bir **ihtiyaç
 * finansmanı** 2. sırada listeleniyordu — hiçbir uyarı olmadan.
 *
 * Çözüm süzmeyi zorunlu kılmak DEĞİL (o, veriyi gizlemek olurdu): «Tümü»
 * seçiliyken satırlar kampanya türüne göre BÖLÜMLENİYOR ve sıralama yalnız
 * bölüm içinde yapılıyor. Farklı türler hiçbir koşulda aynı sıralamaya
 * girmiyor. `compare.py:502-507` bu boşluğu kendi docstring'inde zaten
 * yazmıştı; burası onun kullanıcıya dönük karşılığı.
 *
 * ## TEK TERİM (2026-08-09)
 *
 * Yukarıdaki kapı ilk yazıldığında kavrama «ürün ailesi» deniyordu; oysa
 * ekrandaki süzgecin etiketi «Kampanya türü» idi ve kullanıcı ikisini iki
 * ayrı süzgeç sandı. Kavram tektir: `campaign_type`, 8 sınıf. Arayüzün
 * tamamında adı **kampanya türü**dür. Tanımı `FairnessNotice`'ta bir kez
 * yazılır; buradaki tablo notu ona atıf yapar, kavramı yeniden tanımlamaz.
 *
 * ## GRAFİK ÖNCE, TABLO SONRA (2026-08-12)
 *
 * Ekran grafik ağırlıklı hâle getirildi: kapsama cetveli tablonun ÜSTÜNDE,
 * tablo altında denetlenebilir ayrıntı olarak kalıyor. Cetvel `/banks`ten gelen
 * TAM banka listesini de alıyor; verisi olmayan banka kesik taban çizgisiyle
 * çizilip listede kalıyor (ölçüldü: `kar_payi_orani` 1.774 belgenin 56'sında,
 * 11 bankanın 6'sında var — grafiği yalnız `/compare` satırlarıyla çizmek beş
 * bankayı sessizce yok ederdi).
 *
 * **Grafik TEK kampanya türü çizer.** Türler arası sıralama yasak (§17) ve bir
 * ekseni paylaşan çubuklar tam da o sıralamayı ima eder. Seçenekler ikisiydi:
 * bölüm başına bir grafik, ya da seçili tür. Bölüm başına grafik seçilmedi —
 * «Tümü» hâlinde 8 tür × 11 banka ≈ 88 çubuk, yani ilk veri satırından önce
 * ~2.600 piksel; bu «grafik ağırlıklı» değil, grafik yığınıdır. Grafik seçili
 * türü çizer; «Tümü» seçiliyken EN ÇOK BANKANIN veri taşıdığı türü alır ve
 * hangi türü çizdiğini başlıkta yazar. Kalan türler tabloda bölüm bölüm durur.
 *
 * ## CANVAS ÇIKTI, KAPSAMA CETVELİ GİRDİ (2026-08-12)
 *
 * Birincil görselleştirme Chart.js tuvali değil,
 * `KapsamaCetveli` (saf DOM + CSS grid). Tuval üç şeyi birden yapamıyordu:
 * erişilebilirlik ağacında yoktu (altına ayrıca metin liste basılıyordu, yani
 * aynı bilgi iki kez), dört kapsama hâlini ayrı BİÇİMLERLE anlatamıyordu
 * (elde yalnız renk + uzunluk vardı; renk TEK sinyal olamaz, WCAG 1.4.1) ve
 * çubuk başına `aria-label` taşıyamıyordu. Cetvel üçünü de çözüyor.
 * Tuval bileşenleri (`KiyasCubuklari`, `RadarKiyas`) 2026-08-12'de silindi;
 * gerekçe `grafik/KapsamaCetveli.tsx` başlığında.
 *
 * ## EKRANIN TEK KESRİ: KAPSAMA SAYACI (2026-08-12)
 *
 * Başlığın sağında provenans şeridiyle (`.rail .rail-doktrin`) tek bir kesir
 * durur: «4 / 11 banka», altında kırılımı. Bu, ekranın iddiasını değiştiren
 * bir öğedir — soru «kim kazandı» değil, «neyi ne kadar biliyoruz». Kesir
 * GERÇEK veriden hesaplanır (`/compare` satırları + `/banks` kataloğu) ve
 * kırılımı cetvelin çubuk biçimleriyle AYNI kuraldan gelir
 * (`KapsamaCetveli.kapsamaOzeti`) — iki yerde hesaplanan bir sayı ayrışır.
 *
 * ## KAYNAK JESTİ TEK (2026-08-12)
 *
 * Satır içi kaynak çekmecesi (`openRow` + `SourceDrawer`) kaldırıldı; yerine
 * her yüzeyde aynı olan `KaynakDipnotu` geldi. Çekmece tabloyu iterek açılıyor
 * ve kullanıcı okuduğu satırı kaybediyordu; yan panel tabloyu yerinde bırakıp
 * iddia ile kanıtı aynı ekranda tutuyor. Gerekçenin tamamı KaynakDipnotu.tsx
 * başlığında.
 *
 * ## TÜR SÜZGECİ ALANA GÖRE BUDANIR (2026-08-13)
 *
 * Süzgeç 8 türün tamamını her alan için basıyordu, oysa tür kapsaması alandan
 * alana değişiyor (ölçüldü, `data/demo.db`, 1.774 belge): `kar_payi_orani` 7
 * tür, `tahsis_ucreti` yalnız 4. `tahsis_ucreti` + `Finansman` seçen kullanıcı
 * hiçbir uyarı olmadan boş ekran alıyordu — yani süzgeç, ekranın ölçemediği bir
 * şeyi ölçebilirmiş gibi sunuyordu. Artık liste SEÇİLİ ALANDA veri taşıyan
 * türlere inip alan değişince yeniden hesaplanıyor. Karar mantığı saf tutuldu
 * (`../lib/turBudama.ts`); ayrı dosya olmasının nedeni testin `.tsx` içe
 * alamaması, gerekçesi o dosyanın başlığında.
 *
 * Dört ayrıntı, dördü de bilinçli:
 *
 *  - **Budama sessiz değil.** Düşen türler süzgecin altında ADIYLA sayılıyor.
 *    Bu ekranın doktrini «boşluğu gizleme, say»; budama tek başına o doktrini
 *    ihlal ederdi, düşen türler satırı onu geri veriyor. Reddedilen seçenek —
 *    türü listede pasif bırakmak — doktrine daha sadikti ama istenen
 *    sadeleşmeyi vermiyordu.
 *  - **Bağımlılık dizisi YALNIZ `field`.** Seçenek sorgusu `intent` ve `type`
 *    almıyor: `intent` sıralamayı değiştirir, satır KÜMESİNİ değil; `per_bank`
 *    ise `best` ve `all` hâllerinde aynı tür kümesini döndürüyor (`best`,
 *    banka+tür çifti başına en iyi satırı tutuyor, türü düşürmüyor — ölçüldü).
 *    `type` ile bağlamak ise kendini yiyen bir döngü olurdu: tür seçilince
 *    liste o tek türe inerdi.
 *  - **Tabloyu besleyen sorgu DEĞİŞMEDİ.** Süzme sunucuda kalıyor. İstemci
 *    tarafı süzme denendi ve reddedildi: satır kümesi aynı çıkıyor ama sunucu
 *    `rank`'i süzülmüş küme üzerinden numaralıyor (ölçüldü: `kar_payi_orani` +
 *    `Kart`, Kuveyt Türk `rank` 3 yerine 5). `turlereBol()` sırayı bölüm içinde
 *    zaten yeniden verdiği için ekranda fark görünmezdi — istenmemiş bir
 *    davranış değişikliğini görünmez diye kabul etmek daha kötüsü.
 *  - **Ölçemediğimizde budama YOK.** Seçenek sorgusu yüklenirken ya da hata
 *    verdiğinde tam liste basılır ve seçili tür korunur. Yanıt gelmediği için
 *    boş görünen bir küme «o tür bu alanda yok» demek değildir; ölçülemeyen bir
 *    yokluğu yokluk gibi göstermek bu ekranın reddettiği hatanın ta kendisi.
 *
 * **Alan çipleri budanmaz.** `FieldChips` başlığındaki «12 alanın 12'si her
 * hâlde basılır, boş olan gizlenmez» vaadi bağlayıcıdır: alan seçmek ölçüm
 * yüzeyini seçmektir, tür seçmek o yüzeyi daraltmaktır.
 */

import { Fragment, useEffect, useState } from "react";
import { api } from "../lib/api";
import type {
  BankaKapsami,
  CompareRow,
  FieldMeta,
  PerBank,
} from "../lib/api";
import {
  extractorClass,
  extractorLabel,
  formatValue,
  trNum,
} from "../lib/format";
import { useJuryMode } from "../lib/juryMode";
import { turSecenekleri } from "../lib/turBudama";
import { useAsync } from "../lib/useAsync";
import ConfidenceBadge from "./ConfidenceBadge";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import FairnessNotice from "./FairnessNotice";
import FieldChips from "./FieldChips";
import GrafikIskeleti from "./grafik/GrafikIskeleti";
import KatilmaPanel from "./KatilmaPanel";
import KapsamaCetveli, {
  kapsamaOzeti,
  satirHali,
} from "./grafik/KapsamaCetveli";
import KaynakDipnotu from "./KaynakDipnotu";
import ScoringExplainer from "./ScoringExplainer";
import UrunTablosuPanel from "./UrunTablosuPanel";

type Intent = "" | "lowest" | "highest";

const INTENTS: { key: Intent; label: string }[] = [
  { key: "", label: "Alanın doğal yönü" },
  { key: "lowest", label: "En düşük önce" },
  { key: "highest", label: "En yüksek önce" },
];

type Props = {
  fields: FieldMeta[];
  campaignTypes: string[];
  /**
   * Dışarıdan gelen kampanya türü süzgeci — komut paletinden bir tür
   * seçildiğinde kullanılır.
   *
   * Tür bir EKRAN değil bir SÜZGEÇTİR: palette «Konut Finansmanı» seçen
   * kullanıcıyı ayrı bir sayfaya götürmek yerine, aradığı şeyin kıyaslandığı
   * yere bırakıp süzgeci onun adına ayarlamak doğru olan. Değer değişince
   * yerel duruma yazılır; sonrasında kullanıcı süzgeci serbestçe değiştirir.
   */
  baslangicTuru?: string | null;
  /**
   * Banka slug → belge/alan kapsamı (`/stats` → `banka_kapsami`).
   *
   * Cetveldeki «veri yok · 291 belge» etiketi bundan yazılır: belge sayısı
   * olmadan o satır «hiç bakmadık» diye okunurdu, oysa 291 belge tarandı ve
   * alan geçmedi. `BankaSayfasi` aynı veriyi aynı biçimde alıyor.
   *
   * `undefined` = çağıran bu veriyi HİÇ bağlamadı; bileşen `/stats`i kendisi
   * okur (yedek yol). `null` = çağıran bağladı ama veri henüz yok/alınamadı;
   * o hâlde sayı UYDURULMAZ, yalnız «veri yok» yazılır.
   */
  kapsam?: Record<string, BankaKapsami> | null;
};

/** Türü boş gelen satırların bölüm başlığı. */
const TURSUZ = "Türü belirlenemedi";

/**
 * Satırları kampanya türüne böler ve her bölüm içinde SIRA NUMARASINI yeniden
 * verir.
 *
 * Sunucu `rank`'i tüm sonuç kümesi üzerinden hesaplar; tek tür seçiliyken bu
 * zaten bölüm-içi sıradır. «Tümü» seçiliyken ise bir bölümün başında «5»
 * yazması kafa karıştırıcı olurdu — ve daha kötüsü, türler arasında bir
 * sıralama varmış izlenimi verirdi. Sıra bölüm içinde yeniden numaralanır;
 * `rank === null` olan (kıyaslanamaz) satırlar numara ALMAZ.
 */
function turlereBol(
  rows: CompareRow[],
): { tur: string; satirlar: { row: CompareRow; sira: number | null }[] }[] {
  const bolumler = new Map<string, { row: CompareRow; sira: number | null }[]>();
  for (const row of rows) {
    const tur = row.campaign_type || TURSUZ;
    const liste = bolumler.get(tur) ?? [];
    liste.push({ row, sira: null });
    bolumler.set(tur, liste);
  }
  return Array.from(bolumler, ([tur, satirlar]) => {
    let konum = 0;
    return {
      tur,
      satirlar: satirlar.map(({ row }) => ({
        row,
        sira: row.rank === null ? null : ++konum,
      })),
    };
  });
}

/**
 * Kapsam satırı mı — bankanın bu ailede belgesi var, bu alanda kaydı yok.
 *
 * Sunucu bu satırları `campaign_id: null` ile gönderir (`/compare`, kapsam
 * kapısı). Ayırt etmek gerekiyor çünkü satırın bir KAYNAĞI yoktur: dipnot
 * rozeti «#null» belgesini açmaya çalışırdı.
 *
 * `CompareRow.campaign_id` tipi henüz `number` (dar); daraltma bu yüzden
 * dönüştürmeyle yapılıyor. Tipin `number | null` olarak genişletilmesi
 * `lib/api.ts` sahibinin işidir — genişleyince bu dönüştürme silinebilir.
 */
function kapsamSatiri(row: CompareRow): boolean {
  return (row.campaign_id as number | null) === null;
}

export default function ComparePanel({
  fields,
  campaignTypes,
  baslangicTuru,
  kapsam,
}: Props) {
  const [field, setField] = useState(fields[0]?.field ?? "kar_payi_orani");
  const [intent, setIntent] = useState<Intent>("");
  const [type, setType] = useState(baslangicTuru ?? "");

  // Palet açıkken kullanıcı ikinci kez tür seçebilir; o zaman bileşen zaten
  // takılı olduğu için `useState` başlangıcı yeniden çalışmaz. Değer
  // değiştiğinde süzgeç güncellenir — sonrası yine kullanıcının.
  useEffect(() => {
    if (baslangicTuru) setType(baslangicTuru);
  }, [baslangicTuru]);
  const [perBank, setPerBank] = useState<PerBank>("best");
  const { jury } = useJuryMode();

  const rows = useAsync(
    () => api.compare(field, intent || undefined, type || undefined, perBank),
    [field, intent, type, perBank],
  );
  // SEÇENEK LİSTESİ İÇİN İKİNCİ SORGU. Tabloyu besleyen `rows` kullanılamaz:
  // bir tür seçiliyken o sorgu yalnız o türün satırlarını döndürür, yani liste
  // seçime göre kendini yer. Bu sorgu süzülmemiş kümeyi okur ve YALNIZ `field`e
  // bağlıdır (gerekçe dosya başlığında). Fazladan bir tur atıyor; alternatifi,
  // bir süzgecin kendi seçenek kümesini kendi seçimiyle daraltmasıydı.
  const turKaynagi = useAsync(
    () => api.compare(field, undefined, undefined, "best"),
    [field],
  );
  const turSecenek = turSecenekleri(campaignTypes, turKaynagi);
  /**
   * Budama yüzünden geri alınan tür adı — uyarı metni bunu yazar.
   *
   * Sessiz sıfırlama yasak: kullanıcı «Kart» seçiliyken başka bir alana
   * geçtiğinde süzgecin kendi kendine «Tümü»ye dönmesi, arayüzün kullanıcının
   * seçimini gizlice yediği izlenimini verirdi. Uyarı bir SONRAKİ kullanıcı
   * etkileşimine kadar durur (bkz. `etkilesim`) — zamanlayıcıyla kaybolan bir
   * bildirim, okumaya yetişemeyen kullanıcı için hiç basılmamış sayılır.
   */
  const [turUyarisi, setTurUyarisi] = useState<string | null>(null);

  // Seçili tür budandıysa süzgeç «Tümü»ye alınır. Sıra önemli: kullanıcı alanı
  // değiştirdiğinde `etkilesim()` uyarıyı önce siler, yanıt gelince bu etki
  // YENİ alanın uyarısını basar — yani ekranda her zaman en son ölçümün sözü
  // durur. Budama yapılmadıysa (yükleniyor/hata) seçim ASLA bozulmaz.
  const listeAnahtari = turSecenek.liste.join(" ");
  useEffect(() => {
    if (!turSecenek.budandi) return;
    if (!type || turSecenek.liste.includes(type)) return;
    setType("");
    setTurUyarisi(type);
    // `liste` her render'da yeni bir dizi olarak kurulur; bağımlılık olarak
    // İÇERİĞİ (`listeAnahtari`) izlenir — kimlik değişimi tek başına bu etkiyi
    // her render'da koşturmak demekti.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [turSecenek.budandi, listeAnahtari, type]);

  /**
   * Kullanıcının süzgeçlere her dokunuşu tür uyarısını kapatır.
   *
   * «Sonraki etkileşime kadar durur» kuralının karşılığı burası: uyarıyı
   * kapatmak için ayrı bir × düğmesi konmadı, çünkü kullanıcının bildirimi
   * onayladığının en güvenilir kanıtı bir sonraki süzgeç hareketidir.
   */
  const etkilesim = () => setTurUyarisi(null);
  // Banka kataloğu cetvelin «veri yok» satırları için; `/compare` yalnız değer
  // TAŞIYAN satırları döndürdüğü için eksik bankalar ancak buradan bilinir.
  const banks = useAsync(() => api.banks(), []);
  // Belge sayaçları için YEDEK yol: `kapsam` propu hiç bağlanmadıysa (undefined)
  // `/stats` buradan okunur. Prop bağlıysa istek HİÇ atılmaz — sayfa o çağrıyı
  // zaten yapıyor ve ikinci bir tur boşuna olurdu (bkz. `Props.kapsam`).
  const kapsamYok = kapsam === undefined;
  const stats = useAsync(
    () => (kapsamYok ? api.stats() : Promise.resolve(null)),
    [kapsamYok],
  );
  const bankaKapsami = kapsam ?? stats.data?.banka_kapsami ?? null;
  const meta = fields.find((f) => f.field === field);
  const bolumler = turlereBol(rows.data ?? []);
  // Sütun sayısı: Sıra, Banka, Değer, Ham ifade, [Güven], Katman, Durum,
  // Kaynak.
  const sutunSayisi = jury ? 8 : 7;

  // Grafiğe giden bölüm: tek tür seçiliyse o, «Tümü» ise en çok bankanın veri
  // taşıdığı tür (gerekçe dosya başlığında). Eşitlikte ilk gelen kazanır —
  // sunucunun sırası korunur, burada yeniden sıralama yapılmaz.
  const grafikBolumu =
    bolumler.length === 0
      ? null
      : bolumler.reduce((en, b) => (b.satirlar.length > en.satirlar.length ? b : en));

  // CETVEL VE KAPSAMA SAYACI kapsam satırlarını GÖRMEZ.
  //
  // `/compare` artık alanı hiç olmayan bankalar için de satır gönderiyor
  // (kapsam kapısı). Tablo için doğrusu budur — şartnamenin s.11–12 tablosu
  // eksik hücreli satırları gösteriyor. Ama iki tüketici bu satırları YANLIŞ
  // sayardı: `kapsamaOzeti` her tekrarsız bankayı «kapsanan» sayıyor (kesir
  // şişerdi) ve `satirHali` değeri olmayan satırı «koşullu» diye
  // sınıflandırırdı — ölçülmemiş bir hâli ölçülmüş bir hâlin kovasına yazmak
  // olurdu. Cetvelin «ölçülemedi» bölümü de bu bankaları kendi yolundan
  // (belge sayacıyla) zaten çiziyor; iki kez basılırlardı.
  const grafikSatirlari =
    grafikBolumu?.satirlar.filter(({ row }) => !kapsamSatiri(row)) ?? [];
  // Kapsama kesri GERÇEK veriden gelir, sabit yazılmaz: pay `/compare`
  // satırlarındaki tekrarsız banka sayısı, payda `/banks` kataloğunun boyu.
  // Katalog okunamadıysa payda UYDURULMAZ — kesir hiç basılmaz.
  const ozet = grafikBolumu ? kapsamaOzeti(grafikSatirlari) : null;
  const toplamBanka = banks.data?.length ?? null;

  // GÖRÜNÜM ANAHTARI (2026-08-16). Şartname s.11–12 çıktıyı bir tabloyla
  // tarif ediyor: banka başına TEK satır, YEDİ kolon. Bu, aşağıdaki tablonun
  // devriğidir (o: tek alan × çok banka) ve onun YERİNE GEÇMEZ — tek alanlı
  // görünüm sıralar ve sıralamanın denetimini taşır (kanıt, güven, katman,
  // sıra rozeti), ürün tablosu sıralamaz ve bir bankanın bir üründe ilan
  // ettiği her şeyi tek satırda gösterir.
  //
  // Varsayılan BİLEREK tek alanlı görünüm: bu ekranın bugünkü kullanıcıları
  // (ve tüm derin bağlantıları) onu bekliyor; yeni bir görünümü varsayılan
  // yapmak, kimsenin istemediği bir taşınma olurdu.
  //
  // Anahtar ayrı bir SEKME değil çünkü ikisi aynı soruyu iki biçimde
  // cevaplıyor: «bankalar bu üründe ne veriyor». Ayrı sekme, kullanıcıya
  // bunları iki ayrı araç olarak sunardı.
  //
  // ÜÇÜNCÜ GÖRÜNÜM — katılma hesabı oranları (2026-08-24).
  //
  // Eskiden ayrı bir sekmeydi. Aynı gerekçe onu da buraya taşıdı: sorduğu
  // soru bu panelinkiyle AYNI («hangi banka daha iyi veriyor»), yalnız
  // kaynağı farklı — TKBB'nin haftalık yayını, kampanya korpusu değil.
  // Ayrı sekme, kullanıcıya iki ayrı araç varmış izlenimi veriyordu.
  //
  // Kaynak farkı GİZLENMİYOR, seçeneğin adında yazıyor. İki büyüklüğün
  // (getiri ↔ pay) karışmaması ise panelin kendi işi; ayrımı o basıyor.
  const [gorunum, setGorunum] = useState<"alan" | "tablo" | "katilma">("alan");

  const gorunumSecici = (
    <div className="row-tight" role="group" aria-label="Görünüm">
      <span className="mono muted">görünüm</span>
      <label className="row-tight" htmlFor="gorunum-alan">
        <input
          id="gorunum-alan"
          type="radio"
          name="kiyas-gorunum"
          checked={gorunum === "alan"}
          onChange={() => setGorunum("alan")}
        />
        <span>Tek alan kıyası</span>
      </label>
      <label className="row-tight" htmlFor="gorunum-tablo">
        <input
          id="gorunum-tablo"
          type="radio"
          name="kiyas-gorunum"
          checked={gorunum === "tablo"}
          onChange={() => setGorunum("tablo")}
        />
        <span>Ürün tablosu (şartname s.12)</span>
      </label>
      <label className="row-tight" htmlFor="gorunum-katilma">
        <input
          id="gorunum-katilma"
          type="radio"
          name="kiyas-gorunum"
          checked={gorunum === "katilma"}
          onChange={() => setGorunum("katilma")}
        />
        <span>Katılma hesabı oranları (TKBB)</span>
      </label>
    </div>
  );

  if (gorunum === "katilma") {
    return (
      <div className="stack">
        {gorunumSecici}
        <KatilmaPanel />
      </div>
    );
  }

  if (gorunum === "tablo") {
    return (
      <div className="stack">
        {gorunumSecici}
        <UrunTablosuPanel
          fields={fields}
          type={type}
          campaignTypes={campaignTypes}
          onTypeChange={(t) => {
            etkilesim();
            setType(t);
          }}
        />
      </div>
    );
  }

  return (
    <div className="stack">
      {gorunumSecici}
      <section className="card">
        {/* Başlık artık «Karşılaştırma Paneli» değil: sekme adı bunu zaten
            söylüyordu ve başlığın taşıyabileceği en değerli iki bilgi —
            HANGİ ALAN ve HANGİ TÜR kıyaslanıyor — hiçbir yerde yazmıyordu. */}
        <div className="cetvel-kabuk">
          <div className="cetvel-ust">
            <h2>
              {meta?.label ?? field}
              {grafikBolumu ? ` · ${grafikBolumu.tur}` : ""}
            </h2>
            {/* Alan adı ve sıralama yönü MAKİNE verisidir: birincisi
                `extracted_fields.field_name` sütununun değeri, ikincisi
                `compare.py`nin `_LOWER_IS_BETTER` / `_HIGHER_IS_BETTER`
                kümelerinden geliyor. Türkçe bir cümle değil, bir etiket. */}
            <span
              className="cetvel-alan"
              title="Kaynak: compare.py _LOWER_IS_BETTER / _HIGHER_IS_BETTER"
            >
              alan: {field}
              {meta ? ` · yön: ${meta.direction_label}` : ""}
            </span>
          </div>

          {ozet && toplamBanka !== null && (
            <div className="kapsama-sayaci rail rail-doktrin">
              <span className="kapsama-etiket">kapsama</span>
              <span className="kapsama-kesir">
                {trNum(ozet.kapsanan)} / {trNum(toplamBanka)} banka
              </span>
              {/* Kapsanan 4 bankanın hepsi aynı şey değildir: biri sıralamaya
                  girer, üçü gerekçesiyle listede kalır. Kesir tek başına bu
                  ayrımı gizlerdi. */}
              <span className="kapsama-kirilim">
                kıyaslanabilir: {trNum(ozet.kiyaslanabilir)} · aralık:{" "}
                {trNum(ozet.aralik)} · koşullu: {trNum(ozet.kosullu)}
              </span>
            </div>
          )}
        </div>

        {/* Buradaki `lede` KALDIRILDI (2026-08-11). İki cümlesi de — «yalnız
            aynı birime normalize edilmiş değerler kıyaslanır» ve
            «kıyaslanamayan değer silinmez» — adil kıyas şeridinin ilk
            satırında zaten yazıyor. Ölçüm: ilk veri satırından önce basılan
            ~400 kelimeyi düşürmek için önce TEKRARLAR atıldı; aynı kuralı iki
            kez okumak kimseye bir şey öğretmiyordu.

            Aynı gerekçeyle, cetvelin «adil kıyas gerekçesi» katlaması AYRI bir
            `<details>` olarak yazılmadı: v2 tasarımının üç paragrafından ikisi
            (%0 ceza değil / türler arası sıralama üretilmez) bu şeridin
            açılınca gösterdiği metnin ta kendisi. Üçüncüsü — verisi olmayan
            banka listeden düşmez — şeritte YOKTU ve bu yüzeye özgü; `ek`
            olarak eklendi. Kural cetvelde ayrıca GÖRÜNÜR biçimde de
            duruyor: «ölçülemedi · N banka» ayırıcı satırı. */}
        <FairnessNotice
          varyant="serit"
          ek={
            <>
              <b>Verisi olmayan banka listeden düşmez.</b> On bir satırın on biri
              her zaman çizilir; ölçülemeyen satır kesik taban çizgisi ve{" "}
              <span className="mono">veri yok</span> etiketiyle yerini korur.
              Boşluk gizlenmiyor, sayılıyor — cetvelin başındaki kapsama kesri
              tam olarak bunu ölçer.
            </>
          }
        />

        {/* Çipler budanmaz (bkz. dosya başlığı); yalnız tür uyarısını kapatır. */}
        <FieldChips
          fields={fields}
          value={field}
          onChange={(f) => {
            etkilesim();
            setField(f);
          }}
        />

        <div className="row" style={{ marginTop: 12 }}>
          <div className="row-tight">
            <label className="small muted" htmlFor="cmp-intent">
              Sıralama
            </label>
            <select
              id="cmp-intent"
              className="select"
              style={{ width: "auto" }}
              value={intent}
              onChange={(e) => {
                etkilesim();
                setIntent(e.target.value as Intent);
              }}
            >
              {INTENTS.map((i) => (
                <option key={i.key} value={i.key}>
                  {i.label}
                </option>
              ))}
            </select>
          </div>
          <div className="row-tight">
            {/* Etiket bilinçli olarak «süzgeci» ile bitiyor: hemen üstündeki
                alan çipleriyle karıştırılıyordu. Çipler NEYİN kıyaslanacağını
                seçer, bu süzgeç KİMİN kıyaslanacağını daraltır. */}
            <label className="small muted" htmlFor="cmp-type">
              Kampanya türü süzgeci
            </label>
            <select
              id="cmp-type"
              className="select"
              style={{ width: "auto" }}
              value={type}
              onChange={(e) => {
                etkilesim();
                setType(e.target.value);
              }}
            >
              <option value="">Tümü (türe göre bölümlenir)</option>
              {/* Liste ALANA GÖRE budanmış hâlidir; sıra `campaignTypes`
                  propunun kanonik sırasıdır, yanıttan yeniden üretilmez. */}
              {turSecenek.liste.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div className="row-tight">
            <label className="small muted" htmlFor="cmp-perbank">
              Banka başına
            </label>
            <select
              id="cmp-perbank"
              className="select"
              style={{ width: "auto" }}
              value={perBank}
              onChange={(e) => {
                etkilesim();
                setPerBank(e.target.value as PerBank);
              }}
            >
              <option value="best">En iyi kampanya (tek satır)</option>
              <option value="all">Tüm kampanyaları göster</option>
            </select>
          </div>
          {/* Yön rozeti KALDIRILDI: aynı bilgi başlığın altındaki makine
              satırında («yön: düşük daha avantajlı») zaten yazıyor ve süzgeç
              şeridinin sonunda ikinci kez basılması, süzgeç gibi görünen ama
              tıklanmayan bir öğe üretiyordu. */}
        </div>

        {/* DÜŞEN TÜRLER — budamanın makbuzu. Sayı ve adlar birlikte verilir:
            yalnız sayı «neyi kaybettim» sorusunu cevaplamaz, yalnız adlar ise
            kaybın büyüklüğünü göstermez. Hiç tür düşmediyse satır BASILMAZ —
            «0 tür düştü» diye bir bilgi yoktur, gürültü vardır. */}
        {turSecenek.dusen.length > 0 && (
          <p className="small muted" style={{ marginTop: "var(--sp-2)" }}>
            {trNum(turSecenek.dusen.length)} tür bu alanda veri taşımıyor,
            listeden düştü: {turSecenek.dusen.join(" · ")}
          </p>
        )}

        {/* Geri alınan seçimin bildirimi. `role="status"` çünkü bu, kullanıcının
            YAPMADIĞI bir değişikliktir; ekran okuyucu bunu görsel değişiklikle
            aynı anda duymalı. */}
        {turUyarisi && (
          <p className="small" role="status" style={{ marginTop: "var(--sp-2)" }}>
            «{turUyarisi}» bu alanda veri taşımıyor; süzgeç Tümü&apos;ne alındı.
          </p>
        )}

        <div style={{ marginTop: "var(--sp-4)" }}>
          {/* YÜKLENİYOR: banka adları ve satır sayısı hemen basılır, yalnız
              çubuklar bekler. Hiçbir sayı, hiçbir sıra numarası, hiçbir
              animasyonlu sayaç görünmez — gerekçe GrafikIskeleti başlığında. */}
          {rows.loading && (
            <>
              <Loading label="Kıyas satırları yükleniyor…" />
              <GrafikIskeleti
                bankalar={banks.data?.map((b) => b.name)}
                yukseklik={(banks.data?.length ?? 8) * 32 + 32}
              />
            </>
          )}
          {!!rows.error && <ErrorNotice error={rows.error} />}
          {!rows.loading && !rows.error && rows.data?.length === 0 && (
            <EmptyNotice title="Bu alan için kayıt bulunamadı">
              API çalışıyor ve yanıt verdi, ancak seçilen alan
              {type ? ` ve «${type}» türü` : ""} için çıkarılmış değer yok. Bu bir
              hata değil: alan metinlerde geçmiyorsa sistem değer UYDURMAZ.
            </EmptyNotice>
          )}
          {/* CETVEL ÖNCE — ekranın taşıyıcı öğesi bu. Tablo altında kalır ve
              denetlenebilir ayrıntıyı verir. */}
          {rows.data && rows.data.length > 0 && grafikBolumu && (
            <>
              <KapsamaCetveli
                satirlar={grafikSatirlari}
                bankalar={banks.data ?? undefined}
                alan={field}
                kapsam={bankaKapsami}
              />
              {bolumler.length > 1 && (
                <p className="small muted">
                  Cetvel yalnız <b>{grafikBolumu.tur}</b> türünü çizer: en çok
                  bankanın bu alanda veri taşıdığı tür. Farklı türler tek eksene
                  konmaz — yan yana duran çubuklar, sistemin reddettiği türler
                  arası sıralamayı ima ederdi. Diğer {bolumler.length - 1} tür
                  aşağıdaki tabloda bölüm bölüm durur; cetveli başka bir türe
                  almak için üstteki «Kampanya türü süzgeci»ni kullanın.
                </p>
              )}
              {!!banks.error && (
                <p className="small muted">
                  Banka kataloğu (<span className="mono">/banks</span>)
                  okunamadı; cetvelde yalnız değer taşıyan bankalar var. Verisi
                  olmayan bankaların satırları ve kapsama kesri bu turda
                  çizilemedi — kesir uydurulmuyor, hiç basılmıyor.
                </p>
              )}
            </>
          )}

          {rows.data && rows.data.length > 0 && (
            <div className="table-wrap">
              <table className="data stackable">
                <caption
                  className="small muted"
                  style={{
                    captionSide: "bottom",
                    textAlign: "left",
                    paddingTop: "var(--sp-2)",
                  }}
                >
                  {/* «Türler arasında sıralama yapılmaz» cümlesi buradan
                      çıkarıldı: adil kıyas şeridi onu tablodan ÖNCE zaten
                      söylüyor. Kalan bilgiler şeritte yok ve tabloya özgü. */}
                  Cetveldeki AYNI satırlar, denetlenebilir hâlde.{" "}
                  <span className="mono">¶</span> rozetine basınca belge yandan
                  açılır ve değerin kaynak metindeki karakter aralığı
                  vurgulanır; tablo yerinde kalır. Rozetteki sayı o aralığın
                  kendisidir. «Ham ifade» sütunu bankanın kendi yazdığı metni
                  tırnaklı yazıyla verir — normalize edilmiş değerin nereden
                  geldiği orada okunur. Satırın kampanya türü bölüm başlığında
                  yazar; üstteki «Kampanya türü süzgeci» listeyi tek türe
                  indirir.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Sıra</th>
                    <th scope="col">Banka</th>
                    <th scope="col">Değer</th>
                    <th scope="col">Ham ifade</th>
                    {jury && <th scope="col">Güven</th>}
                    <th scope="col">Katman</th>
                    <th scope="col">Durum</th>
                    <th scope="col">Kaynak</th>
                  </tr>
                </thead>
                <tbody>
                  {bolumler.map((bolum) => {
                    return (
                      <Fragment key={bolum.tur}>
                        {/* Bölüm başlığı yalnız birden fazla tür varsa gerekli;
                            tek tür seçiliyken gereksiz bir katman olurdu.
                            «Kampanya türü:» öneki bilinçli: başlıkta çıplak bir
                            ürün adı görünce kullanıcı onu bir banka ürünü
                            zannediyordu, oysa bir SINIF adıdır. */}
                        {bolumler.length > 1 && (
                          <tr className="group-head">
                            <td colSpan={sutunSayisi}>
                              Kampanya türü: {bolum.tur} ·{" "}
                              {bolum.satirlar.length} banka
                            </td>
                          </tr>
                        )}
                        {bolum.satirlar.map(({ row, sira }, i) => (
                          <Satir
                            key={`${row.campaign_id}-${bolum.tur}-${i}`}
                            row={row}
                            sira={sira}
                            field={field}
                            jury={jury}
                          />
                        ))}
                        {/* İSTEMCİ TARAFI «eksik bankalar» SATIRI KALDIRILDI
                            (2026-08-16). Burada `/banks` kataloğundaki her
                            banka, o bölümde satırı yoksa «değer çıkarılamadı»
                            diye tek bir toplu satıra yazılıyordu. Üç kusuru
                            vardı:

                             1. KAPSAM YANLIŞTI. Katalog TÜM bankalardır; o
                                ürün ailesinde hiç kampanyası olmayan banka da
                                «değer çıkarılamadı» sayılıyordu. Bu, `/bank-
                                delta`nın özenle ayırdığı `eksik_urun` ile
                                `eksik_veri`yi tek etikette topluyordu — yani
                                olmayan bir ürün eksikliği iddiası.
                             2. GEREKÇE ÖLÇÜLMEMİŞTİ. «alan metinde geçmiyor»
                                deniyordu; bilinen tek şey alanın
                                ÇIKARILAMADIĞIdır, metinde geçip geçmediği
                                değil.
                             3. DEĞER HÜCRESİ «null» BASIYORDU — makine jetonu,
                                üstelik şartnamenin beklediği «Belirtilmemiş»
                                biçiminin (s.11–12) yerine.

                            Satırları artık SUNUCU üretiyor (`/compare` kapsam
                            kapısı): kapsam, bankanın o ailede gerçekten belgesi
                            olup olmadığından okunur ve her banka kendi satırını
                            alır. Karar tek yerde — bu depoda «aynı karar iki
                            yerde» hatası beş kez pahalıya mal oldu. */}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      <ScoringExplainer field={field} type={type} />
    </div>
  );
}

function Satir({
  row,
  sira,
  field,
  jury,
}: {
  row: CompareRow;
  /** Kampanya türü İÇİNDEKİ sıra; kıyaslanamaz satırlarda null. */
  sira: number | null;
  field: string;
  /** Jüri modu — güven sütunu yalnız açıkken basılır. */
  jury: boolean;
}) {
  return (
    <>
      <tr>
        <td data-label="Sıra" className="num">
          <span className={`rank-pill${sira === 1 ? " first" : ""}`}>
            {sira ?? "—"}
          </span>
        </td>
        <td data-label="Banka">
          {row.bank_name || row.bank}
          {/* Elenen kampanyalar gizlenmiyor, SAYILIYOR. Tamamı «Tüm
              kampanyaları göster» ile alınabilir. */}
          {row.other_count > 0 && (
            <div className="small faint">
              +{row.other_count} kampanya daha
            </div>
          )}
        </td>
        <td data-label="Değer" className="num">
          <strong>{formatValue(row.value, field)}</strong>
        </td>
        {/* HAM İFADE kendi sütununa çıktı ve TIRNAKLI yazıya geçti.
            Önceden değerin altında mono fısıltı olarak duruyordu, yani
            bankanın kendi cümlesi makine verisiyle aynı sesle basılıyordu.
            Oysa üç sesin ayrımı bu ürünün tezinin görsel karşılığı: mono
            makine, tırnaklı yazı BANKA (bkz. tokens.css, "ÜÇ SES"). Sütun
            olması ayrıca kıyası mümkün kılıyor — «Vade Kar Oranı» ile
            «vade ve kar oranı» aynı alanı doldurup farklı yazılmış. */}
        <td data-label="Ham ifade" className="cetvel-ham">
          {row.raw_value ? (
            `«${row.raw_value.trim()}»`
          ) : (
            <span className="mono faint">ham ifade kaydedilmemiş</span>
          )}
        </td>
        {jury && (
          <td data-label="Güven">
            <ConfidenceBadge value={row.confidence} source={row.confidence_source} />
            <div className="conf-src">{row.confidence_source ? `kaynak: ${labelOf(row.confidence_source)}` : "kaynak: kaydedilmedi"}</div>
          </td>
        )}
        <td data-label="Katman">
          <span className={extractorClass(row.extractor)}>
            {extractorLabel(row.extractor)}
          </span>
        </td>
        <td data-label="Durum">
          {row.comparable ? (
            <span className="badge badge-ok">kıyaslanabilir</span>
          ) : (
            /* Gerekçe SUNUCUNUN sözüdür (`compare.py` → `note`); istemci onu
               yeniden yazmaz. Yalnız `note` hiç gelmediğinde satırın hâline
               göre bir gerekçe basılır — «kıyaslanamaz» tek başına neden
               kıyaslanamadığını söylemiyordu. */
            <span className="badge badge-warn" title={row.note ?? ""}>
              {row.note ??
                (satirHali(row) === "aralik"
                  ? "aralık — doğrudan kıyaslanamaz"
                  : "koşullu oran (kanal/müşteri/taban)")}
            </span>
          )}
          {row.campaign_status === "expired" && (
            <div style={{ marginTop: "var(--sp-1)" }}>
              <span
                className="badge badge-expired"
                title="Kampanya sayfası kendi bitişini ilan ediyor ya da arşivde. Değer görünür kalır, sıralamaya girmez."
              >
                süresi dolmuş
              </span>
            </div>
          )}
          {row.contradiction_count > 0 && (
            <div style={{ marginTop: "var(--sp-1)" }}>
              <span className="badge badge-bad">
                {row.contradiction_count} çelişki
              </span>
            </div>
          )}
        </td>
        <td data-label="Kaynak">
          {/* Her yüzeydeki AYNI jest: rozete bas, belge yandan açılsın, değerin
              aralığı vurgulu olsun. `CompareRow` zaten `SpanInfo`'yu taşıdığı
              için satırın kendisi span olarak geçilebiliyor.

              KAPSAM SATIRLARINDA dipnot YOKTUR: gösterilecek bir kaynak
              belgesi yok, çünkü bu alanda hiç çıkarım kaydı yok. Rozeti yine
              de basmak «#null» diye bir belge açmaya çalışırdı. */}
          {kapsamSatiri(row) ? (
            <span className="mono faint">kaynak yok</span>
          ) : (
            <KaynakDipnotu
              campaignId={row.campaign_id}
              span={row}
              rawValue={row.raw_value}
            />
          )}
          {/* Karakter aralığı rozetin YÜZÜNDE zaten yazıyor (`¶ 1284–1298`):
              `KaynakDipnotu` etiket verilmediğinde span'i basıyor. Buraya
              ikinci bir ofset satırı eklemek aynı sayıyı iki kez basmaktı. */}
        </td>
      </tr>
    </>
  );
}

function labelOf(src: string): string {
  // format.ts'deki sözlüğün kısa hali; tabloda satır yüksekliği korunsun diye.
  const map: Record<string, string> = {
    rule_heuristic: "kanıt tabanlı",
    constant: "sabit (kalibre değil)",
    logprob: "logprob",
    self_reported: "model beyanı",
  };
  return map[src] ?? src;
}
