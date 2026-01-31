import unittest

from tactix.config import Settings
from tactix import analyze_tactics__positions as impl


class TacticSeverityTests(unittest.TestCase):
    def test_severity_uses_eval_magnitude(self) -> None:
        severity = impl._compute_severity__tactic(
            base_cp=80,
            delta=-20,
            motif="hanging_piece",
            mate_in=None,
            result="found",
            settings=None,
        )
        self.assertAlmostEqual(severity, 0.2, places=2)

    def test_severity_caps_at_max(self) -> None:
        severity = impl._compute_severity__tactic(
            base_cp=250,
            delta=-400,
            motif="hanging_piece",
            mate_in=None,
            result="missed",
            settings=None,
        )
        self.assertEqual(severity, impl._SEVERITY_MAX)

    def test_mate_in_forces_max(self) -> None:
        severity = impl._compute_severity__tactic(
            base_cp=0,
            delta=0,
            motif="mate",
            mate_in=impl.MATE_IN_ONE,
            result="found",
            settings=None,
        )
        self.assertEqual(severity, impl._SEVERITY_MAX)

    def test_fork_severity_floor_applies(self) -> None:
        settings = Settings(fork_severity_floor=1.5)
        severity = impl._compute_severity__tactic(
            base_cp=40,
            delta=0,
            motif="fork",
            mate_in=None,
            result="found",
            settings=settings,
        )
        self.assertEqual(severity, 1.5)


if __name__ == "__main__":
    unittest.main()
