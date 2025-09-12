"use client";

import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  Download, 
  Eye, 
  EyeOff, 
  Check, 
  X, 
  Sparkles,
  Image as ImageIcon,
  Clock,
  AlertCircle
} from "lucide-react";

export interface Variant {
  id: string;
  status: 'generating' | 'completed' | 'failed';
  previewUrl?: string;
  finalUrl?: string;
  progress?: number;
  error?: string;
  estimatedTime?: number;
}

interface VariantGridProps {
  variants: Variant[];
  selectedVariantId?: string;
  comparing: string[];
  onSelectVariant: (id: string) => void;
  onToggleCompare: (id: string) => void;
  onDownload?: (variant: Variant) => void;
  isGenerating: boolean;
}

function VariantCard({ 
  variant, 
  isSelected, 
  isComparing, 
  onSelect, 
  onToggleCompare, 
  onDownload,
  isGenerating 
}: {
  variant: Variant;
  isSelected: boolean;
  isComparing: boolean;
  onSelect: () => void;
  onToggleCompare: () => void;
  onDownload?: () => void;
  isGenerating: boolean;
}) {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);

  const imageUrl = variant.finalUrl || variant.previewUrl;
  const isCompleted = variant.status === 'completed' && imageUrl;
  const isFailed = variant.status === 'failed';
  const isGeneratingVariant = variant.status === 'generating' || (isGenerating && !isCompleted && !isFailed);

  useEffect(() => {
    setImageLoaded(false);
    setImageError(false);
  }, [imageUrl]);

  return (
    <Card className={`
      relative overflow-hidden transition-all duration-300 cursor-pointer group
      ${isSelected ? 'ring-2 ring-blue-500 shadow-lg' : 'hover:shadow-md'}
      ${isComparing ? 'ring-2 ring-purple-500' : ''}
      ${isFailed ? 'border-red-200 bg-red-50' : ''}
    `}>
      <CardContent className="p-0">
        {/* Image Container */}
        <div className="aspect-square relative bg-gray-100">
          {isGeneratingVariant && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-br from-blue-50 to-purple-50">
              <div className="relative mb-4">
                <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                <Sparkles className="w-6 h-6 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-blue-600" />
              </div>
              
              <div className="text-center space-y-2">
                <p className="text-sm font-medium text-blue-900">Generating...</p>
                {variant.progress !== undefined && (
                  <div className="w-32 bg-blue-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${variant.progress}%` }}
                    />
                  </div>
                )}
                {variant.estimatedTime && (
                  <p className="text-xs text-blue-700">
                    ~{variant.estimatedTime}s remaining
                  </p>
                )}
              </div>
            </div>
          )}

          {isFailed && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-red-50">
              <AlertCircle className="w-12 h-12 text-red-500 mb-2" />
              <p className="text-sm font-medium text-red-700 text-center px-4">
                Generation Failed
              </p>
              {variant.error && (
                <p className="text-xs text-red-600 text-center px-4 mt-1">
                  {variant.error}
                </p>
              )}
            </div>
          )}

          {isCompleted && (
            <>
              {!imageLoaded && !imageError && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <Skeleton className="w-full h-full" />
                </div>
              )}
              
              {imageError ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-100">
                  <ImageIcon className="w-12 h-12 text-gray-400 mb-2" />
                  <p className="text-sm text-gray-500">Failed to load</p>
                </div>
              ) : (
                <img
                  src={imageUrl}
                  alt={`Generated variant ${variant.id}`}
                  className={`
                    w-full h-full object-cover transition-all duration-300
                    ${imageLoaded ? 'opacity-100' : 'opacity-0'}
                    ${isSelected ? 'scale-105' : 'group-hover:scale-102'}
                  `}
                  onLoad={() => setImageLoaded(true)}
                  onError={() => setImageError(true)}
                  onClick={onSelect}
                />
              )}
            </>
          )}

          {/* Status Badge */}
          <div className="absolute top-2 left-2">
            {isGeneratingVariant && (
              <Badge variant="secondary" className="bg-blue-100 text-blue-700 text-xs">
                <Clock className="w-3 h-3 mr-1" />
                Generating
              </Badge>
            )}
            {isCompleted && (
              <Badge variant="secondary" className="bg-green-100 text-green-700 text-xs">
                <Check className="w-3 h-3 mr-1" />
                Ready
              </Badge>
            )}
            {isFailed && (
              <Badge variant="destructive" className="text-xs">
                <X className="w-3 h-3 mr-1" />
                Failed
              </Badge>
            )}
          </div>

          {/* Action Buttons */}
          {isCompleted && (
            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              <div className="flex gap-1">
                <Button
                  size="sm"
                  variant="secondary"
                  className="h-8 w-8 p-0 bg-white/90 hover:bg-white"
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleCompare();
                  }}
                >
                  {isComparing ? (
                    <EyeOff className="h-3 w-3" />
                  ) : (
                    <Eye className="h-3 w-3" />
                  )}
                </Button>
                
                {onDownload && (
                  <Button
                    size="sm"
                    variant="secondary"
                    className="h-8 w-8 p-0 bg-white/90 hover:bg-white"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDownload();
                    }}
                  >
                    <Download className="h-3 w-3" />
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* Selection Indicator */}
          {isSelected && (
            <div className="absolute inset-0 border-4 border-blue-500 rounded-lg pointer-events-none">
              <div className="absolute -top-2 -right-2 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                <Check className="w-4 h-4 text-white" />
              </div>
            </div>
          )}

          {/* Compare Indicator */}
          {isComparing && (
            <div className="absolute bottom-2 left-2">
              <Badge variant="secondary" className="bg-purple-100 text-purple-700 text-xs">
                Compare
              </Badge>
            </div>
          )}
        </div>

        {/* Variant Info */}
        <div className="p-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-900">
              Variant {variant.id.slice(-4)}
            </span>
            {variant.finalUrl && (
              <Badge variant="outline" className="text-xs">
                HD Ready
              </Badge>
            )}
          </div>
          
          {isGeneratingVariant && variant.progress !== undefined && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-gray-600">
                <span>Progress</span>
                <span>{Math.round(variant.progress)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-1">
                <div 
                  className="bg-blue-600 h-1 rounded-full transition-all duration-500"
                  style={{ width: `${variant.progress}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function VariantGrid({
  variants,
  selectedVariantId,
  comparing,
  onSelectVariant,
  onToggleCompare,
  onDownload,
  isGenerating
}: VariantGridProps) {
  const completedCount = variants.filter(v => v.status === 'completed').length;
  const failedCount = variants.filter(v => v.status === 'failed').length;
  const generatingCount = variants.filter(v => v.status === 'generating').length;

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <span className="text-gray-600">{completedCount} completed</span>
        </div>
        
        {generatingCount > 0 && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
            <span className="text-gray-600">{generatingCount} generating</span>
          </div>
        )}
        
        {failedCount > 0 && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-red-500 rounded-full"></div>
            <span className="text-gray-600">{failedCount} failed</span>
          </div>
        )}
        
        {comparing.length > 0 && (
          <div className="flex items-center gap-2">
            <Eye className="w-4 h-4 text-purple-600" />
            <span className="text-gray-600">{comparing.length} comparing</span>
          </div>
        )}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {variants.map((variant) => (
          <VariantCard
            key={variant.id}
            variant={variant}
            isSelected={selectedVariantId === variant.id}
            isComparing={comparing.includes(variant.id)}
            onSelect={() => onSelectVariant(variant.id)}
            onToggleCompare={() => onToggleCompare(variant.id)}
            onDownload={onDownload ? () => onDownload(variant) : undefined}
            isGenerating={isGenerating}
          />
        ))}
      </div>

      {/* Empty State */}
      {variants.length === 0 && (
        <div className="text-center py-12">
          <ImageIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No variants yet</h3>
          <p className="text-gray-500">
            Click "Generate" to create your first set of variants
          </p>
        </div>
      )}
    </div>
  );
}
