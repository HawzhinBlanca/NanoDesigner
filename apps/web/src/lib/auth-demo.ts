/**
 * Demo authentication for development/testing when Clerk is not configured
 */

// Demo user ID for testing
const DEMO_USER_ID = 'demo-user-123';

/**
 * Auth function that works in demo mode when Clerk is not configured
 */
export async function authDemo() {
  // Check if we're in demo mode (no Clerk key)
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    // Return demo user for testing
    return {
      userId: DEMO_USER_ID,
      sessionId: 'demo-session',
      orgId: null,
      orgRole: null,
      orgSlug: null,
      has: () => true,
      protect: () => {},
    };
  }
  
  // If Clerk is configured, use the real auth
  const { auth } = await import('@clerk/nextjs/server');
  return auth();
}

/**
 * Get current user ID (demo or real)
 */
export async function getCurrentUserId(): Promise<string | null> {
  const authResult = await authDemo();
  return authResult.userId;
}