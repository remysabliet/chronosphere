'use client';

import { motion } from 'framer-motion';

/**
 * Memosphere's quiz-creation mascot. Artwork lives at
 * /public/assets/svg/wizard.svg (a real SVG asset, not inlined here) — do not
 * swap it for a different icon/illustration without checking with the user
 * first. See README.md in this folder for why.
 */
const WIZARD_SRC = '/assets/svg/wizard.svg';

const SIZE_CLASSES = {
  sm: 'size-10',
  md: 'size-12',
} as const;

export function WizardAvatar({
  size = 'sm',
  talking = false,
}: {
  size?: 'sm' | 'md';
  talking?: boolean;
}) {
  const image = (
    <img
      src={WIZARD_SRC}
      alt='Wizard'
      className={`${SIZE_CLASSES[size]} shrink-0`}
    />
  );

  if (!talking) {
    return image;
  }

  return (
    <motion.div
      animate={{ y: [0, -4, 0], scale: [1, 1.05, 1] }}
      transition={{ repeat: Infinity, duration: 1.1, ease: 'easeInOut' }}
      className='shrink-0'
    >
      {image}
    </motion.div>
  );
}
