'use client';

import {
  BarChart3,
  Layers,
  LayoutDashboard,
  Library,
  PlusCircle,
  User,
} from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { ROUTES } from '@/lib/constants';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: ROUTES.QUIZZES, label: 'Quizzes', icon: Library, enabled: true },
  { href: ROUTES.QUIZ_NEW, label: 'New Quiz', icon: PlusCircle, enabled: true },
  {
    href: ROUTES.HOME_APP,
    label: 'Home',
    icon: LayoutDashboard,
    enabled: false,
  },
  { href: ROUTES.MEMOCARDS, label: 'Memocards', icon: Layers, enabled: false },
  {
    href: ROUTES.ANALYTICS,
    label: 'Analytics',
    icon: BarChart3,
    enabled: false,
  },
  { href: ROUTES.PROFILE, label: 'Profile', icon: User, enabled: false },
] as const;

function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppNav() {
  const pathname = usePathname();

  return (
    <nav className='flex flex-col gap-1'>
      {NAV_ITEMS.map(item => {
        const Icon = item.icon;

        if (!item.enabled) {
          return (
            <span
              key={item.href}
              aria-disabled='true'
              className='flex cursor-not-allowed items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground opacity-50'
            >
              <Icon className='size-4' />
              {item.label}
              <span className='ml-auto rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium uppercase'>
                Soon
              </span>
            </span>
          );
        }

        const active = isActive(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              active
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
            )}
          >
            <Icon className='size-4' />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
