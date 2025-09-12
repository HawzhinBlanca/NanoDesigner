"use client";

import { useState, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Upload, X, CheckCircle, AlertCircle } from "lucide-react";

interface SimpleFileUploaderProps {
  projectId: string;
  onUploadComplete?: (files: any[]) => void;
  maxFileSize?: number;
  maxNumberOfFiles?: number;
  allowedFileTypes?: string[];
}

interface UploadFile {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  progress: number;
  error?: string;
  response?: any;
}

export function SimpleFileUploader({
  projectId,
  onUploadComplete,
  maxFileSize = 100 * 1024 * 1024, // 100MB default
  maxNumberOfFiles = 10,
  allowedFileTypes = ["image/*", "video/*", ".pdf"],
}: SimpleFileUploaderProps) {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    if (file.size > maxFileSize) {
      return `File size exceeds ${Math.round(maxFileSize / 1024 / 1024)}MB limit`;
    }

    const fileType = file.type;
    const isValidType = allowedFileTypes.some(type => {
      if (type.endsWith('/*')) {
        return fileType.startsWith(type.slice(0, -1));
      }
      return fileType === type || file.name.toLowerCase().endsWith(type);
    });

    if (!isValidType) {
      return `File type not allowed. Allowed types: ${allowedFileTypes.join(', ')}`;
    }

    return null;
  };

  const addFiles = useCallback(async (newFiles: FileList | File[]) => {
    const fileArray = Array.from(newFiles);
    const currentFileCount = files.length;
    
    if (currentFileCount + fileArray.length > maxNumberOfFiles) {
      alert(`Cannot upload more than ${maxNumberOfFiles} files`);
      return;
    }

    const validFiles: UploadFile[] = [];
    
    fileArray.forEach(file => {
      const error = validateFile(file);
      validFiles.push({
        id: `${Date.now()}-${Math.random()}`,
        file,
        status: error ? 'error' : 'pending',
        progress: 0,
        error: error || undefined
      });
    });

    setFiles(prev => [...prev, ...validFiles]);
    
    // Auto-upload valid files after adding them
    setTimeout(async () => {
      for (const file of validFiles) {
        if (file.status === 'pending') {
          try {
            await uploadFile(file);
          } catch (error) {
            console.error('Upload error:', error);
          }
        }
      }
    }, 100);
  }, [files.length, maxNumberOfFiles, maxFileSize, allowedFileTypes]);

  const uploadFile = async (uploadFile: UploadFile) => {
    setFiles(prev => prev.map(f => 
      f.id === uploadFile.id ? { ...f, status: 'uploading', progress: 0 } : f
    ));

    const formData = new FormData();
    formData.append('file', uploadFile.file);
    formData.append('projectId', projectId);

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Save asset to localStorage for persistence
      if (result.asset && typeof window !== 'undefined') {
        try {
          const { demoStorage } = await import('@/lib/demo-storage');
          demoStorage.saveAsset(result.asset);
        } catch (error) {
          console.error('Error saving asset to localStorage:', error);
        }
      }
      
      setFiles(prev => prev.map(f => 
        f.id === uploadFile.id 
          ? { ...f, status: 'completed', progress: 100, response: result }
          : f
      ));

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      setFiles(prev => prev.map(f => 
        f.id === uploadFile.id 
          ? { ...f, status: 'error', error: errorMessage }
          : f
      ));
      throw error;
    }
  };

  const uploadAll = async () => {
    const pendingFiles = files.filter(f => f.status === 'pending');
    const results = [];

    for (const file of pendingFiles) {
      try {
        const result = await uploadFile(file);
        results.push(result);
      } catch (error) {
        console.error('Upload error:', error);
      }
    }

    if (onUploadComplete && results.length > 0) {
      onUploadComplete(results);
    }
  };

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    if (e.dataTransfer.files) {
      addFiles(e.dataTransfer.files);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addFiles(e.target.files);
    }
  };

  const getStatusIcon = (status: UploadFile['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'uploading':
        return <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-500 border-t-transparent" />;
      default:
        return <Upload className="h-4 w-4 text-gray-400" />;
    }
  };

  const pendingCount = files.filter(f => f.status === 'pending').length;
  const completedCount = files.filter(f => f.status === 'completed').length;

  return (
    <div className="w-full space-y-4">
      {/* Drop Zone */}
      <div
        className={`
          border-2 border-dashed rounded-lg p-8 text-center transition-colors
          ${isDragOver 
            ? 'border-blue-500 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
          }
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <Upload className="h-12 w-12 mx-auto text-gray-400 mb-4" />
        <p className="text-lg font-medium text-gray-900 mb-2">
          Drop files here or click to browse
        </p>
        <p className="text-sm text-gray-500 mb-2">
          Images, videos, or PDFs up to {Math.round(maxFileSize / 1024 / 1024)}MB
        </p>
        <p className="text-xs text-blue-600 mb-4">
          Files will be uploaded automatically when selected
        </p>
        <Button
          onClick={() => fileInputRef.current?.click()}
          variant="outline"
        >
          Choose Files
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={allowedFileTypes.join(',')}
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      {/* File List */}
      {files.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">Files ({files.length})</h3>
                {pendingCount > 0 && (
                  <Button onClick={uploadAll} size="sm">
                    Upload All ({pendingCount})
                  </Button>
                )}
              </div>
              
              {files.map(file => (
                <div key={file.id} className="flex items-center gap-3 p-3 border rounded-lg">
                  {getStatusIcon(file.status)}
                  
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{file.file.name}</p>
                    <p className="text-xs text-gray-500">
                      {(file.file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                    {file.error && (
                      <p className="text-xs text-red-500">{file.error}</p>
                    )}
                  </div>

                  {file.status === 'uploading' && (
                    <div className="w-20">
                      <div className="bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${file.progress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeFile(file.id)}
                    disabled={file.status === 'uploading'}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>

            {completedCount > 0 && (
              <div className="mt-4 p-3 bg-green-50 rounded-lg">
                <p className="text-sm text-green-800">
                  ✅ {completedCount} file{completedCount > 1 ? 's' : ''} uploaded successfully
                </p>
                <p className="text-xs text-green-700 mt-1">
                  Files are automatically saved to your project
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
