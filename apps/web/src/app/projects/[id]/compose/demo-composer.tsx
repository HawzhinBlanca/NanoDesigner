"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { useCanonStore } from "@/stores/useCanonStore";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Sparkles, Download, Copy, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { apiClient, RenderRequest } from "@/lib/api-client";

export default function DemoComposer({ projectId }: { projectId: string }) {
  const [prompt, setPrompt] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedImage, setGeneratedImage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError("Please enter a prompt");
      return;
    }

    setIsGenerating(true);
    setError(null);

    try {
      // Prepare the render request
      const renderRequest: RenderRequest = {
        project_id: projectId || "demo",
        prompts: {
          task: "create",
          instruction: prompt,
          references: []
        },
        outputs: {
          count: 1,
          format: "png",
          dimensions: "1024x1024"
        },
        constraints: currentCanon ? {
          palette_hex: [
            currentCanon.palette.primary,
            currentCanon.palette.secondary,
            currentCanon.palette.accent,
            ...currentCanon.palette.custom
          ].filter(Boolean),
          fonts: currentCanon.typography.fonts,
          logoSafeZone: 20.0
        } : null
      };

      // Call real backend API
      const response = await apiClient.render(renderRequest);
      
      // Set the first generated image
      if (response.assets && response.assets.length > 0) {
        setGeneratedImage(response.assets[0].url);
        
        // Save generated image to localStorage for persistence
        if (typeof window !== 'undefined') {
          try {
            const { demoStorage } = await import('@/lib/demo-storage');
            const generatedImageData = {
              id: `image-${Date.now()}`,
              projectId: projectId,
              prompt: prompt,
              imageUrl: response.assets[0].url,
              createdAt: new Date().toISOString(),
            };
            demoStorage.saveGeneratedImage(generatedImageData);
          } catch (storageError) {
            console.error('Error saving generated image to localStorage:', storageError);
          }
        }
      } else {
        throw new Error('No images generated');
      }
    } catch (err: any) {
      console.error('Generation error:', err);
      setError(err.message || "Failed to generate image. Please try again.");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        {/* Header */}
        <div className="mb-8">
          <Link 
            href="/dashboard" 
            className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Dashboard
          </Link>
          
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Sparkles className="h-6 w-6 text-blue-600" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900">AI Image Composer</h1>
          </div>
          
          <p className="text-gray-600">
            Generate stunning images with AI for project {projectId}
          </p>
          {currentCanon && (
            <p className="text-sm text-green-600 mt-2">
              ✓ Brand Canon loaded - constraints will be applied automatically
            </p>
          )}
          {canonError && (
            <p className="text-sm text-red-600 mt-2">
              ⚠ Canon error: {canonError}
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Input Section */}
          <Card>
            <CardHeader>
              <CardTitle>Compose Your Image</CardTitle>
              <CardDescription>
                Describe what you want to create
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="prompt">Image Prompt</Label>
                <Textarea
                  id="prompt"
                  placeholder="A futuristic city at sunset with flying cars..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  rows={4}
                  className="w-full"
                />
              </div>

              <div className="space-y-2">
                <Label>Quick Styles</Label>
                <div className="flex flex-wrap gap-2">
                  {["Photorealistic", "Artistic", "3D Render", "Minimalist"].map((style) => (
                    <Button
                      key={style}
                      variant="outline"
                      size="sm"
                      onClick={() => setPrompt(prev => prev + ` ${style.toLowerCase()} style`)}
                    >
                      {style}
                    </Button>
                  ))}
                </div>
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {error}
                </div>
              )}

              <Button
                onClick={handleGenerate}
                disabled={isGenerating || !prompt.trim()}
                className="w-full"
              >
                {isGenerating ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Generate Image
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Output Section */}
          <Card>
            <CardHeader>
              <CardTitle>Generated Image</CardTitle>
              <CardDescription>
                Your AI-generated image will appear here
              </CardDescription>
            </CardHeader>
            <CardContent>
              {generatedImage ? (
                <div className="space-y-4">
                  <div className="relative aspect-square bg-gray-100 rounded-lg overflow-hidden">
                    <img
                      src={generatedImage}
                      alt="Generated image"
                      className="w-full h-full object-cover"
                    />
                  </div>
                  
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      className="flex-1"
                      onClick={() => navigator.clipboard.writeText(generatedImage)}
                    >
                      <Copy className="h-4 w-4 mr-2" />
                      Copy URL
                    </Button>
                    <Button
                      variant="default"
                      className="flex-1"
                      onClick={() => window.open(generatedImage, '_blank')}
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Download
                    </Button>
                  </div>

                  <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm text-green-800">
                      ✅ Image generated successfully!
                    </p>
                    <p className="text-xs text-green-700 mt-1">
                      Powered by AI image generation API
                    </p>
                  </div>
                </div>
              ) : (
                <div className="aspect-square bg-gray-100 rounded-lg flex items-center justify-center">
                  <div className="text-center">
                    <Sparkles className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                    <p className="text-gray-500">No image generated yet</p>
                    <p className="text-sm text-gray-400 mt-1">Enter a prompt and click generate</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Info Section */}
        <Card className="mt-8 bg-blue-50 border-blue-200">
          <CardContent className="pt-6">
            <h3 className="font-semibold text-blue-900 mb-2">Real Image Generation</h3>
            <p className="text-sm text-blue-800">
              This demo uses Unsplash to fetch real, high-quality images based on your prompts. In production, this would connect to AI services like DALL-E 3, Stable Diffusion XL, or Midjourney for true AI-generated images.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}