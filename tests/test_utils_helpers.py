import importlib
import logging

from tactix import utils
from tactix.utils.logger import Logger, funclogger, get_logger, set_level
from tactix.utils.to_int import to_int


def test_to_int_coerces_values() -> None:
    assert to_int(7) == 7
    assert to_int("42") == 42
    assert to_int("nope") is None
    assert to_int(3.14) is None


def test_get_logger_configures_default_handler() -> None:
    logger = logging.getLogger("tactix.test")
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)

    configured = get_logger("tactix.test")

    assert configured.level != logging.NOTSET
    assert configured.handlers
    assert configured.propagate is False


def test_funclogger_decorator_returns_value() -> None:
    @funclogger
    def add(left: int, right: int, *, extra: int = 0) -> int:
        return left + right + extra

    assert add(2, 3, extra=1) == 6


def test_set_level_updates_named_loggers() -> None:
    set_level(logging.INFO, logger_names=["tactix.test.one", "tactix.test.two"])
    assert logging.getLogger("tactix.test.one").level == logging.INFO
    assert logging.getLogger("tactix.test.two").level == logging.INFO


def test_logger_factory_returns_configured_logger() -> None:
    logger = Logger("tactix.test.factory")
    assert logger.name == "tactix.test.factory"


def test_utils_exports_expected_helpers() -> None:
    assert utils.to_int is to_int
    assert "to_int" in utils.__all__


def test_utils_all_exports_are_resolvable() -> None:
    for name in utils.__all__:
        assert getattr(utils, name)


def test_utils_reload_executes_module() -> None:
    importlib.reload(utils)
    assert utils.Logger


def test_logger_reload_executes_module() -> None:
    import tactix.utils.logger as logger_module

    importlib.reload(logger_module)
    logger_module.set_level(logging.INFO, logger_names=["tactix.reload"])
    assert logger_module.Logger("tactix.reload").name == "tactix.reload"
