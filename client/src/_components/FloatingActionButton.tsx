import { useEffect, useId, useRef, useState } from 'react';

import BaseButton from './BaseButton';

export type FloatingAction = {
  id: string;
  label: string;
  onClick: () => void;
  testId?: string;
  ariaLabel?: string;
};

type FloatingActionButtonProps = {
  label: string;
  actions: FloatingAction[];
  testId?: string;
};

export default function FloatingActionButton({
  label,
  actions,
  testId = 'fab-toggle',
}: FloatingActionButtonProps) {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      setOpen(false);
    };

    const handlePointerDown = (event: MouseEvent | TouchEvent) => {
      const target = event.target as Node | null;
      if (!target) return;
      if (containerRef.current?.contains(target)) return;
      setOpen(false);
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('mousedown', handlePointerDown);
    window.addEventListener('touchstart', handlePointerDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('mousedown', handlePointerDown);
      window.removeEventListener('touchstart', handlePointerDown);
    };
  }, [open]);

  return (
    <div
      ref={containerRef}
      className="fixed bottom-6 right-6 z-40 flex flex-col items-end gap-3"
    >
      {open ? (
        <div
          id={menuId}
          role="menu"
          aria-label="Quick actions"
          className="flex flex-col items-end gap-2"
        >
          {actions.map((action) => (
            <BaseButton
              key={action.id}
              type="button"
              role="menuitem"
              aria-label={action.ariaLabel ?? action.label}
              data-testid={action.testId}
              className="rounded-full border border-white/15 bg-slate-950/95 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-sand shadow-lg hover:border-white/30"
              onClick={() => {
                action.onClick();
                setOpen(false);
              }}
            >
              {action.label}
            </BaseButton>
          ))}
        </div>
      ) : null}
      <BaseButton
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        data-testid={testId}
        className="flex h-14 w-14 items-center justify-center rounded-full border border-teal/60 bg-teal text-2xl font-semibold text-night shadow-xl transition hover:bg-teal/90"
        onClick={() => setOpen((prev) => !prev)}
      >
        <span aria-hidden="true">+</span>
        <span className="sr-only">{label}</span>
      </BaseButton>
    </div>
  );
}
