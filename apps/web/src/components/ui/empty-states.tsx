"use client";

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { 
  Sparkles, 
  FileImage, 
  Palette, 
  Rocket, 
  PlusCircle,
  Wand2,
  Stars,
  Image
} from "lucide-react";

interface EmptyStateConfig {
  illustration?: React.ReactNode;
  title: string;
  subtitle: string;
  cta?: string;
  ctaAction?: () => void;
  animation?: "fadeInUp" | "pulse" | "bounce";
}

const emptyStates: Record<string, EmptyStateConfig> = {
  noProjects: {
    title: "Your creative journey starts here",
    subtitle: "Create your first masterpiece in seconds",
    cta: "Start Creating",
    animation: "fadeInUp",
  },
  noVariants: {
    title: "Ready to make magic?",
    subtitle: "Describe your vision and watch it come to life",
    cta: "Generate Designs",
    animation: "pulse",
  },
  noHistory: {
    title: "Your story begins now",
    subtitle: "Every great design starts with a single creation",
    cta: "Create First Design",
    animation: "bounce",
  },
  noTemplates: {
    title: "Templates coming soon",
    subtitle: "We're crafting beautiful starting points for you",
    animation: "fadeInUp",
  },
  noAssets: {
    title: "Build your visual library",
    subtitle: "Upload images, logos, and brand assets to get started",
    cta: "Upload Assets",
    animation: "fadeInUp",
  },
};

interface EmptyStateProps {
  type: keyof typeof emptyStates;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({ type, onAction, className }: EmptyStateProps) {
  const config = emptyStates[type] || emptyStates.noProjects;
  
  const getAnimation = () => {
    switch (config.animation) {
      case "fadeInUp":
        return {
          initial: { opacity: 0, y: 20 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.5 }
        };
      case "pulse":
        return {
          initial: { scale: 0.95 },
          animate: { scale: 1 },
          transition: { 
            duration: 2,
            repeat: Infinity,
            repeatType: "reverse" as const
          }
        };
      case "bounce":
        return {
          initial: { y: 0 },
          animate: { y: [-5, 0, -5] },
          transition: { 
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }
        };
      default:
        return {};
    }
  };

  const getIllustration = () => {
    switch (type) {
      case "noProjects":
        return <CreativeIllustration />;
      case "noVariants":
        return <SparklesAnimation />;
      case "noHistory":
        return <TimelineIllustration />;
      case "noAssets":
        return <AssetIllustration />;
      default:
        return <CreativeIllustration />;
    }
  };

  return (
    <motion.div
      {...getAnimation()}
      className={`flex flex-col items-center justify-center py-12 px-6 text-center ${className}`}
    >
      <div className="mb-6">
        {getIllustration()}
      </div>
      
      <h3 className="text-2xl font-bold text-foreground mb-2">
        {config.title}
      </h3>
      
      <p className="text-muted-foreground mb-6 max-w-md">
        {config.subtitle}
      </p>
      
      {config.cta && (
        <Button
          onClick={onAction || (() => {})}
          size="lg"
          className="premium-button btn-primary group"
        >
          <PlusCircle className="w-5 h-5 mr-2 group-hover:rotate-90 transition-transform duration-300" />
          {config.cta}
        </Button>
      )}
    </motion.div>
  );
}

// Creative illustration for empty projects
function CreativeIllustration() {
  return (
    <motion.div
      className="relative w-32 h-32"
      animate={{
        rotate: [0, 5, -5, 0],
      }}
      transition={{
        duration: 4,
        repeat: Infinity,
        ease: "easeInOut",
      }}
    >
      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-600/20 rounded-full blur-2xl" />
      <div className="relative w-full h-full bg-gradient-to-br from-blue-500 to-purple-600 rounded-3xl flex items-center justify-center">
        <FileImage className="w-16 h-16 text-white" />
        <motion.div
          className="absolute -top-2 -right-2"
          animate={{
            scale: [1, 1.2, 1],
            rotate: [0, 180, 360],
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          <Sparkles className="w-6 h-6 text-yellow-400" />
        </motion.div>
      </div>
    </motion.div>
  );
}

// Sparkles animation for empty variants
function SparklesAnimation() {
  return (
    <div className="relative w-32 h-32">
      {[...Array(3)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute"
          style={{
            top: `${20 + i * 25}%`,
            left: `${20 + i * 25}%`,
          }}
          animate={{
            y: [-10, 10, -10],
            x: [-10, 10, -10],
            rotate: [0, 360],
          }}
          transition={{
            duration: 3 + i,
            repeat: Infinity,
            ease: "easeInOut",
            delay: i * 0.3,
          }}
        >
          <Wand2 className={`w-8 h-8 text-purple-${400 + i * 100}`} />
        </motion.div>
      ))}
      <div className="absolute inset-0 flex items-center justify-center">
        <motion.div
          animate={{
            scale: [1, 1.1, 1],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          <Stars className="w-16 h-16 text-yellow-500" />
        </motion.div>
      </div>
    </div>
  );
}

// Timeline illustration for empty history
function TimelineIllustration() {
  return (
    <motion.div className="relative w-32 h-32">
      <div className="absolute inset-0 bg-gradient-to-r from-green-500/20 to-blue-600/20 rounded-full blur-2xl" />
      <motion.div
        className="relative w-full h-full bg-gradient-to-br from-green-500 to-blue-600 rounded-full flex items-center justify-center"
        animate={{
          scale: [1, 1.05, 1],
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      >
        <Rocket className="w-16 h-16 text-white" />
      </motion.div>
    </motion.div>
  );
}

// Asset illustration for empty assets
function AssetIllustration() {
  return (
    <motion.div className="relative w-32 h-32">
      <div className="grid grid-cols-2 gap-2 p-4">
        {[...Array(4)].map((_, i) => (
          <motion.div
            key={i}
            className="w-12 h-12 bg-gradient-to-br from-gray-200 to-gray-300 dark:from-gray-700 dark:to-gray-800 rounded-lg flex items-center justify-center"
            animate={{
              y: i % 2 === 0 ? [-2, 2, -2] : [2, -2, 2],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut",
              delay: i * 0.2,
            }}
          >
            <Image className="w-6 h-6 text-gray-500 dark:text-gray-400" />
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

// Quick empty state for inline use
export function QuickEmptyState({ 
  message, 
  icon: Icon = Sparkles 
}: { 
  message: string;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center py-8 text-center"
    >
      <motion.div
        animate={{
          rotate: [0, -10, 10, 0],
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      >
        <Icon className="w-12 h-12 text-muted-foreground mb-3" />
      </motion.div>
      <p className="text-sm text-muted-foreground">{message}</p>
    </motion.div>
  );
}