'use client';

import { signOut } from 'next-auth/react';

import { ROUTES } from '@/lib/constants';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/ui/alert-dialog';

// Uncontrolled close on purpose: the only way out is signing back in, so there's
// no Cancel action and no onOpenChange — Escape/outside-click can't dismiss it.
export function SessionExpiredDialog({ open }: { open: boolean }) {
  return (
    <AlertDialog open={open}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Your session has expired</AlertDialogTitle>
          <AlertDialogDescription>
            For your security, you&apos;ve been signed out. Please sign in again
            to continue.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogAction
            onClick={() => signOut({ callbackUrl: ROUTES.HOME })}
          >
            OK
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
