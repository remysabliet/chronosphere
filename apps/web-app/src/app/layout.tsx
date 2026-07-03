import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { Toaster } from 'sonner';
import '../styles/globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    default: 'Memosphere - AI-Powered Adaptive Learning Platform',
    template: '%s | Memosphere',
  },
  description:
    'Transform your learning with AI-powered adaptive education. Master any subject faster with personalized quizzes, spaced repetition, and multimedia memocards.',
  keywords: [
    'adaptive learning',
    'AI education',
    'spaced repetition',
    'flashcards',
    'quiz platform',
    'personalized learning',
    'memocards',
  ],
  authors: [{ name: 'Memosphere' }],
  creator: 'Memosphere',
  metadataBase: new URL('https://memosphere.com'),
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://memosphere.com',
    title: 'Memosphere - AI-Powered Adaptive Learning Platform',
    description: 'Transform your learning with AI-powered adaptive education.',
    siteName: 'Memosphere',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Memosphere - AI-Powered Adaptive Learning Platform',
    description: 'Transform your learning with AI-powered adaptive education.',
    creator: '@memosphere',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang='en' className={inter.variable} suppressHydrationWarning>
      <body className='antialiased'>
        {children}
        <Toaster richColors closeButton position='top-right' />
      </body>
    </html>
  );
}
