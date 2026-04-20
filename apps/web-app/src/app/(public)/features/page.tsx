'use client';

import { motion } from 'framer-motion';
import {
  ArrowRight,
  BarChart3,
  Brain,
  Calendar,
  CheckCircle2,
  Globe,
  Image as ImageIcon,
  Settings,
  Shield,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  Volume2,
  Zap,
} from 'lucide-react';
import Link from 'next/link';

import { ROUTES } from '@/lib/constants';
import { cn } from '@/lib/utils';
import { HeroSection } from '@/shared/components/layout/hero-section';
import { Button } from '@/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/ui/card';
import { Separator } from '@/ui/separator';

const coreFeatures = [
  {
    icon: Brain,
    title: 'Adaptive Learning Engine',
    description:
      'AI-powered BKT and IRT algorithms that adapt to your knowledge level in real-time.',
    details: [
      'Bayesian Knowledge Tracing models your understanding',
      'Item Response Theory optimizes question difficulty',
      'Real-time adaptation based on your responses',
      'Personalized learning paths for every topic',
    ],
  },
  {
    icon: Calendar,
    title: 'Spaced Repetition System',
    description:
      'SM-2 algorithm optimizes review timing for maximum long-term retention.',
    details: [
      'Reviews scheduled at optimal intervals',
      'Prevents forgetting before it happens',
      'Adapts to your individual retention patterns',
      'Proven to increase retention by 94%',
    ],
  },
  {
    icon: Sparkles,
    title: 'Interactive Memocards',
    description:
      'Multi-sensory flashcards with multimedia content and mnemonic techniques.',
    details: [
      'Rich text, images, and audio support',
      'Mnemonic imagery and associations',
      'Text-to-speech for audio learning',
      'Flip animations and visual feedback',
    ],
  },
  {
    icon: Target,
    title: 'Diverse Question Types',
    description:
      'Engage with multiple question formats designed for different learning styles.',
    details: [
      'Multiple choice questions',
      'Listening comprehension exercises',
      'Drag-and-drop matching',
      'Sequencing and ordering tasks',
    ],
  },
  {
    icon: TrendingUp,
    title: 'Advanced Analytics',
    description:
      'Track your progress with detailed insights and performance metrics.',
    details: [
      'Knowledge mastery heatmaps',
      'Retention rate tracking',
      'Study time analytics',
      'Strength and weakness identification',
    ],
  },
  {
    icon: Zap,
    title: 'Real-Time Feedback',
    description:
      'Instant explanations and guidance to reinforce learning moments.',
    details: [
      'Immediate answer validation',
      'Detailed explanations for wrong answers',
      'Progress celebrations and motivation',
      'Adaptive hints and guidance',
    ],
  },
];

const multimediaFeatures = [
  {
    icon: ImageIcon,
    title: 'Visual Learning',
    description: 'Images, diagrams, and visual mnemonics for better retention.',
  },
  {
    icon: Volume2,
    title: 'Audio Support',
    description: 'Native audio files and text-to-speech for auditory learners.',
  },
  {
    icon: CheckCircle2,
    title: 'Interactive Exercises',
    description: 'Drag-and-drop, matching, and ordering for hands-on learning.',
  },
];

const platformFeatures = [
  {
    icon: BarChart3,
    title: 'Progress Dashboard',
    description:
      'Visualize your learning journey with comprehensive analytics.',
  },
  {
    icon: Users,
    title: 'Collaborative Learning',
    description: 'Share decks and learn together with friends and classmates.',
  },
  {
    icon: Settings,
    title: 'Customizable Experience',
    description: 'Tailor the platform to your preferences and learning style.',
  },
  {
    icon: Globe,
    title: 'Multi-Platform Access',
    description: 'Learn anywhere with responsive web and mobile support.',
  },
  {
    icon: Shield,
    title: 'Privacy-First',
    description: 'Your data is encrypted and never shared without permission.',
  },
];

