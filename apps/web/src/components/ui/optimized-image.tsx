"use client";

import Image from 'next/image';
import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

interface OptimizedImageProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  priority?: boolean;
  className?: string;
  quality?: number;
  fill?: boolean;
  sizes?: string;
  onLoad?: () => void;
  aspectRatio?: string;
}

// Generate blur data URL for placeholder
function getBlurDataURL(width = 10, height = 10): string {
  const canvas = typeof document !== 'undefined' ? document.createElement('canvas') : null;
  if (!canvas) return '';
  
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) return '';
  
  // Create gradient blur effect
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, 'rgba(200, 200, 200, 0.5)');
  gradient.addColorStop(1, 'rgba(150, 150, 150, 0.5)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);
  
  return canvas.toDataURL();
}

export function OptimizedImage({
  src,
  alt,
  width = 1920,
  height = 1080,
  priority = false,
  className,
  quality = 85,
  fill = false,
  sizes,
  onLoad,
  aspectRatio = '16/9',
}: OptimizedImageProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [blurDataURL, setBlurDataURL] = useState('');

  useEffect(() => {
    setBlurDataURL(getBlurDataURL());
  }, []);

  const handleLoad = () => {
    setIsLoading(false);
    onLoad?.();
  };

  const handleError = () => {
    setError(true);
    setIsLoading(false);
  };

  // Default sizes for responsive images
  const defaultSizes = fill
    ? '(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw'
    : undefined;

  if (error) {
    return (
      <div 
        className={cn(
          "flex items-center justify-center bg-secondary rounded-lg",
          className
        )}
        style={{ aspectRatio }}
      >
        <div className="text-center p-4">
          <svg
            className="w-12 h-12 mx-auto text-muted-foreground mb-2"
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
          <p className="text-sm text-muted-foreground">Failed to load image</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("relative overflow-hidden", className)}>
      {fill ? (
        <Image
          src={src}
          alt={alt}
          fill
          quality={quality}
          priority={priority}
          sizes={sizes || defaultSizes}
          placeholder={blurDataURL ? 'blur' : 'empty'}
          blurDataURL={blurDataURL}
          onLoad={handleLoad}
          onError={handleError}
          className={cn(
            "object-cover transition-all duration-500",
            isLoading ? "scale-105 blur-sm" : "scale-100 blur-0"
          )}
        />
      ) : (
        <Image
          src={src}
          alt={alt}
          width={width}
          height={height}
          quality={quality}
          priority={priority}
          sizes={sizes}
          placeholder={blurDataURL ? 'blur' : 'empty'}
          blurDataURL={blurDataURL}
          onLoad={handleLoad}
          onError={handleError}
          className={cn(
            "transition-all duration-500",
            isLoading ? "scale-105 blur-sm" : "scale-100 blur-0"
          )}
        />
      )}
      
      {/* Loading skeleton overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer" />
      )}
    </div>
  );
}

// Gallery component with optimized images
export function OptimizedImageGallery({ 
  images,
  columns = 3,
  gap = 4,
  priority = false,
}: {
  images: Array<{ src: string; alt: string; width?: number; height?: number }>;
  columns?: number;
  gap?: number;
  priority?: boolean;
}) {
  return (
    <div 
      className={`grid gap-${gap}`}
      style={{
        gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
      }}
    >
      {images.map((image, index) => (
        <OptimizedImage
          key={image.src}
          src={image.src}
          alt={image.alt}
          width={image.width}
          height={image.height}
          priority={priority && index < 4} // Prioritize first 4 images
          className="rounded-lg overflow-hidden"
          sizes={`(max-width: 768px) 100vw, ${Math.floor(100 / columns)}vw`}
        />
      ))}
    </div>
  );
}

// Lightbox component for full-size viewing
export function ImageLightbox({
  src,
  alt,
  isOpen,
  onClose,
}: {
  src: string;
  alt: string;
  isOpen: boolean;
  onClose: () => void;
}) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }
    
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm"
      onClick={onClose}
    >
      <button
        className="absolute top-4 right-4 text-white hover:text-gray-300 transition-colors"
        onClick={onClose}
        aria-label="Close lightbox"
      >
        <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
      
      <div className="relative max-w-[90vw] max-h-[90vh]" onClick={(e) => e.stopPropagation()}>
        <OptimizedImage
          src={src}
          alt={alt}
          width={1920}
          height={1080}
          priority
          quality={95}
          className="rounded-lg"
        />
      </div>
    </div>
  );
}

// Progressive image loading with multiple resolutions
export function ProgressiveImage({
  src,
  alt,
  thumbnailSrc,
  className,
}: {
  src: string;
  alt: string;
  thumbnailSrc?: string;
  className?: string;
}) {
  const [currentSrc, setCurrentSrc] = useState(thumbnailSrc || src);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!thumbnailSrc) return;

    const img = new window.Image();
    img.src = src;
    img.onload = () => {
      setCurrentSrc(src);
      setIsLoading(false);
    };
  }, [src, thumbnailSrc]);

  return (
    <div className={cn("relative", className)}>
      <Image
        src={currentSrc}
        alt={alt}
        fill
        className={cn(
          "object-cover transition-all duration-700",
          isLoading && thumbnailSrc ? "blur-lg scale-105" : "blur-0 scale-100"
        )}
      />
    </div>
  );
}