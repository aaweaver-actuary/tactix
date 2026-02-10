import BaseButton from './BaseButton';

interface ModalCloseButtonProps {
  onClick: () => void;
  testId: string;
  ariaLabel?: string;
  label?: string;
}

export default function ModalCloseButton({
  onClick,
  testId,
  ariaLabel,
  label = 'Close',
}: ModalCloseButtonProps) {
  return (
    <BaseButton
      onClick={onClick}
      className="rounded-md border border-white/10 px-3 py-1 text-xs text-sand/70 hover:border-white/30"
      aria-label={ariaLabel}
      data-testid={testId}
    >
      {label}
    </BaseButton>
  );
}
