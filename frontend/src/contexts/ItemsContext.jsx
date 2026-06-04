// Items Context — the isolated items module on the frontend.
//
// All item-related state lives here:
//   * the tier list (S/A/B/C/D buckets)
//   * a flat list of items used by pickers
//   * a fetch helper, refresh helper, and a lookup by id
//
// The provider is mounted once at the app root, so every component reads
// items the same way: `const { tierList } = useItems()`. No component fetches
// item data directly — they all go through this context.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../api/client.js';

const ItemsContext = createContext(null);

export function ItemsProvider({ children }) {
  const [items, setItems] = useState([]);
  const [tierList, setTierList] = useState({ S: [], A: [], B: [], C: [], D: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [flatResult, tierResult] = await Promise.allSettled([api.items(), api.tierList()]);

    if (flatResult.status === 'fulfilled') {
      setItems(flatResult.value);
    } else if (flatResult.reason?.response?.status === 404) {
      setItems([]);
    }

    if (tierResult.status === 'fulfilled') {
      setTierList({ S: [], A: [], B: [], C: [], D: [], ...tierResult.value });
    } else if (tierResult.reason?.response?.status === 404) {
      setTierList({ S: [], A: [], B: [], C: [], D: [] });
    }

    const failures = [flatResult, tierResult].filter((r) => r.status === 'rejected' && r.reason?.response?.status !== 404);
    if (failures.length) {
      setError(failures.map((r) => r.reason?.message || 'items request failed').join(' · '));
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const byId = useMemo(() => {
    const m = new Map();
    for (const it of items) m.set(it.item_id, it);
    return m;
  }, [items]);

  const value = useMemo(
    () => ({ items, tierList, byId, loading, error, reload: load }),
    [items, tierList, byId, loading, error, load],
  );
  return <ItemsContext.Provider value={value}>{children}</ItemsContext.Provider>;
}

export function useItems() {
  const ctx = useContext(ItemsContext);
  if (!ctx) throw new Error('useItems must be used inside <ItemsProvider>');
  return ctx;
}
