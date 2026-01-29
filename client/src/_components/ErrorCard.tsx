import BaseCard from './BaseCard';

interface ErrorCardProps {
  message: string;
  testId?: string;
}

export default function ErrorCard({ message, testId }: ErrorCardProps) {
  return (
    <BaseCard
      className="p-3"
      collapsible={false}
      header={<span className="sr-only">Error</span>}
      data-testid={testId}
    >
      <div className="text-rust">{message}</div>
    </BaseCard>
  );
}
