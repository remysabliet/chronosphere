import { NextResponse } from 'next/server';

import { auth } from '@/lib/auth';
import { ROUTES } from '@/lib/constants';

export default auth(req => {
  if (!req.auth) {
    const loginUrl = new URL(ROUTES.LOGIN, req.nextUrl.origin);
    loginUrl.searchParams.set('callbackUrl', req.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }
});

export const config = {
  matcher: ['/app/:path*'],
};
