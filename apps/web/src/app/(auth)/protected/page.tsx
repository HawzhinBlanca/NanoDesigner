"use client";
import { SignedIn, SignedOut, SignInButton } from "@clerk/nextjs";

export default function ProtectedPage() {
  return (
    <div className="p-6">
      <SignedIn>
        <h1 className="text-xl font-semibold">Protected Area</h1>
        <p className="text-sm text-muted-foreground">You are signed in.</p>
      </SignedIn>
      <SignedOut>
        <p className="text-sm">Please sign in to access this page.</p>
        <SignInButton />
      </SignedOut>
    </div>
  );
}

