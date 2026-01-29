import pytest
import warnings


warnings.filterwarnings(
	"ignore",
	message=r"The \(path: py\.path\.local\) argument is deprecated",
	category=pytest.PytestRemovedIn9Warning,
)


def pytest_ignore_collect(collection_path, config):
	return collection_path.name == "test_discovered_check_rapid_low.py"
