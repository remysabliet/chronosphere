import type { DefaultSession } from 'next-auth';

// JWT can't be augmented this way (next-auth re-exports it from @auth/core via a
// type-only re-export that declaration merging doesn't see through), so token.idToken
// is read back with a `typeof` guard in auth.ts instead of relying on a typed field.
declare module 'next-auth' {
  interface Session extends DefaultSession {
    idToken?: string;
    error?: string;
  }
}

export {};
