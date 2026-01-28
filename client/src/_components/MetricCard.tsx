import BaseCard from './BaseCard';
import Text from './Text';

interface MetricCardProps {
  title: string;
  value: string;
  note?: string;
}

/**
 * Displays a metric card with a title, value, and optional note.
 *
 * @param title - The title of the metric.
 * @param value - The value to display for the metric.
 * @param note - An optional note to display below the value.
 *
 * @returns A styled card component showing the metric information.
 */
export default function MetricCard({ title, value, note }: MetricCardProps) {
  const header = (
    <div className="flex flex-col gap-2">
      <Text mode="uppercase" value={title} />
      <Text mode="teal" size="3xl" value={value} />
    </div>
  );

  return (
    <BaseCard
      className="p-4"
      header={header}
      contentClassName={note ? 'pt-2' : undefined}
    >
      {note ? <Text size="xs" mode="normal" value={note} /> : null}
    </BaseCard>
  );
}
