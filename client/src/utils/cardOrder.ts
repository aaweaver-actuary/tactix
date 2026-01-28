export const normalizeOrder = (order: string[], allowed: string[]) => {
  const allowedSet = new Set(allowed);
  const seen = new Set<string>();
  const normalized: string[] = [];

  order.forEach((id) => {
    if (!allowedSet.has(id) || seen.has(id)) return;
    seen.add(id);
    normalized.push(id);
  });

  allowed.forEach((id) => {
    if (!seen.has(id)) normalized.push(id);
  });

  return normalized;
};

export const reorderList = <T>(
  list: T[],
  startIndex: number,
  endIndex: number,
): T[] => {
  const result = [...list];
  const [removed] = result.splice(startIndex, 1);
  result.splice(endIndex, 0, removed);
  return result;
};

export const readCardOrder = (
  storageKey: string,
  fallback: string[],
  storage?: Storage | null,
): string[] => {
  const resolvedStorage =
    storage ?? (typeof window === 'undefined' ? null : window.localStorage);
  if (!resolvedStorage) return fallback;
  try {
    const raw = resolvedStorage.getItem(storageKey);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return fallback;
    return parsed.filter((value) => typeof value === 'string');
  } catch {
    return fallback;
  }
};

export const writeCardOrder = (
  storageKey: string,
  order: string[],
  storage?: Storage | null,
): boolean => {
  const resolvedStorage =
    storage ?? (typeof window === 'undefined' ? null : window.localStorage);
  if (!resolvedStorage) return false;
  try {
    resolvedStorage.setItem(storageKey, JSON.stringify(order));
    return true;
  } catch {
    return false;
  }
};
