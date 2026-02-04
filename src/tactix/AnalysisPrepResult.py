from dataclasses import dataclass


@dataclass(slots=True)
class AnalysisPrepResult:
    """Outputs from preparing analysis inputs."""

    positions: list[dict[str, object]]
    resume_index: int
    analysis_signature: str
    raw_pgns_inserted: int
    raw_pgns_hashed: int
    raw_pgns_matched: int
    postgres_raw_pgns_inserted: int
