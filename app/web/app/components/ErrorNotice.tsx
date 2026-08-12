"use client";

/**
 * DURUM YÜZEYLERİ — hata, boşluk, yükleme ve `null` ≠ `%0` ayrımı.
 *
 * İlgili: ../lib/api.ts (`toDisplayError`), ../lib/saglik.tsx,
 *         ../styles/durum.css, ./DurumSeridi.tsx (`ApiKapaliUyarisi`)
 *
 * ## Durumlar birinci sınıf vatandaş
 *
 * Bu panelin iddiası «neyi ne kadar biliyoruz». O iddia, ancak bilmediğimiz
 * yerin de bir BİÇİMİ varsa okunur. Bu dosyadaki dört bileşen dört ayrı şeyi
 * söyler ve hiçbiri ötekinin kalıbını giymez:
 *
 *   ErrorNotice        istek GERÇEKTEN başarısız oldu (kırmızı, arıza)
 *   EmptyNotice        API çalıştı, yanıt verdi ve sonuç boş (nötr, hata değil)
 *   Loading            yapı basıldı, yalnız değerler bekliyor (iskelet)
 *   VeriYokSifirDegil  `null` ile `%0` aynı çubuğa çizilmez (açıklayıcı yüzey)
 *
 * ## «use client» neden gerekti
 *
 * `ErrorNotice` artık sağlık durumunu okuyor (`useSaglik`). Sebebi ölçüldü:
 * sunucu düştüğünde her panel kendi isteğini ayrı deniyor, ayrı başarısız
 * oluyor ve ekranda BEŞ AYRI KIRMIZI KUTU beliriyordu — hepsi aynı tek olayı
 * anlatarak. Kutuları panellerden tek tek kaldırmak her paneli değiştirmeyi
 * gerektirirdi; bunun yerine kutu KENDİSİ susuyor: API topluca kapalıysa
 * `ErrorNotice` tek satırlık bir atıf basar ve olayı kabuktaki banda bırakır.
 *
 * Bu dosyayı çağıran her bileşen zaten istemci bileşenidir; `useSaglik`
 * sağlayıcı dışında da güvenlidir (bağlam varsayılanı «kapalı değil»dir), yani
 * sağlayıcısız bir ağaçta davranış eskisiyle aynı kalır.
 */

import { toDisplayError } from "../lib/api";
import { trNum } from "../lib/format";
import { useSaglik } from "../lib/saglik";

/**
 * OPERATÖR metninin izleri.
 *
 * `api.ts` çevrimdışı ipucunu operatöre yazıyor: bir kabuk komutu ve bir port
 * numarası taşır. O cümle sunucuyu yeniden başlatacak kişi için doğrudur ama
 * jüri ekranında geliştirme talimatı görünmemelidir — panelin okuyucusu
 * süreç yöneticisi değil. İpucu bu yüzden gösterim tarafında süzülür: komut
 * izi taşıyan ipucu basılmaz, yerine kullanıcıya dönük tek cümle geçer.
 *
 * Süzgeç ipucu SİLMİYOR, YERİNE KOYUYOR: bilgi kaybı olmaması için
 * `api.ts`'teki metnin kendisi de sadeleştirilmeli (bkz. rapor).
 */
