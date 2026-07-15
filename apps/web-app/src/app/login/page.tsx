import type { Metadata } from 'next';

import { auth, signIn } from '@/lib/auth';
import { DEFAULT_AUTHENTICATED_ROUTE } from '@/lib/constants';
import { Button } from '@/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/ui/card';
import { redirect } from 'next/navigation';

export const metadata: Metadata = {
  title: 'Sign in',
};

// Only same-site relative paths are safe to redirect to — an absolute or
// protocol-relative callbackUrl would let an attacker send an authenticated
// user off-site (open redirect).
function isSafeCallbackUrl(url: string | undefined): url is string {
  return !!url && url.startsWith('/') && !url.startsWith('//');
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string }>;
}) {
  const session = await auth();
  const { callbackUrl } = await searchParams;
  const redirectTo = isSafeCallbackUrl(callbackUrl)
    ? callbackUrl
    : DEFAULT_AUTHENTICATED_ROUTE;

  if (session && !session.error) {
    redirect(redirectTo);
  }

  return (
    <main className='flex min-h-screen items-center justify-center px-4'>
      <Card className='w-full max-w-sm'>
        <CardHeader className='text-center'>
          <CardTitle>Sign in to Memosphere</CardTitle>
          <CardDescription>
            Continue with your Memosphere account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            action={async () => {
              'use server';
              await signIn('cognito', { redirectTo });
            }}
          >
            <Button type='submit' className='w-full' size='lg'>
              Continue with Cognito
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
