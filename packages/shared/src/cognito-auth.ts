import { CognitoJwtVerifier } from 'aws-jwt-verify';

export interface CognitoAuthConfig {
  userPoolId: string;
  clientId: string;
}

export type CognitoVerifier = ReturnType<typeof createCognitoVerifier>;

/** One verifier per service process; the JWKS is fetched once and cached internally. */
export function createCognitoVerifier(config: CognitoAuthConfig) {
  return CognitoJwtVerifier.create({
    userPoolId: config.userPoolId,
    tokenUse: 'id',
    clientId: config.clientId,
  });
}

export async function verifyBearerToken(
  authorizationHeader: string | undefined,
  verifier: CognitoVerifier
) {
  if (!authorizationHeader?.startsWith('Bearer ')) {
    throw new Error('Missing bearer token');
  }
  const token = authorizationHeader.slice('Bearer '.length);
  return verifier.verify(token);
}
