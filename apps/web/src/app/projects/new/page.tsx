"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import { ArrowLeft, Plus, Sparkles, AlertCircle } from "lucide-react";
import Link from "next/link";
import { sanitizeInput, VALIDATION_LIMITS } from "@/lib/validation/schemas";

export default function NewProjectPage() {
  const router = useRouter();
  
  // Simple form state
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    industry: "",
    brandGuidelines: ""
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleInputChange = (field: string, value: string) => {
    const sanitizedValue = sanitizeInput(value, field === 'name' ? 255 : field === 'description' ? 1000 : field === 'industry' ? 100 : 2000);
    setFormData(prev => ({
      ...prev,
      [field]: sanitizedValue
    }));
    
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
    if (submitError) {
      setSubmitError(null);
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.name.trim()) {
      newErrors.name = 'Project name is required';
    } else if (formData.name.length > 255) {
      newErrors.name = 'Project name must be less than 255 characters';
    }
    
    if (formData.description.length > 1000) {
      newErrors.description = 'Description must be less than 1000 characters';
    }
    
    if (formData.industry.length > 100) {
      newErrors.industry = 'Industry must be less than 100 characters';
    }
    
    if (formData.brandGuidelines.length > 2000) {
      newErrors.brandGuidelines = 'Brand guidelines must be less than 2000 characters';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleCreateProject = async () => {
    // Validate form before submission
    if (!validateForm()) {
      setSubmitError('Please fix the errors above before submitting.');
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);
    
    try {
      // Call demo API endpoint that works without database
      const response = await fetch('/api/projects/demo', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create project');
      }
      
      const { project } = await response.json();
      
      // Save to localStorage for persistence
      if (typeof window !== 'undefined') {
        const { demoStorage } = await import('@/lib/demo-storage');
        demoStorage.saveProject(project);
      }
      
      // Redirect to the new project's assets page
      router.push(`/projects/${project.id}/assets`);
    } catch (error) {
      console.error("Failed to create project:", error);
      setSubmitError(
        error instanceof Error ? error.message : 'Failed to create project. Please try again.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const isFormValid = formData.name.trim().length > 0 && Object.keys(errors).length === 0;

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-2xl mx-auto px-4">
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
            <h1 className="text-3xl font-bold text-gray-900">Create New Project</h1>
          </div>
          
          <p className="text-gray-600">
            Set up a new design project with your brand guidelines and preferences.
          </p>
        </div>

        {/* Form */}
        <Card>
          <CardHeader>
            <CardTitle>Project Details</CardTitle>
            <CardDescription>
              Provide basic information about your project to get started.
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-6">
            {/* Project Name */}
            <div className="space-y-2">
              <Label htmlFor="name">Project Name *</Label>
              <Input
                id="name"
                placeholder="e.g., Brand Refresh 2024, Product Launch Campaign"
                value={formData.name}
                onChange={(e) => handleInputChange("name", e.target.value)}
                className={`w-full ${
                  errors.name ? 'border-red-500 focus:border-red-500' : ''
                }`}
                aria-invalid={!!errors.name}
                aria-describedby={errors.name ? "name-error" : undefined}
              />
              {errors.name && (
                <div id="name-error" className="flex items-center gap-1 text-sm text-red-600">
                  <AlertCircle className="h-4 w-4" />
                  {errors.name}
                </div>
              )}
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Brief description of your project goals and requirements..."
                value={formData.description}
                onChange={(e) => handleInputChange("description", e.target.value)}
                rows={3}
                className={`w-full ${
                  errors.description ? 'border-red-500 focus:border-red-500' : ''
                }`}
                aria-invalid={!!errors.description}
                aria-describedby={errors.description ? "description-error" : undefined}
              />
              {errors.description && (
                <div id="description-error" className="flex items-center gap-1 text-sm text-red-600">
                  <AlertCircle className="h-4 w-4" />
                  {errors.description}
                </div>
              )}
            </div>

            {/* Industry */}
            <div className="space-y-2">
              <Label htmlFor="industry">Industry</Label>
              <Input
                id="industry"
                placeholder="e.g., Technology, Healthcare, Finance, Retail"
                value={formData.industry}
                onChange={(e) => handleInputChange("industry", e.target.value)}
                className={`w-full ${
                  errors.industry ? 'border-red-500 focus:border-red-500' : ''
                }`}
                aria-invalid={!!errors.industry}
                aria-describedby={errors.industry ? "industry-error" : undefined}
              />
              {errors.industry && (
                <div id="industry-error" className="flex items-center gap-1 text-sm text-red-600">
                  <AlertCircle className="h-4 w-4" />
                  {errors.industry}
                </div>
              )}
            </div>

            {/* Brand Guidelines */}
            <div className="space-y-2">
              <Label htmlFor="guidelines">Brand Guidelines</Label>
              <Textarea
                id="guidelines"
                placeholder="Any specific brand requirements, color preferences, style guidelines, or constraints..."
                value={formData.brandGuidelines}
                onChange={(e) => handleInputChange("brandGuidelines", e.target.value)}
                rows={4}
                className={`w-full ${
                  errors.brandGuidelines ? 'border-red-500 focus:border-red-500' : ''
                }`}
                aria-invalid={!!errors.brandGuidelines}
                aria-describedby={errors.brandGuidelines ? "guidelines-error" : undefined}
              />
              {errors.brandGuidelines && (
                <div id="guidelines-error" className="flex items-center gap-1 text-sm text-red-600">
                  <AlertCircle className="h-4 w-4" />
                  {errors.brandGuidelines}
                </div>
              )}
            </div>

            {/* Form-level Error */}
            {submitError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-center gap-2 text-red-800">
                  <AlertCircle className="h-4 w-4" />
                  <span className="font-medium">Error</span>
                </div>
                <p className="text-red-700 text-sm mt-1">{submitError}</p>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-4">
              <Button
                onClick={handleCreateProject}
                disabled={!isFormValid || isSubmitting}
                className="flex-1"
              >
                {isSubmitting ? (
                  <>
                    <Spinner className="w-4 h-4 mr-2" />
                    Creating Project...
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Project
                  </>
                )}
              </Button>
              
              <Button
                variant="outline"
                onClick={() => router.push("/dashboard")}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Next Steps Preview */}
        <Card className="mt-6 bg-blue-50 border-blue-200">
          <CardContent className="pt-6">
            <h3 className="font-semibold text-blue-900 mb-2">What happens next?</h3>
            <div className="space-y-2 text-sm text-blue-800">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-blue-600 rounded-full"></div>
                <span>Upload your brand assets and reference materials</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-blue-600 rounded-full"></div>
                <span>Set up your brand canon (colors, fonts, voice)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-blue-600 rounded-full"></div>
                <span>Start generating designs with AI</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
