// Sign-in with Amazon Cognito, using the authorization code flow with PKCE.
//
// The site never sees a password. It sends the visitor to Cognito's own
// sign-in page and gets back a one-time code, which it swaps for a token.
// PKCE ties that code to this browser: the swap only works with a secret
// (the "verifier") that never left it, so a code intercepted on the way
// back is useless to anyone else.

// Neither value is a secret. They say which sign-in page and which app.
const COGNITO_DOMAIN =
  process.env.NEXT_PUBLIC_COGNITO_DOMAIN ??
  "https://pillarscan-8cf06f80.auth.us-east-1.amazoncognito.com";
const CLIENT_ID = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? "7t6utkue0gvevikhffi16v4821";

const SESSION_KEY = "pillarscan.session";
const PENDING_KEY = "pillarscan.sign-in";

export type Session = {
  accessToken: string;
  email: string | null;
  expiresAt: number;
};

function redirectUri(): string {
  return `${window.location.origin}/account`;
}

function base64Url(bytes: Uint8Array): string {
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function randomString(): string {
  return base64Url(crypto.getRandomValues(new Uint8Array(48)));
}

/** Send the visitor to Cognito's sign-in page. */
export async function signIn(): Promise<void> {
  const verifier = randomString();
  const state = randomString();
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  sessionStorage.setItem(PENDING_KEY, JSON.stringify({ verifier, state }));

  const query = new URLSearchParams({
    response_type: "code",
    client_id: CLIENT_ID,
    redirect_uri: redirectUri(),
    scope: "openid email",
    state,
    code_challenge: base64Url(new Uint8Array(digest)),
    code_challenge_method: "S256",
  });
  // This leaves the site for Cognito's sign-in page, so it is a real
  // navigation and not something the Next.js router can do.
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.assign(`${COGNITO_DOMAIN}/oauth2/authorize?${query}`);
}

/**
 * Finish a sign-in if this page load is Cognito sending the visitor back.
 * Returns the new session, or null if there was nothing to finish.
 */
export async function completeSignIn(): Promise<Session | null> {
  const query = new URLSearchParams(window.location.search);
  const code = query.get("code");
  const problem = query.get("error_description") ?? query.get("error");
  if (!code && !problem) return null;

  const pending = sessionStorage.getItem(PENDING_KEY);
  sessionStorage.removeItem(PENDING_KEY);
  // Take the code out of the address bar, so it is not kept in history
  // or sent anywhere by a later reload.
  window.history.replaceState(null, "", window.location.pathname);

  if (problem) throw new Error(problem);
  const { verifier, state } = pending ? JSON.parse(pending) : { verifier: null, state: null };
  // The state must be the one this browser sent, or the response is not
  // an answer to a sign-in started here.
  if (!verifier || state !== query.get("state")) {
    throw new Error("The sign-in could not be completed. Please try again.");
  }

  const response = await fetch(`${COGNITO_DOMAIN}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: CLIENT_ID,
      code: code as string,
      redirect_uri: redirectUri(),
      code_verifier: verifier,
    }),
  });
  if (!response.ok) throw new Error("The sign-in could not be completed. Please try again.");
  const tokens = (await response.json()) as {
    access_token: string;
    id_token: string;
    expires_in: number;
  };

  const session: Session = {
    accessToken: tokens.access_token,
    email: emailFrom(tokens.id_token),
    expiresAt: Date.now() + tokens.expires_in * 1000,
  };
  // Kept for this tab only and gone when it closes. The token lasts an
  // hour, which limits what a stolen one is worth.
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  return session;
}

// Only used to show who is signed in. The API never trusts this: it reads
// the user from the token that API Gateway has verified.
function emailFrom(idToken: string): string | null {
  try {
    const payload = idToken.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return (JSON.parse(atob(payload)) as { email?: string }).email ?? null;
  } catch {
    return null;
  }
}

/** The current session, or null if nobody is signed in or it has expired. */
export function currentSession(): Session | null {
  const stored = sessionStorage.getItem(SESSION_KEY);
  if (!stored) return null;
  const session = JSON.parse(stored) as Session;
  if (session.expiresAt <= Date.now()) {
    sessionStorage.removeItem(SESSION_KEY);
    return null;
  }
  return session;
}

export function forgetSession(): void {
  sessionStorage.removeItem(SESSION_KEY);
}

/** Sign out here and at Cognito, so the next sign-in asks for the password. */
export function signOut(): void {
  forgetSession();
  const query = new URLSearchParams({ client_id: CLIENT_ID, logout_uri: redirectUri() });
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.assign(`${COGNITO_DOMAIN}/logout?${query}`);
}
