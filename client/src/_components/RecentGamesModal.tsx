import { ColumnDef } from '@tanstack/react-table';
import { createPortal } from 'react-dom';
import { DashboardPayload } from '../api';
import Badge from './Badge';
import BaseButton from './BaseButton';
import ModalHeader from './ModalHeader';
import ModalShell from './ModalShell';
import RecentGamesTable from './RecentGamesTable';

interface RecentGamesModalProps {
  open: boolean;
  onClose: () => void;
  data: DashboardPayload['recent_games'];
  columns: ColumnDef<DashboardPayload['recent_games'][number]>[];
  onRowClick?: (row: DashboardPayload['recent_games'][number]) => void;
  rowTestId?: (
    row: DashboardPayload['recent_games'][number],
    index: number,
  ) => string;
}

export default function RecentGamesModal({
  open,
  onClose,
  data,
  columns,
  onRowClick,
  rowTestId,
}: RecentGamesModalProps) {
  if (!open) return null;

  return createPortal(
    <ModalShell
      testId="recent-games-modal"
      onClose={onClose}
      panelClassName="max-w-5xl"
    >
      <ModalHeader
        title="Recent games"
        description="Latest games across all sources"
        className="flex-wrap"
        rightSlot={
          <div className="flex items-center gap-2">
            <Badge label="All sources" />
            <BaseButton
              onClick={onClose}
              className="rounded-md border border-white/10 px-3 py-1 text-xs text-sand/70 hover:border-white/30"
              aria-label="Close recent games"
              data-testid="recent-games-modal-close"
            >
              Close
            </BaseButton>
          </div>
        }
      />
      <div className="mt-4">
        <RecentGamesTable
          data={data}
          columns={columns}
          onRowClick={onRowClick}
          rowTestId={rowTestId}
        />
      </div>
    </ModalShell>,
    document.body,
  );
}
