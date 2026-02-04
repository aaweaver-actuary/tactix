import sys
from pathlib import Path
import pytest
import warnings


warnings.filterwarnings(
    "ignore",
    message=r"The \(path: py\.path\.local\) argument is deprecated",
    category=pytest.PytestRemovedIn9Warning,
)

project_root = Path(__file__).resolve().parents[1]
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

if "tactix" in sys.modules:
    for name in list(sys.modules):
        if name == "tactix" or name.startswith("tactix."):
            del sys.modules[name]


def pytest_ignore_collect(collection_path, config):
    return collection_path.name == "test_discovered_check_rapid_low.py"
