"use client";

import { useEffect, useState } from "react";
import Uppy from "@uppy/core";
import { Dashboard } from "@uppy/react";
import XHRUpload from "@uppy/xhr-upload";
import { api } from "@/lib/api";

// Note: Uppy CSS should be imported in global CSS or removed if using custom styling

interface FileUploaderProps {
  projectId: string;
  onUploadComplete?: (files: any[]) => void;
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
  const [uppy] = useState(() =>
    new Uppy({
      id: "file-uploader",
      autoProceed: false,
      restrictions: {
        maxFileSize,
        maxNumberOfFiles,
        allowedFileTypes,
      },
    })
      .use(XHRUpload, {
        endpoint: `${process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}/ingest/file`,
        method: "POST",
        formData: true,
        fieldName: "file",
        headers: {},
        getResponseData: (xhr: XMLHttpRequest) => {
          try {
            const data = JSON.parse(xhr.responseText);
            return {
              processed: data.processed,
              qdrant_ids: data.qdrant_ids,
              success: data.processed > 0
            };
          } catch (error) {
            console.error("Failed to parse response:", error);
            return { success: false };
          }
        },
      })
  );

  useEffect(() => {
    // Set project_id as metadata for all files
    uppy.setMeta({ project_id: projectId });
    
    uppy.on("complete", (result) => {
      console.log("Upload complete:", result);
      if (onUploadComplete && result.successful && result.successful.length > 0) {
        onUploadComplete(result.successful);
      }
    });

    uppy.on("error", (error) => {
      console.error("Upload error:", error);
    });

    return () => {
      uppy.destroy();
    };
  }, [uppy, onUploadComplete, projectId]);

  return (
    <div className="w-full">
      <Dashboard
        uppy={uppy}
        width="100%"
        height={400}
        hideProgressDetails={false}
        proudlyDisplayPoweredByUppy={false}
        theme="light"
        note="Images, videos, or PDFs up to 100MB"
      />
    </div>
  );
}