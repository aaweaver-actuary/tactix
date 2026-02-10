import { useState } from 'react';
import { createPortal } from 'react-dom';
import { CHESSCOM_PROFILE_OPTIONS } from '../utils/CHESSCOM_PROFILE_OPTIONS';
import { LICHESS_PROFILE_OPTIONS } from '../utils/LICHESS_PROFILE_OPTIONS';
import { SOURCE_OPTIONS } from '../utils/SOURCE_OPTIONS';
import { ChessPlatform, ChesscomProfile, LichessProfile } from '../types';
import Badge from './Badge';
import BaseButton from './BaseButton';
import BaseCard, { BaseCardDragProps } from './BaseCard';
import ModalShell from './ModalShell';
import Text from './Text';

interface FiltersState {
  motif: string;
  timeControl: string;
  ratingBucket: string;
  startDate: string;
  endDate: string;
}

interface FiltersCardProps extends BaseCardDragProps {
  source: ChessPlatform;
  loading: boolean;
  lichessProfile: LichessProfile;
  chesscomProfile: ChesscomProfile;
  filters: FiltersState;
  motifOptions: string[];
  timeControlOptions: string[];
  ratingOptions: string[];
  onSourceChange: (next: ChessPlatform) => void;
  onLichessProfileChange: (next: LichessProfile) => void;
  onChesscomProfileChange: (next: ChesscomProfile) => void;
  onFiltersChange: (next: FiltersState) => void;
  onResetFilters: () => void;
  modalOpen?: boolean;
  onModalOpenChange?: (open: boolean) => void;
  showOpenButton?: boolean;
  showCard?: boolean;
}

export default function FiltersCard({
  source,
  loading,
  lichessProfile,
  chesscomProfile,
  filters,
  motifOptions,
  timeControlOptions,
  ratingOptions,
  onSourceChange,
  onLichessProfileChange,
  onChesscomProfileChange,
  onFiltersChange,
  onResetFilters,
  modalOpen,
  onModalOpenChange,
  showOpenButton = true,
  showCard = true,
  ...dragProps
}: FiltersCardProps) {
  const [internalModalOpen, setInternalModalOpen] = useState(false);
  const resolvedModalOpen = modalOpen ?? internalModalOpen;
  const setModalOpen = onModalOpenChange ?? setInternalModalOpen;
  const updateFilter = (key: keyof FiltersState, value: string) =>
    onFiltersChange({ ...filters, [key]: value });

  const filtersBody = (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3">
      <label className="text-xs text-sand/60 flex flex-col gap-2">
        Site / source
        <select
          className="rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand"
          value={source}
          onChange={(event) =>
            onSourceChange(event.target.value as ChessPlatform)
          }
          disabled={loading}
          data-testid="filter-source"
        >
          {SOURCE_OPTIONS.map((opt) => (
            <option key={opt.id} value={opt.id}>
              {opt.label}
            </option>
          ))}
        </select>
      </label>
      {source === 'lichess' ? (
        <label className="text-xs text-sand/60 flex flex-col gap-2">
          Lichess profile
          <select
            className="rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand"
            value={lichessProfile}
            onChange={(event) =>
              onLichessProfileChange(event.target.value as LichessProfile)
            }
            disabled={loading}
            data-testid="filter-lichess-profile"
          >
            {LICHESS_PROFILE_OPTIONS.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {source === 'chesscom' ? (
        <label className="text-xs text-sand/60 flex flex-col gap-2">
          Chess.com time class
          <select
            className="rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand"
            value={chesscomProfile}
            onChange={(event) =>
              onChesscomProfileChange(event.target.value as ChesscomProfile)
            }
            disabled={loading}
            data-testid="filter-chesscom-profile"
          >
            {CHESSCOM_PROFILE_OPTIONS.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <label className="text-xs text-sand/60 flex flex-col gap-2">
        Motif
        <select
          className="rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand"
          value={filters.motif}
          onChange={(event) => updateFilter('motif', event.target.value)}
          disabled={loading}
          data-testid="filter-motif"
        >
          {motifOptions.map((motif) => (
            <option key={motif} value={motif}>
              {motif === 'all' ? 'All motifs' : motif}
            </option>
          ))}
        </select>
      </label>
      <label className="text-xs text-sand/60 flex flex-col gap-2">
        Time control
        <select
          className="rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand"
          value={filters.timeControl}
          onChange={(event) => updateFilter('timeControl', event.target.value)}
          disabled={loading}
          data-testid="filter-time-control"
        >
          {timeControlOptions.map((value) => (
            <option key={value} value={value}>
              {value === 'all' ? 'All time controls' : value}
            </option>
          ))}
        </select>
      </label>
      <label className="text-xs text-sand/60 flex flex-col gap-2">
        Rating band
        <select
          className="rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand"
          value={filters.ratingBucket}
          onChange={(event) => updateFilter('ratingBucket', event.target.value)}
          disabled={loading}
          data-testid="filter-rating"
        >
          {ratingOptions.map((value) => (
            <option key={value} value={value}>
              {value === 'all' ? 'All ratings' : value}
            </option>
          ))}
        </select>
      </label>
      <div className="flex flex-col gap-2 text-xs text-sand/60">
        Date range
        <div className="flex gap-2">
          <input
            type="date"
            value={filters.startDate}
            onChange={(event) => updateFilter('startDate', event.target.value)}
            className="flex-1 rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand"
            disabled={loading}
            data-testid="filter-start-date"
          />
          <input
            type="date"
            value={filters.endDate}
            onChange={(event) => updateFilter('endDate', event.target.value)}
            className="flex-1 rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand"
            disabled={loading}
            data-testid="filter-end-date"
          />
        </div>
        <BaseButton
          className="self-start text-xs text-sand/50 hover:text-sand"
          onClick={onResetFilters}
          disabled={loading}
        >
          Reset filters
        </BaseButton>
      </div>
    </div>
  );

  return (
    <>
      {showCard ? (
        <BaseCard
          className="p-4"
          header={
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-display text-sand">Filters</h3>
                <Badge label="Live" />
              </div>
              {showOpenButton ? (
                <BaseButton
                  className="rounded-md border border-white/10 px-3 py-1 text-xs text-sand/70 hover:border-white/30"
                  onClick={() => setModalOpen(true)}
                  data-testid="filters-open"
                  disabled={loading}
                >
                  Open filters
                </BaseButton>
              ) : null}
            </div>
          }
          contentClassName="pt-3"
          {...dragProps}
        >
          <Text value="Refine the dashboard using source and motif filters." />
        </BaseCard>
      ) : null}
      {resolvedModalOpen
        ? createPortal(
            <ModalShell
              testId="filters-modal"
              onClose={() => setModalOpen(false)}
              panelClassName="max-w-5xl"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <Text mode="uppercase" value="Filters" />
                  <div className="text-xs text-sand/60">
                    Adjust sources, motifs, and time windows
                  </div>
                </div>
                <BaseButton
                  onClick={() => setModalOpen(false)}
                  className="rounded-md border border-white/10 px-3 py-1 text-xs text-sand/70 hover:border-white/30"
                  aria-label="Close filters"
                  data-testid="filters-modal-close"
                >
                  Close
                </BaseButton>
              </div>
              <div className="mt-4">{filtersBody}</div>
            </ModalShell>,
            document.body,
          )
        : null}
    </>
  );
}
