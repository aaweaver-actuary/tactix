"""Coordinate tactic detectors and normalize findings."""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping

import chess

from tactix.TacticContext import TacticContext
from tactix.TacticDetector import TacticDetector
from tactix.TacticFinding import TacticFinding


class TacticDetectionService:
    """Coordinate detectors and return normalized findings."""

    def __init__(
        self,
        detectors: Iterable[TacticDetector],
        *,
        motif_aliases: Mapping[str, str] | None = None,
        motif_filter: Collection[str] | None = None,
    ) -> None:
        self._detectors = tuple(detectors)
        self._motif_aliases = dict(motif_aliases or {})
        self._motif_filter = set(motif_filter) if motif_filter else None

    def detect(self, context: TacticContext) -> list[TacticFinding]:
        findings: list[TacticFinding] = []
        for detector in self._detectors:
            for finding in detector.detect(context):
                normalized = self._normalize_finding(finding)
                if normalized is not None:
                    findings.append(normalized)
        return self._dedupe_findings(findings)

    def infer_motif(self, board: chess.Board, best_move: chess.Move | None) -> str:
        if best_move is None:
            return "unknown"
        context = self._build_context(board, best_move)
        findings = self.detect(context)
        return findings[0].motif if findings else "unknown"

    @staticmethod
    def _build_context(board: chess.Board, move: chess.Move) -> TacticContext:
        board_after = board.copy()
        board_after.push(move)
        return TacticContext(
            board_before=board,
            board_after=board_after,
            best_move=move,
            mover_color=board.turn,
        )

    def _normalize_finding(self, finding: TacticFinding) -> TacticFinding | None:
        motif = self._motif_aliases.get(finding.motif, finding.motif)
        if self._motif_filter is not None and motif not in self._motif_filter:
            return None
        if motif == finding.motif:
            return finding
        return TacticFinding(motif=motif)

    @staticmethod
    def _dedupe_findings(findings: Iterable[TacticFinding]) -> list[TacticFinding]:
        seen: set[str] = set()
        ordered: list[TacticFinding] = []
        for finding in findings:
            if finding.motif in seen:
                continue
            seen.add(finding.motif)
            ordered.append(finding)
        return ordered
