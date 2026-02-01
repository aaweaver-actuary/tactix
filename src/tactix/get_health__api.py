from tactix.utils.now import now

_HEALTH_SERVICE = "tactix"
_HEALTH_VERSION = "0.1.0"


def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": _HEALTH_SERVICE,
        "version": _HEALTH_VERSION,
        "timestamp": now().isoformat(),
    }
