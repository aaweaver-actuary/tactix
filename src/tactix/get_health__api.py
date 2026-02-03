from tactix.utils.now import Now

_HEALTH_SERVICE = "tactix"
_HEALTH_VERSION = "0.1.0"


def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": _HEALTH_SERVICE,
        "version": _HEALTH_VERSION,
        "timestamp": Now.as_datetime().isoformat(),
    }
