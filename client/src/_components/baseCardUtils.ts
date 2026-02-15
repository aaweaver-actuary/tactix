const INTERACTIVE_SELECTOR = 'button, a, input, select, textarea, label';

export const isInteractiveTarget = (target: EventTarget | null) => {
  if (!(target instanceof HTMLElement)) return false;
  return Boolean(target.closest(INTERACTIVE_SELECTOR));
};
