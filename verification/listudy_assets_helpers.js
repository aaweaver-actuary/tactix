const LISTUDY_PIECE_PATH_SEGMENT = '/pieces/cburnett/';
const LISTUDY_CARD_TEXTURE_NAME = 'listudy-brown';

async function waitForListudyAssets(page, timeout = 60000) {
  await page.waitForFunction(
    (piecePathSegment) =>
      Array.from(document.querySelectorAll('img')).some((img) =>
        img.getAttribute('src')?.includes(piecePathSegment),
      ),
    { timeout },
    LISTUDY_PIECE_PATH_SEGMENT,
  );

  await page.waitForFunction(
    (cardTextureName) => {
      const card = document.querySelector('.card');
      if (!card) return false;
      const style = window.getComputedStyle(card);
      return style.backgroundImage.includes(cardTextureName);
    },
    { timeout },
    LISTUDY_CARD_TEXTURE_NAME,
  );
}

async function checkForListudyAssets(page) {
  const hasPieceAssets = await page.evaluate(
    (piecePathSegment) =>
      Array.from(document.querySelectorAll('img')).some((img) =>
        img.getAttribute('src')?.includes(piecePathSegment),
      ),
    LISTUDY_PIECE_PATH_SEGMENT,
  );

  const hasListudyCardTexture = await page.evaluate((cardTextureName) => {
    const card = document.querySelector('.card');
    if (!card) return false;
    return window
      .getComputedStyle(card)
      .backgroundImage.includes(cardTextureName);
  }, LISTUDY_CARD_TEXTURE_NAME);

  return { hasPieceAssets, hasListudyCardTexture };
}

module.exports = {
  LISTUDY_PIECE_PATH_SEGMENT,
  LISTUDY_CARD_TEXTURE_NAME,
  waitForListudyAssets,
  checkForListudyAssets,
};
