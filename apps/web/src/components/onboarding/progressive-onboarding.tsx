"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { 
  Sparkles, 
  ArrowRight, 
  CheckCircle2, 
  Palette, 
  Wand2,
  Upload,
  Rocket,
  X
} from "lucide-react";
import { useLocalStorage } from "@/hooks/use-local-storage";
import { cn } from "@/lib/utils";

interface OnboardingStep {
  id: string;
  title: string;
  content: string;
  visual?: React.ReactNode;
  interactive?: boolean;
  placeholder?: string;
  optional?: boolean;
  celebration?: boolean;
  action?: () => void;
}

const onboardingSteps: OnboardingStep[] = [
  {
    id: 'welcome',
    title: 'Welcome to NanoDesigner',
    content: 'Let\'s create something amazing together in just a few steps',
    visual: <WelcomeAnimation />,
  },
  {
    id: 'prompt',
    title: 'Describe Your Vision',
    content: 'Tell us what you want to create - be as detailed or simple as you like',
    interactive: true,
    placeholder: 'A modern logo for a tech startup...',
  },
  {
    id: 'customize',
    title: 'Make It Yours',
    content: 'Add your brand colors, upload assets, or skip to use smart defaults',
    optional: true,
    visual: <CustomizeAnimation />,
  },
  {
    id: 'generate',
    title: 'Watch the Magic',
    content: 'AI will create multiple unique options based on your vision',
    celebration: true,
    visual: <GenerateAnimation />,
  },
];

