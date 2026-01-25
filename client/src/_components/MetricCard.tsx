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
  return (
    <div className="card p-4 flex flex-col gap-2">
      <Text mode="uppercase" value={title} />
      <Text mode="teal" size="3xl" value={value} />
      {note ? <Text size="xs" mode="normal" value={note} /> : null}
    </div>
  );
}
