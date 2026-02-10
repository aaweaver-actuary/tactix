import { HTMLAttributes, ReactNode } from 'react';

interface ChessboardPanelProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

const BASE_PANEL_CLASSES = 'rounded-lg border border-white/10 bg-white/5 p-3';

export default function ChessboardPanel({
  children,
  className,
  ...rest
}: ChessboardPanelProps) {
  return (
    <div
      className={[BASE_PANEL_CLASSES, className].filter(Boolean).join(' ')}
      {...rest}
    >
      {children}
    </div>
  );
}
