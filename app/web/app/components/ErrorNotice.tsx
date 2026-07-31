/**
 * Anlamlı hata / boş durum bildirimleri.
 *
 * Kural (görev şartı): API çökerse veya boş dönerse arayüz SESSİZCE boş tablo
 * göstermez. "Veri yok" ile "API kapalı" birbirinden ayrılır.
 */

import { toDisplayError } from "../lib/api";

export function ErrorNotice({ error }: { error: unknown }) {
  const { message, hint } = toDisplayError(error);
  return (
    <div className="notice notice-error" role="alert">
      <strong>İstek başarısız</strong>
      {message}
      {hint && <div className="small" style={{ marginTop: 6 }}>{hint}</div>}
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
