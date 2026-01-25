import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import puppeteer, { Browser, Page } from 'puppeteer';
import React from 'react';
import ReactDOMServer from 'react-dom/server';
import Text from './Text';

let browser: Browser;
let page: Page;

function renderHtml(element: React.ReactElement) {
  const markup = ReactDOMServer.renderToStaticMarkup(element);
  return `<!doctype html><html><body><div id="root">${markup}</div></body></html>`;
}

async function getRenderedInfo(element: React.ReactElement) {
  const html = renderHtml(element);
  await page.setContent(html);
  return page.$eval('#root p', (el) => ({
    className: el.className,
    text: el.textContent ?? '',
  }));
}

beforeAll(async () => {
  browser = await puppeteer.launch({ headless: 'new' });
  page = await browser.newPage();
});

afterAll(async () => {
  await page.close();
  await browser.close();
});

describe('Text', () => {
  it('renders default mode and size', async () => {
    const { className, text } = await getRenderedInfo(<Text value="Hello" />);
    expect(text).toBe('Hello');
    expect(className).toContain('text-xs');
    expect(className).toContain('text-sand/60');
    expect(className).not.toContain('mt-');
  });

  it('renders uppercase mode with tracking and mt', async () => {
    const { className, text } = await getRenderedInfo(
      <Text value="Caps" mode="uppercase" size="sm" mt="4" />
    );
    expect(text).toBe('Caps');
    expect(className).toContain('text-sm');
    expect(className).toContain('uppercase');
    expect(className).toContain('tracking-[0.08em]');
    expect(className).toContain('mt-4');
  });

  it('renders teal mode', async () => {
    const { className } = await getRenderedInfo(
      <Text value="Teal" mode="teal" size="lg" />
    );
    expect(className).toContain('text-lg');
    expect(className).toContain('font-display');
    expect(className).toContain('text-teal');
  });

  it('renders monospace mode', async () => {
    const { className } = await getRenderedInfo(
      <Text value="Mono" mode="monospace" />
    );
    expect(className).toContain('font-mono');
    expect(className).toContain('text-sand/60');
  });

  it('renders error mode', async () => {
    const { className } = await getRenderedInfo(
      <Text value="Error" mode="error" />
    );
    expect(className).toContain('text-rust');
  });

  it('falls back to normal for unknown mode', async () => {
    const { className } = await getRenderedInfo(
      <Text value="Fallback" mode={'unknown' as any} />
    );
    expect(className).toContain('text-sand/60');
  });
});
