import type { ButtonHTMLAttributes, ReactNode } from 'react';

import BaseButton from './BaseButton';

type ActionButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
};

export default function ActionButton(props: ActionButtonProps) {
  return <BaseButton {...props} />;
}
