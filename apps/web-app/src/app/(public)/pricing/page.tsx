import { ArrowRight, CheckCircle2, HelpCircle } from 'lucide-react';
import Link from 'next/link';
import React from 'react';

import { PRICING_TIERS, ROUTES } from '@/lib/constants';
import { cn } from '@/lib/utils';
import { HeroSection } from '@/shared/components/layout/hero-section';
import { Button } from '@/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/ui/card';
import { FadeIn } from '@/ui/fade-in';

const comparisonFeatures = [
  {
    category: 'Core Features',
    features: [
      {
        name: 'Adaptive Learning Engine',
        free: true,
        pro: true,
        enterprise: true,
      },
      {
        name: 'Spaced Repetition System',
        free: true,
        pro: true,
        enterprise: true,
      },
      { name: 'Basic Analytics', free: true, pro: true, enterprise: true },
      { name: 'Mobile Access', free: true, pro: true, enterprise: true },
    ],
  },
  {
    category: 'Content & Decks',
    features: [
      {
        name: 'Active Decks',
        free: '3 decks',
        pro: 'Unlimited',
        enterprise: 'Unlimited',
      },
      {
        name: 'Cards per Deck',
        free: '100',
        pro: 'Unlimited',
        enterprise: 'Unlimited',
      },
      {
        name: 'Multimedia Support',
        free: 'Basic',
        pro: 'Full',
        enterprise: 'Full',
      },
      { name: 'Audio & TTS', free: false, pro: true, enterprise: true },
      { name: 'Custom Mnemonics', free: false, pro: true, enterprise: true },
    ],
  },
  {
    category: 'Advanced Features',
    features: [
      { name: 'Advanced Analytics', free: false, pro: true, enterprise: true },
      { name: 'Knowledge Heatmaps', free: false, pro: true, enterprise: true },
      {
        name: 'Collaborative Learning',
        free: false,
        pro: true,
        enterprise: true,
      },
      { name: 'Offline Mode', free: false, pro: true, enterprise: true },
      { name: 'Priority Support', free: false, pro: false, enterprise: true },
      { name: 'Custom Branding', free: false, pro: false, enterprise: true },
      {
        name: 'SSO & Advanced Security',
        free: false,
        pro: false,
        enterprise: true,
      },
      {
        name: 'Dedicated Success Manager',
        free: false,
        pro: false,
        enterprise: true,
      },
    ],
  },
];

const faqs = [
  {
    question: 'Can I switch plans later?',
    answer:
      "Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately, and we'll prorate any charges.",
  },
  {
    question: 'What payment methods do you accept?',
    answer:
      'We accept all major credit cards (Visa, MasterCard, Amex), PayPal, and bank transfers for Enterprise customers.',
  },
  {
    question: 'Is there a free trial for paid plans?',
    answer:
      'The Free plan is available forever - no trial needed! You can upgrade to Pro or Enterprise anytime to unlock additional features.',
  },
  {
    question: 'What happens to my data if I downgrade?',
    answer:
      "Your data is never deleted. If you downgrade, you'll simply have limited access to decks/cards beyond your plan limits. Upgrade again to restore full access.",
  },
  {
    question: 'Do you offer student discounts?',
    answer:
      'Yes! Students with a valid .edu email get 50% off Pro plans. Contact support@memosphere.com with your student ID.',
  },
  {
    question: 'How does Enterprise pricing work?',
    answer:
      'Enterprise pricing is customized based on your needs (number of users, features, support level). Contact our sales team for a quote.',
  },
];

function FeatureValue({ value }: { value: boolean | string }) {
  if (typeof value === 'boolean') {
    return value ? (
      <CheckCircle2
        className='h-5 w-5 text-brand-500 mx-auto'
        aria-label='Included'
      />
    ) : (
      <span className='text-muted-foreground' aria-label='Not included'>
        -
      </span>
    );
  }
  return <span className='text-sm font-medium'>{value}</span>;
}

