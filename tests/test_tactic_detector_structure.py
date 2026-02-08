from pathlib import Path

import tactix.analyze_tactics__positions as analyzer
from tactix.detect_tactics__motifs import MotifDetectorSuite


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


def test_detectors_do_not_import_infra_dependencies() -> None:
    detector_paths = [
        Path("src/tactix/detect_tactics__motifs.py"),
        Path("src/tactix/BaseTacticDetector.py"),
        Path("src/tactix/CaptureDetector.py"),
        Path("src/tactix/DiscoveredAttackDetector.py"),
        Path("src/tactix/DiscoveredCheckDetector.py"),
        Path("src/tactix/ForkDetector.py"),
        Path("src/tactix/HangingPieceDetector.py"),
        Path("src/tactix/PinDetector.py"),
        Path("src/tactix/SkewerDetector.py"),
    ]
    forbidden = {
        "fastapi",
        "sqlalchemy",
        "duckdb",
        "psycopg",
        "httpx",
        "requests",
        "streamlit",
        "gradio",
        "tkinter",
    }

    for path in detector_paths:
        contents = path.read_text(encoding="utf-8").lower()
        hits = [token for token in forbidden if token in contents]
        assert not hits, f"{path} imports forbidden modules: {hits}"
