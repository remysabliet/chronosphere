import {
  ArrowRight,
  Brain,
  Calendar,
  BarChart3,
  CheckCircle2,
  Image,
  Layers,
  Quote,
  Sparkles,
  Star,
  Target,
  Trophy,
} from 'lucide-react';
import Link from 'next/link';

import { FEATURES, PRICING_TIERS, ROUTES, TESTIMONIALS } from '@/lib/constants';
import { cn } from '@/lib/utils';
import { HeroSection } from '@/shared/components/layout/hero-section';
import { Button } from '@/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/ui/card';
import { FadeIn } from '@/ui/fade-in';

const featureIcons = {
  brain: Brain,
  calendar: Calendar,
  image: Image,
  chart: BarChart3,
  layers: Layers,
  trophy: Trophy,
};

export default function HomePage() {
  return (
    <div className='flex flex-col'>
      {/* Hero Section */}
      <HeroSection
        title='Transform Your Learning with AI-Powered Adaptive Education'
        description='Master any subject faster with personalized quizzes, spaced repetition, and multimedia memocards. Join thousands of learners achieving their goals.'
        primaryCta={{
          text: 'Start Learning Free',
          href: ROUTES.REGISTER,
        }}
        secondaryCta={{
          text: 'See How It Works',
          href: ROUTES.DEMO,
        }}
      />

      {/* Social Proof */}
      <section
        className='py-12 bg-muted/30'
        aria-labelledby='social-proof-heading'
      >
        <div className='container mx-auto px-4 sm:px-6 lg:px-8'>
          <h2 id='social-proof-heading' className='sr-only'>
            Trusted by learners worldwide
          </h2>
          <div className='grid grid-cols-2 md:grid-cols-4 gap-8 items-center justify-items-center'>
            <div className='text-center' role='group' aria-label='Active users'>
              <p className='heading-2 gradient-text'>50K+</p>
              <p className='text-sm text-muted-foreground'>Active Learners</p>
            </div>
            <div
              className='text-center'
              role='group'
              aria-label='Quizzes completed'
            >
              <p className='heading-2 gradient-text'>2M+</p>
              <p className='text-sm text-muted-foreground'>Quizzes Completed</p>
            </div>
            <div
              className='text-center'
              role='group'
              aria-label='Retention rate'
            >
              <p className='heading-2 gradient-text'>94%</p>
              <p className='text-sm text-muted-foreground'>Retention Rate</p>
            </div>
            <div className='text-center' role='group' aria-label='User rating'>
              <div className='flex items-center justify-center gap-1 mb-1'>
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    className='h-5 w-5 fill-yellow-400 text-yellow-400'
                    aria-hidden='true'
                  />
                ))}
              </div>
              <p className='text-sm text-muted-foreground'>4.9/5 Rating</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className='py-24 sm:py-32' aria-labelledby='features-heading'>
        <div className='container mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='text-center mb-16'>
            <FadeIn
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 id='features-heading' className='heading-2 mb-4'>
                Everything You Need to Learn Effectively
              </h2>
              <p className='paragraph-lg max-w-2xl mx-auto'>
                Powered by cutting-edge AI and proven learning science,
                Memosphere adapts to your unique learning style.
              </p>
            </FadeIn>
          </div>

          <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8'>
            {FEATURES.map((feature, index) => {
              const Icon =
                featureIcons[feature.icon as keyof typeof featureIcons];
              return (
                <FadeIn
                  key={feature.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                >
                  <Card className='h-full hover:shadow-xl transition-all duration-300 hover:-translate-y-1 group'>
                    <CardHeader>
                      <div className='mb-4 inline-flex p-3 rounded-lg bg-gradient-to-br from-brand-500 to-blue-500 text-white group-hover:scale-110 transition-transform'>
                        <Icon className='h-6 w-6' aria-hidden='true' />
                      </div>
                      <CardTitle className='text-xl'>{feature.title}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className='text-muted-foreground'>
                        {feature.description}
                      </p>
                    </CardContent>
                  </Card>
                </FadeIn>
              );
            })}
          </div>

          <div className='mt-12 text-center'>
            <Button asChild variant='outline' size='lg'>
              <Link href={ROUTES.FEATURES}>
                Explore All Features
                <ArrowRight className='ml-2 h-5 w-5' aria-hidden='true' />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section
        className='py-24 sm:py-32 bg-muted/30'
        aria-labelledby='how-it-works-heading'
      >
        <div className='container mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='text-center mb-16'>
            <FadeIn
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 id='how-it-works-heading' className='heading-2 mb-4'>
                Your Learning Journey in 3 Simple Steps
              </h2>
              <p className='paragraph-lg max-w-2xl mx-auto'>
                Get started in minutes and see results from day one.
              </p>
            </FadeIn>
          </div>

          <div className='grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto'>
            {[
              {
                step: '01',
                title: 'Choose Your Topic',
                description:
                  'Select from thousands of subjects or create your own custom learning path.',
                icon: Target,
              },
              {
                step: '02',
                title: 'Learn Interactively',
                description:
                  'Engage with multimedia memocards, quizzes, and adaptive exercises.',
                icon: Sparkles,
              },
              {
                step: '03',
                title: 'Master with AI',
                description:
                  'Our AI adapts to your pace, optimizing review timing for maximum retention.',
                icon: Brain,
              },
            ].map((item, index) => (
              <FadeIn
                key={item.step}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.2 }}
                className='relative'
              >
                <Card className='h-full border-2 hover:border-brand-500 transition-all duration-300'>
                  <CardHeader>
                    <div className='mb-4'>
                      <span className='text-6xl font-bold text-brand-500/20'>
                        {item.step}
                      </span>
                    </div>
                    <div className='mb-4 inline-flex p-3 rounded-lg bg-brand-50 dark:bg-brand-950 text-brand-600 dark:text-brand-400'>
                      <item.icon className='h-6 w-6' aria-hidden='true' />
                    </div>
                    <CardTitle className='text-xl'>{item.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className='text-muted-foreground'>{item.description}</p>
                  </CardContent>
                </Card>
                {index < 2 && (
                  <div
                    className='hidden md:block absolute top-1/2 -right-4 transform -translate-y-1/2 z-10'
                    aria-hidden='true'
                  >
                    <ArrowRight className='h-8 w-8 text-brand-500' />
                  </div>
                )}
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section
        className='py-24 sm:py-32'
        aria-labelledby='testimonials-heading'
      >
        <div className='container mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='text-center mb-16'>
            <FadeIn
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 id='testimonials-heading' className='heading-2 mb-4'>
                Loved by Learners Worldwide
              </h2>
              <p className='paragraph-lg max-w-2xl mx-auto'>
                Join thousands of successful learners who transformed their
                education with Memosphere.
              </p>
            </FadeIn>
          </div>

          <div className='grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto'>
            {TESTIMONIALS.map((testimonial, index) => (
              <FadeIn
                key={testimonial.name}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card className='h-full hover:shadow-xl transition-shadow duration-300'>
                  <CardContent className='pt-6'>
                    <Quote
                      className='h-8 w-8 text-brand-500/20 mb-4'
                      aria-hidden='true'
                    />
                    <blockquote>
                      <p className='text-muted-foreground mb-6 italic'>
                        "{testimonial.content}"
                      </p>
                      <footer className='flex items-center gap-4'>
                        <div
                          className='h-12 w-12 rounded-full bg-gradient-to-br from-brand-500 to-blue-500 flex items-center justify-center text-white font-bold'
                          aria-hidden='true'
                        >
                          {testimonial.name.charAt(0)}
                        </div>
                        <div>
                          <cite className='not-italic font-semibold text-foreground'>
                            {testimonial.name}
                          </cite>
                          <p className='text-sm text-muted-foreground'>
                            {testimonial.role}
                          </p>
                        </div>
                      </footer>
                    </blockquote>
                  </CardContent>
                </Card>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Teaser */}
      <section
        className='py-24 sm:py-32 bg-muted/30'
        aria-labelledby='pricing-teaser-heading'
      >
        <div className='container mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='text-center mb-16'>
            <FadeIn
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 id='pricing-teaser-heading' className='heading-2 mb-4'>
                Start Free, Upgrade When You're Ready
              </h2>
              <p className='paragraph-lg max-w-2xl mx-auto'>
                Try Memosphere with our free plan. No credit card required.
              </p>
            </FadeIn>
          </div>

          <div className='grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto'>
            {PRICING_TIERS.map((tier, index) => (
              <FadeIn
                key={tier.name}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card
                  className={cn(
                    'h-full relative',
                    tier.popular &&
                      'border-2 border-brand-500 shadow-2xl scale-105'
                  )}
                >
                  {tier.popular && (
                    <div className='absolute -top-4 left-1/2 transform -translate-x-1/2'>
                      <span className='bg-gradient-to-r from-brand-600 to-blue-500 text-white px-4 py-1 rounded-full text-sm font-semibold'>
                        Most Popular
                      </span>
                    </div>
                  )}
                  <CardHeader className='text-center'>
                    <CardTitle className='text-2xl mb-2'>{tier.name}</CardTitle>
                    <div className='mb-4'>
                      <span className='text-5xl font-bold gradient-text'>
                        ${tier.price}
                      </span>
                      <span className='text-muted-foreground'>/month</span>
                    </div>
                    <p className='text-sm text-muted-foreground'>
                      {tier.description}
                    </p>
                  </CardHeader>
                  <CardContent>
                    <ul role='list' className='space-y-3 mb-6'>
                      {tier.features.slice(0, 4).map(feature => (
                        <li key={feature} className='flex items-start gap-2'>
                          <CheckCircle2
                            className='h-5 w-5 text-brand-500 shrink-0 mt-0.5'
                            aria-hidden='true'
                          />
                          <span className='text-sm text-muted-foreground'>
                            {feature}
                          </span>
                        </li>
                      ))}
                    </ul>
                    <Button
                      asChild
                      variant={tier.popular ? 'gradient' : 'outline'}
                      className='w-full'
                      size='lg'
                    >
                      <Link href={ROUTES.PRICING}>Choose {tier.name}</Link>
                    </Button>
                  </CardContent>
                </Card>
              </FadeIn>
            ))}
          </div>

          <div className='mt-12 text-center'>
            <Button asChild variant='ghost' size='lg'>
              <Link href={ROUTES.PRICING}>
                See All Plans & Features
                <ArrowRight className='ml-2 h-5 w-5' aria-hidden='true' />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section
        className='py-24 sm:py-32 bg-gradient-to-br from-brand-600 via-blue-500 to-brand-500 text-white relative overflow-hidden'
        aria-labelledby='final-cta-heading'
      >
        {/* Decorative elements */}
        <div className='absolute inset-0 -z-10'>
          <div className='absolute top-0 left-1/4 w-96 h-96 bg-white rounded-full mix-blend-overlay filter blur-3xl opacity-10 animate-blob' />
          <div className='absolute bottom-0 right-1/4 w-96 h-96 bg-white rounded-full mix-blend-overlay filter blur-3xl opacity-10 animate-blob animation-delay-2000' />
        </div>

        <div className='container mx-auto px-4 sm:px-6 lg:px-8 text-center relative'>
          <FadeIn
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className='max-w-3xl mx-auto'
          >
            <h2 id='final-cta-heading' className='heading-1 mb-6 text-white'>
              Ready to Transform Your Learning?
            </h2>
            <p className='paragraph-lg mb-10 text-white/90'>
              Join 50,000+ learners who are already achieving their goals with
              Memosphere. Start your free trial today.
            </p>
            <div className='flex flex-col sm:flex-row gap-4 justify-center'>
              <Button
                asChild
                size='xl'
                variant='default'
                className='bg-white text-brand-600 hover:bg-gray-100 hover:scale-105 transition-all duration-300 shadow-2xl'
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
                <Link href={ROUTES.DEMO}>Watch Demo</Link>
              </Button>
            </div>
            <p className='mt-6 text-sm text-white/70'>
              No credit card required • Free forever plan available
            </p>
          </FadeIn>
        </div>
      </section>
    </div>
  );
}
