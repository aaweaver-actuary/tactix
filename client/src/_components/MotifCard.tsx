import BaseCard, { BaseCardDragHandleProps } from './BaseCard';
import Text from './Text';

interface MotifCardProps {
  motif: string;
  found: number;
  total: number;
  missed: number;
  failedAttempt: number;
  dragHandleProps?: BaseCardDragHandleProps;
  dragHandleLabel?: string;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export default function MotifCard({
  motif,
  found,
  total,
  missed,
  failedAttempt,
  dragHandleProps,
  dragHandleLabel,
  onCollapsedChange,
}: MotifCardProps) {
  const header = (
    <div className="flex flex-col gap-1">
      <Text mode="uppercase" value={motif} />
      <Text mode="teal" size="2xl" value={`${found}/${total}`} />
      <Text
        size="xs"
        mode="normal"
        value={`${missed} missed, ${failedAttempt} failed`}
      />
    </div>
  );

  return (
    <BaseCard
      className="p-4"
      header={header}
      dragHandleProps={dragHandleProps}
      dragHandleLabel={dragHandleLabel}
      onCollapsedChange={onCollapsedChange}
    >
      {null}
    </BaseCard>
  );
}
