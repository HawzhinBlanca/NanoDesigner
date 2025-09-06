"use client";

import React, { useState, useMemo } from 'react';
import { SignedIn, SignedOut, SignInButton } from "@clerk/nextjs";
import { 
  Search, 
  Filter, 
  Grid, 
  List, 
  Download, 
  Share2, 
  Calendar, 
  DollarSign, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  MoreHorizontal,
  Eye,
  Copy
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

// Types
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

// Mock data
const mockHistory: RenderHistory[] = [
  {
    id: '1',
    synthId: 'SYNTH_001_ABC',
    name: 'Protein Structure Analysis v1',
    status: 'completed',
    cost: 12.50,
    timestamp: new Date('2024-01-15T10:30:00'),
    duration: 125000,
    preview: '/api/placeholder/300/200',
    metadata: {
      resolution: '1024x1024',
      format: 'PNG',
      quality: 'High',
      samples: 1000
    },
    constraints: {
      maxIterations: 500,
      convergenceThreshold: 0.001,
      memoryLimit: '8GB',
      gpuType: 'A100'
    },
    tags: ['protein', 'analysis', 'v1']
  },
  {
    id: '2',
    synthId: 'SYNTH_002_DEF',
    name: 'Molecular Dynamics Simulation',
    status: 'failed',
    cost: 8.75,
    timestamp: new Date('2024-01-14T15:45:00'),
    duration: 85000,
    preview: '/api/placeholder/300/200',
    metadata: {
      resolution: '2048x2048',
      format: 'TIFF',
      quality: 'Ultra',
      samples: 2000
    },
    constraints: {
      maxIterations: 1000,
      convergenceThreshold: 0.0001,
      memoryLimit: '16GB',
      gpuType: 'V100'
    },
    tags: ['molecular', 'dynamics', 'failed']
  },
  {
    id: '3',
    synthId: 'SYNTH_003_GHI',
    name: 'Nano Structure Visualization',
    status: 'in-progress',
    cost: 15.25,
    timestamp: new Date('2024-01-16T09:15:00'),
    duration: 45000,
    preview: '/api/placeholder/300/200',
    metadata: {
      resolution: '512x512',
      format: 'PNG',
      quality: 'Medium',
      samples: 500
    },
    constraints: {
      maxIterations: 300,
      convergenceThreshold: 0.01,
      memoryLimit: '4GB',
      gpuType: 'RTX4090'
    },
    tags: ['nano', 'visualization']
  },
  {
    id: '4',
    synthId: 'SYNTH_004_JKL',
    name: 'Crystal Lattice Render',
    status: 'completed',
    cost: 22.80,
    timestamp: new Date('2024-01-13T14:20:00'),
    duration: 180000,
    preview: '/api/placeholder/300/200',
    metadata: {
      resolution: '4096x4096',
      format: 'EXR',
      quality: 'Ultra',
      samples: 5000
    },
    constraints: {
      maxIterations: 800,
      convergenceThreshold: 0.0005,
      memoryLimit: '32GB',
      gpuType: 'A100'
    },
    tags: ['crystal', 'lattice', 'high-res']
  },
  {
    id: '5',
    synthId: 'SYNTH_005_MNO',
    name: 'DNA Helix Animation',
    status: 'queued',
    cost: 18.90,
    timestamp: new Date('2024-01-17T11:00:00'),
    duration: 0,
    preview: '/api/placeholder/300/200',
    metadata: {
      resolution: '1920x1080',
      format: 'MP4',
      quality: 'High',
      samples: 1500
    },
    constraints: {
      maxIterations: 600,
      convergenceThreshold: 0.002,
      memoryLimit: '12GB',
      gpuType: 'RTX4080'
    },
    tags: ['dna', 'animation', 'biology']
  }
];

export default function HistoryPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [costRange, setCostRange] = useState({ min: '', max: '' });
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(12);
  const [sortBy, setSortBy] = useState<'timestamp' | 'cost' | 'duration'>('timestamp');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Filtered and sorted data
  const filteredHistory = useMemo(() => {
    let filtered = mockHistory.filter((item) => {
      const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          item.synthId.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          item.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
      
      const matchesStatus = statusFilter === 'all' || item.status === statusFilter;
      
      const matchesDateRange = !dateRange.start || !dateRange.end || 
                              (item.timestamp >= new Date(dateRange.start) && 
                               item.timestamp <= new Date(dateRange.end));
      
      const matchesCostRange = (!costRange.min || item.cost >= parseFloat(costRange.min)) &&
                              (!costRange.max || item.cost <= parseFloat(costRange.max));
      
      return matchesSearch && matchesStatus && matchesDateRange && matchesCostRange;
    });

    // Sort the filtered results
    filtered.sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case 'timestamp':
          comparison = a.timestamp.getTime() - b.timestamp.getTime();
          break;
        case 'cost':
          comparison = a.cost - b.cost;
          break;
        case 'duration':
          comparison = a.duration - b.duration;
          break;
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });

    return filtered;
  }, [searchQuery, statusFilter, dateRange, costRange, sortBy, sortOrder]);

  // Pagination
  const totalPages = Math.ceil(filteredHistory.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedHistory = filteredHistory.slice(startIndex, startIndex + itemsPerPage);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'failed': return <XCircle className="h-4 w-4 text-red-500" />;
      case 'in-progress': return <AlertCircle className="h-4 w-4 text-blue-500" />;
      case 'queued': return <Clock className="h-4 w-4 text-yellow-500" />;
      default: return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "destructive" | "secondary"> = {
      'completed': 'default',
      'failed': 'destructive',
      'in-progress': 'secondary',
      'queued': 'secondary'
    };
    return (
      <Badge variant={variants[status] || 'secondary'} className="capitalize">
        {getStatusIcon(status)}
        <span className="ml-1">{status.replace('-', ' ')}</span>
      </Badge>
    );
  };

  const formatDuration = (ms: number) => {
    if (ms === 0) return 'N/A';
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  const handleDownload = (item: RenderHistory) => {
    console.log('Downloading:', item.synthId);
  };

  const handleShare = (item: RenderHistory) => {
    navigator.clipboard.writeText(`${window.location.origin}/render/${item.id}`);
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="p-6 space-y-6">
      <SignedOut>
        <p className="text-sm">Please sign in to access History.</p>
        <SignInButton />
      </SignedOut>
      <SignedIn>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Render History</h1>
          <p className="text-muted-foreground">
            Track and manage your render history with detailed metadata and performance metrics
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            variant={viewMode === 'grid' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('grid')}
          >
            <Grid className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === 'list' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('list')}
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Search & Filters
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by name, SynthID, or tags..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
            >
              <option value="all">All Status</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="in-progress">In Progress</option>
              <option value="queued">Queued</option>
            </select>

            {/* Date Range */}
            <div className="flex gap-2">
              <Input
                type="date"
                placeholder="Start date"
                value={dateRange.start}
                onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
              />
              <Input
                type="date"
                placeholder="End date"
                value={dateRange.end}
                onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
              />
            </div>

            {/* Cost Range */}
            <div className="flex gap-2">
              <Input
                type="number"
                placeholder="Min cost"
                value={costRange.min}
                onChange={(e) => setCostRange({ ...costRange, min: e.target.value })}
              />
              <Input
                type="number"
                placeholder="Max cost"
                value={costRange.max}
                onChange={(e) => setCostRange({ ...costRange, max: e.target.value })}
              />
            </div>
          </div>

          {/* Sort Options */}
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium">Sort by:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'timestamp' | 'cost' | 'duration')}
              className="h-8 rounded-md border border-input bg-background px-2 text-sm"
            >
              <option value="timestamp">Date</option>
              <option value="cost">Cost</option>
              <option value="duration">Duration</option>
            </select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            >
              {sortOrder === 'asc' ? '↑' : '↓'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results Summary */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Showing {paginatedHistory.length} of {filteredHistory.length} renders
        </p>
        <div className="text-sm text-muted-foreground">
          Total cost: ${filteredHistory.reduce((sum, item) => sum + item.cost, 0).toFixed(2)}
        </div>
      </div>

      {/* History Grid/List */}
      {viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {paginatedHistory.map((item) => (
            <Card key={item.id} className="group hover:shadow-lg transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-lg">{item.name}</CardTitle>
                    <CardDescription className="flex items-center gap-2">
                      <code className="text-xs bg-muted px-2 py-1 rounded cursor-pointer"
                            onClick={() => handleCopy(item.synthId)}>
                        {item.synthId}
                      </code>
                      <Copy className="h-3 w-3" />
                    </CardDescription>
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" onClick={() => handleShare(item)}>
                      <Share2 className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDownload(item)}>
                      <Download className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              
              <CardContent className="space-y-4">
                {/* Preview */}
                <div className="aspect-video bg-muted rounded-lg flex items-center justify-center">
                  <Eye className="h-8 w-8 text-muted-foreground" />
                </div>

                {/* Status and Timing */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {getStatusBadge(item.status)}
                    <Badge variant="secondary" className="text-xs" title="SynthID policy">
                      verified_by: declared
                    </Badge>
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {formatDuration(item.duration)}
                  </span>
                </div>

                {/* Metadata */}
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Cost:</span>
                    <span className="font-medium">${item.cost.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Resolution:</span>
                    <span>{item.metadata.resolution}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Quality:</span>
                    <span>{item.metadata.quality}</span>
                  </div>
                </div>

                {/* Tags */}
                <div className="flex flex-wrap gap-1">
                  {item.tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>

                {/* Timestamp */}
                <div className="text-xs text-muted-foreground border-t pt-2">
                  {item.timestamp.toLocaleDateString()} at {item.timestamp.toLocaleTimeString()}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        /* List View */
        <div className="space-y-4">
          {paginatedHistory.map((item) => (
            <Card key={item.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="grid grid-cols-12 gap-4 items-center">
                  <div className="col-span-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-muted rounded-lg flex items-center justify-center">
                        <Eye className="h-5 w-5 text-muted-foreground" />
                      </div>
                      <div>
                        <h3 className="font-medium">{item.name}</h3>
                        <code className="text-xs text-muted-foreground cursor-pointer"
                              onClick={() => handleCopy(item.synthId)}>
                          {item.synthId}
                        </code>
                      </div>
                    </div>
                  </div>
                  
                  <div className="col-span-2">
                    {getStatusBadge(item.status)}
                  </div>
                  
                  <div className="col-span-2 text-sm">
                    <div className="font-medium">${item.cost.toFixed(2)}</div>
                    <div className="text-muted-foreground">{formatDuration(item.duration)}</div>
                  </div>
                  
                  <div className="col-span-2 text-sm text-muted-foreground">
                    <div>{item.timestamp.toLocaleDateString()}</div>
                    <div>{item.timestamp.toLocaleTimeString()}</div>
                  </div>
                  
                  <div className="col-span-2 flex justify-end gap-2">
                    <Button variant="ghost" size="sm" onClick={() => handleShare(item)}>
                      <Share2 className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDownload(item)}>
                      <Download className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          
          <div className="flex gap-1">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <Button
                key={page}
                variant={currentPage === page ? "default" : "outline"}
                size="sm"
                onClick={() => setCurrentPage(page)}
              >
                {page}
              </Button>
            ))}
          </div>
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Empty State */}
      {filteredHistory.length === 0 && (
        <div className="text-center py-12">
          <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">No renders found</h3>
          <p className="text-muted-foreground mb-4">
            Try adjusting your search criteria or filters
          </p>
          <Button variant="outline" onClick={() => {
            setSearchQuery('');
            setStatusFilter('all');
            setDateRange({ start: '', end: '' });
            setCostRange({ min: '', max: '' });
          }}>
            Clear filters
          </Button>
        </div>
      )}
    </SignedIn>
    </div>
  );
}