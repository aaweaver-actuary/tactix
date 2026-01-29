import { Droppable, Draggable } from '@hello-pangea/dnd';
import { DashboardPayload } from '../api';
import Badge from './Badge';
import BaseCard, { BaseCardDragHandleProps } from './BaseCard';
import MotifCard from './MotifCard';

interface MetricsGridProps {
  metricsData: DashboardPayload['metrics'];
  dragHandleProps?: BaseCardDragHandleProps;
  dragHandleLabel?: string;
  onCollapsedChange?: (collapsed: boolean) => void;
  droppableId: string;
  dropIndicatorIndex?: number | null;
}

/**
 * Renders a grid of metric cards displaying motif breakdown data.
 *
 * @param metricsData - An array of metric objects containing motif statistics.
 * @returns A React component displaying the motif breakdown in a card layout.
 *
 * @remarks
 * Each metric card shows the motif name, the number of found and total motifs,
 * and a note with missed and failed attempt counts.
 *
 * @example
 * <MetricsGrid metricsData={[
 *   { motif: 'Motif A', found: 5, total: 10, missed: 3, failed_attempt: 2 },
 *   { motif: 'Motif B', found: 8, total: 12, missed: 2, failed_attempt: 2 }
 * ]} />
 */
export default function MetricsGrid({
  metricsData,
  dragHandleProps,
  dragHandleLabel,
  onCollapsedChange,
  droppableId,
  dropIndicatorIndex,
}: MetricsGridProps) {
  const header = (
    <div className="flex items-center justify-between">
      <h3 className="text-lg font-display text-sand">Motif breakdown</h3>
      <Badge label="Updated" />
    </div>
  );

  const motifRows = metricsData.filter(
    (row): row is DashboardPayload['metrics'][number] & { motif: string } =>
      typeof row.motif === 'string' && row.motif.length > 0,
  );

  return (
    <BaseCard
      className="p-4"
      data-testid="motif-breakdown"
      header={header}
      contentClassName="pt-3"
      dragHandleProps={dragHandleProps}
      dragHandleLabel={dragHandleLabel}
      onCollapsedChange={onCollapsedChange}
    >
      <Droppable droppableId={droppableId}>
        {(dropProvided) => (
          <div
            ref={dropProvided.innerRef}
            {...dropProvided.droppableProps}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3"
          >
            {motifRows.map((row, index) => (
              <div key={row.motif} className="contents">
                {dropIndicatorIndex === index ? (
                  <div
                    className="col-span-full h-0.5 rounded-full bg-teal/60"
                    data-testid="motif-drop-indicator"
                  />
                ) : null}
                <Draggable
                  draggableId={row.motif}
                  index={index}
                  disableInteractiveElementBlocking
                >
                  {(dragProvided, dragSnapshot) => (
                    <div
                      ref={dragProvided.innerRef}
                      {...dragProvided.draggableProps}
                      style={dragProvided.draggableProps.style}
                      data-motif-id={row.motif}
                      className={
                        dragSnapshot.isDragging
                          ? 'rounded-xl ring-2 ring-teal/40 shadow-lg'
                          : undefined
                      }
                    >
                      <MotifCard
                        motif={row.motif}
                        found={row.found}
                        total={row.total}
                        missed={row.missed}
                        failedAttempt={row.failed_attempt}
                        dragHandleProps={
                          (dragProvided.dragHandleProps ?? undefined) as
                            | BaseCardDragHandleProps
                            | undefined
                        }
                        dragHandleLabel={`Reorder ${row.motif}`}
                      />
                    </div>
                  )}
                </Draggable>
              </div>
            ))}
            {dropIndicatorIndex === motifRows.length ? (
              <div
                className="col-span-full h-0.5 rounded-full bg-teal/60"
                data-testid="motif-drop-indicator"
              />
            ) : null}
            {dropProvided.placeholder}
          </div>
        )}
      </Droppable>
    </BaseCard>
  );
}
