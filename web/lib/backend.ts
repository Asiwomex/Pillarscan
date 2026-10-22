// Where the site finds the backend in infra/platform. Each value comes from
// an environment variable, set in Vercel and printed by scripts/deploy.ps1.
// None of them is a secret: they say which API, which sign-in page and
// which app.
//
// When they are not set, the backend is switched off. It is torn down when
// nobody is using it, so the project costs nothing, and comes back with one
// command. The site then runs on its saved scans alone: the demo still works
// in full, and the parts that need the backend say they are paused instead
// of sending people to an address that no longer exists.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";
export const COGNITO_DOMAIN = process.env.NEXT_PUBLIC_COGNITO_DOMAIN ?? "";
export const COGNITO_CLIENT_ID = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? "";

/** The API is deployed, so the project account's scan history can be fetched. */
export const API_ONLINE = API_URL !== "";

/** Signing in and connecting an account work. */
export const ACCOUNTS_ONLINE = API_ONLINE && COGNITO_DOMAIN !== "" && COGNITO_CLIENT_ID !== "";
