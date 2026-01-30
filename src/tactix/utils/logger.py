from __future__ import annotations

import logging
import sys


class Logger(logging.Logger):
    """Custom Logger class for Tactix."""

    def __init__(self, name: str = "tactix", level: int = logging.INFO) -> None:
        super().__init__(name, level)
        self.formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self.formatter)
        self.addHandler(handler)

    @property
    def level(self) -> int:
        return super().level

    @level.setter
    def level(self, value: int) -> None:
        super(Logger, type(self)).level.fset(self, value)
