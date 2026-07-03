'use client';

import { motion, type HTMLMotionProps } from 'framer-motion';

export function FadeIn(props: HTMLMotionProps<'div'>) {
  return <motion.div {...props} />;
}
