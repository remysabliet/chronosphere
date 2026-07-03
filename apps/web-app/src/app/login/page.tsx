import type { Metadata } from 'next';

import { auth, signIn } from '@/lib/auth';
import { ROUTES } from '@/lib/constants';
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

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string }>;
}) {
  const session = await auth();
  const { callbackUrl } = await searchParams;

  if (session) {
    redirect(callbackUrl ?? ROUTES.DASHBOARD);
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
              await signIn('cognito', {
                redirectTo: callbackUrl ?? ROUTES.DASHBOARD,
              });
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
