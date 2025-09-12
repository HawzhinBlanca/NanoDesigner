"use client";

import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { 
  Sparkles, 
  Brain, 
  Palette, 
  Image, 
  CheckCircle, 
  AlertCircle,
  Clock,
  Zap
} from "lucide-react";

export interface GenerationStep {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  status: 'pending' | 'active' | 'completed' | 'error';
  progress?: number;
  duration?: number;
}

interface ProgressTrackerProps {
  isGenerating: boolean;
  progress: number;
  currentStep?: string;
  estimatedTime?: number;
  variantCount: number;
  onCancel?: () => void;
}

const DEFAULT_STEPS: GenerationStep[] = [
  {
    id: 'validation',
    name: 'Input Validation',
    description: 'Validating prompt and parameters',
    icon: CheckCircle,
    status: 'pending'
  },
  {
    id: 'planning',
    name: 'AI Planning',
    description: 'Creating generation strategy',
    icon: Brain,
    status: 'pending'
  },
  {
    id: 'generation',
    name: 'Image Generation',
    description: 'Creating visual content',
    icon: Sparkles,
    status: 'pending'
  },
  {
    id: 'processing',
    name: 'Post-Processing',
    description: 'Optimizing and finalizing',
    icon: Palette,
    status: 'pending'
  },
  {
    id: 'delivery',
    name: 'Delivery',
    description: 'Preparing results',
    icon: Image,
    status: 'pending'
  }
];

export function ProgressTracker({
  isGenerating,
  progress,
  currentStep,
  estimatedTime = 30,
  variantCount,
  onCancel
}: ProgressTrackerProps) {
  const [steps, setSteps] = useState<GenerationStep[]>(DEFAULT_STEPS);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [startTime, setStartTime] = useState<number | null>(null);

  // Update steps based on progress
  useEffect(() => {
    if (!isGenerating) {
      setSteps(DEFAULT_STEPS.map(step => ({ ...step, status: 'pending' })));
      setElapsedTime(0);
      setStartTime(null);
      return;
    }

    if (startTime === null) {
      setStartTime(Date.now());
    }

    setSteps(prevSteps => {
      return prevSteps.map((step, index) => {
        const stepProgress = (index + 1) * 20; // Each step is 20% of total
        
        if (progress >= stepProgress) {
          return { ...step, status: 'completed' };
        } else if (progress >= stepProgress - 20) {
          return { 
            ...step, 
            status: 'active',
            progress: ((progress - (stepProgress - 20)) / 20) * 100
          };
        }
        return { ...step, status: 'pending' };
      });
    });
  }, [isGenerating, progress, startTime]);

  // Update elapsed time
  useEffect(() => {
    if (!isGenerating || !startTime) return;

    const interval = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [isGenerating, startTime]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const remainingTime = Math.max(0, estimatedTime - elapsedTime);
  const activeStep = steps.find(step => step.status === 'active');

  if (!isGenerating) {
    return null;
  }

  return (
    <Card className="border-blue-200 bg-blue-50/50">
      <CardContent className="pt-6">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Spinner className="h-6 w-6 text-blue-600" />
                <Sparkles className="h-3 w-3 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold text-blue-900">
                  Generating {variantCount} variant{variantCount > 1 ? 's' : ''}
                </h3>
                <p className="text-sm text-blue-700">
                  {activeStep ? activeStep.description : 'Preparing generation...'}
                </p>
              </div>
            </div>
            
            <div className="text-right">
              <div className="flex items-center gap-2 text-sm text-blue-700">
                <Clock className="h-4 w-4" />
                <span>{formatTime(elapsedTime)} / ~{formatTime(estimatedTime)}</span>
              </div>
              <div className="text-xs text-blue-600 mt-1">
                {remainingTime > 0 ? `~${formatTime(remainingTime)} remaining` : 'Finalizing...'}
              </div>
            </div>
          </div>

          {/* Overall Progress */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-blue-900">Overall Progress</span>
              <span className="text-sm font-bold text-blue-900">{Math.round(progress)}%</span>
            </div>
            <Progress 
              value={progress} 
              className="h-3 bg-blue-100"
            />
          </div>

          {/* Step Progress */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-blue-900">Generation Steps</h4>
            <div className="space-y-2">
              {steps.map((step, index) => {
                const Icon = step.icon;
                return (
                  <div key={step.id} className="flex items-center gap-3">
                    <div className={`
                      flex items-center justify-center w-8 h-8 rounded-full border-2 transition-all duration-300
                      ${step.status === 'completed' 
                        ? 'bg-green-100 border-green-500 text-green-600' 
                        : step.status === 'active'
                        ? 'bg-blue-100 border-blue-500 text-blue-600 animate-pulse'
                        : step.status === 'error'
                        ? 'bg-red-100 border-red-500 text-red-600'
                        : 'bg-gray-100 border-gray-300 text-gray-400'
                      }
                    `}>
                      {step.status === 'active' ? (
                        <Spinner className="h-4 w-4" />
                      ) : step.status === 'error' ? (
                        <AlertCircle className="h-4 w-4" />
                      ) : (
                        <Icon className="h-4 w-4" />
                      )}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`
                          text-sm font-medium
                          ${step.status === 'completed' ? 'text-green-700' : 
                            step.status === 'active' ? 'text-blue-700' :
                            step.status === 'error' ? 'text-red-700' :
                            'text-gray-500'}
                        `}>
                          {step.name}
                        </span>
                        
                        {step.status === 'completed' && (
                          <Badge variant="secondary" className="text-xs bg-green-100 text-green-700">
                            Done
                          </Badge>
                        )}
                        
                        {step.status === 'active' && step.progress !== undefined && (
                          <Badge variant="secondary" className="text-xs bg-blue-100 text-blue-700">
                            {Math.round(step.progress)}%
                          </Badge>
                        )}
                      </div>
                      
                      <p className="text-xs text-gray-600 truncate">
                        {step.description}
                      </p>
                      
                      {step.status === 'active' && step.progress !== undefined && (
                        <div className="mt-1">
                          <Progress 
                            value={step.progress} 
                            className="h-1 bg-blue-100"
                          />
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Performance Metrics */}
          <div className="grid grid-cols-2 gap-4 pt-4 border-t border-blue-200">
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 text-blue-700">
                <Zap className="h-4 w-4" />
                <span className="text-sm font-medium">Speed</span>
              </div>
              <p className="text-xs text-blue-600 mt-1">
                {elapsedTime > 0 ? `${(progress / elapsedTime * 60).toFixed(1)}%/min` : 'Calculating...'}
              </p>
            </div>
            
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 text-blue-700">
                <Image className="h-4 w-4" />
                <span className="text-sm font-medium">Queue</span>
              </div>
              <p className="text-xs text-blue-600 mt-1">
                {variantCount} image{variantCount > 1 ? 's' : ''}
              </p>
            </div>
          </div>

          {/* Cancel Button */}
          {onCancel && (
            <div className="pt-2 border-t border-blue-200">
              <button
                onClick={onCancel}
                className="w-full text-sm text-blue-600 hover:text-blue-800 transition-colors"
              >
                Cancel Generation
              </button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
