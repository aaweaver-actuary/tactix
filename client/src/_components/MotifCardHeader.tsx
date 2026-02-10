import Text from './Text';

interface MotifCardHeaderProps {
  motif: string;
  found: number;
  total: number;
  missed: number;
  failedAttempt: number;
}

export default function MotifCardHeader({
  motif,
  found,
  total,
  missed,
  failedAttempt,
}: MotifCardHeaderProps) {
  return (
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
}
