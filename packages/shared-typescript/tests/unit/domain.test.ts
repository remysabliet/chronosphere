import { describe, expect, it } from 'vitest';
import { EXPOSURE_TO_P_L0, type ExposureLevel } from '../../src/index.js';

describe('EXPOSURE_TO_P_L0', () => {
  it('covers every exposure level', () => {
    const levels: ExposureLevel[] = [
      'Unseen',
      'Recognized',
      'Practiced',
      'Mastered',
    ];
    expect(Object.keys(EXPOSURE_TO_P_L0).sort()).toEqual([...levels].sort());
  });

  it('is monotonically increasing from Unseen to Mastered', () => {
    const ordered = (
      ['Unseen', 'Recognized', 'Practiced', 'Mastered'] as const
    ).map(level => EXPOSURE_TO_P_L0[level]);
    expect(ordered).toEqual([...ordered].sort((a, b) => a - b));
  });
});
