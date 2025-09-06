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
        endpoint: `${process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}/ingest`,
        method: "POST",
        formData: true,
        fieldName: "files",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("auth_token")}`,
        },
        getResponseData: (xhr: XMLHttpRequest) => {
          try {
            const data = JSON.parse(xhr.responseText);
            return {
              url: data.url,
              uploadURL: data.url,
            };
          } catch (error) {
            console.error("Failed to parse response:", error);
            return { url: "" };
          }
        },
      })
  );

  useEffect(() => {
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
  }, [uppy, onUploadComplete]);

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