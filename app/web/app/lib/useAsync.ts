"use client";

/**
 * Küçük veri-çekme kancası — yükleniyor / hata / veri üçlüsünü tek yerde tutar.
 *
 * Neden kendi kancamız: `swr`/`react-query` yeni bağımlılık demek. Kısıt gereği
 * (offline + lisans denetimi) ek paket eklenmiyor; ihtiyaç 30 satırla karşılanır.
 * Hata ASLA yutulmaz — `error` çağırana döner ve arayüzde gösterilir.
 */

import { useCallback, useEffect, useState } from "react";

export type AsyncState<T> = {
  data: T | null;
  error: unknown;
  loading: boolean;
  reload: () => void;
};

export function useAsync<T>(
  loader: () => Promise<T>,
  deps: ReadonlyArray<unknown>,
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    loader()
      .then((d) => {
        if (alive) {
          setData(d);
          setLoading(false);
        }
      })
      .catch((e: unknown) => {
        if (alive) {
          setError(e);
          setData(null);
          setLoading(false);
        }
      });
    return () => {
      alive = false;
    };
    // loader her render'da yeniden oluşur; bağımlılık listesi çağırana bırakılır.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  return { data, error, loading, reload };
}
