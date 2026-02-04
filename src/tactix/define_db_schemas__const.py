"""Database schema name definitions."""

from dataclasses import dataclass


@dataclass(slots=True)
class DbSchemas:
    """
    A container class for database schema names used in the Tactix application.

    Attributes:
        analysis (str): The schema name for analysis-related tables.
        pgn (str): The schema name for PGN (Portable Game Notation) related tables.
    """

    analysis: str = "tactix_analysis"
    pgn: str = "tactix_pgns"