const OPERATOR_IZI = /[`$]|uvicorn|docker|compose|localhost|--port|npm |pip /i;

/** Kullanıcıya dönük ipucu — operatör metni ise `null`. */
function gosterilebilirIpucu(hint: string): string | null {
  if (!hint.trim()) return null;
  return OPERATOR_IZI.test(hint) ? null : hint;
}

/**
 * `onRetry` VERİLİRSE bir «Tekrar dene» düğmesi basılır, verilmezse hiçbir
 * düğme çıkmaz.
 *
 * Varsayılanın "düğme yok" olması bilinçlidir: her hataya tekrar denetmek,
 * çözümü olmayan bir hata için de tekrar dene demektir ve bu kullanıcıyı
 * yanıltır (aynı ayrım için bkz. ../lib/tazeleme.ts `isCikmazi`). Düğmeyi
 * çağıran taraf, hatanın gerçekten geçici olduğunu bildiği yerde AÇIKÇA
 * ister; sessiz varsayılan bir söz vermez.
 */
export function ErrorNotice({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  const { kapali, hazir } = useSaglik();
  const { message, hint } = toDisplayError(error);

  // Olay tek, bant tek: API topluca kapalıyken bu kutu bir arıza İDDİA ETMEZ,
  // yalnız kendisini bandın altına bağlar. Beş panel beş kutu basmasın.
  if (hazir && kapali) {
    return (
      <p className="durum-atif" role="status">
        Bu panel sunucunun yanıtını bekliyor — sebep yukarıdaki durum bandında
        bir kez yazılı.
      </p>
    );
  }

  const ipucu = gosterilebilirIpucu(hint);

  return (
    <div className="notice notice-error" role="alert">
      <strong>İstek başarısız</strong>
      {message}
      {ipucu ? (
        <div className="small" style={{ marginTop: "var(--sp-2)" }}>
          {ipucu}
        </div>
      ) : (
        <div className="small" style={{ marginTop: "var(--sp-2)" }}>
          Sunucu şu an bu isteği yanıtlamıyor; panelin geri kalanı okunmaya
          devam ediyor.
        </div>
      )}
      {onRetry && (
        <div className="row" style={{ marginTop: "var(--sp-3)" }}>
          <button type="button" className="btn btn-ghost" onClick={onRetry}>
            Tekrar dene
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * BOŞ ≠ HATA.
 *
 * Nötr çerçeve, uyarı rengi DEĞİL. Kutu üç şeyi birden söyler:
 *   1. isteğin ÇALIŞTIĞINI  — «API çalıştı ve yanıt verdi»
 *   2. boşluğun ÖLÇÜSÜNÜ    — alanın korpustaki gerçek kapsaması + mono kesir
 *   3. değer uydurulmayacağını
 *
 * Kesik taban çizgisi boşluğun imzasıdır: dolu bir çubuk «ölçüldü» der, kesik
 * çizgi «satır duruyor, değer yok» der ve ikisi hiçbir ekranda aynı biçime
 * düşmez.
 *
 * `alan` / `kapsam` / `kesir` VERİLİRSE kutu alan düzeyinde okunur ve `null`
 * ile `%0` ayrımı kutunun altına eklenir. Verilmezse (banka listesi boş, süzgeç
 * sonucu boş gibi) o ayrım basılmaz: orada `%0` diye bir hâl yoktur ve
 * anlatmak gürültü olurdu.
 */
export function EmptyNotice({
  title,
  children,
  alan,
  kapsam,
  kesir,
}: {
  title: string;
  children?: React.ReactNode;
  /** Şema adı (`tahsis_ucreti` gibi). Mono basılır. */
  alan?: string;
  /** Alanın korpustaki gerçek kapsaması. Sunucudan gelir, sabit değil. */
  kapsam?: { gecen: number; toplam: number } | null;
  /** Sağ alttaki mono kesir (`0 / 11 banka`). Boşluğun ölçüsü. */
  kesir?: string;
}) {
  return (
    <div className="durum-bos">
      <div className="durum-bos-baslik">{title}</div>
      <p className="durum-bos-govde">
        API çalıştı ve yanıt verdi.{" "}
        {alan ? (
          <>
            <span className="durum-alan">{alan}</span>
            {kapsam
              ? ` alanı ${trNum(kapsam.toplam)} belgenin ${trNum(
                  kapsam.gecen,
                )} tanesinde geçiyor ve bu seçimde hiç geçmiyor.`
              : " alanı bu seçimdeki hiçbir belgede geçmiyor."}{" "}
            Alan metinde yoksa sistem değer uydurmaz.
          </>
        ) : (
          <>Sonuç gerçekten boş; eksik satır değer uydurularak doldurulmaz.</>
        )}
      </p>

      {children && <div className="durum-bos-ek">{children}</div>}

      {/* Boşluğun KENDİ görsel biçimi: kesik taban çizgisi + mono kesir. */}
      <div className="durum-bos-taban">
        <span className="durum-bos-cizgi" aria-hidden="true" />
        {kesir && <span className="durum-bos-kesir">{kesir}</span>}
      </div>

      {alan && <VeriYokSifirDegil />}
    </div>
  );
}

/**
 * `veri yok` ≠ `değer sıfır` — açıklayıcı yüzey.
 *
 * Bu ayrım ürünün dürüstlük iddiasının çekirdeğidir. `null` ölçülemedi
 * demektir ve sıralamaya girmez; `%0` (masrafsız, ilk 6 ay ödemesiz) GERÇEK
 * bir üründür ve alanın en avantajlı ucudur. İkisi aynı çubuğa çizilirse
 * ölçülemeyen bir alan, en iyi teklif gibi sıralanır — panelin yapmamaya söz
 * verdiği tek şey budur.
 *
 * İki hâl iki ayrı BİÇİM taşır: biri kesik çizgi (genişlik var, mürekkep yok),
 * öteki sıfır genişlikli ama görünür bir mürekkep işareti (ölçülmüş değer
 * ekranda iz bırakır). Renk üçüncü sinyaldir, ilk değil.
 *
 * `katlanabilir` varsayılan olarak açıktır: yüzey her ekranda bulunmalı ama
 * her ekranda YER KAPLAMAMALI — göz-üstü etiketi görünür, gövde istenince
 * açılır.
 */
export function VeriYokSifirDegil({
  katlanabilir = true,
}: {
  katlanabilir?: boolean;
}) {
  const govde = (
    <div className="durum-ayrim">
      <div className="durum-ayrim-satir durum-ayrim-null">
        <span className="durum-ayrim-isaret" aria-hidden="true">
          <span className="durum-ayrim-kesik" />
        </span>
        <div>
          <div className="durum-ayrim-etiket">null</div>
          <div className="durum-ayrim-metin">
            Alan metinde geçmiyor. Sıralamaya girmez, satır kalır.
          </div>
        </div>
      </div>

      <div className="durum-ayrim-satir durum-ayrim-sifir">
        <span className="durum-ayrim-isaret" aria-hidden="true">
          <span className="durum-ayrim-murekkep" />
        </span>
        <div>
          <div className="durum-ayrim-etiket">%0</div>
          <div className="durum-ayrim-metin">
            Kâr payı ya da masraf <b>alınmıyor</b>. Gerçek bir üründür ve alanın
            en avantajlı ucudur.
          </div>
        </div>
      </div>

      <p className="durum-ayrim-not">
        İki hâl aynı çubuğa çizilmez: biri kesik çizgi, öteki sıfır genişlikli
        ama görünür bir mürekkep işareti.
      </p>
    </div>
  );

  if (!katlanabilir) return govde;

  return (
    <details className="durum-ayrim-kutu">
      <summary className="durum-goz-ustu durum-ayrim-basi">
        veri yok ≠ değer sıfır
      </summary>
      {govde}
    </details>
  );
}

/**
 * YÜKLENİYOR — cetvel önce çizilir.
 *
 * İskelet yapı hemen basılır, yalnız DEĞERLER bekler. Yükleme sırasında
 * hiçbir sayı, hiçbir sıra numarası ve hiçbir animasyonlu sayaç görünmez:
 * sayaç dönerken okunan sayı, hiç okunmamış bir sayıdır. Nabız yalnız
 * «bekliyor» der ve `prefers-reduced-motion` altında durur.
 *
 * `satir` iskelet satır sayısıdır; `0` verilirse yalnız etiket basılır (küçük,
 * satır içi bekleyişler için). İskelet ekran okuyucudan gizlidir — okunacak
 * şey etikettir, on iki boş dikdörtgen değil.
 */
export function Loading({
  label = "Yükleniyor…",
  satir = 3,
}: {
  label?: string;
  satir?: number;
}) {
  return (
    <div className="durum-yukleniyor" role="status" aria-live="polite" aria-busy="true">
      <p className="durum-yukleniyor-etiket">{label}</p>
      {satir > 0 && (
        <div className="durum-iskelet" aria-hidden="true">
          {Array.from({ length: satir }, (_, i) => (
            <div className="durum-iskelet-satir" key={i}>
              <span className="durum-iskelet-ad" />
              <span className="durum-iskelet-cubuk" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
