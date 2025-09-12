// Dynamic imports for code splitting and performance optimization
import dynamic from 'next/dynamic';
import { ComponentType } from 'react';

// Loading component for dynamic imports
const LoadingFallback = () => (
  <div className="flex items-center justify-center p-8">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
  </div>
);

// Heavy components that should be loaded dynamically
export const DynamicComposer = dynamic(
  () => import('@/app/projects/[id]/compose/composer').then(mod => mod.default as ComponentType<any>),
  {
    loading: LoadingFallback,
    ssr: false,
  }
);

export const DynamicCanonEditor = dynamic(
  () => import('@/app/projects/[id]/canon/page').then(mod => mod.default as ComponentType<any>),
  {
    loading: LoadingFallback,
    ssr: false,
  }
);

export const DynamicHistory = dynamic(
  () => import('@/app/projects/[id]/history/page').then(mod => mod.default as ComponentType<any>),
  {
    loading: LoadingFallback,
    ssr: true, // Keep SSR for SEO
  }
);

export const DynamicTemplates = dynamic(
  () => import('@/app/projects/[id]/templates/page').then(mod => mod.default as ComponentType<any>),
  {
    loading: LoadingFallback,
    ssr: true,
  }
);

// UI Components that are not immediately needed
export const DynamicConfetti = dynamic(
  () => import('@/components/ui/celebrations').then(mod => mod.Confetti),
  {
    ssr: false,
  }
);

export const DynamicSuccessModal = dynamic(
  () => import('@/components/ui/celebrations').then(mod => mod.SuccessModal),
  {
    ssr: false,
  }
);

export const DynamicLoadingPoetry = dynamic(
  () => import('@/components/ui/loading-poetry').then(mod => mod.LoadingPoetry),
  {
    loading: () => <div className="animate-pulse">Loading...</div>,
    ssr: false,
  }
);

export const DynamicEmptyState = dynamic(
  () => import('@/components/ui/empty-states').then(mod => mod.EmptyState),
  {
    loading: LoadingFallback,
    ssr: true,
  }
);

// Chart and visualization components
export const DynamicProgressTracker = dynamic(
  () => import('@/components/ui/progress-tracker').then(mod => mod.default as ComponentType<any>),
  {
    loading: LoadingFallback,
    ssr: false,
  }
);

// Modal components
export const DynamicUploadModal = dynamic(
  () => import('@/components/upload/FileUploader').then(mod => mod.default as ComponentType<any>),
  {
    loading: LoadingFallback,
    ssr: false,
  }
);

// Utility function to preload components
export const preloadComponent = (componentName: keyof typeof componentMap) => {
  const component = componentMap[componentName];
  if (component && 'preload' in component) {
    component.preload();
  }
};

// Map of all dynamic components for easy preloading
const componentMap = {
  composer: DynamicComposer,
  canonEditor: DynamicCanonEditor,
  history: DynamicHistory,
  templates: DynamicTemplates,
  confetti: DynamicConfetti,
  successModal: DynamicSuccessModal,
  loadingPoetry: DynamicLoadingPoetry,
  emptyState: DynamicEmptyState,
  progressTracker: DynamicProgressTracker,
  uploadModal: DynamicUploadModal,
};

// Preload critical components on idle
if (typeof window !== 'undefined') {
  if ('requestIdleCallback' in window) {
    requestIdleCallback(() => {
      // Preload critical components
      preloadComponent('composer');
      preloadComponent('loadingPoetry');
    });
  }
}

// Route-based code splitting configuration
export const routeConfig = {
  '/': {
    preload: ['emptyState'],
    prefetch: ['composer'],
  },
  '/dashboard': {
    preload: ['emptyState', 'progressTracker'],
    prefetch: ['composer', 'uploadModal'],
  },
  '/projects/[id]/compose': {
    preload: ['composer', 'loadingPoetry'],
    prefetch: ['successModal', 'confetti'],
  },
  '/projects/[id]/history': {
    preload: ['history'],
    prefetch: ['emptyState'],
  },
  '/projects/[id]/canon': {
    preload: ['canonEditor'],
    prefetch: ['uploadModal'],
  },
  '/projects/[id]/templates': {
    preload: ['templates', 'emptyState'],
    prefetch: [],
  },
};

// Hook to preload components based on current route
export function useRoutePreload(pathname: string) {
  const config = Object.entries(routeConfig).find(([route]) => {
    // Simple route matching (could be enhanced with path-to-regexp)
    const pattern = route.replace(/\[.*?\]/g, '.*');
    return new RegExp(`^${pattern}$`).test(pathname);
  });

  if (config) {
    const [, { preload, prefetch }] = config;
    
    // Preload immediately needed components
    preload.forEach((name) => preloadComponent(name as keyof typeof componentMap));
    
    // Prefetch components that might be needed soon
    if ('requestIdleCallback' in window) {
      requestIdleCallback(() => {
        prefetch.forEach((name) => preloadComponent(name as keyof typeof componentMap));
      });
    }
  }
}