import { PostgresRawPgnsSummary } from '../api';
import Badge from './Badge';
import BaseCard, { BaseCardDragHandleProps } from './BaseCard';
import Text from './Text';

interface PostgresRawPgnsCardProps {
  data: PostgresRawPgnsSummary | null;
  loading: boolean;
  error?: string | null;
  dragHandleProps?: BaseCardDragHandleProps;
  dragHandleLabel?: string;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export default function PostgresRawPgnsCard({
  data,
  loading,
  error,
  dragHandleProps,
  dragHandleLabel,
  onCollapsedChange,
}: PostgresRawPgnsCardProps) {
  if (!data && !loading && !error) return null;

  return (
    <BaseCard
      className="p-4"
      header={
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-display text-sand">Postgres raw PGNs</h3>
          <Badge label={data?.status ?? 'loading'} />
        </div>
      }
      contentClassName="pt-3"
      data-testid="postgres-raw-pgns"
      dragHandleProps={dragHandleProps}
      dragHandleLabel={dragHandleLabel}
      onCollapsedChange={onCollapsedChange}
    >
      {error ? <Text mode="error" value={error} mt="2" /> : null}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="flex flex-col gap-1">
          <Text mode="uppercase" value="Total rows" />
          <Text
            size="sm"
            mode="normal"
            value={data ? data.total_rows.toLocaleString() : '...'}
          />
        </div>
        <div className="flex flex-col gap-1">
          <Text mode="uppercase" value="Distinct games" />
          <Text
            size="sm"
            mode="normal"
            value={data ? data.distinct_games.toLocaleString() : '...'}
          />
        </div>
        <div className="flex flex-col gap-1">
          <Text mode="uppercase" value="Latest ingest" />
          <Text
            size="sm"
            mode="normal"
            value={
              data?.latest_ingested_at
                ? new Date(data.latest_ingested_at).toLocaleString()
                : 'n/a'
            }
          />
        </div>
      </div>
      <div className="mt-4">
        <Text mode="uppercase" value="By source" />
        {data?.sources?.length ? (
          <ul className="mt-2 space-y-2 text-xs text-sand/70">
            {data.sources.map((row) => (
              <li key={row.source} className="flex flex-wrap gap-2">
                <Badge label={row.source} />
                <span className="text-sand">
                  {row.total_rows.toLocaleString()} rows
                </span>
                <span className="text-sand/60">
                  {row.distinct_games.toLocaleString()} games
                </span>
                {row.latest_ingested_at ? (
                  <span className="text-sand/50">
                    {new Date(row.latest_ingested_at).toLocaleString()}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <Text
            size="xs"
            mode="normal"
            value={loading ? 'Loading raw PGNs...' : 'No raw PGN rows yet'}
            mt="2"
          />
        )}
      </div>
    </BaseCard>
  );
}
