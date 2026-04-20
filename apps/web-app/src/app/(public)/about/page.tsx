'use client';

import { motion } from 'framer-motion';
import {
  ArrowRight,
  Brain,
  Heart,
  Sparkles,
  Target,
  TrendingUp,
  Users,
} from 'lucide-react';
import Link from 'next/link';

import { ROUTES } from '@/lib/constants';
import { HeroSection } from '@/shared/components/layout/hero-section';
import { Button } from '@/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/ui/card';

const values = [
  {
    icon: Brain,
    title: 'Science-Backed',
    description:
      'Every feature is grounded in cognitive science and proven learning research.',
  },
  {
    icon: Target,
    title: 'Learner-Centered',
    description:
      'We put learners first, adapting to individual needs and learning styles.',
  },
  {
    icon: Sparkles,
    title: 'Innovation-Driven',
    description:
      'Continuously pushing boundaries with cutting-edge AI and technology.',
  },
  {
    icon: Users,
    title: 'Inclusive',
    description:
      'Accessible education for everyone, regardless of background or ability.',
  },
  {
    icon: TrendingUp,
    title: 'Results-Focused',
    description:
      'Measurable outcomes and proven retention rates drive our development.',
  },
  {
    icon: Heart,
    title: 'Passionate',
    description:
      'Built by educators and learners who genuinely care about education.',
  },
];

const howItWorks = [
  {
    step: 1,
    title: 'Bayesian Knowledge Tracing (BKT)',
    description:
      'Our AI models your knowledge state in real-time, predicting what you know and what you need to practice. BKT adapts to your responses, creating a personalized learning path.',
  },
  {
    step: 2,
    title: 'Item Response Theory (IRT)',
    description:
      "Questions are calibrated for difficulty and discrimination. IRT ensures you're always challenged at the right level - not too easy, not too hard.",
  },
  {
    step: 3,
    title: 'Spaced Repetition (SM-2)',
    description:
      "Based on the SuperMemo algorithm, we optimize review timing to maximize long-term retention. Content resurfaces just as you're about to forget it.",
  },
  {
    step: 4,
    title: 'Multimedia Learning',
    description:
      'Combine text, images, audio, and mnemonic techniques. Our memocards engage multiple senses, creating stronger memory associations.',
  },
];

export default function AboutPage() {
  return (
    <div className='flex flex-col'>
      {/* Hero Section */}
      <HeroSection
        title='Revolutionizing Learning with AI'
        description="We're on a mission to make education adaptive, personalized, and effective for every learner around the world."
        primaryCta={{
          text: 'Join Our Mission',
          href: ROUTES.REGISTER,
        }}
        secondaryCta={{
          text: 'See Our Impact',
          href: '#mission',
        }}
      />

      {/* Mission Section */}
      <section
        id='mission'
        className='py-24 sm:py-32'
        aria-labelledby='mission-heading'
      >
        <div className='container mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='grid grid-cols-1 lg:grid-cols-2 gap-12 items-center'>
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <h2 id='mission-heading' className='heading-2 mb-6'>
                Our Mission
              </h2>
              <div className='space-y-4 text-muted-foreground'>
                <p className='paragraph-lg'>
                  Education shouldn't be one-size-fits-all. Every learner is
                  unique, with different strengths, challenges, and goals.
                </p>
                <p className='paragraph-lg'>
                  Memosphere was born from a simple belief:{' '}
                  <strong className='text-foreground'>
                    technology can make learning personal
                  </strong>
                  . By combining AI with proven learning science, we create
                  adaptive experiences that meet each learner exactly where they
                  are.
                </p>
                <p className='paragraph-lg'>
                  We're not just building an app - we're building a future where
                  everyone has access to world-class, personalized education.
                </p>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              className='relative'
            >
              <div className='aspect-square rounded-2xl bg-gradient-to-br from-brand-500 via-blue-500 to-brand-600 p-12 flex items-center justify-center relative overflow-hidden'>
                <div className='absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]' />
                <div className='relative z-10 text-center text-white'>
                  <p className='text-6xl font-bold mb-4'>50K+</p>
                  <p className='text-2xl font-semibold mb-2'>Learners</p>
                  <p className='text-white/80'>across 100+ countries</p>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Values Section */}
      <section
        className='py-24 sm:py-32 bg-muted/30'
        aria-labelledby='values-heading'
      >
        <div className='container mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='text-center mb-16'>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 id='values-heading' className='heading-2 mb-4'>
                Our Core Values
              </h2>
              <p className='paragraph-lg max-w-2xl mx-auto'>
                These principles guide every decision we make and every feature
                we build.
              </p>
            </motion.div>
          </div>

          <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8'>
            {values.map((value, index) => (
              <motion.div
                key={value.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card className='h-full hover:shadow-xl transition-all duration-300 hover:-translate-y-1'>
                  <CardHeader>
                    <div className='mb-4 inline-flex p-3 rounded-lg bg-gradient-to-br from-brand-500 to-blue-500 text-white'>
                      <value.icon className='h-6 w-6' aria-hidden='true' />
                    </div>
                    <CardTitle className='text-xl'>{value.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className='text-muted-foreground'>{value.description}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section
        className='py-24 sm:py-32'
        aria-labelledby='how-it-works-heading'
      >
        <div className='container mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='text-center mb-16'>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 id='how-it-works-heading' className='heading-2 mb-4'>
                The Science Behind Memosphere
              </h2>
              <p className='paragraph-lg max-w-2xl mx-auto'>
                Our platform combines four powerful learning technologies to
                create the most effective learning experience.
              </p>
            </motion.div>
          </div>

          <div className='max-w-4xl mx-auto space-y-8'>
            {howItWorks.map((item, index) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, x: index % 2 === 0 ? -20 : 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
              >
                <Card className='border-l-4 border-l-brand-500 hover:shadow-lg transition-shadow duration-300'>
                  <CardHeader>
                    <div className='flex items-start gap-4'>
                      <div className='flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-br from-brand-500 to-blue-500 text-white font-bold text-xl shrink-0'>
                        {item.step}
                      </div>
                      <div>
                        <CardTitle className='text-xl mb-2'>
                          {item.title}
                        </CardTitle>
                        <p className='text-muted-foreground'>
                          {item.description}
                        </p>
                      </div>
                    </div>
                  </CardHeader>
                </Card>
              </motion.div>
            ))}
          </div>

          <div className='mt-12 text-center'>
            <Button asChild variant='gradient' size='lg'>
              <Link href={ROUTES.DEMO}>
                See It In Action
                <ArrowRight className='ml-2 h-5 w-5' aria-hidden='true' />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section
        className='py-24 sm:py-32 bg-gradient-to-br from-brand-600 via-blue-500 to-brand-500 text-white'
        aria-labelledby='cta-heading'
      >
        <div className='container mx-auto px-4 sm:px-6 lg:px-8 text-center'>
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className='max-w-3xl mx-auto'
          >
            <h2 id='cta-heading' className='heading-1 mb-6 text-white'>
              Be Part of the Learning Revolution
            </h2>
            <p className='paragraph-lg mb-10 text-white/90'>
              Join thousands of learners who are already experiencing the future
              of education.
            </p>
            <Button
              asChild
              size='xl'
              variant='default'
              className='bg-white text-brand-600 hover:bg-gray-100 hover:scale-105 transition-all duration-300 shadow-2xl'
            >
              <Link href={ROUTES.REGISTER}>
                Start Learning Today
                <ArrowRight className='ml-2 h-5 w-5' aria-hidden='true' />
              </Link>
            </Button>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
