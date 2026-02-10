import { ColumnDef } from '@tanstack/react-table';
import { createPortal } from 'react-dom';
import { DashboardPayload } from '../api';
import Badge from './Badge';
import BaseButton from './BaseButton';
import ModalHeader from './ModalHeader';
import ModalShell from './ModalShell';
import TacticsTable from './TacticsTable';

interface RecentTacticsModalProps {
  open: boolean;
  onClose: () => void;
  data: DashboardPayload['tactics'];
  columns: ColumnDef<DashboardPayload['tactics'][number]>[];
  onRowClick?: (row: DashboardPayload['tactics'][number]) => void;
  rowTestId?: (row: DashboardPayload['tactics'][number]) => string;
}

export default function RecentTacticsModal({
  open,
  onClose,
  data,
  columns,
  onRowClick,
  rowTestId,
}: RecentTacticsModalProps) {
  if (!open) return null;

  return createPortal(
    <ModalShell
      testId="recent-tactics-modal"
      onClose={onClose}
      panelClassName="max-w-5xl"
    >
      <ModalHeader
        title="Recent tactics"
        description="Latest tactics from the current metrics window"
        className="flex-wrap"
        rightSlot={
          <div className="flex items-center gap-2">
            <Badge label="Live" />
            <BaseButton
              onClick={onClose}
              className="rounded-md border border-white/10 px-3 py-1 text-xs text-sand/70 hover:border-white/30"
              aria-label="Close recent tactics"
              data-testid="recent-tactics-modal-close"
            >
              Close
            </BaseButton>
          </div>
        }
      />
      <div className="mt-4">
        <TacticsTable
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
