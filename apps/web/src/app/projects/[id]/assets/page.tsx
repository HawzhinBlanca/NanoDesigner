"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { SimpleFileUploader } from "@/components/upload/SimpleFileUploader";
// import { SignedIn, SignedOut, SignInButton } from "@clerk/nextjs"; // Removed for demo mode
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Search, Filter, Grid, List, Download, Trash2, Tag, Folder, Upload, FileImage, FolderOpen, ArrowLeft } from "lucide-react";

interface Asset {
  id: string;
  fileName: string;
  storedFileName: string;
  fileSize: number;
  fileType: string;
  url: string;
  uploadedAt: string;
}

interface Project {
  id: string;
  name: string;
  description: string;
  assets: Asset[];
  createdAt: string;
  updatedAt: string;
}

export default function AssetsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;
  const [project, setProject] = useState<Project | null>(null);
  const [view, setView] = useState<"grid" | "list">("grid");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showUploader, setShowUploader] = useState(false);

  // Fetch project data including assets
  const fetchProject = async () => {
    if (!projectId) return;
    
    setLoading(true);
    try {
      // Try to load from localStorage first (for demo mode)
      if (typeof window !== 'undefined') {
        try {
          const { demoStorage } = await import('@/lib/demo-storage');
          const storedProject = demoStorage.getProject(projectId);
          const storedAssets = demoStorage.getAssetsByProject(projectId);
          
          if (storedProject) {
            setProject({
              ...storedProject,
              assets: storedAssets
            });
            setLoading(false);
            return;
          }
        } catch (storageError) {
          console.error('Error loading from localStorage:', storageError);
        }
      }
      
      // Fallback to API
      const response = await fetch(`/api/projects/${projectId}`);
      if (response.ok) {
        const data = await response.json();
        setProject(data.project);
      }
    } catch (error) {
      console.error('Failed to fetch project:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProject();
  }, [projectId]);

  const handleUploadComplete = (files: { url: string; name: string; size: number; type: string }[]) => {
    // Files uploaded successfully, refresh project data
    fetchProject();
    setShowUploader(false);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
  };

  const filteredAssets = project?.assets?.filter(asset => {
    if (searchQuery) {
      return asset.fileName.toLowerCase().includes(searchQuery.toLowerCase());
    }
    return true;
  }) || [];

  return (
    <main className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={() => router.push(`/projects/${projectId}`)}
            className="hover:bg-gray-100"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{project?.name || 'Loading...'} - Assets</h1>
            <p className="text-gray-600 mt-1">Manage your project assets</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            variant="outline"
            onClick={() => router.push(`/projects/${projectId}`)}
          >
            Back to Project
          </Button>
          <Button onClick={() => setShowUploader(!showUploader)}>
            <Upload className="h-4 w-4 mr-2" />
            {showUploader ? "Hide Uploader" : "Upload Assets"}
          </Button>
        </div>
      </div>

      {showUploader && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Assets</CardTitle>
            <CardDescription>
              Drag and drop files or click to browse. Files will be uploaded to R2 storage.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SimpleFileUploader
              projectId={projectId}
              onUploadComplete={handleUploadComplete}
            />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4 flex-1">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search assets..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Button variant="outline" size="icon">
                <Filter className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant={view === "grid" ? "default" : "ghost"}
                size="icon"
                onClick={() => setView("grid")}
              >
                <Grid className="h-4 w-4" />
              </Button>
              <Button
                variant={view === "list" ? "default" : "ghost"}
                size="icon"
                onClick={() => setView("list")}
              >
                <List className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className={view === "grid" ? "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4" : "space-y-2"}>
              {[...Array(8)].map((_, i) => (
                <Skeleton key={i} className={view === "grid" ? "h-48" : "h-16"} />
              ))}
            </div>
          ) : filteredAssets.length === 0 ? (
            <div className="text-center py-12">
              <div className="mx-auto w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                <FolderOpen className="h-10 w-10 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No assets uploaded yet</h3>
              <p className="text-gray-600 mb-6">Get started by uploading your first asset to this project</p>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => setShowUploader(true)}
              >
                <Upload className="h-4 w-4 mr-2" />
                Upload your first asset
              </Button>
            </div>
          ) : (
            <div className={view === "grid" ? "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4" : "space-y-2"}>
              {filteredAssets.map((asset) => (
                <Card key={asset.id} className={view === "grid" ? "" : "flex items-center justify-between p-4"}>
                  {view === "grid" ? (
                    <>
                      <div className="aspect-square bg-muted rounded-t-lg flex items-center justify-center">
                        {asset.fileType?.startsWith('image/') ? (
                          <img src={asset.url} alt={asset.fileName} className="object-cover w-full h-full rounded-t-lg" />
                        ) : (
                          <div className="text-4xl text-muted-foreground">📄</div>
                        )}
                      </div>
                      <CardContent className="p-4">
                        <p className="font-medium truncate">{asset.fileName}</p>
                        <p className="text-sm text-muted-foreground">{formatFileSize(asset.fileSize)}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {new Date(asset.uploadedAt).toLocaleDateString()}
                        </p>
                      </CardContent>
                    </>
                  ) : (
                    <>
                      <div className="flex items-center gap-4 flex-1">
                        <div className="h-12 w-12 bg-muted rounded flex items-center justify-center">
                          {asset.fileType?.startsWith('image/') ? (
                            <img src={asset.url} alt={asset.fileName} className="object-cover w-full h-full rounded" />
                          ) : (
                            <div className="text-lg">📄</div>
                          )}
                        </div>
                        <div className="flex-1">
                          <p className="font-medium">{asset.fileName}</p>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span>{formatFileSize(asset.fileSize)}</span>
                            <span>{asset.fileType}</span>
                            <span>{new Date(asset.uploadedAt).toLocaleDateString()}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button variant="ghost" size="icon">
                          <Download className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </>
                  )}
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  );
}

