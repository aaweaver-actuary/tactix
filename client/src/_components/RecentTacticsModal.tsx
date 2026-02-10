import { ColumnDef } from '@tanstack/react-table';
import { createPortal } from 'react-dom';
import { DashboardPayload } from '../api';
import Badge from './Badge';
import BaseButton from './BaseButton';
import ModalShell from './ModalShell';
import TacticsTable from './TacticsTable';
import Text from './Text';

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
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Text mode="uppercase" value="Recent tactics" />
          <div className="text-xs text-sand/60">
            Latest tactics from the current metrics window
          </div>
        </div>
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
      </div>
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
