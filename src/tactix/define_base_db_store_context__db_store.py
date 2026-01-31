from __future__ import annotations

import logging
from dataclasses import dataclass

from tactix.config import Settings


@dataclass(slots=True)
class BaseDbStoreContext:
    """Shared context for database stores.

    Attributes:
        settings: Application settings for store configuration.
        logger: Logger for store-specific messages.
    """

    settings: Settings
    logger: logging.Logger
