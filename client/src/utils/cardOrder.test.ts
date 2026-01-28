import { describe, expect, it } from 'vitest';
import {
  normalizeOrder,
  reorderList,
  readCardOrder,
  writeCardOrder,
} from './cardOrder';

const createMemoryStorage = () => {
  const store = new Map<string, string>();
  return {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(key, value);
    },
  } as Storage;
};

describe('cardOrder utilities', () => {
  it('normalizes order by removing unknowns and appending missing ids', () => {
    const order = ['b', 'a', 'x', 'b'];
    const allowed = ['a', 'b', 'c'];
    expect(normalizeOrder(order, allowed)).toEqual(['b', 'a', 'c']);
  });

  it('reorders list items between indices', () => {
    expect(reorderList(['a', 'b', 'c'], 0, 2)).toEqual(['b', 'c', 'a']);
  });

  it('reads and writes card order safely', () => {
    const storage = createMemoryStorage();
    const key = 'order-key';
    const fallback = ['a', 'b'];

    expect(readCardOrder(key, fallback, storage)).toEqual(fallback);
    expect(writeCardOrder(key, ['b', 'a'], storage)).toBe(true);
    expect(readCardOrder(key, fallback, storage)).toEqual(['b', 'a']);
  });

  it('returns fallback on invalid storage payload', () => {
    const storage = createMemoryStorage();
    storage.setItem('order-key', '{not-json');

    expect(readCardOrder('order-key', ['a'], storage)).toEqual(['a']);
  });
});
