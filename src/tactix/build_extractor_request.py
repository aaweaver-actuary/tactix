"""Helpers for constructing extractor requests."""

from tactix.extractor_context import ExtractorRequest
from tactix.pgn_context_kwargs import PgnContextInputs, build_pgn_context_kwargs


def build_extractor_request(inputs: PgnContextInputs) -> ExtractorRequest:
    """Build an ExtractorRequest from PGN context inputs."""
    return ExtractorRequest(**build_pgn_context_kwargs(inputs=inputs))
