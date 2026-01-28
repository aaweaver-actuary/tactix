import { HTMLAttributes, ReactNode, useId, useState } from 'react';

interface BaseCardProps extends HTMLAttributes<HTMLDivElement> {
  header: ReactNode;
  children: ReactNode;
  defaultCollapsed?: boolean;
  headerClassName?: string;
  contentClassName?: string;
}

const INTERACTIVE_SELECTOR = 'button, a, input, select, textarea, label';

const isInteractiveTarget = (target: EventTarget | null) => {
  if (!(target instanceof HTMLElement)) return false;
  return Boolean(target.closest(INTERACTIVE_SELECTOR));
};

export default function BaseCard({
  header,
  children,
  defaultCollapsed = true,
  headerClassName,
  contentClassName,
  className,
  ...rest
}: BaseCardProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const contentId = useId();

  const toggle = () => setCollapsed((prev) => !prev);

  const handleHeaderClick = (event: React.MouseEvent<HTMLDivElement>) => {
    if (isInteractiveTarget(event.target)) return;
    toggle();
  };

  const handleHeaderKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    toggle();
  };

  const containerClassName = ['card', className].filter(Boolean).join(' ');
  const headerClasses = [
    'cursor-pointer',
    'focus-visible:outline-none',
    'focus-visible:ring-2',
    'focus-visible:ring-teal/60',
    'focus-visible:ring-offset-2',
    'focus-visible:ring-offset-night',
    headerClassName,
  ]
    .filter(Boolean)
    .join(' ');
  const contentClasses = [
    'transition-[max-height,opacity]',
    'duration-300',
    'ease-out',
    'overflow-hidden',
    collapsed
      ? 'max-h-0 opacity-0 pointer-events-none'
      : 'max-h-[2000px] opacity-100 pointer-events-auto',
  ].join(' ');

  return (
    <div className={containerClassName} {...rest}>
      <div
        role="button"
        tabIndex={0}
        aria-expanded={!collapsed}
        aria-controls={contentId}
        onClick={handleHeaderClick}
        onKeyDown={handleHeaderKeyDown}
        className={headerClasses}
      >
        {header}
      </div>
      <div
        id={contentId}
        aria-hidden={collapsed}
        data-state={collapsed ? 'collapsed' : 'expanded'}
        className={contentClasses}
      >
        <div className={contentClassName}>{children}</div>
      </div>
    </div>
  );
}
