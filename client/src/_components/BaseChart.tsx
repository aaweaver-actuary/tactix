import { ReactNode, useId } from 'react';

interface BaseChartProps {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  headerClassName?: string;
  contentClassName?: string;
  testId?: string;
}

export default function BaseChart({
  title,
  description,
  actions,
  children,
  className,
  headerClassName,
  contentClassName,
  testId,
}: BaseChartProps) {
  const titleId = useId();
  const hasHeader = Boolean(title || description || actions);
  const wrapperClassName = [
    'space-y-3 rounded-xl border border-white/10 bg-white/5 p-3',
    className,
  ]
    .filter(Boolean)
    .join(' ');
  const resolvedHeaderClassName = [
    'flex flex-wrap items-start justify-between gap-3',
    headerClassName,
  ]
    .filter(Boolean)
    .join(' ');
  const resolvedContentClassName = ['min-w-0', contentClassName]
    .filter(Boolean)
    .join(' ');

  return (
    <section
      className={wrapperClassName}
      aria-labelledby={title ? titleId : undefined}
      data-testid={testId}
    >
      {hasHeader ? (
        <div className={resolvedHeaderClassName}>
          <div className="space-y-1">
            {title ? (
              <h4 id={titleId} className="text-sm font-display text-sand">
                {title}
              </h4>
            ) : null}
            {description ? (
              <p className="text-xs text-sand/70">{description}</p>
            ) : null}
          </div>
          {actions ? <div className="shrink-0">{actions}</div> : null}
        </div>
      ) : null}
      <div className={resolvedContentClassName}>{children}</div>
    </section>
  );
}
