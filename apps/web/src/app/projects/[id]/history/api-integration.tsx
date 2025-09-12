/**
 * Real API integration for project history - replaces mock data
 */

import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/nextjs';

interface RenderHistory {
  id: string;
  synthId: string;
  name: string;
  status: 'completed' | 'failed' | 'in-progress' | 'queued';
  cost: number;
  timestamp: Date;
  duration: number;
  preview: string;
  metadata: {
    resolution: string;
    format: string;
    quality: string;
    samples: number;
  };
  constraints: {
    maxIterations: number;
    convergenceThreshold: number;
    memoryLimit: string;
    gpuType: string;
  };
  tags: string[];
}

interface HistoryResponse {
  history: RenderHistory[];
  total: number;
  page: number;
  pageSize: number;
}

export function useProjectHistory(projectId: string) {
  const { getToken } = useAuth();
  const [history, setHistory] = useState<RenderHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  const fetchHistory = async (page = 1, pageSize = 12, filters?: any) => {
    try {
      setLoading(true);
      const token = await getToken();
      
      const queryParams = new URLSearchParams({
        page: page.toString(),
        pageSize: pageSize.toString(),
        ...filters
      });

      const response = await fetch(`/api/projects/${projectId}/history?${queryParams}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch history: ${response.statusText}`);
      }

      const data: HistoryResponse = await response.json();
      
      // Convert timestamp strings to Date objects
      const processedHistory = data.history.map(item => ({
        ...item,
        timestamp: new Date(item.timestamp)
      }));

      setHistory(processedHistory);
      setTotal(data.total);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history');
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (projectId) {
      fetchHistory();
    }
  }, [projectId, getToken]);

  return {
    history,
    loading,
    error,
    total,
    refetch: fetchHistory
  };
}

export async function downloadRenderAsset(renderId: string, token: string): Promise<void> {
  try {
    const response = await fetch(`/api/renders/${renderId}/download`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      throw new Error('Download failed');
    }

    // Get filename from response headers
    const contentDisposition = response.headers.get('Content-Disposition');
    const filename = contentDisposition?.match(/filename="(.+)"/)?.[1] || `render-${renderId}.png`;

    // Create download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  } catch (error) {
    throw new Error('Failed to download asset');
  }
}

export async function shareRender(renderId: string, token: string): Promise<string> {
  try {
    const response = await fetch(`/api/renders/${renderId}/share`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error('Share failed');
    }

    const data = await response.json();
    return data.shareUrl;
  } catch (error) {
    throw new Error('Failed to create share link');
  }
}
