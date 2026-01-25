import React from 'react';
import ReactDOMServer from 'react-dom/server';
import Badge from './Badge';

const renderBadgeHtml = (label: string) =>
  ReactDOMServer.renderToStaticMarkup(<Badge label={label} />);

describe('Badge', () => {
  beforeAll(async () => {
    const html = renderBadgeHtml('Test Label');
    await page.setContent(`<div id="root">${html}</div>`);
  });

  it('renders the provided label', async () => {
    const text = await page.$eval('span', (el) => el.textContent);
    expect(text).toBe('Test Label');
  });

  it('applies the expected classes', async () => {
    const className = await page.$eval('span', (el) => el.className);
    expect(className).toContain('px-2');
    expect(className).toContain('py-1');
    expect(className).toContain('text-xs');
    expect(className).toContain('rounded-full');
    expect(className).toContain('bg-rust/30');
    expect(className).toContain('text-sand');
    expect(className).toContain('border');
    expect(className).toContain('border-rust/60');
  });

  it('renders different labels', async () => {
    const html = renderBadgeHtml('Another');
    await page.setContent(`<div id="root">${html}</div>`);
    const text = await page.$eval('span', (el) => el.textContent);
    expect(text).toBe('Another');
  });
});
