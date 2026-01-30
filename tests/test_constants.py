from tactix.const import DbSchemas


def test_db_schemas_defaults() -> None:
    schemas = DbSchemas()
    assert schemas.analysis == "tactix_analysis"
    assert schemas.pgn == "tactix_pgns"


def test_db_schemas_custom_values() -> None:
    schemas = DbSchemas(analysis="analysis_schema", pgn="pgn_schema")
    assert schemas.analysis == "analysis_schema"
    assert schemas.pgn == "pgn_schema"
