import shutil
from pathlib import Path

from tactix.config import Settings
from tactix.duckdb_store import (
    get_connection,
    init_schema,
    insert_positions,
    upsert_raw_pgns,
    upsert_tactic_with_outcome,
)
from tactix.pgn_utils import split_pgn_chunks
from tactix.position_extractor import extract_positions
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position

fixture_path = Path('tests/fixtures/chesscom_bullet_sample.pgn')
chunks = split_pgn_chunks(fixture_path.read_text())
mate_pgn = next(chunk for chunk in chunks if 'Bullet Fixture 4' in chunk)

settings = Settings(
    source='chesscom',
    chesscom_user='chesscom',
    chesscom_profile='bullet',
    stockfish_path=Path(shutil.which('stockfish') or 'stockfish'),
    stockfish_movetime_ms=60,
    stockfish_depth=None,
    stockfish_multipv=1,
)
settings.apply_chesscom_profile('bullet')

positions = extract_positions(
    mate_pgn,
    settings.chesscom_user,
    settings.source,
    game_id='bullet-mate-2',
    side_to_move_filter='black',
)
mate_position = next(pos for pos in positions if pos['uci'] == 'c5f2')

conn = get_connection(Path('data/tactix.duckdb'))
init_schema(conn)
upsert_raw_pgns(
    conn,
    [
        {
            'game_id': 'bullet-mate-2',
            'user': settings.chesscom_user,
            'source': settings.source,
            'pgn': mate_pgn,
        }
    ],
)
position_ids = insert_positions(conn, [mate_position])
mate_position['position_id'] = position_ids[0]

with StockfishEngine(settings) as engine:
    result = analyze_position(mate_position, engine, settings=settings)

if result is None:
    raise SystemExit('No tactic result generated')

tactic_row, outcome_row = result
upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
print('Updated tactic:', tactic_row['best_uci'], 'severity', tactic_row['severity'])
