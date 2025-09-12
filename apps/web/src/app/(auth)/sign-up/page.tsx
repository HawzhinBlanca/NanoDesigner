import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

export default function SignUpPage() {
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
                Clerk authentication is not configured. To enable sign-up:
              </p>
              <ol className="text-red-600 text-xs space-y-1 list-decimal list-inside">
                <li>Create a Clerk account at clerk.com</li>
                <li>Get your publishable key from the dashboard</li>
                <li>Set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY in .env.local</li>
                <li>Set CLERK_SECRET_KEY in .env.local</li>
                <li>Restart the development server</li>
              </ol>
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
  
  // Dynamically import and render SignUp component
  try {
    const { SignUp } = require('@clerk/nextjs');
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Create Account</h1>
            <p className="text-gray-600 mt-2">Join NanoDesigner and start creating</p>
          </div>
          <SignUp 
            appearance={{
              elements: {
                formButtonPrimary: "bg-blue-600 hover:bg-blue-700 text-sm normal-case",
                card: "shadow-lg",
                headerTitle: "hidden",
                headerSubtitle: "hidden"
              }
            }}
            redirectUrl="/dashboard"
            signInUrl="/sign-in"
          />
        </div>
      </div>
    );
  } catch (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl text-center text-red-600">
              ⚠️ Clerk Error
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-700 text-sm mb-4">
              Failed to load Clerk authentication component.
            </p>
            <Link href="/">
              <Button variant="outline" className="w-full">
                Return to Home
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }
}