export default function PricingPage() {
  return (
    <div className='flex flex-col'>
      {/* Hero Section */}
      <HeroSection
        title='Simple, Transparent Pricing'
        description='Start free and scale as you grow. No hidden fees, cancel anytime.'
        showDecoration={false}
        className='bg-gradient-to-br from-background to-muted/30'
      />

      {/* Pricing Cards */}
      <section className='py-24 sm:py-32' aria-labelledby='pricing-heading'>
        <div className='container mx-auto px-4 sm:px-6 lg:px-8'>
          <h2 id='pricing-heading' className='sr-only'>
            Pricing plans
          </h2>
          <div className='grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto'>
            {PRICING_TIERS.map((tier, index) => (
              <FadeIn
                key={tier.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card
                  className={cn(
                    'h-full relative flex flex-col',
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
                  <CardHeader className='text-center pb-8'>
                    <CardTitle className='text-2xl mb-4'>{tier.name}</CardTitle>
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
                  <CardContent className='flex-1 flex flex-col'>
                    <ul role='list' className='space-y-3 mb-8 flex-1'>
                      {tier.features.map(feature => (
                        <li key={feature} className='flex items-start gap-3'>
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
                      <Link href={ROUTES.REGISTER}>
                        {tier.cta}
                        {tier.popular && (
                          <ArrowRight
                            className='ml-2 h-5 w-5'
                            aria-hidden='true'
                          />
                        )}
                      </Link>
                    </Button>
                  </CardContent>
                </Card>
              </FadeIn>
            ))}
          </div>

          <div className='mt-12 text-center'>
            <p className='text-sm text-muted-foreground'>
              All plans include 14-day money-back guarantee • No credit card
              required for Free plan
            </p>
          </div>
        </div>
      </section>

      {/* Feature Comparison Table */}
      <section
        className='py-24 sm:py-32 bg-muted/30'
        aria-labelledby='comparison-heading'
      >
        <div className='container mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='text-center mb-16'>
            <FadeIn
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 id='comparison-heading' className='heading-2 mb-4'>
                Compare All Features
              </h2>
              <p className='paragraph-lg max-w-2xl mx-auto'>
                See exactly what's included in each plan.
              </p>
            </FadeIn>
          </div>

          <div className='max-w-5xl mx-auto'>
            <Card className='overflow-hidden'>
              <div className='overflow-x-auto'>
                <table className='w-full'>
                  <thead>
                    <tr className='border-b'>
                      <th className='text-left p-4 font-semibold' scope='col'>
                        Features
                      </th>
                      <th className='text-center p-4 font-semibold' scope='col'>
                        Free
                      </th>
                      <th
                        className='text-center p-4 font-semibold bg-brand-50 dark:bg-brand-950'
                        scope='col'
                      >
                        Pro
                      </th>
                      <th className='text-center p-4 font-semibold' scope='col'>
                        Enterprise
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparisonFeatures.map(category => (
                      <React.Fragment key={category.category}>
                        <tr className='bg-muted/50'>
                          <td
                            colSpan={4}
                            className='p-4 font-semibold text-sm uppercase tracking-wide'
                          >
                            {category.category}
                          </td>
                        </tr>
                        {category.features.map(feature => (
                          <tr key={feature.name} className='border-b'>
                            <td className='p-4 text-sm'>{feature.name}</td>
                            <td className='p-4 text-center'>
                              <FeatureValue value={feature.free} />
                            </td>
                            <td className='p-4 text-center bg-brand-50/50 dark:bg-brand-950/50'>
                              <FeatureValue value={feature.pro} />
                            </td>
                            <td className='p-4 text-center'>
                              <FeatureValue value={feature.enterprise} />
                            </td>
                          </tr>
                        ))}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className='py-24 sm:py-32' aria-labelledby='faq-heading'>
        <div className='container mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='text-center mb-16'>
            <FadeIn
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 id='faq-heading' className='heading-2 mb-4'>
                Frequently Asked Questions
              </h2>
              <p className='paragraph-lg max-w-2xl mx-auto'>
                Have questions? We have answers.
              </p>
            </FadeIn>
          </div>

          <div className='max-w-3xl mx-auto space-y-4'>
            {faqs.map((faq, index) => (
              <FadeIn
                key={faq.question}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: index * 0.05 }}
              >
                <Card className='hover:shadow-md transition-shadow duration-300'>
                  <CardHeader>
                    <CardTitle className='text-lg flex items-start gap-3'>
                      <HelpCircle
                        className='h-5 w-5 text-brand-500 shrink-0 mt-0.5'
                        aria-hidden='true'
                      />
                      {faq.question}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className='text-muted-foreground'>{faq.answer}</p>
                  </CardContent>
                </Card>
              </FadeIn>
            ))}
          </div>

          <div className='mt-12 text-center'>
            <p className='text-muted-foreground mb-4'>Still have questions?</p>
            <Button asChild variant='outline' size='lg'>
              <Link href='/help'>
                Visit Help Center
                <ArrowRight className='ml-2 h-5 w-5' aria-hidden='true' />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section
        className='py-24 sm:py-32 bg-gradient-to-br from-brand-600 via-blue-500 to-brand-500 text-white'
        aria-labelledby='pricing-cta-heading'
      >
        <div className='container mx-auto px-4 sm:px-6 lg:px-8 text-center'>
          <FadeIn
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className='max-w-3xl mx-auto'
          >
            <h2 id='pricing-cta-heading' className='heading-1 mb-6 text-white'>
              Start Learning Today
            </h2>
            <p className='paragraph-lg mb-10 text-white/90'>
              Join thousands of learners who are already achieving their goals
              with Memosphere.
            </p>
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
            <p className='mt-6 text-sm text-white/70'>
              No credit card required • 14-day money-back guarantee
            </p>
          </FadeIn>
        </div>
      </section>
    </div>
  );
}
