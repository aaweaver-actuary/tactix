import { ColumnDef } from '@tanstack/react-table';
import { createPortal } from 'react-dom';
import { DashboardPayload } from '../api';
import Badge from './Badge';
import ModalCloseButton from './ModalCloseButton';
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
            <ModalCloseButton
              onClick={onClose}
              ariaLabel="Close recent games"
              testId="recent-games-modal-close"
            />
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
