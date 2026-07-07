/**
 * Domain types shared across Memosphere's TypeScript services.
 *
 * Mirrors `memosphere_domain` in `shared-python` — each of these maps
 * directly to a Postgres CHECK constraint or a fixed value set used by more
 * than one service. Hand-maintained in parallel with the Python side (no
 * codegen in this repo); keep the two in sync when either changes.
 */

export type BloomLevel =
  | 'Remembering'
  | 'Understanding'
  | 'Applying'
  | 'Analyzing'
  | 'Evaluating'
  | 'Creating';

export type ComplexityLevel = 'Low' | 'Medium' | 'High';

export type QuestionType =
  | 'MCQ'
  | 'MCQMultiSelect'
  | 'TrueFalse'
  | 'FillInBlank';

export type DifficultyTier = 'easy' | 'medium' | 'hard';

export type ValidationStatus = 'Passed' | 'Failed' | 'Warning';

export type ExposureLevel = 'Unseen' | 'Recognized' | 'Practiced' | 'Mastered';

/**
 * Step 5/7 (main-workflow.md): flat starting P(L0) per self-reported exposure
 * level, applied uniformly across every concept-Bloom pair until the
 * placement probe and later BKT updates differentiate them.
 */
export const EXPOSURE_TO_P_L0: Record<ExposureLevel, number> = {
  Unseen: 0.2,
  Recognized: 0.4,
  Practiced: 0.6,
  Mastered: 0.8,
};
