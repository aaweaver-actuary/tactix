import {
  HTMLAttributes,
  ReactNode,
  useEffect,
  useId,
  useRef,
  useState,
} from 'react';
import BaseButton from './BaseButton';

export type BaseCardDragHandleProps =
  React.ButtonHTMLAttributes<HTMLButtonElement>;

export interface BaseCardDragProps {
  dragHandleProps?: BaseCardDragHandleProps;
  dragHandleLabel?: string;
  onCollapsedChange?: (collapsed: boolean) => void;
}

interface BaseCardDragHandleConfig {
  dragHandleProps?: BaseCardDragHandleProps;
  dragHandleLabel?: string;
  dragHandleClassName?: string;
}

interface BaseCardProps
  extends HTMLAttributes<HTMLDivElement>, BaseCardDragProps {
  header: ReactNode;
  children: ReactNode;
  defaultCollapsed?: boolean;
  collapsible?: boolean;
  headerClassName?: string;
  contentClassName?: string;
  dragHandleClassName?: string;
}

const INTERACTIVE_SELECTOR = 'button, a, input, select, textarea, label';

export const isInteractiveTarget = (target: EventTarget | null) => {
  if (!(target instanceof HTMLElement)) return false;
  return Boolean(target.closest(INTERACTIVE_SELECTOR));
};

const buildDragHandleClasses = (
  dragHandleProps: BaseCardDragHandleProps,
  dragHandleClassName?: string,
) =>
  [
    'ml-2 inline-flex h-8 w-8 items-center justify-center rounded-md border border-white/10 bg-white/5 text-sand/70 transition',
    'hover:border-white/30 hover:text-sand',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/60 focus-visible:ring-offset-2 focus-visible:ring-offset-night',
    'opacity-100',
    dragHandleClassName,
    dragHandleProps.className,
  ]
    .filter(Boolean)
    .join(' ');

const BaseCardDragHandle = ({
  dragHandleProps,
  dragHandleLabel,
  dragHandleClassName,
}: BaseCardDragHandleConfig) => {
  if (!dragHandleProps) return null;

  const dragHandleAriaLabel =
    dragHandleProps['aria-label'] || dragHandleLabel || 'Reorder card';

  return (
    <BaseButton
      type={dragHandleProps.type || 'button'}
      {...dragHandleProps}
      aria-label={dragHandleAriaLabel}
      aria-hidden={false}
      className={buildDragHandleClasses(dragHandleProps, dragHandleClassName)}
    >
      <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4">
        <circle cx="8" cy="7" r="1.5" fill="currentColor" />
        <circle cx="16" cy="7" r="1.5" fill="currentColor" />
        <circle cx="8" cy="12" r="1.5" fill="currentColor" />
        <circle cx="16" cy="12" r="1.5" fill="currentColor" />
        <circle cx="8" cy="17" r="1.5" fill="currentColor" />
        <circle cx="16" cy="17" r="1.5" fill="currentColor" />
      </svg>
    </BaseButton>
  );
};

export default function BaseCard({
  header,
  children,
  defaultCollapsed = true,
  collapsible = true,
  headerClassName,
  contentClassName,
  dragHandleProps,
  dragHandleLabel,
  dragHandleClassName,
  onCollapsedChange,
  className,
  ...rest
}: BaseCardProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const contentId = useId();
  const onCollapsedChangeRef = useRef(onCollapsedChange);
  const isCollapsible = Boolean(collapsible);
  const isCollapsed = isCollapsible ? collapsed : false;

  useEffect(() => {
    onCollapsedChangeRef.current = onCollapsedChange;
  }, [onCollapsedChange]);

  useEffect(() => {
    if (!isCollapsible) return;
    onCollapsedChangeRef.current?.(collapsed);
  }, [collapsed, isCollapsible]);

  const toggle = () => {
    setCollapsed((prev) => !prev);
  };

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
    isCollapsible ? 'cursor-pointer' : 'cursor-default',
    isCollapsible
      ? 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/60 focus-visible:ring-offset-2 focus-visible:ring-offset-night'
      : null,
    headerClassName,
  ]
    .filter(Boolean)
    .join(' ');
  const contentClasses = [
    'transition-[max-height,opacity]',
    'duration-300',
    'ease-out',
    'overflow-hidden',
    isCollapsed
      ? 'max-h-0 opacity-0 pointer-events-none'
      : 'max-h-[2000px] opacity-100 pointer-events-auto',
  ].join(' ');
  const headerProps = isCollapsible
    ? {
        role: 'button' as const,
        tabIndex: 0,
        'aria-expanded': !isCollapsed,
        'aria-controls': contentId,
        onClick: handleHeaderClick,
        onKeyDown: handleHeaderKeyDown,
      }
    : {};

  return (
    <div className={containerClassName} {...rest}>
      <div className={headerClasses} {...headerProps}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex-1 min-w-0">{header}</div>
          <BaseCardDragHandle
            dragHandleProps={dragHandleProps}
            dragHandleLabel={dragHandleLabel}
            dragHandleClassName={dragHandleClassName}
          />
        </div>
      </div>
      <div
        id={contentId}
        aria-hidden={isCollapsed}
        data-state={isCollapsed ? 'collapsed' : 'expanded'}
        className={contentClasses}
      >
        <div className={contentClassName}>{children}</div>
      </div>
    </div>
  );
}
