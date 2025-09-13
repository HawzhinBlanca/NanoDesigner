"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { useComposerStore } from "@/stores/useComposerStore";
import { useCanonStore } from "@/stores/useCanonStore";
import { renderAPI, RenderAPIError, type RenderResponse } from "@/lib/api/render";
import { connectJobWS, type JobUpdate } from "@/lib/ws";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import {
  Sparkles,
  Settings,
  Image,
  Palette,
  Type,
  Grid3X3,
  Plus,
  X,
  Download,
  Copy,
  Shuffle,
  Check,
  ChevronRight,
  Eye,
  EyeOff,
  AlertCircle,
} from "lucide-react";
// Conditional Clerk imports - will be handled at runtime
import { useTemplatesStore } from "@/stores/useTemplatesStore";
import { useFeatureFlag } from "@/components/providers/FlagsProvider";
import dynamic from "next/dynamic";
import { track } from "@/lib/analytics";
import { sanitizeInput } from "@/lib/validation/schemas";
import { ProgressTracker } from "@/components/ui/progress-tracker";
import { VariantGrid } from "@/components/ui/variant-grid";
import { estimateRenderTime } from "@/lib/api/render";

// Constants
const MAX_VARIANTS = 8;
const MIN_VARIANTS = 1;
const DEFAULT_LOGO_SAFE_ZONE_PCT = 20.0;
const MAX_PROMPT_LENGTH = 2000;

const CompareGrid = dynamic(
  () => import("@/components/compare/CompareGrid")
    .then(m => m.CompareGrid)
    .catch(() => {
      console.error('Failed to load CompareGrid component');
      return () => <div className="text-center text-muted-foreground p-8">Failed to load comparison view</div>;
    }),
  { ssr: false }
);

