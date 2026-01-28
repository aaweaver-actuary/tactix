import tactix.tactics_analyzer as analyzer
from tactix.tactic_detectors import MotifDetectorSuite


def test_analyzer_uses_detector_suite() -> None:
    assert isinstance(analyzer.MOTIF_DETECTORS, MotifDetectorSuite)


def test_legacy_helpers_removed() -> None:
    legacy_helpers = [
        "_infer_motif",
        "_classify_result",
        "_score_from_pov",
        "_detect_pin",
        "_detect_skewer",
        "_detect_discovered_attack",
        "_is_hanging_capture",
    ]
    remaining = [name for name in legacy_helpers if hasattr(analyzer, name)]
    assert not remaining, f"Legacy helper(s) still exposed: {remaining}"
