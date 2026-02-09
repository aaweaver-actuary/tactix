const MODAL_SELECTOR = '[data-testid="filters-modal"]';
const OPEN_SELECTOR = '[data-testid="filters-open"]';
const CLOSE_SELECTOR = '[data-testid="filters-modal-close"]';
const SOURCE_SELECTOR = '[data-testid="filter-source"]';

async function openFiltersModal(page) {
  if (await page.$(MODAL_SELECTOR)) return;
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
  await page.waitForFunction(
    (selector) => !document.querySelector(selector),
    { timeout: 60000 },
    MODAL_SELECTOR,
  );
}

module.exports = {
  closeFiltersModal,
  openFiltersModal,
};
