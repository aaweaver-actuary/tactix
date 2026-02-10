const ALLOWED_MOTIFS = ['hanging_piece', 'mate'] as const;
const ALLOWED_MOTIFS_SET = new Set(ALLOWED_MOTIFS);

type MotifValue = (typeof ALLOWED_MOTIFS)[number];

type MotifInput = MotifValue | 'all' | string | null | undefined;

type ScopedMotifInput = MotifValue | string | null | undefined;

export const isScopedMotif = (motif: ScopedMotifInput) =>
  Boolean(motif && ALLOWED_MOTIFS_SET.has(motif));

export const isAllowedMotifFilter = (motif: MotifInput) =>
  !motif || motif === 'all' || ALLOWED_MOTIFS_SET.has(motif);

export { ALLOWED_MOTIFS };
