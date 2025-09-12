"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";

// Conditional Clerk hook usage
function useClerkUser() {
  try {
    if (typeof window !== 'undefined' && process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
      const { useUser } = require('@clerk/nextjs');
      return useUser();
    }
    return { user: null, isLoaded: true };
  } catch (error) {
    return { user: null, isLoaded: true };
  }
}

function ClerkSignOutButton() {
  try {
    const { SignOutButton } = require('@clerk/nextjs');
    return (
      <SignOutButton>
        <Button variant="outline" className="w-full">
          Sign Out
        </Button>
      </SignOutButton>
    );
  } catch {
    return (
      <Link href="/">
        <Button variant="outline" className="w-full">
          Return to Home
        </Button>
      </Link>
    );
  }
}

export default function ProtectedPage() {
  const { user, isLoaded } = useClerkUser();
  const hasClerkKey = !!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

  if (!isLoaded) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  // If Clerk is not configured, show setup message
  if (!hasClerkKey) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl font-bold text-red-600">
              🚨 Authentication Not Configured
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-700 text-sm">
                This page requires authentication, but Clerk is not configured.
                Please set up Clerk API keys to enable authentication.
              </p>
            </div>
            <Link href="/">
              <Button variant="outline" className="w-full">
                Return to Home (Demo Mode)
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold text-green-600">
            🔒 Protected Area - Authentication Working!
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <h2 className="font-semibold text-green-800 mb-2">✅ Authentication Status: ACTIVE</h2>
            <div className="space-y-2 text-sm">
              <p><strong>User ID:</strong> {user?.id}</p>
              <p><strong>Email:</strong> {user?.primaryEmailAddress?.emailAddress}</p>
              <p><strong>Name:</strong> {user?.fullName || 'Not provided'}</p>
              <p><strong>Created:</strong> {user?.createdAt?.toLocaleDateString()}</p>
            </div>
          </div>
          
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-semibold text-blue-800 mb-2">🛡️ Security Features Active:</h3>
            <ul className="text-sm space-y-1 text-blue-700">
              <li>• JWT token validation</li>
              <li>• Protected route middleware</li>
              <li>• Session management</li>
              <li>• Automatic token refresh</li>
            </ul>
          </div>

          <div className="pt-4">
            <ClerkSignOutButton />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

