import { createPortal } from 'react-dom';

import type {
  PostgresAnalysisRow,
  PostgresRawPgnsSummary,
  PostgresStatus,
} from '../api';
import BaseButton from './BaseButton';
import ErrorCard from './ErrorCard';
import ModalShell from './ModalShell';
import PostgresAnalysisCard from './PostgresAnalysisCard';
import PostgresRawPgnsCard from './PostgresRawPgnsCard';
import PostgresStatusCard from './PostgresStatusCard';
import Text from './Text';

interface DatabaseModalProps {
  open: boolean;
  onClose: () => void;
  status: PostgresStatus | null;
  statusLoading: boolean;
  statusError?: string | null;
  rawPgns: PostgresRawPgnsSummary | null;
  rawPgnsLoading: boolean;
  rawPgnsError?: string | null;
  analysisRows: PostgresAnalysisRow[];
  analysisLoading: boolean;
  analysisError?: string | null;
}

export default function DatabaseModal({
  open,
  onClose,
  status,
  statusLoading,
  statusError,
  rawPgns,
  rawPgnsLoading,
  rawPgnsError,
  analysisRows,
  analysisLoading,
  analysisError,
}: DatabaseModalProps) {
  if (!open) return null;

  const errors = [statusError, rawPgnsError, analysisError].filter(
    (value): value is string => Boolean(value),
  );

  return createPortal(
    <ModalShell
      testId="database-modal"
      onClose={onClose}
      panelClassName="max-w-5xl"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Text mode="uppercase" value="Database" />
          <div className="text-xs text-sand/60">
            Postgres status, raw PGNs, and analysis results
          </div>
        </div>
        <BaseButton
          onClick={onClose}
          className="rounded-md border border-white/10 px-3 py-1 text-xs text-sand/70 hover:border-white/30"
          aria-label="Close database"
          data-testid="database-modal-close"
        >
          Close
        </BaseButton>
      </div>
      {errors.length ? (
        <div className="mt-4 space-y-3">
          {errors.map((message) => (
            <ErrorCard key={message} message={message} />
          ))}
        </div>
      ) : null}
      <div className="mt-4 space-y-4">
        <PostgresStatusCard
          status={status}
          loading={statusLoading}
          collapsible={false}
          defaultCollapsed={false}
        />
        <PostgresRawPgnsCard
          data={rawPgns}
          loading={rawPgnsLoading}
          error={rawPgnsError}
          collapsible={false}
          defaultCollapsed={false}
        />
        <PostgresAnalysisCard
          rows={analysisRows}
          loading={analysisLoading}
          collapsible={false}
          defaultCollapsed={false}
        />
      </div>
    </ModalShell>,
    document.body,
  );
}
