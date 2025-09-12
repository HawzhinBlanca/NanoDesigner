"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface LoadingMessage {
  text: string;
  emoji?: string;
}

const creativeMessages: LoadingMessage[] = [
  { text: "Mixing pixels with perfection", emoji: "✨" },
  { text: "Teaching AI about good taste", emoji: "🎨" },
  { text: "Crafting your masterpiece", emoji: "🖼️" },
  { text: "Adding a sprinkle of magic", emoji: "🪄" },
  { text: "Consulting the muses", emoji: "🎭" },
  { text: "Painting digital dreams", emoji: "🌈" },
  { text: "Brewing creative potions", emoji: "🧪" },
  { text: "Polishing every pixel", emoji: "💎" },
  { text: "Channeling artistic energy", emoji: "⚡" },
  { text: "Weaving visual stories", emoji: "🕸️" },
];

interface LoadingPoetryProps {
  variant?: "default" | "minimal" | "playful";
  showProgress?: boolean;
  progress?: number;
}

export function LoadingPoetry({
  variant = "default",
  showProgress = false,
  progress = 0,
}: LoadingPoetryProps) {
  const [currentMessage, setCurrentMessage] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentMessage((prev) => (prev + 1) % creativeMessages.length);
    }, 2500);

    return () => clearInterval(interval);
  }, []);

  const message = creativeMessages[currentMessage];

  return (
    <div className="flex flex-col items-center justify-center space-y-6">
      <motion.div
        className="relative w-20 h-20"
        animate={{
          scale: [1, 1.1, 1],
          rotate: [0, 180, 360],
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      >
        <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl opacity-20 blur-xl" />
        <div className="relative w-full h-full bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
          <motion.div
            animate={{
              scale: [1, 1.2, 1],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut",
            }}
            className="text-white text-2xl"
          >
            {message.emoji}
          </motion.div>
        </div>
      </motion.div>

      <AnimatePresence mode="wait">
        <motion.div
          key={currentMessage}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <p className="text-lg font-medium text-foreground">
            {message.text}...
          </p>
          {variant === "playful" && (
            <p className="text-sm text-muted-foreground mt-2">
              Great things take time
            </p>
          )}
        </motion.div>
      </AnimatePresence>

      {showProgress && (
        <div className="w-64">
          <div className="h-2 bg-secondary rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-blue-500 to-purple-600"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          {variant !== "minimal" && (
            <p className="text-xs text-muted-foreground text-center mt-2">
              {Math.round(progress)}% complete
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// Skeleton variant for image placeholders
export function ImageLoadingSkeleton() {
  return (
    <div className="relative overflow-hidden rounded-lg bg-secondary">
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer" />
      <div className="flex items-center justify-center h-full">
        <motion.div
          animate={{
            opacity: [0.5, 1, 0.5],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className="text-muted-foreground"
        >
          <svg
            className="w-12 h-12"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
        </motion.div>
      </div>
    </div>
  );
}