// React Query configuration for API response caching
import { QueryClient, QueryCache, MutationCache } from '@tanstack/react-query';
import { toast } from 'sonner';

// Global error handler for queries
const queryCache = new QueryCache({
  onError: (error, query) => {
    // Only show error toast for user-initiated queries
    if (query.meta?.showErrorToast !== false) {
      toast.error(
        `Something went wrong: ${
          error instanceof Error ? error.message : 'Unknown error'
        }`
      );
    }
  },
  onSuccess: (data, query) => {
    // Show success toast if specified
    if (query.meta?.showSuccessToast) {
      toast.success(query.meta.successMessage || 'Success!');
    }
  },
});

// Global error handler for mutations
const mutationCache = new MutationCache({
  onError: (error, variables, context, mutation) => {
    if (mutation.meta?.showErrorToast !== false) {
      toast.error(
        `Operation failed: ${
          error instanceof Error ? error.message : 'Unknown error'
        }`
      );
    }
  },
  onSuccess: (data, variables, context, mutation) => {
    if (mutation.meta?.showSuccessToast) {
      toast.success(mutation.meta.successMessage || 'Operation successful!');
    }
  },
});

// Create query client with optimized defaults
export const queryClient = new QueryClient({
  queryCache,
  mutationCache,
  defaultOptions: {
    queries: {
      // Data considered fresh for 30 seconds
      staleTime: 30 * 1000,
      // Keep cache for 5 minutes
      gcTime: 5 * 60 * 1000,
      // Retry failed requests 3 times with exponential backoff
      retry: (failureCount, error) => {
        if (failureCount >= 3) return false;
        if (error instanceof Error) {
          // Don't retry on 4xx errors (client errors)
          if (error.message.includes('4')) return false;
        }
        return true;
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      // Refetch on window focus for fresh data
      refetchOnWindowFocus: true,
      // Don't refetch on reconnect by default
      refetchOnReconnect: 'always',
    },
    mutations: {
      // Retry mutations once
      retry: 1,
      retryDelay: 1000,
    },
  },
});

// Prefetch utilities
export const prefetchQuery = async (key: string[], fetcher: () => Promise<any>) => {
  await queryClient.prefetchQuery({
    queryKey: key,
    queryFn: fetcher,
    staleTime: 60 * 1000, // Consider prefetched data fresh for 1 minute
  });
};

// Invalidation utilities
export const invalidateQueries = (key: string[]) => {
  return queryClient.invalidateQueries({ queryKey: key });
};

// Optimistic update utilities
export const setQueryData = <T>(key: string[], data: T) => {
  queryClient.setQueryData(key, data);
};

// Cache management utilities
export const clearCache = () => {
  queryClient.clear();
};

export const removeQueries = (key: string[]) => {
  queryClient.removeQueries({ queryKey: key });
};

// Query key factory for consistent key generation
export const queryKeys = {
  all: ['nanodesigner'] as const,
  projects: () => [...queryKeys.all, 'projects'] as const,
  project: (id: string) => [...queryKeys.projects(), id] as const,
  projectHistory: (id: string) => [...queryKeys.project(id), 'history'] as const,
  projectAssets: (id: string) => [...queryKeys.project(id), 'assets'] as const,
  projectCanon: (id: string) => [...queryKeys.project(id), 'canon'] as const,
  render: (projectId: string, promptHash: string) => 
    [...queryKeys.project(projectId), 'render', promptHash] as const,
  templates: () => [...queryKeys.all, 'templates'] as const,
  template: (id: string) => [...queryKeys.templates(), id] as const,
  user: () => [...queryKeys.all, 'user'] as const,
  userSettings: () => [...queryKeys.user(), 'settings'] as const,
  userProjects: () => [...queryKeys.user(), 'projects'] as const,
};

// Custom hooks for common queries
import { useQuery, useMutation, UseQueryOptions, UseMutationOptions } from '@tanstack/react-query';

// Generic fetch wrapper with error handling
async function fetchWithAuth<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `Request failed with status ${response.status}`);
  }

  return response.json();
}

// Project queries
export function useProject(id: string, options?: UseQueryOptions) {
  return useQuery({
    queryKey: queryKeys.project(id),
    queryFn: () => fetchWithAuth<any>(`/api/projects/${id}`),
    staleTime: 60 * 1000, // 1 minute
    ...options,
  });
}

export function useProjectHistory(id: string, options?: UseQueryOptions) {
  return useQuery({
    queryKey: queryKeys.projectHistory(id),
    queryFn: () => fetchWithAuth<any>(`/api/projects/${id}/history`),
    staleTime: 30 * 1000, // 30 seconds
    ...options,
  });
}

// Render query with intelligent caching
export function useRenderQuery(
  projectId: string,
  prompt: string,
  options?: UseQueryOptions
) {
  // Generate stable hash for prompt to use as cache key
  const promptHash = btoa(prompt).replace(/[^a-zA-Z0-9]/g, '').substring(0, 16);
  
  return useQuery({
    queryKey: queryKeys.render(projectId, promptHash),
    queryFn: () => fetchWithAuth<any>('/api/render', {
      method: 'POST',
      body: JSON.stringify({ projectId, prompt }),
    }),
    // Cache renders for 10 minutes
    staleTime: 10 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    // Don't refetch on window focus for renders
    refetchOnWindowFocus: false,
    ...options,
  });
}

// Mutations with optimistic updates
export function useCreateProject(options?: UseMutationOptions) {
  return useMutation({
    mutationFn: (data: any) => fetchWithAuth<any>('/api/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
    onSuccess: () => {
      // Invalidate project list to refetch
      invalidateQueries(queryKeys.projects());
    },
    ...options,
  });
}

export function useUpdateProject(options?: UseMutationOptions) {
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      fetchWithAuth<any>(`/api/projects/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onMutate: async ({ id, data }) => {
      // Cancel in-flight queries
      await queryClient.cancelQueries({ queryKey: queryKeys.project(id) });
      
      // Snapshot previous value
      const previousProject = queryClient.getQueryData(queryKeys.project(id));
      
      // Optimistically update
      queryClient.setQueryData(queryKeys.project(id), (old: any) => ({
        ...old,
        ...data,
      }));
      
      return { previousProject };
    },
    onError: (err, { id }, context) => {
      // Rollback on error
      if (context?.previousProject) {
        queryClient.setQueryData(queryKeys.project(id), context.previousProject);
      }
    },
    onSettled: (data, error, { id }) => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: queryKeys.project(id) });
    },
    ...options,
  });
}

// Background refetch for stale data
export function useBackgroundRefetch(keys: string[], interval = 60000) {
  useQuery({
    queryKey: [...keys, 'background'],
    queryFn: async () => {
      // Find all matching queries
      const queries = queryClient.getQueryCache().findAll({
        queryKey: keys,
        type: 'active',
      });
      
      // Refetch stale queries
      for (const query of queries) {
        if (query.isStale()) {
          await query.fetch();
        }
      }
      
      return true;
    },
    refetchInterval: interval,
    refetchIntervalInBackground: true,
  });
}