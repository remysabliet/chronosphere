import { LogOut } from 'lucide-react';
import { redirect } from 'next/navigation';

import { auth, signOut } from '@/lib/auth';
import { ROUTES } from '@/lib/constants';
import { AppNav } from '@/shared/components/layout/app-nav';
import { QueryProvider } from '@/shared/components/providers/query-provider';
import { Button } from '@/ui/button';
import { Separator } from '@/ui/separator';

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();
  if (!session) {
    redirect(ROUTES.LOGIN);
  }

  return (
    <QueryProvider>
      <div className='flex min-h-screen'>
        <aside className='flex w-64 flex-col border-r bg-card px-4 py-6'>
          <span className='gradient-text mb-6 px-3 text-lg font-bold'>
            Memosphere
          </span>
          <AppNav />
          <div className='mt-auto'>
            <Separator className='mb-4' />
            <p className='mb-2 truncate px-3 text-sm text-muted-foreground'>
              {session.user?.email ?? session.user?.name}
            </p>
            <form
              action={async () => {
                'use server';
                await signOut({ redirectTo: ROUTES.HOME });
              }}
            >
              <Button
                type='submit'
                variant='ghost'
                size='sm'
                className='w-full justify-start'
              >
                <LogOut className='size-4' />
                Sign out
              </Button>
            </form>
          </div>
        </aside>
        <main className='flex-1 overflow-y-auto p-8'>{children}</main>
      </div>
    </QueryProvider>
  );
}
