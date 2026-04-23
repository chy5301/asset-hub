import { useEffect, useState } from "react";
import type { COLUMN_KEY } from "./column-visibility-utils";
import { ALL_KEYS, STORAGE_KEY } from "./column-visibility-utils";

export function useColumnVisibility() {
  const [visible, setVisible] = useState<Record<COLUMN_KEY, boolean>>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<Record<COLUMN_KEY, boolean>>;
        return Object.fromEntries(
          ALL_KEYS.map((k) => [k, parsed[k] !== false]),
        ) as Record<COLUMN_KEY, boolean>;
      }
    } catch {
      // fall through to default
    }
    return Object.fromEntries(ALL_KEYS.map((k) => [k, true])) as Record<
      COLUMN_KEY,
      boolean
    >;
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(visible));
  }, [visible]);

  const toggle = (key: COLUMN_KEY) =>
    setVisible((v) => ({ ...v, [key]: !v[key] }));

  return { visible, toggle };
}
