import { PostgresAnalysisRow } from '../api';
import Badge from './Badge';
import BaseCard, { BaseCardDragHandleProps } from './BaseCard';
import Text from './Text';

interface PostgresAnalysisCardProps {
  rows: PostgresAnalysisRow[];
  loading: boolean;
  dragHandleProps?: BaseCardDragHandleProps;
  dragHandleLabel?: string;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export default function PostgresAnalysisCard({
  rows,
  loading,
  dragHandleProps,
  dragHandleLabel,
  onCollapsedChange,
}: PostgresAnalysisCardProps) {
  if (!rows.length && !loading) return null;

  return (
    <BaseCard
      className="p-4"
      header={
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-display text-sand">
            Postgres analysis results
          </h3>
          <Badge label={`${rows.length} rows`} />
        </div>
      }
      contentClassName="pt-3"
      data-testid="postgres-analysis"
      dragHandleProps={dragHandleProps}
      dragHandleLabel={dragHandleLabel}
      onCollapsedChange={onCollapsedChange}
    >
      {rows.length ? (
        <ul className="space-y-2 text-xs text-sand/70">
          {rows.slice(0, 5).map((row) => (
            <li key={row.tactic_id} className="flex flex-wrap gap-2">
              <span className="font-mono text-sand/50">#{row.tactic_id}</span>
              <span className="text-sand">
                {row.motif ?? 'unknown'} · {row.result ?? 'n/a'}
              </span>
              {row.best_uci ? <Badge label={row.best_uci} /> : null}
              {row.severity !== null && row.severity !== undefined ? (
                <Badge label={`sev ${row.severity.toFixed(2)}`} />
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <Text
          size="xs"
          mode="normal"
          value={loading ? 'Loading analysis rows...' : 'No analysis rows yet'}
          mt="2"
        />
      )}
    </BaseCard>
  );
}
