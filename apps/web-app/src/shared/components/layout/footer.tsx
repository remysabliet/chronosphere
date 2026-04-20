import { Brain, Github, Linkedin, Mail, Twitter } from 'lucide-react';
import Link from 'next/link';

import { EXTERNAL_LINKS, ROUTES } from '@/lib/constants';
import { Separator } from '@/ui/separator';

const footerNavigation = {
  product: [
    { name: 'Features', href: ROUTES.FEATURES },
    { name: 'Pricing', href: ROUTES.PRICING },
    { name: 'Demo', href: ROUTES.DEMO },
    { name: 'About', href: ROUTES.ABOUT },
  ],
  resources: [
    { name: 'Blog', href: '/blog' },
    { name: 'Help Center', href: '/help' },
    { name: 'Community', href: '/community' },
    { name: 'Status', href: '/status' },
  ],
  legal: [
    { name: 'Privacy Policy', href: ROUTES.PRIVACY },
    { name: 'Terms of Service', href: ROUTES.TERMS },
    { name: 'Cookie Policy', href: '/cookies' },
  ],
  social: [
    {
      name: 'GitHub',
      href: EXTERNAL_LINKS.GITHUB,
      icon: Github,
    },
    {
      name: 'Twitter',
      href: EXTERNAL_LINKS.TWITTER,
      icon: Twitter,
    },
    {
      name: 'LinkedIn',
      href: EXTERNAL_LINKS.LINKEDIN,
      icon: Linkedin,
    },
    {
      name: 'Email',
      href: EXTERNAL_LINKS.SUPPORT,
      icon: Mail,
    },
  ],
};

export function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className='border-t bg-muted/50' aria-labelledby='footer-heading'>
      <h2 id='footer-heading' className='sr-only'>
        Footer
      </h2>
      <div className='container mx-auto px-4 sm:px-6 lg:px-8 py-12'>
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8 lg:gap-12'>
          {/* Brand section */}
          <div className='lg:col-span-2'>
            <Link
              href={ROUTES.HOME}
              className='flex items-center gap-2 group w-fit'
              aria-label='Memosphere home'
            >
              <Brain className='h-8 w-8 text-brand-600 transition-transform group-hover:scale-110' />
              <span className='text-xl font-bold gradient-text'>
                Memosphere
              </span>
            </Link>
            <p className='mt-4 text-sm text-muted-foreground max-w-md'>
              AI-powered adaptive learning platform that transforms how you
              learn with personalized quizzes, spaced repetition, and multimedia
              memocards.
            </p>
            <div className='mt-6 flex gap-4'>
              {footerNavigation.social.map(item => (
                <a
                  key={item.name}
                  href={item.href}
                  className='text-muted-foreground hover:text-brand-600 transition-colors'
                  target='_blank'
                  rel='noopener noreferrer'
                  aria-label={`Follow us on ${item.name}`}
                >
                  <span className='sr-only'>{item.name}</span>
                  <item.icon className='h-5 w-5' aria-hidden='true' />
                </a>
              ))}
            </div>
          </div>

          {/* Product links */}
          <div>
            <h3 className='text-sm font-semibold text-foreground'>Product</h3>
            <ul role='list' className='mt-4 space-y-3'>
              {footerNavigation.product.map(item => (
                <li key={item.name}>
                  <Link
                    href={item.href}
                    className='text-sm text-muted-foreground hover:text-foreground transition-colors'
                  >
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Resources links */}
          <div>
            <h3 className='text-sm font-semibold text-foreground'>Resources</h3>
            <ul role='list' className='mt-4 space-y-3'>
              {footerNavigation.resources.map(item => (
                <li key={item.name}>
                  <Link
                    href={item.href}
                    className='text-sm text-muted-foreground hover:text-foreground transition-colors'
                  >
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal links */}
          <div>
            <h3 className='text-sm font-semibold text-foreground'>Legal</h3>
            <ul role='list' className='mt-4 space-y-3'>
              {footerNavigation.legal.map(item => (
                <li key={item.name}>
                  <Link
                    href={item.href}
                    className='text-sm text-muted-foreground hover:text-foreground transition-colors'
                  >
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <Separator className='my-8' />

        <div className='flex flex-col sm:flex-row items-center justify-between gap-4'>
          <p className='text-sm text-muted-foreground'>
            &copy; {currentYear} Memosphere. All rights reserved.
          </p>
          <p className='text-sm text-muted-foreground'>
            Built with{' '}
            <span className='text-red-500' aria-label='love'>
              ♥
            </span>{' '}
            for learners everywhere
          </p>
        </div>
      </div>
    </footer>
  );
}
