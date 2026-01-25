interface BadgeProps {
  label: string;
}

/**
 * Renders a stylized badge displaying the provided label.
 *
 * @param label - The text to display inside the badge.
 * @returns A span element with badge styling.
 */
export default function Badge({ label }: BadgeProps) {
  return (
    <span className="px-2 py-1 text-xs rounded-full bg-rust/30 text-sand border border-rust/60">
      {label}
    </span>
  );
}
