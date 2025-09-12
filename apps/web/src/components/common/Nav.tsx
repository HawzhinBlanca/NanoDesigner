"use client";
import Link from "next/link";
import { Button } from "@/components/ui/button";

// Conditional import and hook usage for Clerk
function useClerkUser() {
  try {
    // Only import and use Clerk hooks if publishable key is available
    if (typeof window !== 'undefined' && process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
      const { useUser } = require('@clerk/nextjs');
      return useUser();
    }
    return { user: null, isSignedIn: false, isLoaded: true };
  } catch (error) {
    console.warn('Clerk hooks not available:', error);
    return { user: null, isSignedIn: false, isLoaded: true };
  }
}

// Conditional Clerk components
function ClerkSignInButton() {
  try {
    const { SignInButton } = require('@clerk/nextjs');
    return (
      <SignInButton mode="modal">
        <Button size="sm">
          Sign In
        </Button>
      </SignInButton>
    );
  } catch {
    return (
      <Link href="/sign-in">
        <Button size="sm">
          Sign In
        </Button>
      </Link>
    );
  }
}

function ClerkSignOutButton() {
  try {
    const { SignOutButton } = require('@clerk/nextjs');
    return (
      <SignOutButton>
        <Button variant="outline" size="sm">
          Sign Out
        </Button>
      </SignOutButton>
    );
  } catch {
    return (
      <Button variant="outline" size="sm" onClick={() => window.location.href = '/'}>
        Sign Out
      </Button>
    );
  }
}

export function Nav() {
  const { user, isSignedIn, isLoaded } = useClerkUser();
  const hasClerkKey = !!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

  return (
    <nav className="flex items-center gap-4 p-4 border-b border-gray-200">
      <Link href="/" className="font-semibold text-blue-600">NanoDesigner</Link>
      
      {isSignedIn && (
        <>
          <Link href="/dashboard" className="hover:text-blue-600 transition-colors">Dashboard</Link>
          <Link href="/projects/new" className="hover:text-blue-600 transition-colors">New Project</Link>
          <Link href="/templates" className="hover:text-blue-600 transition-colors">Templates</Link>
          <Link href="/admin" className="hover:text-blue-600 transition-colors">Admin</Link>
        </>
      )}
      
      <div className="ml-auto flex items-center gap-4">
        {/* Authentication Status */}
        <div className={`px-3 py-1 rounded-md text-sm ${
          isSignedIn 
            ? "bg-green-100 text-green-700" 
            : "bg-red-100 text-red-700"
        }`}>
          {isLoaded ? (
            isSignedIn ? "🔒 Authenticated" : "🔓 Not Signed In"
          ) : (
            "Loading..."
          )}
        </div>
        
        {/* User Actions */}
        {isLoaded && (
          <div className="flex items-center gap-2">
            {hasClerkKey ? (
              isSignedIn ? (
                <>
                  <span className="text-sm text-gray-600">
                    {user?.firstName || user?.emailAddresses?.[0]?.emailAddress}
                  </span>
                  <ClerkSignOutButton />
                </>
              ) : (
                <ClerkSignInButton />
              )
            ) : (
              <Link href="/sign-in">
                <Button size="sm">
                  Sign In (Demo)
                </Button>
              </Link>
            )}
          </div>
        )}
      </div>
    </nav>
  );
}

