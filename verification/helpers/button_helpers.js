const clickButtonByText = async (page, text) => {
  if (typeof page.locator === 'function') {
    await page.locator('button', { hasText: text }).click();
    return;
  }
  await page.$$eval('button', (buttons, targetText) => {
    const target = buttons.find(
      (btn) => btn.textContent && btn.textContent.includes(targetText),
    );
    if (target) target.click();
  }, text);
};

module.exports = {
  clickButtonByText,
};