export function ProgressiveOnboarding({ 
  onComplete,
  onSkip,
}: { 
  onComplete?: (data: any) => void;
  onSkip?: () => void;
}) {
  const [currentStep, setCurrentStep] = useState(0);
  const [hasSeenOnboarding, setHasSeenOnboarding] = useLocalStorage('hasSeenOnboarding', false);
  const [onboardingData, setOnboardingData] = useState<Record<string, any>>({});
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    if (hasSeenOnboarding) {
      setIsVisible(false);
    }
  }, [hasSeenOnboarding]);

  if (!isVisible) return null;

  const step = onboardingSteps[currentStep];
  const isLastStep = currentStep === onboardingSteps.length - 1;
  const progress = ((currentStep + 1) / onboardingSteps.length) * 100;

  const handleNext = () => {
    if (isLastStep) {
      handleComplete();
    } else {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSkip = () => {
    setHasSeenOnboarding(true);
    setIsVisible(false);
    onSkip?.();
  };

  const handleComplete = () => {
    setHasSeenOnboarding(true);
    setIsVisible(false);
    onComplete?.(onboardingData);
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="relative w-full max-w-2xl mx-4 bg-background rounded-2xl shadow-2xl overflow-hidden"
          >
            {/* Progress bar */}
            <div className="absolute top-0 left-0 right-0 h-1 bg-secondary">
              <motion.div
                className="h-full bg-gradient-to-r from-blue-500 to-purple-600"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>

            {/* Close button */}
            <button
              onClick={handleSkip}
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors z-10"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="p-8 pt-12">
              <AnimatePresence mode="wait">
                <motion.div
                  key={step.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  {/* Step visual */}
                  {step.visual && (
                    <div className="flex justify-center mb-6">
                      {step.visual}
                    </div>
                  )}

                  {/* Step content */}
                  <div className="text-center mb-8">
                    <h2 className="text-3xl font-bold mb-3">{step.title}</h2>
                    <p className="text-lg text-muted-foreground">{step.content}</p>
                  </div>

                  {/* Interactive element */}
                  {step.interactive && (
                    <div className="mb-6">
                      <textarea
                        className="w-full p-4 rounded-lg border bg-background resize-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                        placeholder={step.placeholder}
                        rows={3}
                        onChange={(e) => setOnboardingData({ 
                          ...onboardingData, 
                          [step.id]: e.target.value 
                        })}
                      />
                    </div>
                  )}

                  {/* Optional step indicator */}
                  {step.optional && (
                    <div className="text-center mb-4">
                      <span className="text-sm text-muted-foreground bg-secondary px-3 py-1 rounded-full">
                        Optional - You can skip this
                      </span>
                    </div>
                  )}
                </motion.div>
              </AnimatePresence>

              {/* Navigation buttons */}
              <div className="flex justify-between items-center">
                <Button
                  variant="ghost"
                  onClick={currentStep === 0 ? handleSkip : handleBack}
                  className="group"
                >
                  {currentStep === 0 ? 'Skip Tour' : 'Back'}
                </Button>

                <div className="flex gap-2">
                  {/* Step indicators */}
                  {onboardingSteps.map((_, index) => (
                    <div
                      key={index}
                      className={cn(
                        "w-2 h-2 rounded-full transition-all",
                        index === currentStep
                          ? "w-8 bg-primary"
                          : index < currentStep
                          ? "bg-primary/50"
                          : "bg-secondary"
                      )}
                    />
                  ))}
                </div>

                <Button
                  onClick={handleNext}
                  className="group premium-button btn-primary"
                >
                  {isLastStep ? 'Start Creating' : 'Next'}
                  <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                </Button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// Animated visuals for onboarding steps
function WelcomeAnimation() {
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
        <Sparkles className="w-16 h-16 text-white" />
      </div>
    </motion.div>
  );
}

function CustomizeAnimation() {
  return (
    <div className="flex gap-4">
      {[Palette, Upload, Wand2].map((Icon, index) => (
        <motion.div
          key={index}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: index * 0.1 }}
          className="w-16 h-16 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 rounded-lg flex items-center justify-center"
        >
          <Icon className="w-8 h-8 text-primary" />
        </motion.div>
      ))}
    </div>
  );
}

function GenerateAnimation() {
  return (
    <motion.div
      animate={{
        scale: [1, 1.1, 1],
      }}
      transition={{
        duration: 2,
        repeat: Infinity,
        ease: "easeInOut",
      }}
      className="relative"
    >
      <div className="absolute inset-0 bg-gradient-to-r from-green-500/20 to-blue-600/20 rounded-full blur-2xl" />
      <div className="relative w-32 h-32 bg-gradient-to-br from-green-500 to-blue-600 rounded-full flex items-center justify-center">
        <Rocket className="w-16 h-16 text-white" />
      </div>
    </motion.div>
  );
}

// Contextual hints for features
export function ContextualHint({
  title,
  content,
  targetRef,
  isVisible,
  onDismiss,
}: {
  title: string;
  content: string;
  targetRef: React.RefObject<HTMLElement>;
  isVisible: boolean;
  onDismiss: () => void;
}) {
  const [position, setPosition] = useState({ top: 0, left: 0 });

  useEffect(() => {
    if (targetRef.current && isVisible) {
      const rect = targetRef.current.getBoundingClientRect();
      setPosition({
        top: rect.bottom + 10,
        left: rect.left + rect.width / 2,
      });
    }
  }, [targetRef, isVisible]);

  if (!isVisible) return null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="fixed z-50 glass-panel rounded-lg p-4 max-w-xs"
      style={{
        top: position.top,
        left: position.left,
        transform: 'translateX(-50%)',
      }}
    >
      <div className="flex items-start justify-between mb-2">
        <h4 className="font-semibold text-sm">{title}</h4>
        <button
          onClick={onDismiss}
          className="text-muted-foreground hover:text-foreground"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
      <p className="text-sm text-muted-foreground">{content}</p>
      <div className="absolute -top-2 left-1/2 transform -translate-x-1/2 w-4 h-4 bg-background rotate-45" />
    </motion.div>
  );
}

// Feature discovery tooltips
export function FeatureDiscovery() {
  const [discoveries, setDiscoveries] = useLocalStorage<string[]>('discoveredFeatures', []);
  
  const markAsDiscovered = (featureId: string) => {
    if (!discoveries.includes(featureId)) {
      setDiscoveries([...discoveries, featureId]);
    }
  };

  const isDiscovered = (featureId: string) => discoveries.includes(featureId);

  return {
    markAsDiscovered,
    isDiscovered,
    resetDiscoveries: () => setDiscoveries([]),
  };
}