export default function Composer({ projectId }: { projectId: string }) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const {
    prompt,
    constraints,
    references,
    format,
    dimensions,
    variants,
    selectedVariantId,
    comparing,
    isGenerating,
    currentJobId,
    progress,
    setPrompt,
    setConstraints,
    addReference,
    removeReference,
    setFormat,
    setDimensions,
    generateVariants,
    selectVariant,
    compareVariants,
    updateVariant,
    removeVariant,
    setGenerating,
    setJobId,
    setProgress,
  } = useComposerStore();

  const [showConstraints, setShowConstraints] = useState(false);
  const [variantCount, setVariantCount] = useState(4);
  const [activeTab, setActiveTab] = useState<"preview" | "variants" | "compare">("preview");
  const [lastRenderResult, setLastRenderResult] = useState<RenderResponse | null>(null);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<string>('');
  const [estimatedTime, setEstimatedTime] = useState<number>(30);
  const pollAbortRef = useRef<AbortController | null>(null);
  const { items: templates } = useTemplatesStore();
  const templatesEnabled = useFeatureFlag("enable_templates");

  // Canon store for brand constraints
  const {
    currentCanon,
    isLoading: canonLoading,
    load: loadCanon,
    error: canonError
  } = useCanonStore();

  // Load Canon data on component mount
  useEffect(() => {
    if (projectId && !currentCanon) {
      loadCanon(projectId);
    }
  }, [projectId, currentCanon, loadCanon]);

  // Cancel generation function
  const cancelGeneration = useCallback(() => {
    if (pollAbortRef.current) {
      pollAbortRef.current.abort();
    }
    setGenerating(false);
    setProgress(0);
    setCurrentStep('');
    setRenderError('Generation cancelled by user');
    
    // Mark all generating variants as failed (using immutable update)
    const freshVariants = useComposerStore.getState().variants;
    const updatedVariants = freshVariants.map(variant => {
      if (variant.status === 'generating') {
        return {
          ...variant,
          status: 'failed' as const,
          error: 'Cancelled',
        };
      }
      return variant;
    });
    
    // Update all variants at once
    updatedVariants.forEach(variant => {
      if (variant.status === 'failed' && variant.error === 'Cancelled') {
        updateVariant(variant.id, variant);
      }
    });
  }, [setGenerating, setProgress, variants, updateVariant]);

  // Toggle compare function
  const toggleCompare = useCallback((variantId: string) => {
    const newComparing = comparing.includes(variantId)
      ? comparing.filter(id => id !== variantId)
      : [...comparing, variantId];
    compareVariants(newComparing);
  }, [comparing, compareVariants]);

  useEffect(() => {
    return () => {
      if (pollAbortRef.current) pollAbortRef.current.abort();
    };
  }, []);

  const isValidImageUrl = useCallback((url: string) => {
    if (!url) return false;
    
    // Special handling for blob URLs (file uploads)
    if (url.startsWith('blob:')) {
      // Blob URLs are safe as they're created by the browser
      return true;
    }
    
    // Special handling for base64 data URLs (AI-generated images)
    if (url.startsWith('data:image/')) {
      // Validate base64 image data URLs from AI generation
      const validImageTypes = [
        'data:image/png;base64,',
        'data:image/jpeg;base64,',
        'data:image/jpg;base64,',
        'data:image/webp;base64,',
        'data:image/gif;base64,'
      ];
      
      const isValidImageDataUrl = validImageTypes.some(prefix => url.startsWith(prefix));
      if (isValidImageDataUrl) {
        // Additional validation: ensure base64 format is valid
        const base64Part = url.split(',')[1];
        if (base64Part && base64Part.length > 20) { // More lenient size check for any valid base64 image
          // Proper base64 validation using atob
          try {
            // Attempt to decode the base64 string
            // This will throw if the base64 is invalid
            const decoded = atob(base64Part);
            
            // Additional check: decoded data should have reasonable size for an image
            // Images are typically at least a few KB
            if (decoded.length > 100) {
              return true;
            }
          } catch (e) {
            // Invalid base64 - atob throws on invalid input
            console.warn('Invalid base64 image data:', e);
            return false;
          }
        }
      }
      console.warn('Invalid or suspicious data URL format - URL:', url.substring(0, 100) + '...');
      return false;
    }
    
    try {
      const u = new URL(url);
      
      // STRICT: Only allow HTTPS in production, HTTP in dev
      const allowedProtocols = process.env.NODE_ENV === 'development' 
        ? ['http:', 'https:'] 
        : ['https:'];
      
      if (!allowedProtocols.includes(u.protocol)) {
        console.warn(`Blocked URL with protocol: ${u.protocol}`);
        return false;
      }
      
      // Block any potential XSS vectors (but not legitimate data: URLs)
      const xssPatterns = [
        '<script',
        'javascript:',
        'vbscript:',
        'onclick',
        'onerror',
        'onload',
        'eval(',
        'alert(',
        'document.cookie',
        'window.location',
        '.innerHTML'
      ];
      
      const urlLower = url.toLowerCase();
      for (const pattern of xssPatterns) {
        if (urlLower.includes(pattern)) {
          console.warn(`Blocked URL containing XSS pattern: ${pattern}`);
          return false;
        }
      }
      
      // Additional hostname validation (allow localhost in dev for API server)
      if (process.env.NODE_ENV === 'production') {
        const suspiciousHosts = ['localhost', '127.0.0.1', '0.0.0.0', '::1'];
        if (suspiciousHosts.includes(u.hostname)) {
          console.warn(`Blocked URL with suspicious hostname: ${u.hostname}`);
          return false;
        }
      }
      
      return true;
    } catch (e) {
      console.error('Invalid URL format:', e);
      return false;
    }
  }, []);

  const startGeneration = useCallback(async () => {
    const sanitizedPrompt = prompt.trim().slice(0, MAX_PROMPT_LENGTH);
    if (!sanitizedPrompt) return;

    const controller = new AbortController();
    const signal = controller.signal;

    setGenerating(true);
    setProgress(0);
    setRenderError(null);
    setLastRenderResult(null);
    setCurrentStep('validation');
    
    // Calculate estimated time based on variant count and dimensions
    const validatedCount = Math.min(Math.max(variantCount, MIN_VARIANTS), MAX_VARIANTS);
    const estimated = estimateRenderTime(validatedCount, dimensions);
    setEstimatedTime(estimated);
    
    track.previewStarted(projectId);

    // Generate variants placeholders
    generateVariants(validatedCount);

    // Prepare render parameters
    const renderParams = {
      projectId,
      prompt: sanitizedPrompt,
      variantCount: validatedCount,
      format: format as "png" | "jpg" | "webp",
      dimensions,
      references: references.length > 0 ? references : undefined,
      constraints: Object.keys(constraints).length > 0 ? {
        colors: constraints.palette,
        fonts: constraints.fonts,
        logoSafeZone: typeof constraints.logoSafeZone === 'number' ? constraints.logoSafeZone : DEFAULT_LOGO_SAFE_ZONE_PCT
      } : undefined,
    };

    try {
      // Step 1: Validation (0-20%)
      setCurrentStep('validation');
      setProgress(10);
      await new Promise(resolve => setTimeout(resolve, 500)); // Simulate validation time
      
      if (controller.signal.aborted) return;
      
      // Step 2: Planning (20-40%)
      setCurrentStep('planning');
      setProgress(20);
      
      // Step 3: Generation (40-80%)
      setCurrentStep('generation');
      setProgress(40);
      
      const renderResult = await renderAPI.render(renderParams);
      setProgress(70);
      
      if (controller.signal.aborted) return;

      // Step 4: Processing (80-90%)
      setCurrentStep('processing');
      setProgress(80);
      await new Promise(resolve => setTimeout(resolve, 300)); // Simulate processing time

      // Step 5: Delivery (90-100%)
      setCurrentStep('delivery');
      setProgress(90);

      // Store the full result for cost/audit display
      setLastRenderResult(renderResult);
      
      // Update variants with actual results
      // Get fresh variants from store after generateVariants was called
      const freshVariants = useComposerStore.getState().variants;
      console.log('🔍 Fresh variants from store:', freshVariants);
      console.log('🔍 Render result images:', renderResult.images);
      
      // Find the most recent variants (just created) and update them with results
      const recentVariants = freshVariants.slice(-validatedCount);
      renderResult.images.forEach((image, index) => {
        const variant = recentVariants[index];
        console.log(`🔍 Updating variant ${index}:`, variant?.id, 'with URL:', image.url);
        if (variant) {
          updateVariant(variant.id, {
            finalUrl: image.url,
            previewUrl: image.url,
            status: "completed" as const,
          });
        }
      });
      
      // Only duplicate images in explicit test mode
      if (
        process.env.NEXT_PUBLIC_TEST_MODE === '1' &&
        renderResult.images.length < recentVariants.length &&
        renderResult.images.length > 0
      ) {
        const firstImage = renderResult.images[0];
        for (let i = renderResult.images.length; i < recentVariants.length; i++) {
          const variant = recentVariants[i];
          if (variant) {
            updateVariant(variant.id, {
              finalUrl: firstImage.url,
              previewUrl: firstImage.url,
              status: "completed" as const,
            });
          }
        }
      }
      
      // Select the first variant if we have images
      if (renderResult.images.length > 0 && freshVariants.length > 0) {
        selectVariant(freshVariants[0].id);
      }

      setProgress(100);
      setCurrentStep('');
      setGenerating(false);
      track.renderCompleted(projectId);
      
      // Log successful render with audit info in development
      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Render completed:', {
          cost: renderResult.cost_info.total_cost_usd,
          traceId: renderResult.render_id,
          processingTime: renderResult.processing_time_ms,
          threatLevel: renderResult.security_scan.threat_level,
        });
      }

    } catch (error) {
      if (controller.signal.aborted) return; // Prevent state update if aborted

      if (process.env.NODE_ENV === 'development') {
        console.error("Generation failed:", error);
      }
      setGenerating(false);
      setProgress(0);
      
      if (error instanceof RenderAPIError) {
        // Handle specific API errors
        setRenderError(error.getUserMessage());
        
        // Mark all variants as failed
        const freshVariants = useComposerStore.getState().variants;
        freshVariants.forEach(variant => {
          updateVariant(variant.id, {
            status: "failed",
            error: error.message,
          });
        });
      } else {
        setRenderError(`Unexpected error: ${error instanceof Error ? error.message : 'Unknown error'}`);
        
        // Mark all variants as failed
        const freshVariants = useComposerStore.getState().variants;
        freshVariants.forEach(variant => {
          updateVariant(variant.id, {
            status: "failed",
            error: "Generation failed",
          });
        });
      }
    } finally {
      // Ensure the signal is aborted to clean up
      controller.abort();
    }
  }, [prompt, projectId, variantCount, format, dimensions, references, constraints, setGenerating, setProgress, setLastRenderResult, track, generateVariants, updateVariant, variants]);

  const selectedVariant = variants.find((v) => v.id === selectedVariantId);
  const comparingVariants = variants.filter((v) => comparing.includes(v.id));

  return (
    <main className="p-6 space-y-6">
      {/* Authentication check - conditional based on Clerk availability */}
      {!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2 text-yellow-800 font-semibold mb-2">
            ⚠️ Demo Mode - Authentication Disabled
          </div>
          <p className="text-yellow-700 text-sm">
            Clerk authentication is not configured. In production, this page would require sign-in.
          </p>
        </div>
      ) : null}
      
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Composer</h1>
          <p className="text-muted-foreground mt-1">
            Create stunning visuals with AI-powered generation
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setShowConstraints(prev => !prev)}
          >
            <Settings className="h-4 w-4 mr-2" />
            Constraints
          </Button>
          <Button 
            onClick={startGeneration} 
            disabled={
              isGenerating || 
              !prompt.trim() || 
              prompt.length < 5 || 
              prompt.length > 2000 ||
              variantCount < MIN_VARIANTS || 
              variantCount > MAX_VARIANTS
            }
          >
            {isGenerating ? (
              <>
                <Spinner className="h-4 w-4 mr-2" />
                Generating... {Math.round(progress)}%
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4 mr-2" />
                Generate
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Progress Tracker */}
      <ProgressTracker
        isGenerating={isGenerating}
        progress={progress}
        currentStep={currentStep}
        estimatedTime={estimatedTime}
        variantCount={variantCount}
        onCancel={cancelGeneration}
      />

      {/* Error Display */}
      {renderError && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <X className="h-4 w-4" />
              <span className="font-medium">Generation Failed</span>
            </div>
            <p className="text-sm text-muted-foreground mt-1">{renderError}</p>
          </CardContent>
        </Card>
      )}

      {/* Cost & Brand Canon Results */}
      {lastRenderResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-4 w-4" />
              Generation Results
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Cost Tracking */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Cost</span>
                  <Badge variant="secondary">${(lastRenderResult.cost_info.total_cost_usd || 0).toFixed(4)}</Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  Trace: {lastRenderResult.render_id}
                </p>
              </div>

              {/* Security Scan */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Security</span>
                  <Badge variant={lastRenderResult.security_scan.threat_level === "low" ? "default" : "destructive"}>
                    {lastRenderResult.security_scan.threat_level}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  Confidence: {(lastRenderResult.security_scan.confidence * 100).toFixed(0)}%
                </p>
              </div>

              {/* Model & Verification */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Model</span>
                  <Badge variant="outline">{lastRenderResult.metadata.model_used}</Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  Processing: {lastRenderResult.processing_time_ms}ms
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Canvas Area */}
        <div className="lg:col-span-2 space-y-4">
          {/* Tab Navigation */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex gap-2">
                <Button
                  variant={activeTab === "preview" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setActiveTab("preview")}
                >
                  Preview
                </Button>
                <Button
                  variant={activeTab === "variants" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setActiveTab("variants")}
                >
                  Variants ({variants.length})
                </Button>
                <Button
                  variant={activeTab === "compare" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setActiveTab("compare")}
                  disabled={comparing.length < 2}
                >
                  Compare
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {/* Preview Tab */}
              {activeTab === "preview" && (
                <div className="min-h-[500px] flex items-center justify-center bg-muted/20 rounded-lg">
                  {(() => {
                    const src = selectedVariant?.finalUrl || selectedVariant?.previewUrl;
                    if (src && isValidImageUrl(src)) {
                      return (
                        <img
                          src={src}
                          alt="Generated image"
                          className="max-w-full h-auto rounded-lg"
                        />
                      );
                    }
                    return (
                      <div className="text-center">
                        <Image className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                        <p className="text-muted-foreground">
                          {isGenerating
                            ? "Generating preview..."
                            : "No preview available. Generate variants to see results."}
                        </p>
                      </div>
                    );
                  })()}
                </div>
              )}

              {/* Variants Tab */}
              {activeTab === "variants" && (
                <VariantGrid
                  variants={variants.map(v => ({
                    id: v.id,
                    status: v.status === 'completed' ? 'completed' : v.status === 'failed' ? 'failed' : 'generating',
                    previewUrl: v.previewUrl,
                    finalUrl: v.finalUrl,
                    error: v.error,
                    progress: isGenerating ? progress : undefined
                  }))}
                  selectedVariantId={selectedVariantId || undefined}
                  comparing={comparing}
                  onSelectVariant={selectVariant}
                  onToggleCompare={toggleCompare}
                  onDownload={(variant) => {
                    if (variant.finalUrl) {
                      const link = document.createElement('a');
                      link.href = variant.finalUrl;
                      link.download = `variant-${variant.id}.png`;
                      link.click();
                    }
                  }}
                  isGenerating={isGenerating}
                />
              )}

              {/* Compare Tab */}
              {activeTab === "compare" && (
                <CompareGrid variants={comparingVariants} />
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar Controls */}
        <div className="space-y-4">
          {/* Prompt Input */}
          <Card>
            <CardHeader>
              <CardTitle>Prompt</CardTitle>
              <CardDescription>
                Describe what you want to create
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {templatesEnabled && templates.length > 0 && (
                <div className="space-y-2">
                  <Label>Quick Apply Template</Label>
                  <select
                    className="w-full mt-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>)=>{
                      const t = templates.find(tt=>tt.id===e.target.value);
                      if(t){
                        setPrompt(t.prompt);
                        if(t.constraints) setConstraints(t.constraints);
                        track.templateApplied(projectId, t.id);
                      }
                    }}
                  >
                    <option value="">Select a template...</option>
                    {templates.map(t=> (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                </div>
              )}
              <Textarea
                placeholder="A modern logo for a tech startup..."
                value={prompt}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => {
                  const sanitizedValue = sanitizeInput(e.target.value);
                  setPrompt(sanitizedValue);
                }}
                className={`min-h-[120px] ${
                  prompt.length > 2000 ? 'border-red-500 focus:border-red-500' : ''
                }`}
                maxLength={2000}
              />
              
              {/* Character count and validation */}
              <div className="flex justify-between items-center text-sm">
                <div className="flex items-center gap-2">
                  {prompt.length < 5 && prompt.length > 0 && (
                    <span className="text-red-600 flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      Prompt too short (minimum 5 characters)
                    </span>
                  )}
                  {prompt.length > 2000 && (
                    <span className="text-red-600 flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      Prompt too long (maximum 2000 characters)
                    </span>
                  )}
                </div>
                <span className={`${
                  prompt.length > 2000 ? 'text-red-600' : 
                  prompt.length > 1800 ? 'text-yellow-600' : 'text-gray-500'
                }`}>
                  {prompt.length}/2000
                </span>
              </div>
              
              <div className="space-y-2">
                <Label>Output Settings</Label>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">Format</Label>
                    <select
                      className="w-full mt-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={format}
                      onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFormat(e.target.value)} // setFormat is stable from zustand
                    >
                      <option value="png">PNG</option>
                      <option value="jpg">JPG</option>
                      <option value="webp">WebP</option>
                    </select>
                  </div>
                  <div>
                    <Label className="text-xs">Dimensions</Label>
                    <select
                      className="w-full mt-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={dimensions}
                      onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setDimensions(e.target.value)} // setDimensions is stable from zustand
                    >
                      <option value="1920x1080">1920x1080</option>
                      <option value="1280x720">1280x720</option>
                      <option value="1080x1080">1080x1080</option>
                      <option value="640x480">640x480</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Variants to Generate</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    min={MIN_VARIANTS}
                    max={MAX_VARIANTS}
                    value={variantCount}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                      const value = Number(e.target.value);
                      if (value >= MIN_VARIANTS && value <= MAX_VARIANTS) {
                        setVariantCount(value);
                      }
                    }} // setVariantCount is from useState
                    className="w-20"
                  />
                  <span className="text-sm text-muted-foreground">variants</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Constraints Panel */}
          {showConstraints && (
            <Card>
              <CardHeader>
                <CardTitle>Constraints</CardTitle>
                <CardDescription>
                  Apply brand guidelines and restrictions
                  {currentCanon && (
                    <span className="block text-xs text-green-600 mt-1">
                      ✓ Brand Canon loaded for {projectId}
                    </span>
                  )}
                  {canonError && (
                    <span className="block text-xs text-red-600 mt-1">
                      ⚠ Canon error: {canonError}
                    </span>
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label className="flex items-center gap-2 mb-2">
                    <Palette className="h-4 w-4" />
                    Color Palette
                  </Label>
                  <div className="space-y-2">
                    {/* Canon Colors */}
                    {currentCanon && (
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">From Brand Canon:</p>
                        <div className="flex flex-wrap gap-2">
                          {[
                            currentCanon.palette.primary,
                            currentCanon.palette.secondary,
                            currentCanon.palette.accent,
                            ...currentCanon.palette.custom
                          ].filter(Boolean).map((color, idx) => (
                            <div
                              key={`canon-${idx}`}
                              className="w-8 h-8 rounded border-2"
                              style={{ backgroundColor: color }}
                              title={`Canon color: ${color}`}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Manual Override Colors */}
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Manual Override:</p>
                      <div className="flex flex-wrap gap-2">
                        {(constraints.palette || []).map((color, idx) => (
                          <div
                            key={idx}
                            className="w-8 h-8 rounded border"
                            style={{ backgroundColor: color }}
                          />
                        ))}
                        <Button size="icon" variant="outline" className="h-8 w-8">
                          <Plus className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <Label className="flex items-center gap-2 mb-2">
                    <Type className="h-4 w-4" />
                    Fonts
                  </Label>
                  <div className="space-y-2">
                    {/* Canon Fonts */}
                    {currentCanon && (
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">From Brand Canon:</p>
                        <div className="flex flex-wrap gap-1">
                          {currentCanon.typography.fonts.map((font, idx) => (
                            <Badge key={`canon-font-${idx}`} variant="outline">
                              {font}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Manual Override Fonts */}
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Manual Override:</p>
                      <div className="flex flex-wrap gap-1">
                        {(constraints.fonts || []).map((font, idx) => (
                          <Badge key={idx} variant="secondary">
                            {font}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <Label>Logo Safe Zone</Label>
                  <p className="text-xs text-muted-foreground mt-1">
                    Define areas where logos should not overlap
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Reference Images */}
          <Card>
            <CardHeader>
              <CardTitle>References</CardTitle>
              <CardDescription>
                Add images for style reference
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {references.map((ref, idx) => (
                  <div key={idx} className="flex items-center gap-2 p-2 border rounded">
                    {ref.startsWith('blob:') || ref.startsWith('http') ? (
                      <img 
                        src={ref} 
                        alt="Reference" 
                        className="w-12 h-12 object-cover rounded"
                        onError={(e) => {
                          // If image fails to load, show placeholder
                          (e.target as HTMLImageElement).style.display = 'none';
                        }}
                      />
                    ) : (
                      <div className="w-12 h-12 bg-muted rounded flex items-center justify-center">
                        <Image className="h-6 w-6 text-muted-foreground" />
                      </div>
                    )}
                    <span className="text-sm truncate flex-1">
                      {ref.startsWith('blob:') ? 'Uploaded file' : ref.split('/').pop()}
                    </span>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-6 w-6"
                      aria-label={`Remove reference: ${ref}`}
                      onClick={() => {
                        // Clean up blob URL if it's a local file
                        if (ref.startsWith('blob:')) {
                          URL.revokeObjectURL(ref);
                        }
                        removeReference(ref);
                      }}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
                <>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,.pdf,.doc,.docx,.txt"
                    multiple
                    className="hidden"
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                      const files = e.target.files;
                      if (files) {
                        Array.from(files).forEach(file => {
                          // Create a local URL for the file
                          const url = URL.createObjectURL(file);
                          addReference(url);
                        });
                      }
                      // Reset the input so the same file can be selected again
                      e.target.value = '';
                    }}
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => {
                      fileInputRef.current?.click();
                    }}
                  >
                    <Plus className="h-3 w-3 mr-2" />
                    Add Reference
                  </Button>
                </>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
      </div>
    </main>
  );
}
