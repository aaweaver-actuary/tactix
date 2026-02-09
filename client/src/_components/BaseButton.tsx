import type { ButtonHTMLAttributes, ReactNode } from 'react';

type BaseButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
};

export default function BaseButton({
  children,
  type = 'button',
  ...props
}: BaseButtonProps) {
  return (
    <button type={type} {...props}>
      {children}
    </button>
  );
}
