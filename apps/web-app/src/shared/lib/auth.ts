import NextAuth from 'next-auth';
import Cognito from 'next-auth/providers/cognito';
import type { JWT } from 'next-auth/jwt';

// Refresh the ID token this many seconds before it actually expires, to absorb request latency.
const REFRESH_BUFFER_SECONDS = 60;

let cachedTokenEndpoint: string | undefined;

async function getTokenEndpoint(): Promise<string> {
  if (cachedTokenEndpoint) return cachedTokenEndpoint;
  const res = await fetch(
    `${process.env.COGNITO_ISSUER}/.well-known/openid-configuration`
  );
  const config = await res.json();
  cachedTokenEndpoint = config.token_endpoint as string;
  return cachedTokenEndpoint;
}

function decodeJwtExpiry(jwt: string): number | undefined {
  try {
    const [, payloadSegment] = jwt.split('.');
    if (!payloadSegment) return undefined;
    const payload = JSON.parse(
      Buffer.from(payloadSegment, 'base64url').toString('utf8')
    );
    return typeof payload.exp === 'number' ? payload.exp : undefined;
  } catch {
    return undefined;
  }
}

async function refreshIdToken(token: JWT): Promise<JWT> {
  try {
    const tokenEndpoint = await getTokenEndpoint();
    const res = await fetch(tokenEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: process.env.COGNITO_CLIENT_ID!,
        client_secret: process.env.COGNITO_CLIENT_SECRET!,
        refresh_token: token.refreshToken as string,
      }),
    });
    if (!res.ok)
      throw new Error(`Cognito refresh failed with status ${res.status}`);

    const refreshed = await res.json();
    return {
      ...token,
      idToken: refreshed.id_token,
      idTokenExpires: decodeJwtExpiry(refreshed.id_token),
      error: undefined,
    };
  } catch (error) {
    console.error('Failed to refresh Cognito ID token', error);
    // Surface the failure on the session so the UI can force a re-login instead of looping on 401s.
    return { ...token, error: 'RefreshAccessTokenError' };
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Cognito({
      clientId: process.env.COGNITO_CLIENT_ID,
      clientSecret: process.env.COGNITO_CLIENT_SECRET,
      issuer: process.env.COGNITO_ISSUER,
      // App client only has "openid" + "email" allowed in its Hosted UI scopes.
      authorization: { params: { scope: 'openid email' } },
    }),
  ],
  secret: process.env.NEXTAUTH_SECRET,
  trustHost: true,
  pages: {
    signIn: '/login',
  },
  callbacks: {
    async jwt({ token, account }) {
      if (account?.id_token) {
        token.idToken = account.id_token;
        token.refreshToken = account.refresh_token;
        token.idTokenExpires = decodeJwtExpiry(account.id_token);
        return token;
      }

      const expiresAt =
        typeof token.idTokenExpires === 'number' ? token.idTokenExpires : 0;
      const stillValid =
        Date.now() < (expiresAt - REFRESH_BUFFER_SECONDS) * 1000;
      if (stillValid || typeof token.refreshToken !== 'string') {
        return token;
      }

      return refreshIdToken(token);
    },
    session({ session, token }) {
      session.idToken =
        typeof token.idToken === 'string' ? token.idToken : undefined;
      session.error = typeof token.error === 'string' ? token.error : undefined;
      return session;
    },
  },
});
