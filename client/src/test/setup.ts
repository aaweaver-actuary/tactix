import '@testing-library/jest-dom/vitest';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => {
  cleanup();
});

(globalThis as unknown as { jest: typeof vi }).jest = vi;

(
  globalThis as unknown as {
    page: {
      setContent: (html: string) => Promise<void>;
      $eval: <T>(selector: string, fn: (el: Element) => T) => Promise<T>;
    };
  }
).page = {
  async setContent(html: string) {
    document.body.innerHTML = html;
  },
  async $eval(selector, fn) {
    const el = document.querySelector(selector);
    if (!el) {
      throw new Error(`No element found for selector: ${selector}`);
    }
    return fn(el);
  },
};

export {};
