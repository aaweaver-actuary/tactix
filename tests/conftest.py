def pytest_ignore_collect(path, config):
	return path.basename == "test_discovered_check_rapid_low.py"
