/**
 * Complete authentication bypass for development/demo mode
 * This bypasses all Clerk authentication when NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY is not set
 */

import React from 'react';

// Demo user for bypassed auth
export const DEMO_USER = {
  id: 'demo-user-123',
  userId: 'demo-user-123',
  sessionId: 'demo-session',
  email: 'demo@example.com',
  firstName: 'Demo',
  lastName: 'User',
  fullName: 'Demo User',
  imageUrl: null,
  orgId: null,
  orgRole: null,
  orgSlug: null,
  emailAddresses: [{ emailAddress: 'demo@example.com' }],
};

/**
 * Mock auth() function that returns demo user when Clerk is not configured
 */
export async function auth() {
  // Always return demo user in bypass mode
  return {
    userId: DEMO_USER.userId,
    sessionId: DEMO_USER.sessionId,
    orgId: DEMO_USER.orgId,
    orgRole: DEMO_USER.orgRole,
    orgSlug: DEMO_USER.orgSlug,
    has: () => true,
    protect: () => {},
  };
}

/**
 * Mock currentUser() function that returns demo user when Clerk is not configured
 */
export async function currentUser() {
  // Always return demo user in bypass mode
  return DEMO_USER;
}

/**
 * Mock useAuth() hook for client components
 */
export function useAuth() {
  return {
    isLoaded: true,
    isSignedIn: true,
    userId: DEMO_USER.userId,
    sessionId: DEMO_USER.sessionId,
    user: DEMO_USER,
    signOut: async () => {
      console.log('Sign out in demo mode');
    },
  };
}

/**
 * Mock useUser() hook for client components
 */
export function useUser() {
  return {
    isLoaded: true,
    isSignedIn: true,
    user: DEMO_USER,
  };
}

/**
 * Mock SignIn component
 */
export function SignIn() {
  return null;
}

/**
 * Mock SignUp component
 */
export function SignUp() {
  return null;
}

/**
 * Mock UserButton component
 */
export function UserButton() {
  return null;
}

// Mock components are exported from a separate tsx file

/**
 * Mock SignedIn component - always shows children
 */
export function SignedIn({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

/**
 * Mock SignedOut component - never shows children
 */
export function SignedOut({ children }: { children: React.ReactNode }) {
  return null;
}