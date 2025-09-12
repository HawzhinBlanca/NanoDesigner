import { SignIn } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

export default function SignInPage() {
  const clerkPublishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  
  // If no Clerk key is configured, show setup instructions
  if (!clerkPublishableKey) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl text-center text-red-600">
              🚨 Authentication Not Configured
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h3 className="font-semibold text-red-800 mb-2">Setup Required</h3>
              <p className="text-red-700 text-sm mb-3">
                Clerk authentication is not configured. To enable sign-in:
              </p>
              <ol className="text-red-600 text-xs space-y-1 list-decimal list-inside">
                <li>Create a Clerk account at clerk.com</li>
                <li>Get your publishable key from the dashboard</li>
                <li>Set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY in .env.local</li>
                <li>Set CLERK_SECRET_KEY in .env.local</li>
                <li>Restart the development server</li>
              </ol>
            </div>
            
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <h3 className="font-semibold text-yellow-800 mb-2">⚠️ Security Warning</h3>
              <p className="text-yellow-700 text-sm">
                Running without authentication is a critical security vulnerability. 
                Do not deploy to production without proper authentication.
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
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Welcome Back</h1>
          <p className="text-gray-600 mt-2">Sign in to your NanoDesigner account</p>
        </div>
        <SignIn 
          appearance={{
            elements: {
              formButtonPrimary: "bg-blue-600 hover:bg-blue-700 text-sm normal-case",
              card: "shadow-lg",
              headerTitle: "hidden",
              headerSubtitle: "hidden"
            }
          }}
          redirectUrl="/dashboard"
          signUpUrl="/sign-up"
        />
      </div>
    </div>
  );
}
