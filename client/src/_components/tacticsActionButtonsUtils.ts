import type { MouseEvent } from 'react';

export const handleActionClick = (
  event: MouseEvent<HTMLButtonElement>,
  enabled: boolean,
  action: () => void,
) => {
  event.stopPropagation();
  if (!enabled) return;
  action();
};
