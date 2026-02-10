const LISTUDY_PIECE_PATH_SEGMENT = '/pieces/cburnett/';
const LISTUDY_BOARD_TOKEN = 'listudy-board-texture';
const LISTUDY_BOARD_FILE = 'listudy-brown';
const CHESSBOARD_MODAL_SELECTOR = '[data-testid="chessboard-modal-board"]';

async function waitForListudyAssets(page, timeout = 60000) {
  await page.waitForFunction(
    (piecePathSegment, rootSelector) => {
      const root = document.querySelector(rootSelector) || document;
      return Array.from(root.querySelectorAll('img')).some((img) =>
        img.getAttribute('src')?.includes(piecePathSegment),
      );
    },
    { timeout },
    LISTUDY_PIECE_PATH_SEGMENT,
    CHESSBOARD_MODAL_SELECTOR,
  );

  await page.waitForFunction(
    (boardToken, boardFile, rootSelector) => {
      const root = document.querySelector(rootSelector) || document;
      return Array.from(root.querySelectorAll('*')).some((node) => {
        const style = window.getComputedStyle(node);
        const background = style.backgroundImage || '';
        return (
          background.includes(boardToken) || background.includes(boardFile)
        );
      });
    },
    { timeout },
    LISTUDY_BOARD_TOKEN,
    LISTUDY_BOARD_FILE,
    CHESSBOARD_MODAL_SELECTOR,
  );
}

async function checkForListudyAssets(page) {
  const hasPieceAssets = await page.evaluate(
    (piecePathSegment, rootSelector) => {
      const root = document.querySelector(rootSelector) || document;
      return Array.from(root.querySelectorAll('img')).some((img) =>
        img.getAttribute('src')?.includes(piecePathSegment),
      );
    },
    LISTUDY_PIECE_PATH_SEGMENT,
    CHESSBOARD_MODAL_SELECTOR,
  );

  const hasListudyBoardTexture = await page.evaluate(
    (boardToken, boardFile, rootSelector) => {
      const root = document.querySelector(rootSelector) || document;
      return Array.from(root.querySelectorAll('*')).some((node) => {
        const style = window.getComputedStyle(node);
        const background = style.backgroundImage || '';
        return (
          background.includes(boardToken) || background.includes(boardFile)
        );
      });
    },
    LISTUDY_BOARD_TOKEN,
    LISTUDY_BOARD_FILE,
    CHESSBOARD_MODAL_SELECTOR,
  );

  return { hasPieceAssets, hasListudyBoardTexture };
}

module.exports = {
  LISTUDY_PIECE_PATH_SEGMENT,
  LISTUDY_BOARD_FILE,
  LISTUDY_BOARD_TOKEN,
  waitForListudyAssets,
  checkForListudyAssets,
};
