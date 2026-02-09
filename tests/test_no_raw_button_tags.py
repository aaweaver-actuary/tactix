from __future__ import annotations

from pathlib import Path
import re

BUTTON_PATTERN = re.compile(r"<button\b", re.IGNORECASE)
CLIENT_SRC = Path(__file__).resolve().parents[1] / "client" / "src"
ALLOWED_FILES = {
    CLIENT_SRC / "_components" / "BaseButton.tsx",
}


def _iter_client_files() -> list[Path]:
    files: list[Path] = []
    for pattern in ("*.ts", "*.tsx", "*.js", "*.jsx"):
        files.extend(CLIENT_SRC.rglob(pattern))
    return files


def test_no_raw_button_tags_outside_basebutton() -> None:
    offenders: list[str] = []
    for path in _iter_client_files():
        if path in ALLOWED_FILES:
            continue
        content = path.read_text(encoding="utf-8")
        if BUTTON_PATTERN.search(content):
            offenders.append(str(path.relative_to(CLIENT_SRC)))

    assert not offenders, (
        f"Raw <button> tags are only allowed in BaseButton. Found in: {', '.join(offenders)}"
    )
