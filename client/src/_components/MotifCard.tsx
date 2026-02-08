import BaseCard, { BaseCardDragProps } from './BaseCard';
import Text from './Text';

interface MotifCardProps extends BaseCardDragProps {
  motif: string;
  found: number;
  total: number;
  missed: number;
  failedAttempt: number;
}

export default function MotifCard({
  motif,
  found,
  total,
  missed,
  failedAttempt,
  ...dragProps
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
    <BaseCard className="p-4" header={header} {...dragProps}>
      {null}
    </BaseCard>
  );
}
