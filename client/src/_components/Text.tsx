import { TextMode, TextSize } from '../types';

interface TextProps {
  value: string;
  mode?: TextMode;
  size?: TextSize;
  mt?: string;
}

export default function Text({
  value,
  mode = 'normal',
  size = 'xs',
  mt,
}: TextProps) {
  let classes;
  if (mode == 'uppercase') {
    classes = `text-${size} text-sand/60 uppercase tracking-[0.08em]`;
  } else if (mode == 'normal') {
    classes = `text-${size} text-sand/60`;
  } else if (mode == 'teal') {
    classes = `text-${size} font-display text-teal`;
  } else if (mode == 'monospace') {
    classes = `text-${size} text-sand/60 font-mono`;
  } else if (mode == 'error') {
    classes = `text-${size} text-rust`;
  } else {
    classes = `text-${size} text-sand/60`;
  }

  classes += ' ' + (mt ? `mt-${mt}` : '');
  return <p className={classes}>{value}</p>;
}