export default function FeaturesPage() {
  return (
    <div className='flex flex-col'>
      {/* Hero Section */}
      <HeroSection
        title='Every Feature You Need to Master Any Subject'
        description='Powered by AI and learning science, Memosphere provides a complete toolkit for effective, personalized education.'
        primaryCta={{
          text: 'Try It Free',
          href: ROUTES.REGISTER,
        }}
        secondaryCta={{
          text: 'See Demo',
          href: ROUTES.DEMO,
        }}
      />

      {/* Core Features */}
      <section
        className='py-24 sm:py-32'
        aria-labelledby='core-features-heading'
      >
        <div className='container mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='text-center mb-16'>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 id='core-features-heading' className='heading-2 mb-4'>
                Core Learning Features
              </h2>
              <p className='paragraph-lg max-w-2xl mx-auto'>
                Advanced AI and cognitive science working together to optimize
                your learning experience.
              </p>
            </motion.div>
          </div>

          <div className='space-y-16'>
            {coreFeatures.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
              >
                <Card className='overflow-hidden hover:shadow-2xl transition-shadow duration-500'>
                  <div
                    className={cn(
                      'grid grid-cols-1 lg:grid-cols-2 gap-8',
                      index % 2 === 1 && 'lg:grid-flow-dense'
                    )}
                  >
                    {/* Content */}
                    <div
                      className={cn('p-8', index % 2 === 1 && 'lg:col-start-2')}
                    >
                      <div className='mb-6 inline-flex p-4 rounded-xl bg-gradient-to-br from-brand-500 to-blue-500 text-white'>
                        <feature.icon className='h-8 w-8' aria-hidden='true' />
                      </div>
                      <h3 className='heading-3 mb-4'>{feature.title}</h3>
                      <p className='paragraph-lg text-muted-foreground mb-6'>
                        {feature.description}
                      </p>
                      <ul role='list' className='space-y-3'>
                        {feature.details.map(detail => (
                          <li key={detail} className='flex items-start gap-3'>
                            <CheckCircle2
                              className='h-5 w-5 text-brand-500 shrink-0 mt-0.5'
                              aria-hidden='true'
                            />
                            <span className='text-muted-foreground'>
                              {detail}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Visual */}
                    <div
                      className={cn(
                        'bg-gradient-to-br from-brand-50 to-blue-50 dark:from-brand-950 dark:to-blue-950 p-8 flex items-center justify-center',
                        index % 2 === 1 && 'lg:col-start-1 lg:row-start-1'
                      )}
                    >
                      <div className='w-full aspect-square max-w-md rounded-2xl bg-gradient-to-br from-brand-500/20 via-blue-500/20 to-brand-500/20 backdrop-blur-sm border border-white/20 flex items-center justify-center'>
                        <feature.icon
                          className='h-32 w-32 text-brand-500'
                          aria-hidden='true'
                        />
                      </div>
                    </div>
                  </div>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Multimedia Features */}
      <section
        className='py-24 sm:py-32 bg-muted/30'
        aria-labelledby='multimedia-heading'
      >
        <div className='container mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='text-center mb-16'>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 id='multimedia-heading' className='heading-2 mb-4'>
                Multimedia Learning Experience
              </h2>
              <p className='paragraph-lg max-w-2xl mx-auto'>
                Engage multiple senses with rich media content for deeper
                understanding.
              </p>
            </motion.div>
          </div>

          <div className='grid grid-cols-1 md:grid-cols-3 gap-8'>
            {multimediaFeatures.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card className='h-full text-center hover:shadow-xl transition-all duration-300 hover:-translate-y-2'>
                  <CardHeader>
                    <div className='mx-auto mb-4 inline-flex p-4 rounded-xl bg-gradient-to-br from-brand-500 to-blue-500 text-white'>
                      <feature.icon className='h-8 w-8' aria-hidden='true' />
                    </div>
                    <CardTitle className='text-xl'>{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className='text-muted-foreground'>
                      {feature.description}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Platform Features */}
      <section className='py-24 sm:py-32' aria-labelledby='platform-heading'>
        <div className='container mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='text-center mb-16'>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 id='platform-heading' className='heading-2 mb-4'>
                Platform Features
              </h2>
              <p className='paragraph-lg max-w-2xl mx-auto'>
                Everything you need for a seamless learning experience.
              </p>
            </motion.div>
          </div>

          <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-5xl mx-auto'>
            {platformFeatures.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card className='h-full hover:shadow-lg transition-shadow duration-300 border-2 hover:border-brand-500/50'>
                  <CardHeader>
                    <feature.icon
                      className='h-8 w-8 text-brand-500 mb-3'
                      aria-hidden='true'
                    />
                    <CardTitle className='text-lg'>{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className='text-sm text-muted-foreground'>
                      {feature.description}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <Separator className='container mx-auto' />

      {/* CTA Section */}
      <section
        className='py-24 sm:py-32'
        aria-labelledby='features-cta-heading'
      >
        <div className='container mx-auto px-4 sm:px-6 lg:px-8'>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className='relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-600 via-blue-500 to-brand-500 p-12 text-center text-white'
          >
            <div className='absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]' />
            <div className='relative z-10 max-w-2xl mx-auto'>
              <h2
                id='features-cta-heading'
                className='heading-2 mb-6 text-white'
              >
                Ready to Experience These Features?
              </h2>
              <p className='paragraph-lg mb-10 text-white/90'>
                Start your free trial today and discover how Memosphere can
                transform your learning.
              </p>
              <div className='flex flex-col sm:flex-row gap-4 justify-center'>
                <Button
                  asChild
                  size='xl'
                  variant='default'
                  className='bg-white text-brand-600 hover:bg-gray-100 hover:scale-105 transition-all duration-300'
                >
                  <Link href={ROUTES.REGISTER}>
                    Get Started Free
                    <ArrowRight className='ml-2 h-5 w-5' aria-hidden='true' />
                  </Link>
                </Button>
                <Button
                  asChild
                  size='xl'
                  variant='outline'
                  className='border-white text-white hover:bg-white/10'
                >
                  <Link href={ROUTES.PRICING}>View Pricing</Link>
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
