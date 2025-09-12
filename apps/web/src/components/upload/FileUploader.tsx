"use client";

import { SimpleFileUploader } from "./SimpleFileUploader";

interface FileUploaderProps {
  projectId: string;
  onUploadComplete?: (files: { url: string; name: string; size: number; type: string }[]) => void;
  maxFileSize?: number;
  maxNumberOfFiles?: number;
  allowedFileTypes?: string[];
}

export function FileUploader({
  projectId,
  onUploadComplete,
  maxFileSize = 100 * 1024 * 1024, // 100MB default
  maxNumberOfFiles = 10,
  allowedFileTypes = ["image/*", "video/*", ".pdf"],
}: FileUploaderProps) {
  return (
    <SimpleFileUploader
      projectId={projectId}
      onUploadComplete={onUploadComplete}
      maxFileSize={maxFileSize}
      maxNumberOfFiles={maxNumberOfFiles}
      allowedFileTypes={allowedFileTypes}
    />
  );
}