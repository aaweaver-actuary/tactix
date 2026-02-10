import type { ReactNode } from 'react';
import Text from './Text';

interface ModalHeaderProps {
  title: string;
  description?: string;
  rightSlot?: ReactNode;
  className?: string;
}

export default function ModalHeader({
  title,
  description,
  rightSlot,
  className,
}: ModalHeaderProps) {
  const wrapperClass = className
    ? `flex items-center justify-between gap-3 ${className}`
    : 'flex items-center justify-between gap-3';

  return (
    <div className={wrapperClass}>
      <div>
        <Text mode="uppercase" value={title} />
        {description ? (
          <div className="text-xs text-sand/60">{description}</div>
        ) : null}
      </div>
      {rightSlot}
    </div>
  );
}
