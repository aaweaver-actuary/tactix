import BaseCard, { BaseCardDragProps } from './BaseCard';
import MotifCardHeader from './MotifCardHeader';

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
  return (
    <BaseCard
      className="p-4"
      header={
        <MotifCardHeader
          motif={motif}
          found={found}
          total={total}
          missed={missed}
          failedAttempt={failedAttempt}
        />
      }
      {...dragProps}
    >
      {null}
    </BaseCard>
  );
}
