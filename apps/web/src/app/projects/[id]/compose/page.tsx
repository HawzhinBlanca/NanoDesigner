"use client";

import { useRef, useState, useEffect } from "react";
import { useComposerStore } from "@/stores/useComposerStore";
import { api, type RenderRequest } from "@/lib/api";
import { connectJobWS, pollJob, type JobUpdate } from "@/lib/ws";
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
} from "lucide-react";
// import { SignedIn, SignedOut, SignInButton } from "@clerk/nextjs"; // Removed for demo mode
import { useTemplatesStore } from "@/stores/useTemplatesStore";
import { useFeatureFlag } from "@/components/providers/FlagsProvider";
import dynamic from "next/dynamic";
import { track } from "@/lib/analytics";
const CompareGrid = dynamic(() => import("@/components/compare/CompareGrid").then(m => m.CompareGrid), { ssr: false });

export default async function ComposePage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = await params;
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
  const pollAbortRef = useRef<AbortController | null>(null);
  const { items: templates } = useTemplatesStore();
  const templatesEnabled = useFeatureFlag("enable_templates");

  async function startGeneration() {
    if (!prompt.trim()) return;

    setGenerating(true);
    setProgress(0);
    track.previewStarted(resolvedParams.id);

    // Generate variants
    generateVariants(variantCount);

    const req: RenderRequest = {
      project_id: resolvedParams.id,
      prompts: { task: "create", instruction: prompt },
      outputs: { count: variantCount, format, dimensions },
      constraints,
    } as RenderRequest;

    try {
      const resp = await api.renderAsync(req);
      if (resp.job_id) {
        setJobId(resp.job_id);
        let wsClosed = false;
        let gotMessage = false;
        let variantIndex = 0;

        try {
          const ws = connectJobWS(
            resp.job_id,
            (u) => {
              gotMessage = true;
              setProgress(u.progress || 0);

              // Update variant with preview/final URLs
              if (u.preview_url || u.url) {
                const variant = variants[variantIndex];
                if (variant) {
                  updateVariant(variant.id, {
                    previewUrl: u.preview_url,
                    finalUrl: u.url,
                    status: u.url ? "completed" : "generating",
                  });
                  if (u.url) variantIndex++;
                }
              }

              if (u.status === "completed") {
                setGenerating(false);
                track.renderCompleted(resolvedParams.id);
              } else if (u.status === "failed") {
                setGenerating(false);
                if (variants[variantIndex]) {
                  updateVariant(variants[variantIndex]!.id, {
                    status: "failed",
                    error: u.error,
                  });
                }
              }
            },
            () => {
              wsClosed = true;
            }
          );

          // Fallback to polling if WebSocket fails
          setTimeout(() => {
            if (!gotMessage || wsClosed) {
              pollAbortRef.current?.abort();
              const ac = new AbortController();
              pollAbortRef.current = ac;
              void pollJob(
                resp.job_id!,
                (u) => {
                  setProgress(u.progress || 0);
                  // Similar update logic as above
                },
                ac.signal
              );
            }
          }, 3000);

          setTimeout(() => ws.close(), 120000);
        } catch {
          // Fallback to polling
          const ac = new AbortController();
          pollAbortRef.current = ac;
          void pollJob(
            resp.job_id!,
            (u) => {
              setProgress(u.progress || 0);
              // Similar update logic as above
            },
            ac.signal
          );
        }
      }
    } catch (error) {
      console.error("Generation failed:", error);
      setGenerating(false);
    }
  }

  const selectedVariant = variants.find((v) => v.id === selectedVariantId);
  const comparingVariants = variants.filter((v) => comparing.includes(v.id));

  return (
    <main className="p-6 space-y-6">
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
            onClick={() => setShowConstraints(!showConstraints)}
          >
            <Settings className="h-4 w-4 mr-2" />
            Constraints
          </Button>
          <Button onClick={startGeneration} disabled={isGenerating || !prompt.trim()}>
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
                  {selectedVariant?.finalUrl || selectedVariant?.previewUrl ? (
                    <img
                      src={selectedVariant.finalUrl || selectedVariant.previewUrl}
                      alt="Generated image"
                      className="max-w-full h-auto rounded-lg"
                    />
                  ) : (
                    <div className="text-center">
                      <Image className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                      <p className="text-muted-foreground">
                        {isGenerating
                          ? "Generating preview..."
                          : "No preview available. Generate variants to see results."}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Variants Tab */}
              {activeTab === "variants" && (
                <div className="grid grid-cols-2 gap-4">
                  {variants.length === 0 ? (
                    <div className="col-span-2 min-h-[400px] flex items-center justify-center">
                      <div className="text-center">
                        <Grid3X3 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                        <p className="text-muted-foreground">
                          No variants generated yet
                        </p>
                      </div>
                    </div>
                  ) : (
                    variants.map((variant) => (
                      <Card
                        key={variant.id}
                        className={`cursor-pointer transition-all ${
                          selectedVariantId === variant.id
                            ? "ring-2 ring-primary"
                            : ""
                        }`}
                        onClick={() => { selectVariant(variant.id); }}
                      >
                        <CardContent className="p-4">
                          <div className="aspect-video bg-muted/20 rounded mb-2 flex items-center justify-center">
                            {variant.status === "generating" ? (
                              <Spinner className="h-8 w-8" />
                            ) : variant.finalUrl || variant.previewUrl ? (
                              <img
                                src={variant.finalUrl || variant.previewUrl}
                                alt="Variant"
                                className="w-full h-full object-cover rounded"
                              />
                            ) : (
                              <Image className="h-8 w-8 text-muted-foreground" />
                            )}
                          </div>
                          <div className="flex items-center justify-between">
                            <Badge
                              variant={
                                variant.status === "completed"
                                  ? "default"
                                  : variant.status === "failed"
                                  ? "destructive"
                                  : "secondary"
                              }
                            >
                              {variant.status}
                            </Badge>
                            <div className="flex gap-1">
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-6 w-6"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  const newComparing = comparing.includes(variant.id)
                                    ? comparing.filter((id) => id !== variant.id)
                                    : [...comparing, variant.id];
                                  compareVariants(newComparing);
                                }}
                              >
                                {comparing.includes(variant.id) ? (
                                  <Eye className="h-3 w-3" />
                                ) : (
                                  <EyeOff className="h-3 w-3" />
                                )}
                              </Button>
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-6 w-6"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  removeVariant(variant.id);
                                }}
                              >
                                <X className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))
                  )}
                </div>
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
                    onChange={(e)=>{
                      const t = templates.find(tt=>tt.id===e.target.value);
                      if(t){
                        setPrompt(t.prompt);
                        if(t.constraints) setConstraints(t.constraints);
                        track.templateApplied(resolvedParams.id, t.id);
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
                onChange={(e) => setPrompt(e.target.value)}
                className="min-h-[120px]"
              />
              
              <div className="space-y-2">
                <Label>Output Settings</Label>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">Format</Label>
                    <select
                      className="w-full mt-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={format}
                      onChange={(e) => setFormat(e.target.value)}
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
                      onChange={(e) => setDimensions(e.target.value)}
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
                    min="1"
                    max="8"
                    value={variantCount}
                    onChange={(e) => setVariantCount(Number(e.target.value))}
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
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label className="flex items-center gap-2 mb-2">
                    <Palette className="h-4 w-4" />
                    Color Palette
                  </Label>
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

                <div>
                  <Label className="flex items-center gap-2 mb-2">
                    <Type className="h-4 w-4" />
                    Fonts
                  </Label>
                  <div className="space-y-1">
                    {(constraints.fonts || []).map((font, idx) => (
                      <Badge key={idx} variant="secondary">
                        {font}
                      </Badge>
                    ))}
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
                  <div key={idx} className="flex items-center justify-between">
                    <span className="text-sm truncate">{ref}</span>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-6 w-6"
                      onClick={() => removeReference(ref)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={() => {
                    // TODO: Open file picker
                  }}
                >
                  <Plus className="h-3 w-3 mr-2" />
                  Add Reference
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}
