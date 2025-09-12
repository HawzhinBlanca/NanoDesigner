"use client";

import { AlertCircle, RefreshCw, Lightbulb, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";

interface ErrorMessage {
  title: string;
  message: string;
  action?: string;
  suggestion?: string;
  icon?: React.ReactNode;
}

const errorMessages: Record<string, ErrorMessage> = {
  imageGenFailed: {
    title: "Oops, let's try that again!",
    message: "Sometimes great art needs a second attempt.",
    action: "Refine your prompt",
    suggestion: "Try adding more descriptive details like style, colors, or mood",
  },
  networkError: {
    title: "Connection hiccup detected",
    message: "We couldn't reach our servers. Let's reconnect!",
    action: "Retry connection",
    suggestion: "Check your internet connection and try again",
  },
  validationError: {
    title: "Almost there!",
    message: "We need a bit more information to proceed.",
    action: "Review input",
    suggestion: "Make sure all required fields are filled out",
  },
  rateLimit: {
    title: "You're on fire! 🔥",
    message: "You've been creating so fast, we need a quick breather.",
    action: "Take a break",
    suggestion: "Your next creation will be available in a moment",
  },
  serverError: {
    title: "Our servers need a moment",
    message: "We're experiencing some technical magic behind the scenes.",
    action: "Try again",
    suggestion: "Our team has been notified and is on it!",
  },
  authError: {
    title: "Let's get you back in",
    message: "Your session has expired for security.",
    action: "Sign in again",
    suggestion: "This keeps your creative work safe and secure",
  },
};

interface FriendlyErrorProps {
  error: keyof typeof errorMessages | string;
  onRetry?: () => void;
  onAction?: () => void;
  className?: string;
}

export function FriendlyError({
  error,
  onRetry,
  onAction,
  className,
}: FriendlyErrorProps) {
  const errorConfig = typeof error === "string" && error in errorMessages 
    ? errorMessages[error]
    : {
        title: "Something unexpected happened",
        message: "Don't worry, we're here to help you get back on track.",
        action: "Try again",
        suggestion: "If this persists, our support team is ready to help",
      };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={`bg-card border border-border rounded-lg p-6 ${className}`}
    >
      <div className="flex items-start space-x-4">
        <motion.div
          animate={{
            rotate: [0, -10, 10, -10, 0],
          }}
          transition={{
            duration: 0.5,
            delay: 0.2,
          }}
          className="flex-shrink-0"
        >
          <div className="w-12 h-12 rounded-full bg-orange-100 dark:bg-orange-900/20 flex items-center justify-center">
            <AlertCircle className="w-6 h-6 text-orange-600 dark:text-orange-400" />
          </div>
        </motion.div>

        <div className="flex-1 space-y-3">
          <div>
            <h3 className="text-lg font-semibold text-foreground">
              {errorConfig.title}
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              {errorConfig.message}
            </p>
          </div>

          {errorConfig.suggestion && (
            <div className="flex items-start space-x-2 p-3 bg-secondary/50 rounded-md">
              <Lightbulb className="w-4 h-4 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-foreground">
                <span className="font-medium">Tip:</span> {errorConfig.suggestion}
              </p>
            </div>
          )}

          <div className="flex items-center space-x-3">
            {onRetry && (
              <Button
                onClick={onRetry}
                variant="default"
                size="sm"
                className="group"
              >
                <RefreshCw className="w-4 h-4 mr-2 group-hover:rotate-180 transition-transform duration-500" />
                {errorConfig.action || "Try again"}
              </Button>
            )}
            {onAction && (
              <Button
                onClick={onAction}
                variant="outline"
                size="sm"
                className="group"
              >
                Learn more
                <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// Inline error for form fields
export function InlineError({ 
  message, 
  className 
}: { 
  message: string;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className={`text-sm text-orange-600 dark:text-orange-400 mt-1 ${className}`}
    >
      <div className="flex items-center space-x-1">
        <AlertCircle className="w-3 h-3" />
        <span>{message}</span>
      </div>
    </motion.div>
  );
}

// Toast-style error notification
export function ErrorToast({ 
  message, 
  onDismiss 
}: { 
  message: string;
  onDismiss?: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 100 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 100 }}
      className="fixed bottom-4 right-4 z-50 bg-card border border-border rounded-lg shadow-lg p-4 max-w-sm"
    >
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded-full bg-orange-100 dark:bg-orange-900/20 flex items-center justify-center flex-shrink-0">
          <AlertCircle className="w-4 h-4 text-orange-600 dark:text-orange-400" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-foreground">{message}</p>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            ×
          </button>
        )}
      </div>
    </motion.div>
  );
}