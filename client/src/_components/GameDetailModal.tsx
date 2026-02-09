import { ColumnDef } from '@tanstack/react-table';
import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { GameDetailResponse } from '../api';
import BaseButton from './BaseButton';
import BaseTable from './BaseTable';
import Badge from './Badge';
import ModalShell from './ModalShell';
import Text from './Text';

const BLUNDER_EVAL_DELTA = -200;

type AnalysisRow = {
  key: string | number;
  moveLabel: string;
  moveSan: string;
  motif: string;
  evalCp: number | null;
  evalDelta: number | null;
  blunder: boolean;
};

const formatEvalValue = (value: number | null) =>
  value !== null ? value : '--';

const renderEvalFlag = (blunder: boolean, evalDelta: number | null) => {
  if (blunder) return <Badge label="Blunder" />;
  if (evalDelta !== null) return <span className="text-sand/60">OK</span>;
  return <span className="text-sand/40">--</span>;
};

const AnalysisMoveCell = ({
  moveLabel,
  moveSan,
}: {
  moveLabel: string;
  moveSan: string;
}) => (
  <div>
    <div className="text-sand/70">{moveLabel}</div>
    <div className="font-mono text-xs">{moveSan}</div>
  </div>
);

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
  const [currentMoveIndex, setCurrentMoveIndex] = useState(0);
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
        evalCp:
          row.eval_cp !== null && row.eval_cp !== undefined
            ? row.eval_cp
            : null,
        evalDelta,
        blunder,
      };
    });
  }, [game]);

  const analysisColumns = useMemo<ColumnDef<AnalysisRow>[]>(
    () => [
      {
        header: 'Move',
        accessorKey: 'moveLabel',
        cell: ({ row }) => (
          <AnalysisMoveCell
            moveLabel={row.original.moveLabel}
            moveSan={row.original.moveSan}
          />
        ),
      },
      {
        header: 'Motif',
        accessorKey: 'motif',
        cell: ({ row }) => (
          <span className="uppercase tracking-wide">{row.original.motif}</span>
        ),
      },
      {
        header: 'Eval (cp)',
        accessorKey: 'evalCp',
        cell: ({ row }) => (
          <span className="font-mono">
            {formatEvalValue(row.original.evalCp)}
          </span>
        ),
      },
      {
        header: 'Delta',
        accessorKey: 'evalDelta',
        cell: ({ row }) => (
          <span className="font-mono">
            {formatEvalValue(row.original.evalDelta)}
          </span>
        ),
      },
      {
        header: 'Flags',
        id: 'flags',
        cell: ({ row }) =>
          renderEvalFlag(row.original.blunder, row.original.evalDelta),
      },
    ],
    [],
  );

  const moveCount = moves.length;
  const lastMoveIndex = moveCount > 0 ? moveCount - 1 : 0;
  const currentMove = moveCount ? moves[currentMoveIndex] : 'No moves loaded';

  const metadataRows = useMemo(() => {
    if (!game) return [];
    const meta = game.metadata;
    const entries = [
      { label: 'Event', value: meta.event },
      { label: 'Site', value: meta.site },
      { label: 'UTC date', value: meta.utc_date },
      { label: 'UTC time', value: meta.utc_time },
      { label: 'Termination', value: meta.termination },
      { label: 'Time control', value: meta.time_control },
      { label: 'Result', value: meta.result },
      {
        label: 'Start',
        value:
          meta.start_timestamp_ms !== null &&
          meta.start_timestamp_ms !== undefined
            ? new Date(meta.start_timestamp_ms).toLocaleString()
            : null,
      },
    ];
    return entries.filter((entry) => Boolean(entry.value));
  }, [game]);

  useEffect(() => {
    if (!open) return;
    setCurrentMoveIndex(lastMoveIndex);
  }, [open, lastMoveIndex]);

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (!moveCount) return;
      switch (event.key) {
        case 'ArrowLeft':
          event.preventDefault();
          setCurrentMoveIndex((prev) => Math.max(0, prev - 1));
          break;
        case 'ArrowRight':
          event.preventDefault();
          setCurrentMoveIndex((prev) => Math.min(lastMoveIndex, prev + 1));
          break;
        case 'ArrowUp':
          event.preventDefault();
          setCurrentMoveIndex(0);
          break;
        case 'ArrowDown':
          event.preventDefault();
          setCurrentMoveIndex(lastMoveIndex);
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [open, moveCount, lastMoveIndex]);
  if (!open) {
    return null;
  }

  const modalBody = (
    <ModalShell
      testId="game-detail-modal"
      onClose={onClose}
      alignClassName="items-end sm:items-center"
      panelClassName="max-w-5xl"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Text mode="uppercase" value="Game details" />
          <div className="text-xs text-sand/60">
            Review moves, metadata, and analysis
          </div>
        </div>
        <BaseButton
          onClick={onClose}
          className="rounded-md border border-white/10 px-3 py-1 text-xs text-sand/70 hover:border-white/30"
          aria-label="Close game details"
          data-testid="game-detail-close"
        >
          Close
        </BaseButton>
      </div>

      <div className="mt-4">
        <BaseTable
          data={analysisRows}
          columns={analysisColumns}
          emptyMessage="No analysis rows found."
          enablePagination={false}
          tableClassName="text-xs"
          headerCellClassName="py-1"
          cellClassName="py-1"
        />
      </div>

      {loading ? (
        <div className="mt-4 text-sm text-sand/70">Loading game details...</div>
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

          <div className="grid grid-cols-1 gap-4 md:grid-cols-[1.2fr_1fr]">
            <div
              className="rounded-lg border border-white/10 bg-white/5 p-4"
              data-testid="game-detail-players"
            >
              <Text mode="uppercase" value="Players" />
              <div className="mt-3 space-y-2 text-sm text-sand/90">
                <div className="flex items-center justify-between">
                  <span className="text-sand/70">White</span>
                  <span className="font-mono">
                    {game.metadata.white_player || 'Unknown'}
                    {game.metadata.white_elo
                      ? ` (${game.metadata.white_elo})`
                      : ''}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sand/70">Black</span>
                  <span className="font-mono">
                    {game.metadata.black_player || 'Unknown'}
                    {game.metadata.black_elo
                      ? ` (${game.metadata.black_elo})`
                      : ''}
                  </span>
                </div>
              </div>
            </div>
            <div
              className="rounded-lg border border-white/10 bg-white/5 p-4"
              data-testid="game-detail-metadata"
            >
              <Text mode="uppercase" value="Game metadata" />
              <div className="mt-3 space-y-2 text-xs text-sand/70">
                {metadataRows.length ? (
                  metadataRows.map((entry) => (
                    <div
                      key={entry.label}
                      className="flex items-center justify-between gap-2"
                    >
                      <span className="uppercase tracking-wide">
                        {entry.label}
                      </span>
                      <span className="text-sand/90">{entry.value}</span>
                    </div>
                  ))
                ) : (
                  <div className="text-sand/50">No metadata available.</div>
                )}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-4">
            <div className="rounded-lg border border-white/10 bg-white/5 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Text mode="uppercase" value="Move list" />
                <div className="flex flex-wrap items-center gap-2">
                  <Badge label={`${moves.length} ply`} />
                  <Badge label={currentMove} />
                </div>
              </div>
              <div
                className="mt-3 flex flex-wrap items-center gap-2"
                data-testid="game-detail-navigation"
              >
                <BaseButton
                  className="rounded-md border border-white/10 px-2 py-1 text-xs text-sand/70 hover:border-white/30 disabled:opacity-40"
                  onClick={() => setCurrentMoveIndex(0)}
                  disabled={!moveCount || currentMoveIndex === 0}
                  aria-label="First move"
                  data-testid="game-detail-nav-first"
                >
                  First
                </BaseButton>
                <BaseButton
                  className="rounded-md border border-white/10 px-2 py-1 text-xs text-sand/70 hover:border-white/30 disabled:opacity-40"
                  onClick={() =>
                    setCurrentMoveIndex((prev) => Math.max(0, prev - 1))
                  }
                  disabled={!moveCount || currentMoveIndex === 0}
                  aria-label="Previous move"
                  data-testid="game-detail-nav-prev"
                >
                  Prev
                </BaseButton>
                <BaseButton
                  className="rounded-md border border-white/10 px-2 py-1 text-xs text-sand/70 hover:border-white/30 disabled:opacity-40"
                  onClick={() =>
                    setCurrentMoveIndex((prev) =>
                      Math.min(lastMoveIndex, prev + 1),
                    )
                  }
                  disabled={!moveCount || currentMoveIndex === lastMoveIndex}
                  aria-label="Next move"
                  data-testid="game-detail-nav-next"
                >
                  Next
                </BaseButton>
                <BaseButton
                  className="rounded-md border border-white/10 px-2 py-1 text-xs text-sand/70 hover:border-white/30 disabled:opacity-40"
                  onClick={() => setCurrentMoveIndex(lastMoveIndex)}
                  disabled={!moveCount || currentMoveIndex === lastMoveIndex}
                  aria-label="Last move"
                  data-testid="game-detail-nav-last"
                >
                  Last
                </BaseButton>
                <span className="text-xs text-sand/50">
                  Use ←/→ for prev/next, ↑/↓ for start/end
                </span>
              </div>
              <ol
                className="mt-3 max-h-64 space-y-1 overflow-y-auto text-sm text-sand/90"
                data-testid="game-detail-moves"
              >
                {moves.length ? (
                  moves.map((move, index) => (
                    <li
                      key={`${move}-${index}`}
                      data-testid="game-move-row"
                      data-selected={
                        index === currentMoveIndex ? 'true' : 'false'
                      }
                      className={
                        index === currentMoveIndex
                          ? 'rounded-md bg-teal/15 px-2 py-1 text-sand'
                          : undefined
                      }
                      onClick={() => setCurrentMoveIndex(index)}
                    >
                      {move}
                    </li>
                  ))
                ) : (
                  <li className="text-sand/60">No moves available.</li>
                )}
              </ol>
              <div
                className="mt-2 text-xs text-sand/60"
                data-testid="game-detail-current-move"
              >
                Current: <span className="text-sand/90">{currentMove}</span>
              </div>
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
                    {analysisRows.length ? (
                      analysisRows.map((row) => (
                        <tr key={row.key} className="border-b border-white/5">
                          <td className="py-1">
                            <AnalysisMoveCell
                              moveLabel={row.moveLabel}
                              moveSan={row.moveSan}
                            />
                          </td>
                          <td className="py-1 uppercase tracking-wide">
                            {row.motif}
                          </td>
                          <td className="py-1 font-mono">
                            {formatEvalValue(row.evalCp)}
                          </td>
                          <td className="py-1 font-mono">
                            {formatEvalValue(row.evalDelta)}
                          </td>
                          <td className="py-1">
                            {renderEvalFlag(row.blunder, row.evalDelta)}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="py-2 text-sand/60">
                          No analysis rows found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </ModalShell>
  );

  return createPortal(modalBody, document.body);
}
