const HERO_SELECTOR = '[data-testid="dashboard-hero"]';
const REQUIRED_TEST_IDS = [
  'action-run',
  'action-backfill',
  'action-migrate',
  'action-refresh',
  'backfill-start',
  'backfill-end',
];

const waitForHero = (page) =>
  page.waitForSelector(HERO_SELECTOR, { timeout: 60000 });

const getHeroStatus = (page) =>
  page.evaluate((selector, required) => {
    const hero = document.querySelector(selector);
    if (!hero) return { ok: false, missing: required, hasHeroClass: false };
    const missing = required.filter(
      (id) => !hero.querySelector(`[data-testid="${id}"]`),
    );
    const hasHeroClass = hero.classList.contains('hero-card');
    return { ok: missing.length === 0 && hasHeroClass, missing, hasHeroClass };
  }, HERO_SELECTOR, REQUIRED_TEST_IDS);

module.exports = { HERO_SELECTOR, REQUIRED_TEST_IDS, waitForHero, getHeroStatus };
