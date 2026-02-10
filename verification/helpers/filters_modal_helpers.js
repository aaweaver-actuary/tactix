const MODAL_SELECTOR = '[data-testid="filters-modal"]';
const OPEN_SELECTOR = '[data-testid="filters-open"]';
const FAB_TOGGLE_SELECTOR = '[data-testid="fab-toggle"]';
const CLOSE_SELECTOR = '[data-testid="filters-modal-close"]';
const SOURCE_SELECTOR = '[data-testid="filter-source"]';

async function waitForFiltersModalClosed(page) {
  await page.waitForFunction(
    (selector) => !document.querySelector(selector),
    { timeout: 60000 },
    MODAL_SELECTOR,
  );
}

async function openFiltersModal(page) {
  if (await page.$(MODAL_SELECTOR)) return;
  await page.waitForSelector(FAB_TOGGLE_SELECTOR, { timeout: 60000 });
  const isExpanded = await page.$eval(
    FAB_TOGGLE_SELECTOR,
    (button) => button.getAttribute('aria-expanded') === 'true',
  );
  if (!isExpanded) {
    await page.click(FAB_TOGGLE_SELECTOR);
  }
  await page.waitForSelector(OPEN_SELECTOR, { timeout: 60000 });
  await page.click(OPEN_SELECTOR);
  await page.waitForSelector(MODAL_SELECTOR, { timeout: 60000 });
  await page.waitForSelector(SOURCE_SELECTOR, { timeout: 60000 });
}

async function closeFiltersModal(page) {
  if (!(await page.$(MODAL_SELECTOR))) return;
  const closeButton = await page.$(CLOSE_SELECTOR);
  if (closeButton) {
    await closeButton.click();
  } else {
    await page.click(MODAL_SELECTOR);
  }
  await waitForFiltersModalClosed(page);
}

async function closeFiltersModalWithEscape(page) {
  if (!(await page.$(MODAL_SELECTOR))) return;
  await page.keyboard.press('Escape');
  await waitForFiltersModalClosed(page);
}

module.exports = {
  closeFiltersModal,
  closeFiltersModalWithEscape,
  openFiltersModal,
};
