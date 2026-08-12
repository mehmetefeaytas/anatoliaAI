/**
 * Anlamlı hata / boş durum bildirimleri.
 *
 * Kural (görev şartı): API çökerse veya boş dönerse arayüz SESSİZCE boş tablo
 * göstermez. "Veri yok" ile "API kapalı" birbirinden ayrılır.
 */

import { toDisplayError } from "../lib/api";

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
  const { message, hint } = toDisplayError(error);
  return (
    <div className="notice notice-error" role="alert">
      <strong>İstek başarısız</strong>
      {message}
      {hint && <div className="small" style={{ marginTop: "var(--sp-2)" }}>{hint}</div>}
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

export function EmptyNotice({
  title,
  children,
}: {
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="notice notice-info">
      <strong>{title}</strong>
      {children}
    </div>
  );
}

export function Loading({ label = "Yükleniyor…" }: { label?: string }) {
  return (
    <p className="muted small" role="status" aria-live="polite">
      {label}
    </p>
  );
}
