import { useMemo } from 'react';
import { GameDetailResponse } from '../api';
import Badge from './Badge';
import Text from './Text';

const BLUNDER_EVAL_DELTA = -200;

interface GameDetailModalProps {
  open: boolean;
  onClose: () => void;
  game: GameDetailResponse | null;
  moves: string[];
  loading: boolean;
  error?: string | null;
}

export default function GameDetailModal({
  open,
  onClose,
  game,
  moves,
  loading,
  error,
}: GameDetailModalProps) {
  const analysisRows = useMemo(() => {
    if (!game?.analysis?.length) return [];
    return game.analysis.map((row) => {
      const evalDelta =
        row.eval_delta !== null && row.eval_delta !== undefined
          ? Number(row.eval_delta)
          : null;
      const blunder = evalDelta !== null && evalDelta <= BLUNDER_EVAL_DELTA;
      const moveNumber = row.move_number ?? null;
      const ply = row.ply ?? null;
      const moveLabel = moveNumber
        ? `Move ${moveNumber}${ply !== null ? `.${ply}` : ''}`
        : 'Move --';
      const moveSan = row.san || row.user_uci || '--';
      return {
        key: row.tactic_id,
        moveLabel,
        moveSan,
        motif: row.motif || '--',
        result: row.result || '--',
        best: row.best_uci || '--',
        evalCp:
          row.eval_cp !== null && row.eval_cp !== undefined
            ? row.eval_cp
            : null,
        evalDelta,
        blunder,
      };
    });
  }, [game]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-night/80 px-4"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
      data-testid="game-detail-overlay"
    >
      <div
        className="w-full max-w-4xl rounded-xl border border-white/10 bg-night p-6 shadow-xl"
        onClick={(event) => event.stopPropagation()}
        data-testid="game-detail-modal"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-xl font-display text-sand">Game details</h3>
            <Text value="Move list and analysis" size="sm" />
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-white/10 px-3 py-1 text-xs text-sand/70 hover:border-white/30"
            aria-label="Close game details"
            data-testid="game-detail-close"
          >
            Close
          </button>
        </div>

        {loading ? (
          <div className="mt-4 text-sm text-sand/70">
            Loading game details...
          </div>
        ) : error ? (
          <div className="mt-4 text-sm text-rust">{error}</div>
        ) : !game ? (
          <div className="mt-4 text-sm text-sand/70">
            Select a game to view details.
          </div>
        ) : (
          <div className="mt-4 space-y-5">
            <div className="flex flex-wrap items-center gap-2 text-xs text-sand/70">
              {game.metadata.white_player || game.metadata.black_player ? (
                <Badge
                  label={`${game.metadata.white_player || 'White'} vs ${
                    game.metadata.black_player || 'Black'
                  }`}
                />
              ) : null}
              {game.metadata.result ? (
                <Badge label={game.metadata.result} />
              ) : null}
              {game.metadata.time_control ? (
                <Badge label={`TC ${game.metadata.time_control}`} />
              ) : null}
              {game.metadata.user_rating ? (
                <Badge label={`Rating ${game.metadata.user_rating}`} />
              ) : null}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-4">
              <div className="rounded-lg border border-white/10 bg-white/5 p-4">
                <div className="flex items-center justify-between">
                  <Text mode="uppercase" value="Move list" />
                  <Badge label={`${moves.length} ply`} />
                </div>
                <ol
                  className="mt-3 max-h-64 space-y-1 overflow-y-auto text-sm text-sand/90"
                  data-testid="game-detail-moves"
                >
                  {moves.length ? (
                    moves.map((move) => (
                      <li key={move} data-testid="game-move-row">
                        {move}
                      </li>
                    ))
                  ) : (
                    <li className="text-sand/60">No moves available.</li>
                  )}
                </ol>
              </div>

              <div className="rounded-lg border border-white/10 bg-white/5 p-4">
                <div className="flex items-center justify-between">
                  <Text mode="uppercase" value="Analysis" />
                  <Badge label="Engine eval + blunders" />
                </div>
                <div
                  className="mt-3 max-h-64 overflow-y-auto text-sm text-sand/90"
                  data-testid="game-detail-analysis"
                >
                  {analysisRows.length ? (
                    <table className="min-w-full text-xs">
                      <thead className="text-sand/60">
                        <tr>
                          <th className="text-left py-1">Move</th>
                          <th className="text-left py-1">Motif</th>
                          <th className="text-left py-1">Eval (cp)</th>
                          <th className="text-left py-1">Delta</th>
                          <th className="text-left py-1">Flags</th>
                        </tr>
                      </thead>
                      <tbody>
                        {analysisRows.map((row) => (
                          <tr key={row.key} className="border-b border-white/5">
                            <td className="py-1">
                              <div className="text-sand/70">
                                {row.moveLabel}
                              </div>
                              <div className="font-mono text-xs">
                                {row.moveSan}
                              </div>
                            </td>
                            <td className="py-1 uppercase tracking-wide">
                              {row.motif}
                            </td>
                            <td className="py-1 font-mono">
                              {row.evalCp !== null ? row.evalCp : '--'}
                            </td>
                            <td className="py-1 font-mono">
                              {row.evalDelta !== null ? row.evalDelta : '--'}
                            </td>
                            <td className="py-1">
                              {row.blunder ? (
                                <Badge label="Blunder" />
                              ) : row.evalDelta !== null ? (
                                <span className="text-sand/60">OK</span>
                              ) : (
                                <span className="text-sand/40">--</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="text-sand/60">No analysis rows found.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
