'use client';

import {
  BarChart3,
  LayoutDashboard,
  Layers,
  PlusCircle,
  User,
} from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { ROUTES } from '@/lib/constants';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: ROUTES.DASHBOARD, label: 'Dashboard', icon: LayoutDashboard },
  { href: ROUTES.QUIZ_NEW, label: 'New Quiz', icon: PlusCircle },
  { href: ROUTES.MEMOCARDS, label: 'Memocards', icon: Layers },
  { href: ROUTES.ANALYTICS, label: 'Analytics', icon: BarChart3 },
  { href: ROUTES.PROFILE, label: 'Profile', icon: User },
] as const;

export function AppNav() {
  const pathname = usePathname();

  return (
    <nav className='flex flex-col gap-1'>
      {NAV_ITEMS.map(item => {
        const isActive = pathname.startsWith(item.href);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              isActive
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
