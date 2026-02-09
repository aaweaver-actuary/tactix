import { useEffect } from 'react';
import type { MouseEvent, ReactNode } from 'react';

type ModalShellProps = {
  testId: string;
  onClose: () => void;
  children: ReactNode;
  alignClassName?: string;
  panelClassName?: string;
};

const joinClassNames = (...classes: Array<string | null | undefined>) =>
  classes.filter(Boolean).join(' ');

export default function ModalShell({
  testId,
  onClose,
  children,
  alignClassName,
  panelClassName,
}: ModalShellProps) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      onClose();
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [onClose]);

  const handleBackdropClick = (event: MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className={joinClassNames(
        'fixed inset-0 z-50 flex justify-center bg-black/60 px-4 py-6 backdrop-blur-sm',
        alignClassName ?? 'items-center',
      )}
      role="dialog"
      aria-modal="true"
      data-testid={testId}
      onClick={handleBackdropClick}
    >
      <div
        className={joinClassNames(
          'w-full max-h-[90vh] overflow-y-auto rounded-2xl border border-white/10 bg-slate-950/95 p-5 shadow-2xl',
          panelClassName,
        )}
      >
        {children}
      </div>
    </div>
  );
}
